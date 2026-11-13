"""socketbin_core.py - pure-Python part of the SocketBin Fusion script (no adsk imports).

Reads the socket list (.csv or .xlsx, standard library only), plans the Gridfinity bin (row packing,
footprint search, height, row/hole/label positions), and writes the 2-part coloured 3MF for Orca.  Everything here is in millimetres.
Kept free of Fusion imports so it can be unit-tested with plain Python.
"""
import csv, io, math, os, re, zipfile
import xml.etree.ElementTree as ET

PITCH = 42.0      # Gridfinity grid pitch
CLEAR = 0.5       # total outer clearance (bin is pitch*n - 0.5)
UNIT = 7.0        # Gridfinity height unit
BASE = 5.0        # Gridfinity base (feet) height

# Single source of truth for the SocketBin version.
VERSION = "1.3.0"

# SocketBin default TOTAL height (bottom of the feet to the top face, incl. the 5 mm base, no lip).
# height_units (explicit Gridfinity units) overrides it; height_mm=0 means auto from the deepest hole.
DEFAULT_HEIGHT_MM = 40.0
# Hard cap on any socket hole depth, mm (0 = no cap). Applied on top of the height-based limit.
DEFAULT_MAX_DEPTH = 32.0

# Adaptive walls (default on): shrink per-row webs only as much as needed.
# Interior webs may go down to MIN_WEB_FLOOR (~3 perimeters at 0.4 mm nozzle).
# Outer walls (pocket edge to usable rail edge) never go below MIN_OUTER_WALL.
ADAPTIVE_WALLS = True
MIN_WEB_FLOOR = 1.2
MIN_OUTER_WALL = 1.5

DEFAULTS = dict(min_web=2.85, floor_min=3.0, height_units=0, height_mm=DEFAULT_HEIGHT_MM, max_depth=DEFAULT_MAX_DEPTH, grid_x=0, grid_y=0,
                min_grid_x=1, max_grid_x=6, min_grid_y=1, max_grid_y=3,
                label_height=5.0, label_gap=2.0, inlay_depth=1.0, floor_inlay=0.6,
                printer_x=270.0, printer_y=270.0, printer_z=270.0,
                adaptive_walls=ADAPTIVE_WALLS,
                min_web_floor=MIN_WEB_FLOOR,
                min_outer_wall=MIN_OUTER_WALL)

NS_MAIN = "{http://schemas.openxmlformats.org/spreadsheetml/2006/main}"
NS_REL_DOC = "{http://schemas.openxmlformats.org/officeDocument/2006/relationships}"
NS_PKG_REL = "{http://schemas.openxmlformats.org/package/2006/relationships}"


class ListError(Exception):
    """A problem with the socket list the user should fix (message is shown as-is)."""


def num(v):
    """'0.####' number formatting."""
    s = ("%.4f" % float(v)).rstrip("0").rstrip(".")
    return "0" if s in ("-0", "") else s


# ------------------------------------------------------------------ reading the list
def _inner_text(el):
    return "".join(t.text or "" for t in el.iter(NS_MAIN + "t"))


def read_xlsx(path):
    """First worksheet (workbook order) of an .xlsx as a list of {header: text} dicts."""
    with zipfile.ZipFile(path) as z:
        names = set(z.namelist())
        shared = []
        if "xl/sharedStrings.xml" in names:
            sst = ET.fromstring(z.read("xl/sharedStrings.xml"))
            shared = [_inner_text(si) for si in sst.findall(NS_MAIN + "si")]
        wb = ET.fromstring(z.read("xl/workbook.xml"))
        sheets = wb.find(NS_MAIN + "sheets")
        if sheets is None or len(sheets) == 0:
            raise ListError("'%s' has no worksheets" % path)
        rid = sheets[0].get(NS_REL_DOC + "id")
        target = None
        if "xl/_rels/workbook.xml.rels" in names and rid:
            rels = ET.fromstring(z.read("xl/_rels/workbook.xml.rels"))
            for r in rels.findall(NS_PKG_REL + "Relationship"):
                if r.get("Id") == rid:
                    target = r.get("Target")
        if not target:
            target = "worksheets/sheet1.xml"
        target = target.lstrip("/")
        if not target.startswith("xl/"):
            target = "xl/" + target
        ws = ET.fromstring(z.read(target))
    rows = []
    sd = ws.find(NS_MAIN + "sheetData")
    for r in (sd if sd is not None else []):
        if r.tag != NS_MAIN + "row":
            continue
        cells = {}
        for c in r.findall(NS_MAIN + "c"):
            col = re.sub(r"\d", "", c.get("r", ""))
            t = c.get("t")
            v = c.find(NS_MAIN + "v")
            if t == "s":
                val = shared[int(v.text)] if v is not None and v.text else ""
            elif t == "inlineStr":
                isel = c.find(NS_MAIN + "is")
                val = _inner_text(isel) if isel is not None else ""
            else:
                val = v.text if v is not None and v.text is not None else ""
            cells[col] = val
        rows.append(cells)
    if not rows:
        return []
    hdr = rows[0]
    out = []
    for cells in rows[1:]:
        out.append({str(hdr[k]): cells.get(k, "") for k in hdr})
    return out


def read_csv(path):
    """CSV with a header row; leading blank/# lines are skipped ('# name: X' sets the bin name)."""
    with open(path, "r", encoding="utf-8-sig", newline="") as f:
        lines = f.read().splitlines()
    pre = ""
    h = 0
    while h < len(lines) and (lines[h].strip() == "" or lines[h].lstrip().startswith("#") or lines[h].lstrip().startswith('"#')):
        t = lines[h].strip().strip('"').rstrip(",;").strip('"').strip()
        m = re.match(r"^#\s*name\s*[:=]\s*(.+)$", t, re.I)
        if m:
            pre = m.group(1).strip()
        h += 1
    rows = list(csv.DictReader(io.StringIO("\n".join(lines[h:])))) if h < len(lines) else []
    return rows, pre


def col(row, names):
    for k, v in row.items():
        kk = re.sub(r"[^a-zA-Z_]", "", str(k or "")).lower()
        if kk in names:
            return "" if v is None else str(v)
    return ""


def _float(t):
    try:
        v = float(t.strip())
        return v if math.isfinite(v) else None
    except (ValueError, AttributeError):
        return None


D_NAMES = ("hole_diameter_mm", "diameter", "hole_diameter", "diameter_mm")
Z_NAMES = ("hole_depth_mm", "depth", "hole_depth", "depth_mm")
R_NAMES = ("row", "row_hint")


def read_list(path):
    """Returns (sockets, list_name). Each socket: dict(i, label, d, depth, hint)."""
    low = path.lower()
    if low.endswith(".xls"):
        raise ListError("'%s' is an old-format Excel .xls file. Open it in Excel and use File > Save As > "
                        "Excel Workbook (*.xlsx), or save as CSV, then run again." % path)
    if low.endswith(".xlsx"):
        raw, pre = read_xlsx(path), ""
    else:
        raw, pre = read_csv(path)
    socks, name, idx = [], pre, 0
    for r in raw:
        label = col(r, ("label",)).strip()
        dtxt = col(r, D_NAMES).strip()
        if not label and not dtxt:
            continue
        m = re.match(r"^#\s*name\s*[:=]\s*(.+)$", label, re.I)
        if m:
            name = m.group(1).strip(); continue
        m = re.match(r"^name\s*[:=]\s*(.+)$", label, re.I)
        if m and not dtxt:
            name = m.group(1).strip(); continue
        if label.startswith("#"):
            continue
        ztxt = col(r, Z_NAMES).strip()
        rtxt = col(r, R_NAMES).strip()
        idx += 1
        d, z = _float(dtxt), _float(ztxt)
        if d is None or d <= 0:
            raise ListError("Line %d: '%s' has no valid hole_diameter_mm ('%s')" % (idx, label, dtxt))
        if z is None or z <= 0:
            raise ListError("Line %d: '%s' has no valid hole_depth_mm ('%s')" % (idx, label, ztxt))
        hint = 0
        if rtxt:
            hv = _float(rtxt)
            if hv is None:
                raise ListError("Line %d: '%s' has an invalid row ('%s')" % (idx, label, rtxt))
            hint = int(round(hv))   # round to the nearest whole row
        # Excel numeric labels come back as e.g. "15" or "5.5"; tidy "15.0" -> "15"
        if re.match(r"^-?\d+\.0+$", label):
            label = label.split(".")[0]
        socks.append(dict(i=idx, label=label.replace("'", "\u2019"), d=d, depth=z, hint=hint))
    if not socks:
        raise ListError("No sockets found in %s" % path)
    return socks, name


def clean_name(n):
    n = re.sub(r'[\\/:*?"<>|\x00-\x1F]', "-", n).strip().rstrip(".").strip()
    if re.match(r"^(CON|PRN|AUX|NUL|COM[1-9]|LPT[1-9])(\..*)?$", n, re.I):
        n = "_" + n
    return n.replace("[", "(").replace("]", ")")


def default_name(path, list_name):
    if list_name:
        return list_name
    base = os.path.splitext(os.path.basename(path))[0]
    return "Socket Bin" if re.match(r"^sockets?$", base, re.I) else base


# ------------------------------------------------------------------ planning
def _need_length(lst, o):
    """Length needed at the TARGET min_web (equal outers + interiors)."""
    return sum(k["d"] for k in lst) + (len(lst) + 1) * o["min_web"]


def _min_gap_budget(n_items, o):
    """Smallest total wall budget that may still pack n_items (adaptive floors or target)."""
    if n_items <= 0:
        return 0.0
    if o.get("adaptive_walls", ADAPTIVE_WALLS):
        outer = o.get("min_outer_wall", MIN_OUTER_WALL)
        interior = o.get("min_web_floor", MIN_WEB_FLOOR)
        if n_items == 1:
            return 2.0 * outer
        return 2.0 * outer + (n_items - 1) * interior
    return (n_items + 1) * o["min_web"]


def _min_need_length(lst, o):
    return sum(k["d"] for k in lst) + _min_gap_budget(len(lst), o)


def _distribute_gaps(n_gaps, budget, o):
    """Return (gaps[list len n_gaps], adapted[bool]). gaps[0]/gaps[-1] are outers.
    Raises ValueError if the budget is below the printable floors."""
    if n_gaps <= 0:
        return [], False
    target = o["min_web"]
    equal = budget / n_gaps
    if equal + 1e-9 >= target:
        return [equal] * n_gaps, False
    if not o.get("adaptive_walls", ADAPTIVE_WALLS):
        raise ValueError("walls below target min_web and adaptive_walls is off")
    outer_f = o.get("min_outer_wall", MIN_OUTER_WALL)
    int_f = o.get("min_web_floor", MIN_WEB_FLOOR)
    if equal + 1e-9 >= outer_f:
        # Even spacing still respects the outer-wall floor (and therefore interior floor).
        return [equal] * n_gaps, True
    if n_gaps == 1:
        if budget + 1e-9 < outer_f:
            raise ValueError("outer wall below floor")
        return [budget], True
    if n_gaps == 2:
        half = budget / 2.0
        if half + 1e-9 < outer_f:
            raise ValueError("outer wall below floor")
        return [half, half], True
    rem = budget - 2.0 * outer_f
    n_int = n_gaps - 2
    interior = rem / n_int
    if interior + 1e-9 < int_f:
        raise ValueError("interior web below floor")
    return [outer_f] + [interior] * n_int + [outer_f], True


def _row_walls(lst, L, o):
    """(outer, interior, adapted) for packing lst into usable length L."""
    n = len(lst)
    if n == 0:
        return o["min_web"], o["min_web"], False
    budget = L - sum(k["d"] for k in lst)
    gaps, adapted = _distribute_gaps(n + 1, budget, o)
    outer = gaps[0]
    interior = gaps[1] if n > 1 else outer
    return outer, interior, adapted


def _band(lst, o):
    return max([k["d"] for k in lst] + [0.0]) + o["label_gap"] + o["label_height"]


def _row_fits_length(lst, L, o):
    return _min_need_length(lst, o) <= L + 1e-9


def pack(socks, gx, gy, o):
    L = gx * PITCH - CLEAR
    W = gy * PITCH - CLEAR
    rows, bad, wide = [], [], []
    for h in sorted(set(s["hint"] for s in socks if s["hint"] > 0)):
        rows.append([s for s in socks if s["hint"] == h])
    for n, row in enumerate(rows):
        if not _row_fits_length(row, L, o):
            need = _min_need_length(row, o)
            if o.get("adaptive_walls", ADAPTIVE_WALLS):
                bad.append(
                    "hinted row %d needs %s mm even with thinnest walls "
                    "(outer %s / interior %s) > rail %s mm"
                    % (n + 1, num(need), num(o.get("min_outer_wall", MIN_OUTER_WALL)),
                       num(o.get("min_web_floor", MIN_WEB_FLOOR)), num(L)))
            else:
                bad.append("hinted row %d needs %s mm > %s mm" % (n + 1, num(_need_length(row, o)), num(L)))
    for s in sorted([s for s in socks if s["hint"] == 0], key=lambda s: (-s["d"], s["i"])):
        placed = False
        for row in rows:
            row.append(s)
            if _row_fits_length(row, L, o):
                placed = True
                break
            row.remove(s)
        if not placed:
            if not _row_fits_length([s], L, o):
                bad.append("'%s' (D %s) is wider than the bin length %s mm" % (s["label"], num(s["d"]), num(L)))
                wide.append(s)
            else:
                rows.append([s])
    bands_sum = sum(_band(r, o) for r in rows)
    n_rows = len(rows)
    min_w = bands_sum + _min_gap_budget(n_rows, o)
    need_w_target = bands_sum + (n_rows + 1) * o["min_web"]
    overflow = [wide] if wide else []
    if min_w > W + 1e-9:
        bad.append("%d rows need %s mm of depth > %s mm (thinnest walls)" % (n_rows, num(min_w), num(W)))
        acc = o.get("min_outer_wall", MIN_OUTER_WALL) if o.get("adaptive_walls", ADAPTIVE_WALLS) else o["min_web"]
        step = o.get("min_web_floor", MIN_WEB_FLOOR) if o.get("adaptive_walls", ADAPTIVE_WALLS) else o["min_web"]
        for i, row in enumerate(rows):
            gap = acc if i == 0 else step
            acc = gap + _band(row, o) + (o.get("min_outer_wall", MIN_OUTER_WALL)
                                         if o.get("adaptive_walls", ADAPTIVE_WALLS) else o["min_web"])
            # Simpler overflow mark: any row once depth exceeds W
        acc = 0.0
        gaps_try = _min_gap_budget(n_rows, o)
        # Mark trailing rows that push past W at floor spacing
        outer_f = o.get("min_outer_wall", MIN_OUTER_WALL) if o.get("adaptive_walls", ADAPTIVE_WALLS) else o["min_web"]
        int_f = o.get("min_web_floor", MIN_WEB_FLOOR) if o.get("adaptive_walls", ADAPTIVE_WALLS) else o["min_web"]
        acc = outer_f
        for row in rows:
            acc += _band(row, o)
            if acc + outer_f > W + 1e-9:
                overflow.append(row)
            acc += int_f
    return dict(gx=gx, gy=gy, L=L, W=W, rows=rows, ok=not bad, bad=bad,
                need_w=need_w_target, min_w=min_w, overflow=overflow)


class NoFit(Exception):
    def __init__(self, lines, human=None):
        Exception.__init__(self, "\n".join(lines))
        self.lines = lines
        self._human = human

    def human_message(self):
        return self._human if self._human else "\n".join(self.lines)


def _next_grid_length(min_rail):
    """Smallest Gridfinity usable length (gx*42-0.5) that is >= min_rail."""
    gx = max(1, int(math.ceil((min_rail + CLEAR) / PITCH - 1e-12)))
    return gx, gx * PITCH - CLEAR


def _build_nofit_human(q, o):
    L, W = q["L"], q["W"]
    outer_f = o.get("min_outer_wall", MIN_OUTER_WALL)
    int_f = o.get("min_web_floor", MIN_WEB_FLOOR)
    lines = ["These sockets don't fit on a %s mm rail." % num(L)]
    min_rail = 0.0
    for n, row in enumerate(q["rows"]):
        labels = ", ".join(k["label"] for k in sorted(row, key=lambda k: k["i"]))
        need = _min_need_length(row, o)
        min_rail = max(min_rail, need)
        if need > L + 1e-9:
            lines.append(
                "Row %d (sockets: %s) needs %s mm even with the thinnest walls "
                "(outer %s mm / interior %s mm), %s mm too long."
                % (n + 1, labels, num(round(need, 1)), num(outer_f), num(int_f), num(round(need - L, 1))))
    for b in q["bad"]:
        if not b.startswith("hinted row"):
            lines.append(b)
    if min_rail > L + 1e-9:
        gx, next_L = _next_grid_length(min_rail)
        lines.append(
            "Use a rail at least %s mm long (next Gridfinity size: %d units / %s mm usable), "
            "or move/remove a socket from the overflowing row(s)."
            % (num(round(min_rail, 1)), gx, num(next_L)))
    else:
        lines.append("Remove or shrink those sockets, or allow a bigger grid.")
    return "\n".join(lines)


def plan(socks, **kw):
    """Full plan: footprint, rows (left->right in list order), height, every hole/label position.
    Raises NoFit with a technical log (str) and human_message() for UI dialogs."""
    o = dict(DEFAULTS); o.update({k: v for k, v in kw.items() if v is not None})
    if o["grid_x"] > 0 and o["grid_y"] > 0:
        cands = [(o["grid_x"], o["grid_y"])]
    else:
        cands = [(gx, gy) for gx in range(o["min_grid_x"], o["max_grid_x"] + 1)
                 for gy in range(o["min_grid_y"], o["max_grid_y"] + 1)]
        cands.sort(key=lambda c: (c[0] * c[1], c[1], c[0]))   # Sort-Object a, gy, gx
    p = None
    for gx, gy in cands:
        q = pack(socks, gx, gy, o)
        if q["ok"]:
            p = q
            break
    if p is None:
        gxm, gym = (o["grid_x"], o["grid_y"]) if o["grid_x"] > 0 else (o["max_grid_x"], o["max_grid_y"])
        q = pack(socks, gxm, gym, o)
        # Avoid %d truncating fractional footprints.
        size_txt = ("%g x %g" % (gym, gxm)) if (isinstance(gxm, float) or isinstance(gym, float)) else ("%dx%d" % (gym, gxm))
        lines = ["NOTHING FITS up to %s (bin %s x %s mm, target web %s mm, adaptive %s, outer floor %s, interior floor %s):"
                 % (size_txt, num(q["L"]), num(q["W"]), num(o["min_web"]),
                    "on" if o.get("adaptive_walls", ADAPTIVE_WALLS) else "off",
                    num(o.get("min_outer_wall", MIN_OUTER_WALL)),
                    num(o.get("min_web_floor", MIN_WEB_FLOOR)))]
        lines += ["  - " + b for b in q["bad"]]
        left = ["%s (D %s)" % (k["label"], num(k["d"])) for row in q["overflow"] for k in row]
        if left:
            lines.append("  Sockets that do not fit (%d): %s" % (len(left), ", ".join(left)))
        lines.append("  Remove or shrink those sockets, lower the wall floors, or allow a bigger grid.")
        raise NoFit(lines, human=_build_nofit_human(q, o))
    L, W = p["L"], p["W"]
    rows = [sorted(r, key=lambda k: k["i"]) for r in p["rows"]]
    max_depth = max(s["depth"] for s in socks)
    # Precedence: explicit Gridfinity units > height_mm (default 40) > auto (height_mm = 0).
    hu = int(o["height_units"])
    hmm = float(o.get("height_mm") or 0.0)
    if hu > 0:
        H = hu * UNIT
        height_src = "%d Gridfinity units" % hu
    elif hmm > 0:
        H = hmm
        height_src = "height_mm"
        hu = None
    else:
        eff_depth = min(max_depth, float(o.get("max_depth") or 0.0)) if float(o.get("max_depth") or 0.0) > 0 else max_depth
        hu = int(math.ceil((eff_depth + o["floor_min"] + BASE) / UNIT - 1e-9))
        H = hu * UNIT
        height_src = "auto"
    top_z = H - BASE
    if top_z <= o["floor_min"]:
        raise ValueError("Total height %s mm is too small: it must be more than %s mm (5 mm base + %s mm floor)." % (
            num(H), num(BASE + o["floor_min"]), num(o["floor_min"])))
    report, warnings = [], []
    report.append("Socket planner %s (adaptive walls %s)" % (VERSION, "on" if o.get("adaptive_walls", ADAPTIVE_WALLS) else "off"))
    if float(p["gy"]).is_integer() and float(p["gx"]).is_integer():
        size_line = "Chosen size: %d x %d Gridfinity units (grid_y x grid_x), %s mm total height" % (int(p["gy"]), int(p["gx"]), num(H))
    else:
        size_line = "Measured footprint: %.4f x %.4f grid units (gy x gx) -> %s x %s mm usable, %s mm total height" % (
            p["gy"], p["gx"], num(L), num(W), num(H))
    report.append(size_line)
    report.append("  Bin: %s x %s x %s mm total height (incl. 5 mm base; set by %s), top face z = %s" % (num(L), num(W), num(H), height_src, num(top_z)))
    max_hole = top_z - o["floor_min"]
    cap = float(o.get("max_depth") or 0.0)
    deepest = max_depth
    report.append("  Deepest hole %s mm; %s mm available above a %s mm floor -> %s" % (
        num(deepest), num(max_hole), num(o["floor_min"]),
        "all holes fit" if deepest <= max_hole + 1e-9 else "some holes will be shortened"))
    if o.get("adaptive_walls", ADAPTIVE_WALLS):
        report.append("  Adaptive walls ON (target web %s mm; outer floor %s mm; interior floor %s mm)"
                      % (num(o["min_web"]), num(o.get("min_outer_wall", MIN_OUTER_WALL)),
                         num(o.get("min_web_floor", MIN_WEB_FLOOR))))
    bands = [_band(r, o) for r in rows]
    depth_budget = W - sum(bands)
    try:
        depth_gaps, depth_adapted = _distribute_gaps(len(rows) + 1, depth_budget, o)
    except ValueError:
        depth_gaps = [depth_budget / (len(rows) + 1)] * (len(rows) + 1)
        depth_adapted = False
    # Front-to-back: cumulative gap before each row band.
    holes = []
    y_cursor = 0.0
    for r, row in enumerate(rows):
        y_cursor += depth_gaps[r]
        outer, interior, adapted = _row_walls(row, L, o)
        dmax = max(k["d"] for k in row)
        y = y_cursor + o["label_gap"] + o["label_height"] + dmax / 2
        if abs(outer - interior) < 1e-9:
            if adapted:
                wall_txt = "web %s mm (adapted from %s)" % (num(round(outer, 3)), num(o["min_web"]))
            else:
                wall_txt = "web %s mm" % num(round(outer, 3))
        else:
            wall_txt = "outer %s mm, interior %s mm (adapted from %s)" % (
                num(round(outer, 3)), num(round(interior, 3)), num(o["min_web"]))
        report.append("  Row %d (%s): %d sockets, %s: %s" % (
            r + 1, "front" if r == 0 else "behind row %d" % r, len(row), wall_txt,
            " ".join("%s=%s" % (k["label"], num(k["d"])) for k in row)))
        x_acc = outer
        n = len(row)
        for j, k in enumerate(row):
            x = x_acc + k["d"] / 2
            x_acc += k["d"] + (interior if j < n - 1 else 0.0)
            cut = min(k["depth"], top_z - o["floor_min"], cap if cap > 0 else k["depth"])
            lw = 0.0
            for ch in k["label"]:
                lw += 0.39 if ch in ".,:;!| " else 0.78
            lw *= o["label_height"]
            if k["label"] and lw > k["d"] + interior - 0.5:
                warnings.append("label '%s' (~%s mm wide) may run into its neighbours (space %s mm)" % (
                    k["label"], num(round(lw, 1)), num(round(k["d"] + interior, 1))))
            holes.append(dict(k, row=r + 1, x=x, y=y, cut=cut, web=interior, outer_web=outer,
                              label_y=y - k["d"] / 2 - o["label_gap"] - o["label_height"]))
        y_cursor += bands[r]
    y_cursor += depth_gaps[-1]
    row_gap = depth_gaps[0]  # front outer; kept for callers expecting a scalar
    if depth_adapted:
        report.append("  Row depth gaps adapted: %s" % ", ".join(num(round(g, 3)) for g in depth_gaps))
    if cap > 0:
        clamped = [k for k in socks if k["depth"] > cap + 1e-9]
        report.append("  Max hole depth %s mm: %s" % (num(cap),
            "no sockets clamped" if not clamped else "%d socket(s) clamped: %s" % (
                len(clamped), ", ".join("%s (%s -> %s mm)" % (k["label"], num(k["depth"]), num(min(cap, top_z - o["floor_min"]))) for k in clamped))))
        for k in clamped:
            warnings.append("'%s' depth %s mm is limited to the %s mm max hole depth" % (k["label"], num(k["depth"]), num(cap)))
    for k in socks:
        if k["depth"] > top_z - o["floor_min"] + 1e-9:
            warnings.append("'%s' depth %s mm is limited to %s mm by the total height of %s mm (floor %s mm)" % (
                k["label"], num(k["depth"]), num(top_z - o["floor_min"]), num(H), num(o["floor_min"])))
    px, py, pz = o["printer_x"], o["printer_y"], o["printer_z"]
    if L > px or W > py or H > pz:
        if L <= py and W <= px and H <= pz:
            warnings.append("bin fits the %sx%s bed only rotated 90 degrees" % (num(px), num(py)))
        else:
            warnings.append("bin %s x %s x %s mm EXCEEDS the Snapmaker U1 build volume %s x %s x %s mm" % (
                num(L), num(W), num(H), num(px), num(py), num(pz)))
    elif L > px - 10 or W > py - 10:
        warnings.append("bin is within 10 mm of the U1 bed edge (%s x %s); leave room for the prime tower / purge line" % (num(px), num(py)))
    else:
        report.append("  Snapmaker U1 check: OK (%s x %s x %s mm fits %s x %s x %s mm)" % (num(L), num(W), num(H), num(px), num(py), num(pz)))
    return dict(gx=p["gx"], gy=p["gy"], L=L, W=W, H=H, hu=hu, top_z=top_z, rows=rows, row_gap=row_gap,
                bands=bands, holes=holes, report=report, warnings=warnings, opts=o, version=VERSION)


# ------------------------------------------------------------------ 2-part 3MF for Snapmaker Orca
def _xml_escape(s):
    return (s.replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;").replace('"', "&quot;"))


def write_orca_3mf(path, title, parts, colors=("#1F1F1F", "#FFFFFF")):
    """parts: list of (name, vertices[(x,y,z) mm], triangles[(a,b,c)]) - normally Bin then Labels.
    Writes one object with one part per entry; part n -> extruder n."""
    parts = [p for p in parts if p[2]]
    xt = _xml_escape(title)
    sb = ['<?xml version="1.0" encoding="UTF-8"?>\n<model unit="millimeter" xml:lang="en-US" '
          'xmlns="http://schemas.microsoft.com/3dmanufacturing/core/2015/02">\n',
          ' <metadata name="Title">%s</metadata>\n <resources>\n  <basematerials id="1">\n' % xt]
    for n, (name, _, _) in enumerate(parts):
        sb.append('   <base name="%s" displaycolor="%s"/>\n' % (_xml_escape(name), colors[min(n, len(colors) - 1)]))
    sb.append("  </basematerials>\n")
    for n, (name, verts, tris) in enumerate(parts):
        sb.append('  <object id="%d" type="model" name="%s" pid="1" pindex="%d">\n   <mesh>\n    <vertices>\n' % (n + 2, _xml_escape(name), n))
        sb.extend('     <vertex x="%.5f" y="%.5f" z="%.5f"/>\n' % v for v in verts)
        sb.append("    </vertices>\n    <triangles>\n")
        sb.extend('     <triangle v1="%d" v2="%d" v3="%d"/>\n' % t for t in tris)
        sb.append("    </triangles>\n   </mesh>\n  </object>\n")
    asm = len(parts) + 2
    sb.append('  <object id="%d" type="model" name="%s">\n   <components>\n' % (asm, xt))
    sb.extend('    <component objectid="%d"/>\n' % (n + 2) for n in range(len(parts)))
    sb.append('   </components>\n  </object>\n </resources>\n <build>\n  <item objectid="%d"/>\n </build>\n</model>\n' % asm)
    cfg = ['<?xml version="1.0" encoding="UTF-8"?>\n<config>\n  <object id="%d">\n' % asm,
           '    <metadata key="name" value="%s"/>\n    <metadata key="extruder" value="1"/>\n' % xt]
    for n, (name, _, _) in enumerate(parts):
        cfg.append('    <part id="%d" subtype="normal_part">\n      <metadata key="name" value="%s"/>\n'
                   '      <metadata key="extruder" value="%d"/>\n    </part>\n' % (n + 2, _xml_escape(name), n + 1))
    cfg.append("  </object>\n</config>\n")
    types = ('<?xml version="1.0" encoding="UTF-8"?>\n<Types xmlns="http://schemas.openxmlformats.org/package/2006/content-types">\n'
             ' <Default Extension="rels" ContentType="application/vnd.openxmlformats-package.relationships+xml"/>\n'
             ' <Default Extension="model" ContentType="application/vnd.ms-package.3dmanufacturing-3dmodel+xml"/>\n'
             ' <Default Extension="config" ContentType="text/xml"/>\n</Types>\n')
    rels = ('<?xml version="1.0" encoding="UTF-8"?>\n<Relationships xmlns="http://schemas.openxmlformats.org/package/2006/relationships">\n'
            ' <Relationship Target="/3D/3dmodel.model" Id="rel0" Type="http://schemas.microsoft.com/3dmanufacturing/2013/01/3dmodel"/>\n'
            '</Relationships>\n')
    with zipfile.ZipFile(path, "w", zipfile.ZIP_DEFLATED) as z:
        z.writestr("[Content_Types].xml", types)
        z.writestr("_rels/.rels", rels)
        z.writestr("3D/3dmodel.model", "".join(sb))
        z.writestr("Metadata/model_settings.config", "".join(cfg))


def weld(coords, indices, digits=5):
    """Fusion mesh -> (verts, tris): merge duplicate nodes so the mesh is closed. coords in mm, flat."""
    key_to_new, verts, remap = {}, [], []
    for n in range(0, len(coords), 3):
        key = (round(coords[n], digits), round(coords[n + 1], digits), round(coords[n + 2], digits))
        if key not in key_to_new:
            key_to_new[key] = len(verts)
            verts.append(key)
        remap.append(key_to_new[key])
    tris = []
    for n in range(0, len(indices), 3):
        a, b, c = remap[indices[n]], remap[indices[n + 1]], remap[indices[n + 2]]
        if a != b and b != c and a != c:
            tris.append((a, b, c))
    return verts, tris
