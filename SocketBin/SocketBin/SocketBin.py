"""SocketBin - Fusion 360 script: build a Gridfinity socket bin from a socket list (.xlsx or .csv).

Plans the rows (auto footprint up to 6 x 3 cells, which fits a 270 mm printer bed), with adaptive walls,
then builds the bin (version is socketbin_core.VERSION):
  * 42 mm pitch, 41.5 mm cells (bin = n*42 - 0.5), 3.75 mm outer corner radius
  * Gridfinity foot: 0.8 mm @45, 1.8 mm straight, 2.15 mm @45 (radii 0.8 / 1.6 / 4.0 at the cell),
    the upper chamfer runs on as a V between neighbouring feet (like Fusion's own Gridfinity bins)
  * total height = height_mm (default 40 mm, bottom of the feet to the top face, no stacking lip) or
    height=<Gridfinity units> * 7 mm; 1 mm round on the top edge
  * one hole per socket; a label-coloured floor disk inlaid in each pocket bottom; the size label inlaid flush in front of it - floors and labels share the "Labels" body / extruder 2
Optionally exports <list folder>/<bin name>/: a two-colour 3MF for Snapmaker Orca (bin = extruder 1,
labels + pocket floors = extruder 2, one multi-part object) and a build report. No STL/STEP files.

Model units are millimetres; the Fusion API works in centimetres internally, so every numeric value
passed as a real is mm / 10 and every expression is written as a string with explicit "mm".
"""
import adsk.core, adsk.fusion, traceback
import os, sys, importlib, importlib.util, re, datetime, json

_here = os.path.dirname(os.path.realpath(__file__))
if _here not in sys.path:
    sys.path.insert(0, _here)
# Load THIS folder's planner explicitly. A plain "import socketbin_core" can return a copy
# another script already put in sys.modules, and a reload of that would re-read the OTHER folder's file. Fresh load also picks up edits without a restart.
_spec = importlib.util.spec_from_file_location("socketbin_core", os.path.join(_here, "socketbin_core.py"))
core = importlib.util.module_from_spec(_spec)
sys.modules["socketbin_core"] = core
_spec.loader.exec_module(core)
VERSION = core.VERSION

TITLE = "Socket Bin %s" % VERSION
BIN_RGB = (0x1F, 0x1F, 0x1F)
LABEL_RGB = (0xFF, 0xFF, 0xFF)
FONT = "Arial"
_app = None
_ui = None


class Abort(Exception):
    pass


def cm(mm):
    return mm / 10.0


def vi(expr):
    """ValueInput from an expression string ('12 mm', 'top_z', '45 deg') or a number of mm."""
    if isinstance(expr, (int, float)):
        expr = "%s mm" % core.num(expr)
    return adsk.core.ValueInput.createByString(expr)


def P(x, y, z=0.0):
    return adsk.core.Point3D.create(cm(x), cm(y), cm(z))


# ------------------------------------------------------------------ small helpers
class Steps:
    """Runs each build step in try/except; critical failures abort, others are collected."""
    def __init__(self, total):
        self.problems = []
        self.prog = None
        try:
            self.prog = _ui.createProgressDialog()
            self.prog.isCancelButtonShown = False
            self.prog.show(TITLE, "%p% - starting", 0, max(1, total), 0)
        except Exception:
            self.prog = None

    def run(self, what, fn, critical=False):
        if self.prog:
            try:
                self.prog.message = what
                self.prog.progressValue = self.prog.progressValue + 1
            except Exception:
                pass
        adsk.doEvents()
        try:
            return fn()
        except Abort:
            raise
        except Exception as e:
            msg = "%s failed: %s" % (what, e)
            try:        # where it failed, so a problem line says which API call to look at
                fr = traceback.extract_tb(e.__traceback__)[-1]
                msg += " [SocketBin.py line %s: %s]" % (fr.lineno, (fr.line or "").strip()[:90])
            except Exception:
                pass
            if critical:
                self.close()
                raise Abort(msg + "\n\n" + traceback.format_exc())
            self.problems.append(msg)
            return None

    def close(self):
        if self.prog:
            try:
                self.prog.hide()
            except Exception:
                pass


def offset_plane(root, expr, name):
    """Construction plane parallel to XY at z = expr (an expression, so it follows user parameters)."""
    pin = root.constructionPlanes.createInput()
    pin.setByOffset(root.xYConstructionPlane, vi(expr))
    pl = root.constructionPlanes.add(pin)
    pl.name = name
    return pl


def rounded_rect(sketch, x0, y0, x1, y1, r, z_model):
    """Rounded rectangle in model coordinates (mm) on a sketch parallel to XY: a 2-point rectangle
    whose four corners are filleted with sketchArcs.addFillet (reliable, orientation independent)."""
    a = sketch.modelToSketchSpace(P(x0, y0, z_model))
    b = sketch.modelToSketchSpace(P(x1, y1, z_model))
    lines = sketch.sketchCurves.sketchLines.addTwoPointRectangle(a, b)
    if r <= 0:
        return
    ls = [lines.item(i) for i in range(lines.count)]
    arcs = sketch.sketchCurves.sketchArcs
    for i in range(4):
        l1, l2 = ls[i], ls[(i + 1) % 4]
        # the corner shared by the two neighbouring sides
        c = min(((p, q) for p in (l1.startSketchPoint.geometry, l1.endSketchPoint.geometry)
                 for q in (l2.startSketchPoint.geometry, l2.endSketchPoint.geometry)),
                key=lambda pq: pq[0].distanceTo(pq[1]))[0]
        def toward(line, corner):
            s, e = line.startSketchPoint.geometry, line.endSketchPoint.geometry
            far = s if corner.distanceTo(e) < corner.distanceTo(s) else e
            t = min(0.25, cm(r) * 0.5 / max(1e-9, corner.distanceTo(far)))
            return adsk.core.Point3D.create(corner.x + (far.x - corner.x) * t, corner.y + (far.y - corner.y) * t, 0)
        arcs.addFillet(l1, toward(l1, c), l2, toward(l2, c), cm(r))


def one_side(feats, profile, op, dist_expr, negative, taper_deg=None, participants=None):
    """Extrude with a one-side distance extent (optionally tapered)."""
    ei = feats.createInput(profile, op)
    direction = (adsk.fusion.ExtentDirections.NegativeExtentDirection if negative
                 else adsk.fusion.ExtentDirections.PositiveExtentDirection)
    ext = adsk.fusion.DistanceExtentDefinition.create(vi(dist_expr))
    if taper_deg is None:
        ei.setOneSideExtent(ext, direction)
    else:
        ei.setOneSideExtent(ext, direction, adsk.core.ValueInput.createByString("%s deg" % taper_deg))
    if participants is not None:
        ei.participantBodies = list(participants)
    return feats.add(ei)


def single_profile(sketch, loops=None):
    best = None
    for i in range(sketch.profiles.count):
        pr = sketch.profiles.item(i)
        if loops is None or pr.profileLoops.count == loops:
            if best is None or pr.areaProperties().area > best.areaProperties().area:
                best = pr
    if best is None:
        raise RuntimeError("no closed profile in sketch '%s'" % sketch.name)
    return best


def bbox_mm(body):
    b = body.boundingBox
    return [v * 10 for v in (b.minPoint.x, b.minPoint.y, b.minPoint.z, b.maxPoint.x, b.maxPoint.y, b.maxPoint.z)]


def set_appearance(design, bodies, name, rgb):
    """Copy a plastic appearance from Fusion's appearance library, recolour it, apply it."""
    ap = design.appearances.itemByName(name)
    if ap is None:
        src = None
        libs = _app.materialLibraries
        for want in ("Fusion Appearance Library", "Fusion 360 Appearance Library"):
            lib = libs.itemByName(want)
            if lib:
                break
        else:
            lib = None
            for i in range(libs.count):
                if "appearance" in libs.item(i).name.lower():
                    lib = libs.item(i); break
        if lib is None:
            raise RuntimeError("Fusion appearance library not found")
        for pref in ("Plastic - Matte (Black)", "Plastic - Glossy (Black)", "Plastic - Matte", "Plastic"):
            for i in range(lib.appearances.count):
                a = lib.appearances.item(i)
                if a.name.startswith(pref):
                    src = a; break
            if src:
                break
        if src is None:
            src = lib.appearances.item(0)
        ap = design.appearances.addByCopy(src, name)
        colour = None
        for i in range(ap.appearanceProperties.count):
            cp = adsk.core.ColorProperty.cast(ap.appearanceProperties.item(i))
            if cp and (colour is None or cp.name in ("Color", "Colour")):
                colour = cp
                if cp.name in ("Color", "Colour"):
                    break
        if colour is None:
            raise RuntimeError("appearance '%s' has no colour property" % src.name)
        colour.value = adsk.core.Color.create(rgb[0], rgb[1], rgb[2], 0)
    for b in bodies:
        b.appearance = ap


def check_options(o):
    """Shared rules for option values (options text and dialog). Raises ValueError in plain language."""
    if not (o["floor_min"] > 0):
        raise ValueError("Minimum floor must be greater than 0.")
    if not (o["min_web_floor"] > 0):
        raise ValueError("Thinnest wall between holes must be greater than 0.")
    if not (o["min_outer_wall"] > 0):
        raise ValueError("Thinnest outer wall must be greater than 0.")
    if o.get("height_mm", 0) < 0:
        raise ValueError("Total height must be 0 (auto) or a positive number of mm.")
    if o.get("height_units", 0) < 0:
        raise ValueError("Height units must be 0 (use mm) or a positive whole number.")
    if o.get("height_units", 0) == 0 and 0 < o.get("height_mm", 0) <= core.BASE + o["floor_min"]:
        raise ValueError("Total height must be more than %s mm (5 mm base + %s mm floor), or 0 for auto." % (
            core.num(core.BASE + o["floor_min"]), core.num(o["floor_min"])))
    if o.get("max_depth", 0) < 0:
        raise ValueError("Max hole depth must be 0 (no limit) or a positive number of mm.")
    if o["min_web"] < 0:
        raise ValueError("Wall between holes must not be negative.")
    if o["floor_inlay"] < 0 or o["floor_inlay"] != o["floor_inlay"]:
        raise ValueError("Pocket-floor disk thickness must be 0 or more.")


def parse_options(text, d):
    """'height_mm=40 grid=auto web=2.85 floor=3 adaptive=on export=yes' -> dict (unknown keys raise)."""
    o = dict(d)
    for tok in re.split(r"[\s,;]+", text.strip()):
        if not tok:
            continue
        if "=" not in tok:
            raise ValueError("'%s' is not key=value" % tok)
        k, v = [s.strip().lower() for s in tok.split("=", 1)]
        if k in ("height_mm", "total_height", "totalheight", "mm"):
            # auto/0 = size from the deepest hole (old behaviour)
            o["height_mm"] = 0.0 if v in ("auto", "0", "") else float(v)
        elif k in ("max_depth", "maxdepth", "max_hole_depth"):
            o["max_depth"] = 0.0 if v in ("off", "none", "0", "") else float(v)
        elif k in ("height", "units", "height_units"):
            # explicit Gridfinity units win over height_mm; auto/0 = no unit override
            o["height_units"] = 0 if v in ("auto", "0", "") else int(v)
        elif k == "grid":
            if v in ("auto", "0", ""):
                o["grid_x"] = o["grid_y"] = 0
            else:
                m = re.match(r"^(\d+)\s*x\s*(\d+)$", v)
                if not m:
                    raise ValueError("grid must be auto or YxX, e.g. 2x6 (rows of 42 mm deep x 42 mm long)")
                o["grid_y"], o["grid_x"] = int(m.group(1)), int(m.group(2))
        elif k in ("web", "min_web", "minweb"):
            o["min_web"] = float(v)
        elif k in ("floor", "floor_min", "floormin"):
            o["floor_min"] = float(v)
        elif k in ("floor_inlay", "floorinlay", "pocket_floor"):
            o["floor_inlay"] = float(v)
        elif k in ("adaptive", "adaptive_walls"):
            o["adaptive_walls"] = v in ("yes", "y", "1", "true", "on")
        elif k in ("web_floor", "webfloor", "min_web_floor"):
            o["min_web_floor"] = float(v)
        elif k in ("outer_floor", "outerfloor", "min_outer_wall", "outer"):
            o["min_outer_wall"] = float(v)
        elif k in ("maxx", "max_grid_x"):
            o["max_grid_x"] = int(v)
        elif k in ("maxy", "max_grid_y"):
            o["max_grid_y"] = int(v)
        elif k == "export":
            o["export"] = v in ("yes", "y", "1", "true", "on")
        else:
            raise ValueError("unknown option '%s'" % k)
    check_options(o)
    return o


# ------------------------------------------------------------------ build
def build(design, plan, name, steps):
    root = design.rootComponent
    o = plan["opts"]
    L, W, top_z = plan["L"], plan["W"], plan["top_z"]
    ext = root.features.extrudeFeatures
    NB = adsk.fusion.FeatureOperations.NewBodyFeatureOperation
    JOIN = adsk.fusion.FeatureOperations.JoinFeatureOperation
    CUT = adsk.fusion.FeatureOperations.CutFeatureOperation
    up = design.userParameters
    state = {"floors_created": 0, "floors_colored": 0, "floor_failures": []}

    def params():
        def add(n, expr, units, comment):
            p = up.itemByName(n)
            if p:
                p.expression = expr
            else:
                up.add(n, adsk.core.ValueInput.createByString(expr), units, comment)
        add("pitch", "42 mm", "mm", "Gridfinity pitch (informational; rerun the script to change the footprint)")
        add("clearance", "0.5 mm", "mm", "bin = grid * pitch - clearance (informational)")
        add("grid_x", str(plan["gx"]), "", "cells along X (informational; rerun the script to change)")
        add("grid_y", str(plan["gy"]), "", "cells along Y (informational; rerun the script to change)")
        add("total_height", "%s mm" % core.num(plan["H"]), "mm", "TOTAL bin height, bottom of the feet to the top face, incl. the 5 mm base. Editable (default 40 mm).")
        add("top_z", "total_height - 5 mm", "mm", "top face above the base (z=0 is the top of the feet)")
        add("max_depth", "%s mm" % core.num(o.get("max_depth", 0)), "mm", "max hole depth used when the bin was built (informational: each sNN_depth was clamped to this; 0 = no cap)")
        add("inlay_depth", "%s mm" % core.num(o["inlay_depth"]), "mm", "label inlay depth. Editable.")
        add("floor_inlay", "%s mm" % core.num(o.get("floor_inlay", 0.6)), "mm", "coloured socket-floor disk thickness (label colour). Editable; 0 = off.")
        add("top_round", "1 mm", "mm", "top edge round. Editable.")
        add("min_web_target", "%s mm" % core.num(o["min_web"]), "mm", "target wall between holes (informational; rows shrink toward the floors below only when needed)")
        add("min_web_floor", "%s mm" % core.num(o.get("min_web_floor", core.MIN_WEB_FLOOR)), "mm", "thinnest interior web allowed (informational)")
        add("min_outer_wall", "%s mm" % core.num(o.get("min_outer_wall", core.MIN_OUTER_WALL)), "mm", "thinnest outer wall allowed (informational)")
        for h in plan["holes"]:
            n = "s%02d" % h["i"]
            add(n + "_d", "%s mm" % core.num(h["d"]), "mm", "hole diameter, socket '%s'" % h["label"])
            add(n + "_depth", "%s mm" % core.num(h["cut"]), "mm", "hole depth, socket '%s' (keep <= top_z - %s mm; clamped to max_depth %s mm)" % (h["label"], core.num(o["floor_min"]), core.num(o.get("max_depth", 0))))
    steps.run("User parameters", params)

    def planes():
        state["pl_top"] = offset_plane(root, "top_z", "Top face")
        state["pl_body"] = offset_plane(root, "0.5 mm", "Body bottom (z 0.5)")
        state["pl_trim"] = offset_plane(root, "1 mm", "Trim (z 1)")
        state["pl_mid"] = offset_plane(root, "-2.4 mm", "Foot straight top (z -2.4)")
        state["pl_low"] = offset_plane(root, "-4.2 mm", "Foot straight bottom (z -4.2)")
    steps.run("Construction planes", planes, critical=True)

    def body():
        sk = root.sketches.add(state["pl_body"]); sk.name = "Bin outline"
        rounded_rect(sk, 0, 0, L, W, 3.75, 0.5)
        f = one_side(ext, single_profile(sk), NB, "top_z - 0.5 mm", False)
        b = f.bodies.item(0); b.name = "Bin"
        state["bin"] = b; state["body_feat"] = f
    steps.run("Bin body", body, critical=True)

    def top_round():
        f = state["body_feat"]
        edges = adsk.core.ObjectCollection.create()
        for e in f.endFaces.item(0).edges:
            edges.add(e)
        fi = root.features.filletFeatures.createInput()
        try:
            fi.edgeSetInputs.addConstantRadiusEdgeSet(edges, vi("top_round"), True)
        except AttributeError:            # older Fusion builds (pre edgeSetInputs)
            fi.addConstantRadiusEdgeSet(edges, vi("top_round"), True)
        root.features.filletFeatures.add(fi).name = "Top edge round"
    steps.run("1 mm top edge round", top_round)

    def foot():
        # Cell (0,0) spans 0..41.5; foot centred at 20.75. The upper 45 deg chamfer starts 0.5 mm inside
        # the body (43 mm wide, r 4.5) so it is exactly 42 mm wide (r 4.0) at z = 0: neighbouring feet
        # meet there in a V, no shelf. Then 37.2 mm (r 1.6) at z -2.4, straight to -4.2, 35.6 (r 0.8) at -5.
        sk = root.sketches.add(state["pl_body"]); sk.name = "Foot upper chamfer"
        rounded_rect(sk, -0.75, -0.75, 42.25, 42.25, 4.5, 0.5)
        prof = single_profile(sk)
        f = one_side(ext, prof, NB, "2.9 mm", True, taper_deg=-45)
        bb = bbox_mm(f.bodies.item(0))
        if bb[3] - bb[0] > 43.05:          # tapered outwards: flip the sign
            f.deleteMe()
            f = one_side(ext, prof, NB, "2.9 mm", True, taper_deg=45)
            bb = bbox_mm(f.bodies.item(0))
        if abs((bb[3] - bb[0]) - 43.0) > 0.05 or abs(bb[2] + 2.4) > 0.05:
            raise RuntimeError("upper chamfer came out %.2f mm wide, bottom z %.2f (expected 43, -2.4)" % (bb[3] - bb[0], bb[2]))
        ft = f.bodies.item(0); ft.name = "Foot"
        sk2 = root.sketches.add(state["pl_mid"]); sk2.name = "Foot straight"
        rounded_rect(sk2, 2.15, 2.15, 39.35, 39.35, 1.6, -2.4)
        one_side(ext, single_profile(sk2), JOIN, "1.8 mm", True, participants=[ft])
        sk3 = root.sketches.add(state["pl_low"]); sk3.name = "Foot lower chamfer"
        rounded_rect(sk3, 2.15, 2.15, 39.35, 39.35, 1.6, -4.2)
        prof3 = single_profile(sk3)
        f3 = one_side(ext, prof3, JOIN, "0.8 mm", True, taper_deg=-45, participants=[ft])
        bb = bbox_mm(ft)
        if abs(bb[2] + 5.0) > 0.01:
            raise RuntimeError("foot bottom at z %.2f, expected -5" % bb[2])
        # check the bottom face is 35.6 (inward taper): look for a planar face at z = -5
        ok = False
        for fc in ft.faces:
            fb = fc.boundingBox
            if abs(fb.minPoint.z * 10 + 5) < 0.01 and abs(fb.maxPoint.z * 10 + 5) < 0.01:
                ok = abs((fb.maxPoint.x - fb.minPoint.x) * 10 - 35.6) < 0.05
                if not ok:
                    f3.deleteMe()
                    one_side(ext, prof3, JOIN, "0.8 mm", True, taper_deg=45, participants=[ft])
                    ok = True
                break
        if not ok:
            raise RuntimeError("could not find the 35.6 mm foot bottom face")
        state["foot"] = ft
    steps.run("Gridfinity foot", foot, critical=True)

    def pattern():
        gx, gy = plan["gx"], plan["gy"]
        feet = [state["foot"]]
        if gx * gy > 1:
            coll = adsk.core.ObjectCollection.create(); coll.add(state["foot"])
            pats = root.features.rectangularPatternFeatures
            pi = pats.createInput(coll, root.xConstructionAxis, adsk.core.ValueInput.createByReal(gx),
                                  vi("pitch"), adsk.fusion.PatternDistanceType.SpacingPatternDistanceType)
            pi.setDirectionTwo(root.yConstructionAxis, adsk.core.ValueInput.createByReal(gy), vi("pitch"))
            pats.add(pi).name = "Feet"
            feet = [b for b in root.bRepBodies if b.isSolid and b.name != "Bin" and b.entityToken != state["bin"].entityToken]
        if len(feet) != gx * gy:
            raise RuntimeError("expected %d feet, found %d" % (gx * gy, len(feet)))
        lo = min(bbox_mm(b)[0] for b in feet); hi = max(bbox_mm(b)[3] for b in feet)
        if lo < -0.8 or hi > L + 1.3:
            raise RuntimeError("feet pattern went the wrong way (x %.1f..%.1f)" % (lo, hi))
        tools = adsk.core.ObjectCollection.create()
        for b in feet:
            tools.add(b)
        ci = root.features.combineFeatures.createInput(state["bin"], tools)
        ci.operation = JOIN
        ci.isKeepToolBodies = False
        root.features.combineFeatures.add(ci).name = "Join feet"
    steps.run("Foot pattern + join", pattern, critical=True)

    def trim():
        # cut the overhang outside the 3.75 mm-radius envelope (the feet reach 0.75 mm past the wall at z 0.5)
        sk = root.sketches.add(state["pl_trim"]); sk.name = "Envelope trim"
        a = sk.modelToSketchSpace(P(-10, -10, 1)); b = sk.modelToSketchSpace(P(L + 10, W + 10, 1))
        sk.sketchCurves.sketchLines.addTwoPointRectangle(a, b)
        rounded_rect(sk, 0, 0, L, W, 3.75, 1)
        one_side(ext, single_profile(sk, loops=2), CUT, "7 mm", True, participants=[state["bin"]]).name = "Envelope trim"
        bb = bbox_mm(state["bin"])
        if bb[0] < -0.01 or bb[3] > L + 0.01 or bb[2] > -4.99:
            raise RuntimeError("bin bbox after trim is x %.2f..%.2f z %.2f" % (bb[0], bb[3], bb[2]))
    steps.run("Envelope trim", trim, critical=True)

    hole_fail = []
    for h in plan["holes"]:
        def hole(h=h):
            n = "s%02d" % h["i"]
            sk = root.sketches.add(state["pl_top"]); sk.name = "Hole %s (%s)" % (n, h["label"])
            c = sk.modelToSketchSpace(P(h["x"], h["y"], top_z))
            circ = sk.sketchCurves.sketchCircles.addByCenterRadius(c, cm(h["d"] / 2))
            circ.centerSketchPoint.isFixed = True
            dim = sk.sketchDimensions.addDiameterDimension(circ, adsk.core.Point3D.create(c.x + cm(h["d"]), c.y + cm(h["d"]), 0))
            dim.parameter.expression = n + "_d"
            one_side(ext, single_profile(sk), CUT, n + "_depth", True, participants=[state["bin"]]).name = "Hole %s" % n
            return True
        if not steps.run("Hole %s (D %s)" % (h["label"], core.num(h["d"])), hole):
            hole_fail.append(h["label"])

    # Pocket-floor inlays: recess floor_inlay into each hole bottom, then a matching new body so the
    # socket seats at the original depth. Bodies take the Labels appearance / extruder 2.
    floor_bodies = []
    fi = float(o.get("floor_inlay", 0.6) or 0.0)
    if fi > 0 and o["floor_min"] + 1e-9 < fi + 0.8:
        cap = max(0.0, round(o["floor_min"] - 0.8, 3))
        if cap < 0.2:
            steps.problems.append("floor_inlay %.3g mm disabled (floor_min %.3g mm too thin)" % (fi, o["floor_min"]))
            fi = 0.0
        else:
            steps.problems.append("floor_inlay reduced to %.3g mm so floor_min %.3g mm still leaves bin material under the disk" % (cap, o["floor_min"]))
            fi = cap
            # keep parameter in sync with what we build
            p = up.itemByName("floor_inlay")
            if p:
                p.expression = "%s mm" % core.num(fi)
    # Keep the parameter consistent even when a thin-floor guard disabled the inlay.
    p = up.itemByName("floor_inlay")
    if p:
        p.expression = "%s mm" % core.num(max(0.0, fi))
    for h in plan["holes"]:
        if fi <= 0:
            break
        def floor_disk(h=h, fi=fi):
            n = "s%02d" % h["i"]
            # Plane on the recessed floor underside; +Z extrude fills up to the original pocket floor.
            z_expr = "top_z - %s_depth - floor_inlay" % n
            pl = offset_plane(root, z_expr, "Floor plane %s" % n)

            def circle_sketch(name):
                sk = root.sketches.add(pl); sk.name = name
                # Circle centre must lie on the sketch XY plane, not model z=0.
                c = sk.modelToSketchSpace(P(h["x"], h["y"], top_z - h["cut"] - fi))
                c.z = 0.0
                circ = sk.sketchCurves.sketchCircles.addByCenterRadius(c, cm(h["d"] / 2))
                circ.centerSketchPoint.isFixed = True
                dim = sk.sketchDimensions.addDiameterDimension(
                    circ, adsk.core.Point3D.create(c.x + cm(h["d"]), c.y + cm(h["d"]), 0))
                dim.parameter.expression = n + "_d"
                return sk

            # Two sketches: a profile is consumed by the first extrude.
            sk_cut = circle_sketch("Floor pocket sketch %s (%s)" % (n, h["label"] or n))
            pocket = one_side(ext, single_profile(sk_cut), CUT, "floor_inlay", False,
                              participants=[state["bin"]])
            pocket.name = "Floor pocket %s" % n
            try:
                sk_new = circle_sketch("Floor body sketch %s (%s)" % (n, h["label"] or n))
                # Explicit NewBody; no cut/join participants. Coincident faces are intentional.
                fl = one_side(ext, single_profile(sk_new), NB, "floor_inlay", False)
                if fl.bodies.count != 1:
                    fl.deleteMe()
                    raise RuntimeError("expected exactly one distinct floor body")
            except Exception:
                # Never leave a deeper socket floor when its replacement disk failed.
                pocket.deleteMe()
                raise
            fl.name = "Floor %s" % n
            for j in range(fl.bodies.count):
                b = fl.bodies.item(j)
                b.name = "Floor %s" % n if fl.bodies.count == 1 else "Floor %s %d" % (n, j + 1)
                floor_bodies.append(b)
                state["floors_created"] += 1
            return True
        if h["label"] in hole_fail:
            state["floor_failures"].append("s%02d: hole cut failed; floor skipped" % h["i"])
            continue
        if not steps.run("Floor %s (D %s)" % (h["label"] or ("s%02d" % h["i"]), core.num(h["d"])), floor_disk):
            state["floor_failures"].append("s%02d: floor creation failed (see problems below)" % h["i"])
    state["floors"] = floor_bodies

    def labels():
        lh = o["label_height"]
        # 1) calibrate: Fusion's text height is not the digit height, and "bottom" alignment is not the
        #    baseline. Extrude a throw-away "0123456789", measure it, delete it.
        k, off = 1.0, 0.0
        try:
            skc = root.sketches.add(state["pl_top"]); skc.name = "label calibration"
            ti = skc.sketchTexts.createInput2("0123456789", cm(lh)) if not hasattr(skc.sketchTexts, "createInput3") else \
                 skc.sketchTexts.createInput3("'0123456789'", adsk.core.ValueInput.createByReal(cm(lh)))
            ti.fontName = FONT
            ti.textStyle = adsk.fusion.TextStyles.TextStyleBold
            ti.setAsMultiLine(skc.modelToSketchSpace(P(-50, 0, top_z)), skc.modelToSketchSpace(P(50, lh * 3, top_z)),
                              adsk.core.HorizontalAlignments.CenterHorizontalAlignment,
                              adsk.core.VerticalAlignments.BottomVerticalAlignment, 0)
            st = skc.sketchTexts.add(ti)
            fc = one_side(ext, st, NB, "1 mm", False)
            bb = bbox_mm(fc.bodies.item(0))
            gh = bb[4] - bb[1]
            if 0.3 * lh < gh < 3 * lh:
                k = lh / gh
                off = bb[1] * k            # glyph bottom above the box bottom, after rescaling
            fc.deleteMe(); skc.deleteMe()
        except Exception as e:
            steps.problems.append("label size calibration failed (labels use the nominal text height): %s" % e)
        # 2) one sketch with every label, box bottom shifted so the digits sit at label_y
        sk = root.sketches.add(state["pl_top"]); sk.name = "Labels"
        texts = adsk.core.ObjectCollection.create()
        for h in plan["holes"]:
            if not h["label"]:
                continue
            try:
                txt = h["label"].replace("'", "\u2019")
                if hasattr(sk.sketchTexts, "createInput3"):
                    ti = sk.sketchTexts.createInput3("'%s'" % txt, adsk.core.ValueInput.createByReal(cm(lh * k)))
                else:
                    ti = sk.sketchTexts.createInput2(txt, cm(lh * k))
                ti.fontName = FONT
                ti.textStyle = adsk.fusion.TextStyles.TextStyleBold
                half = max(30.0, lh * len(txt) * 1.5)
                yb = h["label_y"] - off
                ti.setAsMultiLine(sk.modelToSketchSpace(P(h["x"] - half, yb, top_z)),
                                  sk.modelToSketchSpace(P(h["x"] + half, yb + lh * 3, top_z)),
                                  adsk.core.HorizontalAlignments.CenterHorizontalAlignment,
                                  adsk.core.VerticalAlignments.BottomVerticalAlignment, 0)
                texts.add(sk.sketchTexts.add(ti))
            except Exception as e:
                steps.problems.append("label '%s' failed: %s" % (h["label"], e))
        if texts.count == 0:
            return
        state["labels_expected"] = texts.count
        # 3) one label solid per text (extruding a whole
        #    collection of texts at once is what failed on the new Fusion build), no participants
        lbodies = []
        for i in range(texts.count):
            t = texts.item(i)
            try:
                try:
                    f = one_side(ext, t, NB, "inlay_depth", True)
                except Exception:
                    f = one_side(ext, t, NB, o["inlay_depth"], True)     # plain mm instead of the parameter
                for j in range(f.bodies.count):
                    lbodies.append(f.bodies.item(j))
            except Exception as e:
                steps.problems.append("label solid %d failed: %s" % (i + 1, e))
        # name them now so later steps find them by name at the current timeline state
        for n, b in enumerate(lbodies):
            b.name = "Labels" if n == 0 else "Labels %d" % (n + 1)
        state["labels_created"] = len(lbodies)
        if not lbodies:
            raise RuntimeError("no label solids could be created (0 of %d)" % texts.count)
        # 4) the matching pockets: ONE combine-cut against the bin only, label solids kept as tools
        try:
            tools = adsk.core.ObjectCollection.create()
            for b in lbodies:
                tools.add(b)
            ci = root.features.combineFeatures.createInput(state["bin"], tools)
            ci.operation = CUT
            ci.isKeepToolBodies = True
            root.features.combineFeatures.add(ci).name = "Label pockets"
        except Exception as e1:
            try:
                for i in range(texts.count):
                    one_side(ext, texts.item(i), CUT, "inlay_depth", True, participants=[state["bin"]])
                steps.problems.append("label pockets: combine-cut failed (%s); used per-text cuts" % e1)
            except Exception as e2:
                raise RuntimeError("label pockets could not be cut (combine: %s; per-text: %s)" % (e1, e2))
        state["labels"] = lbodies
    steps.run("Labels", labels)

    def named_bodies(comp, prefix):
        # Re-fetch at the current timeline state instead of retaining feature-body handles.
        return [comp.bRepBodies.item(i) for i in range(comp.bRepBodies.count)
                if comp.bRepBodies.item(i).name.startswith(prefix)]

    def component():
        labels = named_bodies(root, "Labels")
        floors = named_bodies(root, "Floor s")
        if not labels and not floors:
            return
        try:
            occ = root.occurrences.addNewComponent(adsk.core.Matrix3D.create())
            occ.component.name = "Labels"
        except Exception as e:
            # Newer Fusion Part Designs allow one component only. Keep named bodies,
            # and continue to the appearance pass and body-based multipart export.
            state["labels"] = labels
            state["floors"] = floors
            state["grouping_note"] = "Labels/floors retained as separate bodies (component grouping unavailable: %s)" % e
            return
        state["label_component"] = occ.component
        for b in labels + floors:
            body_name = b.name
            try:
                moved = b.moveToComponent(occ)
                if not moved or not moved.isValid:
                    raise RuntimeError("moveToComponent returned no valid body")
            except Exception as e:
                steps.problems.append("Moving %s failed: %s" % (body_name, e))
        state["labels"] = named_bodies(occ.component, "Labels") + named_bodies(root, "Labels")
        state["floors"] = named_bodies(occ.component, "Floor s") + named_bodies(root, "Floor s")
    steps.run("Labels component", component)

    def colours():
        # Body overrides AFTER moveToComponent; refresh handles from both components.
        comp = state.get("label_component")
        state["labels"] = named_bodies(root, "Labels") + (named_bodies(comp, "Labels") if comp else [])
        state["floors"] = named_bodies(root, "Floor s") + (named_bodies(comp, "Floor s") if comp else [])
        state["bin"] = root.bRepBodies.itemByName("Bin")
        set_appearance(design, [state["bin"]], "SocketBin - bin %02X%02X%02X" % BIN_RGB, BIN_RGB)
        for b in state["labels"] + state["floors"]:
            try:
                set_appearance(design, [b], "SocketBin - labels %02X%02X%02X" % LABEL_RGB, LABEL_RGB)
                if not b.appearance:
                    raise RuntimeError("body appearance override missing")
                if b.name.startswith("Floor s"):
                    state["floors_colored"] += 1
            except Exception as e:
                steps.problems.append("Colouring %s failed: %s" % (b.name, e))
    steps.run("Appearances after move", colours)
    expected = len(plan["holes"]) if fi > 0 else 0
    state["floor_status"] = "Pocket floors: %d expected; %d created; %d colored." % (
        expected, state["floors_created"], state["floors_colored"])
    lab_exp = state.get("labels_expected", sum(1 for h in plan["holes"] if h["label"]))
    lab_made = len(state.get("labels") or [])
    state["label_status"] = "Labels: %d expected; %d created." % (lab_exp, lab_made)
    if lab_made != lab_exp:
        state["label_status"] = "WARNING - " + state["label_status"]
        steps.problems.append(state["label_status"])
    if state["floors_created"] != expected or state["floors_colored"] != expected:
        state["floor_status"] = "WARNING - " + state["floor_status"]
        steps.problems.append(state["floor_status"])
    steps.problems.extend(state["floor_failures"])
    state["hole_fail"] = hole_fail
    return state


def mesh_of(body):
    calc = body.meshManager.createMeshCalculator()
    calc.setQuality(adsk.fusion.TriangleMeshQualityOptions.VeryHighQualityTriangleMesh)
    m = calc.calculate()
    coords = [c * 10.0 for c in m.nodeCoordinatesAsDouble]
    return core.weld(coords, list(m.nodeIndices))


def export(design, state, plan, name, folder, steps, report_lines):
    os.makedirs(folder, exist_ok=True)
    out = []
    label_like = list(state.get("labels") or []) + list(state.get("floors") or [])
    # label_like = text label solids + pocket-floor disks; all go into ONE "Labels" part (extruder 2)
    bodies = [("Bin", state["bin"])] + [
        (("Labels" if i == 0 else "Labels %d" % (i + 1)), b) for i, b in enumerate(label_like)
    ]

    def orca():
        parts = []
        for n, b in bodies:
            v, t = mesh_of(b)
            parts.append((n, v, t))
        if len(parts) > 2:      # several label/floor bodies: merge into one Labels part (extruder 2)
            v, t = list(parts[1][1]), list(parts[1][2])
            for _, v2, t2 in parts[2:]:
                base = len(v); v += v2; t += [(a + base, b + base, c + base) for a, b, c in t2]
            parts = [parts[0], ("Labels", v, t)]
        f = os.path.join(folder, name + ".3mf")
        core.write_orca_3mf(f, name, parts, ("#%02X%02X%02X" % BIN_RGB, "#%02X%02X%02X" % LABEL_RGB))
        out.append(f)
    steps.run("Export 2-colour 3MF (Orca)", orca)
    if len(label_like) == 0:
        steps.problems.append("3MF has NO label or floor bodies (nothing to put on extruder 2)")

    def rep():
        f = os.path.join(folder, name + " - build report.txt")
        with open(f, "w", encoding="utf-8") as fh:
            fh.write("\n".join(report_lines) + "\n")
        out.append(f)
    steps.run("Write build report", rep)
    return out


# ------------------------------------------------------------------ settings (remembered between runs)
SETTINGS_FILE = os.path.join(_here, "socketbin_settings.json")

# Every dialog value with its default. Keys are plain python values (no Fusion objects) so the
# mapping to planner options can be unit-tested without Fusion.
DIALOG_DEFAULTS = dict(
    path="", name="",
    height_mm=40.0, height_units=0, max_depth=32.0,
    grid_auto=True, grid_x=4, grid_y=2, max_grid_x=6, max_grid_y=3,
    web=2.85, floor=3.0,
    adaptive=True, web_floor=1.2, outer_floor=1.5,
    export=True,
    label_height=5.0, label_gap=2.0, inlay_depth=1.0, floor_inlay=0.6,
)


def load_settings():
    v = dict(DIALOG_DEFAULTS)
    try:
        with open(SETTINGS_FILE, "r", encoding="utf-8") as fh:
            saved = json.load(fh)
        for k, dv in DIALOG_DEFAULTS.items():
            if k not in saved:
                continue
            sv = saved[k]
            if isinstance(dv, bool):
                if isinstance(sv, bool):
                    v[k] = sv
            elif isinstance(dv, str):
                if isinstance(sv, str):
                    v[k] = sv
            elif isinstance(sv, (int, float)) and not isinstance(sv, bool):
                v[k] = type(dv)(sv)
    except Exception:
        pass
    return v


def save_settings(v):
    try:
        with open(SETTINGS_FILE, "w", encoding="utf-8") as fh:
            json.dump({k: v[k] for k in DIALOG_DEFAULTS if k in v}, fh, indent=1)
    except Exception:
        pass            # remembering values is a convenience; never block a build


def options_from_values(v):
    """Dialog values -> planner/build options dict (same keys the old options line produced)."""
    o = dict(core.DEFAULTS, export=bool(v["export"]))
    o.update(
        height_mm=float(v["height_mm"]), height_units=int(v["height_units"]), max_depth=float(v["max_depth"]),
        min_web=float(v["web"]), floor_min=float(v["floor"]),
        adaptive_walls=bool(v["adaptive"]), min_web_floor=float(v["web_floor"]), min_outer_wall=float(v["outer_floor"]),
        floor_inlay=float(v["floor_inlay"]), label_height=float(v["label_height"]),
        label_gap=float(v["label_gap"]), inlay_depth=float(v["inlay_depth"]),
        max_grid_x=int(v["max_grid_x"]), max_grid_y=int(v["max_grid_y"]),
    )
    if v["grid_auto"]:
        o["grid_x"] = o["grid_y"] = 0
    else:
        o["grid_x"], o["grid_y"] = int(v["grid_x"]), int(v["grid_y"])
    return o


def validate_values(v, file_error=None):
    """List of plain-language problems with the dialog values (empty = OK). Same rules as before."""
    errs = []
    if file_error:
        errs.append(file_error)
    elif not v.get("path"):
        errs.append("Choose a sockets file (.xlsx or .csv).")
    try:
        check_options(options_from_values(v))
    except ValueError as e:
        errs.append(str(e))
    if not v["grid_auto"] and (v["grid_x"] < 1 or v["grid_y"] < 1):
        errs.append("Grid cells must be 1 or more in both directions.")
    if v["max_grid_x"] < 1 or v["max_grid_y"] < 1:
        errs.append("Largest auto grid must be 1 or more in both directions.")
    if v["label_height"] <= 0:
        errs.append("Label height must be greater than 0.")
    if v["label_gap"] < 0:
        errs.append("Label gap must not be negative.")
    if v["inlay_depth"] <= 0:
        errs.append("Label inlay depth must be greater than 0.")
    if len(core.clean_name(v.get("name", ""))) > 100:
        errs.append("Bin name is too long (100 characters max).")
    return errs


# ------------------------------------------------------------------ command dialog
CMD_ID = "SocketBinCmd"
EVENT_ID = "SocketBinBuildEvent"
_handlers = []          # keep EVERY handler referenced here or Fusion's Python will garbage-collect it
_ctx = dict(sel=None, file_error=None, auto_name="", pending=None, handed_over=False, event=None, cmddef=None, last_dir="")


def _get(inputs, iid):
    """Find an input by id, including those inside the Advanced group."""
    i = inputs.itemById(iid)
    if i is not None:
        return i
    grp = adsk.core.GroupCommandInput.cast(inputs.itemById("advGroup"))
    return grp.children.itemById(iid) if grp else None


def read_values(inputs):
    g = lambda i: _get(inputs, i)
    v = dict(DIALOG_DEFAULTS)
    sel = _ctx["sel"]
    v["path"] = sel["path"] if sel else ""
    v["name"] = g("name").value
    v["height_mm"] = float(g("height_mm").value)
    v["height_units"] = int(g("height_units").value)
    v["max_depth"] = float(g("max_depth").value)
    v["grid_auto"] = bool(g("grid_auto").value)
    v["grid_x"] = int(g("grid_x").value)
    v["grid_y"] = int(g("grid_y").value)
    v["max_grid_x"] = int(g("max_grid_x").value)
    v["max_grid_y"] = int(g("max_grid_y").value)
    v["web"] = float(g("web").value)
    v["floor"] = float(g("floor").value)
    v["adaptive"] = bool(g("adaptive").value)
    v["web_floor"] = float(g("web_floor").value)
    v["outer_floor"] = float(g("outer_floor").value)
    v["export"] = bool(g("export").value)
    v["label_height"] = float(g("label_height").value)
    v["label_gap"] = float(g("label_gap").value)
    v["inlay_depth"] = float(g("inlay_depth").value)
    v["floor_inlay"] = float(g("floor_inlay").value)
    return v


def _clamp(x, lo, hi):
    return max(lo, min(hi, x))


def _status_html(errs):
    if errs:
        return "<font color='#cc0000'><b>Fix before continuing:</b></font><br>" + "<br>".join("&bull; " + e for e in errs)
    return "<font color='#2e7d32'><b>Inputs OK.</b></font> Press OK to see the plan; nothing is built until you confirm it."


def _file_text():
    sel = _ctx["sel"]
    if sel:
        return "%s<br>(%d sockets)" % (sel["path"], len(sel["socks"]))
    return "<i>No file chosen</i>" + ("<br>" + _ctx["file_error"] if _ctx["file_error"] else "")


def _load_file(path):
    """Read the sockets list; returns True on success. Sets _ctx['sel'] / _ctx['file_error']."""
    try:
        socks, list_name = core.read_list(path)
    except core.ListError as e:
        _ctx["sel"] = None; _ctx["file_error"] = str(e)
        return False
    except Exception as e:
        _ctx["sel"] = None; _ctx["file_error"] = "Could not read %s: %s" % (path, e)
        return False
    _ctx["sel"] = dict(path=path, socks=socks, list_name=list_name)
    _ctx["file_error"] = None
    _ctx["last_dir"] = os.path.dirname(path)
    return True


def _sync_enabled(inputs):
    g = lambda i: _get(inputs, i)
    auto = g("grid_auto").value
    g("grid_x").isEnabled = not auto
    g("grid_y").isEnabled = not auto
    ad = g("adaptive").value
    g("web_floor").isEnabled = bool(ad)
    g("outer_floor").isEnabled = bool(ad)
    g("height_mm").isEnabled = int(g("height_units").value) == 0


def _refresh_status(inputs):
    try:
        v = read_values(inputs)
        _get(inputs, "status").formattedText = _status_html(validate_values(v, _ctx["file_error"]))
        _get(inputs, "file_text").formattedText = _file_text()
    except Exception:
        pass


class CreatedHandler(adsk.core.CommandCreatedEventHandler):
    def notify(self, args):
        try:
            cmd = args.command
            cmd.isExecutedWhenPreEmpted = False
            cmd.okButtonText = "Plan bin..."
            try:
                cmd.setDialogInitialSize(520, 760)
                cmd.setDialogMinimumSize(440, 520)
            except Exception:
                pass
            s = load_settings()
            _ctx["sel"] = None; _ctx["file_error"] = None; _ctx["auto_name"] = ""
            if s["path"] and os.path.isfile(s["path"]):
                _load_file(s["path"])
            elif s["path"]:
                _ctx["file_error"] = "Last file not found: %s" % s["path"]
            if s["path"]:
                _ctx["last_dir"] = os.path.dirname(s["path"])
            inp = cmd.commandInputs
            I = adsk.core
            inp.addTextBoxCommandInput("file_text", "Sockets file", _file_text(), 3, True)
            inp.addBoolValueInput("browse", "Browse for a different sockets file... (tick)", True, "", False)
            default_nm = core.default_name(_ctx["sel"]["path"], _ctx["sel"]["list_name"]) if _ctx["sel"] else ""
            nm = s["name"] or default_nm
            _ctx["auto_name"] = default_nm
            inp.addStringValueInput("name", "Bin name", nm)
            inp.addFloatSpinnerCommandInput("height_mm", "Total height (mm)", "", 0.0, 270.0, 1.0, _clamp(s["height_mm"], 0.0, 270.0))
            inp.addIntegerSpinnerCommandInput("height_units", "Height units override (0 = use mm)", 0, 38, 1, _clamp(s["height_units"], 0, 38))
            inp.addFloatSpinnerCommandInput("max_depth", "Max hole depth (mm, 0 = off)", "", 0.0, 500.0, 1.0, _clamp(s["max_depth"], 0.0, 500.0))
            inp.addBoolValueInput("grid_auto", "Grid: auto (smallest that fits)", True, "", bool(s["grid_auto"]))
            inp.addIntegerSpinnerCommandInput("grid_x", "Grid cells long (X)", 1, 6, 1, _clamp(s["grid_x"], 1, 6))
            inp.addIntegerSpinnerCommandInput("grid_y", "Grid cells deep (Y)", 1, 6, 1, _clamp(s["grid_y"], 1, 6))
            inp.addFloatSpinnerCommandInput("web", "Wall between holes / target (mm)", "", 0.0, 20.0, 0.05, _clamp(s["web"], 0.0, 20.0))
            inp.addFloatSpinnerCommandInput("floor", "Min floor under deepest hole (mm)", "", 0.1, 50.0, 0.5, _clamp(s["floor"], 0.1, 50.0))
            inp.addBoolValueInput("adaptive", "Adaptive walls (shrink only as needed)", True, "", bool(s["adaptive"]))
            inp.addFloatSpinnerCommandInput("web_floor", "   Thinnest wall between holes (mm)", "", 0.1, 20.0, 0.05, _clamp(s["web_floor"], 0.1, 20.0))
            inp.addFloatSpinnerCommandInput("outer_floor", "   Thinnest outer wall (mm)", "", 0.1, 20.0, 0.05, _clamp(s["outer_floor"], 0.1, 20.0))
            inp.addBoolValueInput("export", "Export one 3MF + build report", True, "", bool(s["export"]))
            grp = inp.addGroupCommandInput("advGroup", "Advanced")
            grp.isExpanded = False
            c = grp.children
            c.addFloatSpinnerCommandInput("floor_inlay", "Pocket-floor disk thickness (mm, 0 = off)", "", 0.0, 5.0, 0.1, _clamp(s["floor_inlay"], 0.0, 5.0))
            c.addFloatSpinnerCommandInput("label_height", "Label text height (mm)", "", 1.0, 30.0, 0.5, _clamp(s["label_height"], 1.0, 30.0))
            c.addFloatSpinnerCommandInput("label_gap", "Gap hole to label (mm)", "", 0.0, 20.0, 0.5, _clamp(s["label_gap"], 0.0, 20.0))
            c.addFloatSpinnerCommandInput("inlay_depth", "Label inlay depth (mm)", "", 0.1, 5.0, 0.1, _clamp(s["inlay_depth"], 0.1, 5.0))
            c.addIntegerSpinnerCommandInput("max_grid_x", "Largest auto grid, long (cells)", 1, 6, 1, _clamp(s["max_grid_x"], 1, 6))
            c.addIntegerSpinnerCommandInput("max_grid_y", "Largest auto grid, deep (cells)", 1, 6, 1, _clamp(s["max_grid_y"], 1, 6))
            inp.addTextBoxCommandInput("status", "Check", "", 4, True)
            _sync_enabled(inp)
            _refresh_status(inp)
            for cls, ev in ((ChangedHandler, cmd.inputChanged), (ValidateHandler, cmd.validateInputs),
                            (ExecuteHandler, cmd.execute), (DestroyHandler, cmd.destroy)):
                h = cls(); ev.add(h); _handlers.append(h)
        except Exception:
            _ui.messageBox("SocketBin dialog failed to open:\n%s" % traceback.format_exc(), TITLE)


class ChangedHandler(adsk.core.InputChangedEventHandler):
    def notify(self, args):
        try:
            inputs = args.inputs
            ch = args.input
            if ch.id == "browse":
                ch.value = False
                dlg = _ui.createFileDialog()
                dlg.title = "Socket list for the bin (.xlsx or .csv)"
                dlg.filter = "Socket lists (*.xlsx;*.csv);;Excel (*.xlsx);;CSV (*.csv);;All files (*.*)"
                dlg.isMultiSelectEnabled = False
                if _ctx["last_dir"] and os.path.isdir(_ctx["last_dir"]):
                    dlg.initialDirectory = _ctx["last_dir"]
                if dlg.showOpen() == adsk.core.DialogResults.DialogOK:
                    if _load_file(dlg.filename):
                        # follow the new file's name unless the user typed their own
                        nm = _get(inputs, "name")
                        new_auto = core.default_name(_ctx["sel"]["path"], _ctx["sel"]["list_name"])
                        if not nm.value or nm.value == _ctx["auto_name"]:
                            nm.value = new_auto
                        _ctx["auto_name"] = new_auto
            _sync_enabled(inputs)
            _refresh_status(inputs)
        except Exception:
            _ui.messageBox("SocketBin dialog error:\n%s" % traceback.format_exc(), TITLE)


class ValidateHandler(adsk.core.ValidateInputsEventHandler):
    def notify(self, args):
        try:
            args.areInputsValid = not validate_values(read_values(args.inputs), _ctx["file_error"])
        except Exception:
            args.areInputsValid = False


class ExecuteHandler(adsk.core.CommandEventHandler):
    def notify(self, args):
        try:
            v = read_values(args.command.commandInputs)
            save_settings(v)
            _ctx["pending"] = v
            _ctx["handed_over"] = True
            # Build outside the command (new document, message boxes): hand over via a custom event.
            _app.fireCustomEvent(EVENT_ID)
        except Exception:
            _ctx["pending"] = None
            _ctx["handed_over"] = False
            _ui.messageBox("SocketBin failed:\n%s" % traceback.format_exc(), TITLE)


class DestroyHandler(adsk.core.CommandEventHandler):
    def notify(self, args):
        # Cancel (no values handed over): end the script. After OK the build event ends it.
        if not _ctx["handed_over"]:
            _finish()


class BuildEventHandler(adsk.core.CustomEventHandler):
    def notify(self, args):
        again = False
        try:
            v = _ctx["pending"]
            _ctx["pending"] = None
            if v:
                again = (build_flow(v) == "retry")
        except Exception:
            _ui.messageBox("SocketBin failed:\n%s" % traceback.format_exc(), TITLE)
        _ctx["handed_over"] = False
        if again:
            try:
                _ctx["cmddef"].execute()        # reopen the dialog with the values just used
                return
            except Exception:
                _ui.messageBox("Could not reopen the SocketBin dialog:\n%s" % traceback.format_exc(), TITLE)
        _finish()


def _finish():
    """Release the event and command definition and end the script."""
    try:
        if _ctx.get("event"):
            _app.unregisterCustomEvent(EVENT_ID)
            _ctx["event"] = None
    except Exception:
        pass
    try:
        cd = _ui.commandDefinitions.itemById(CMD_ID)
        if cd:
            cd.deleteMe()
    except Exception:
        pass
    _ctx["cmddef"] = None
    del _handlers[:]
    try:
        adsk.terminate()
    except Exception:
        pass


# ------------------------------------------------------------------ plan + build (after the dialog)
def build_flow(v):
    """Plan, confirm and build from dialog values. Returns 'retry' to reopen the dialog."""
    try:
        sel = _ctx["sel"]
        path, socks = sel["path"], sel["socks"]
        name = core.clean_name(v["name"]) or core.clean_name(core.default_name(path, sel["list_name"])) or "Socket Bin"
        o = options_from_values(v)
        try:
            plan = core.plan(socks, **{k: x for k, x in o.items() if k in core.DEFAULTS})
        except core.NoFit as e:
            # Plain-language message (rail length needed, per-row overflow, next Gridfinity size).
            _ui.messageBox(e.human_message() + "\n\nThe dialog will reopen so you can change the options.", "%s - will not fit" % TITLE)
            return "retry"
        except ValueError as e:
            _ui.messageBox(str(e) + "\n\nThe dialog will reopen so you can change the options.", TITLE)
            return "retry"

        deepest = max(h["cut"] for h in plan["holes"])      # after the max_depth and height limits
        lines = ["SocketBin %s" % VERSION, "Bin name: " + name, "Socket list: %s (%d sockets)" % (path, len(socks))] + plan["report"] + \
                ["Total height %s mm; deepest hole as built %s mm; floor under it %s mm (minimum %s mm)." % (
                    core.num(plan["H"]), core.num(deepest), core.num(plan["top_z"] - deepest), core.num(o["floor_min"]))] + \
                ["WARNING: " + w for w in plan["warnings"]]
        if _ui.messageBox("\n".join(lines) + "\n\nBuild it in a new design?\n(No = go back and change the options)", TITLE,
                          adsk.core.MessageBoxButtonTypes.YesNoButtonType,
                          adsk.core.MessageBoxIconTypes.QuestionIconType) != adsk.core.DialogResults.DialogYes:
            return "retry"

        doc = _app.documents.add(adsk.core.DocumentTypes.FusionDesignDocumentType)
        try:
            doc.name = name          # read-only on some builds; the name is applied on first save anyway
        except Exception:
            pass
        design = adsk.fusion.Design.cast(_app.activeProduct)
        mode_note = None
        try:
            design.designType = adsk.fusion.DesignTypes.ParametricDesignType
        except Exception as e:      # Part Design documents do not allow switching; carry on
            mode_note = "Could not switch the new document to parametric mode (%s); building anyway." % e
        design.fusionUnitsManager.distanceDisplayUnits = adsk.fusion.DistanceUnits.MillimeterDistanceUnits
        try:
            design.rootComponent.name = name   # Fusion blocks renaming the root in some builds
        except Exception:
            pass

        steps = Steps(12 + 2 * len(plan["holes"]) + (2 if o.get("export") else 0))
        if mode_note:
            steps.problems.append(mode_note)
        try:
            state = build(design, plan, name, steps)
            lines.append(state["floor_status"])
            lines.append(state["label_status"])
            if state.get("grouping_note"):
                lines.append(state["grouping_note"])
            files = []
            if o.get("export"):
                folder = os.path.join(os.path.dirname(path), name)
                stamp = datetime.datetime.now().strftime("%Y-%m-%d %H:%M")
                files = export(design, state, plan, name, folder, steps,
                               ["Built %s by SocketBin.py %s (Fusion)" % (stamp, VERSION)] + lines +
                               (["PROBLEM: " + p for p in steps.problems] if steps.problems else []))
        finally:
            steps.close()
        msg = "\n".join(lines)
        if files:
            msg += "\n\nSaved:\n  " + "\n  ".join(files)
        if steps.problems:
            msg += "\n\nSome steps had problems (the rest of the bin was built):\n  - " + "\n  - ".join(steps.problems)
        msg += ("\n\nEditable in Modify > Change Parameters: total_height (mm, top_z follows), sNN_d / sNN_depth (hole sizes), "
                "inlay_depth, floor_inlay, top_round. The footprint and hole positions are fixed: rerun the script for a new list.")
        _ui.messageBox(msg, TITLE)
        return "done"
    except Abort as e:
        _ui.messageBox("Build stopped:\n%s" % e, TITLE)
    except Exception:
        _ui.messageBox("SocketBin failed:\n%s" % traceback.format_exc(), TITLE)
    return "done"


# ------------------------------------------------------------------ entry point
def run(context):
    global _app, _ui
    _app = adsk.core.Application.get()
    _ui = _app.userInterface
    try:
        adsk.autoTerminate(False)        # keep the script alive while the dialog / build event runs
        try:                             # a previous run that was killed may have left these behind
            _app.unregisterCustomEvent(EVENT_ID)
        except Exception:
            pass
        ev = _app.registerCustomEvent(EVENT_ID)
        h = BuildEventHandler(); ev.add(h); _handlers.append(h)
        _ctx["event"] = ev
        old = _ui.commandDefinitions.itemById(CMD_ID)
        if old:
            old.deleteMe()
        cd = _ui.commandDefinitions.addButtonDefinition(CMD_ID, "Socket Bin " + VERSION,
                                                        "Build a Gridfinity socket bin from a socket list", "")
        h = CreatedHandler(); cd.commandCreated.add(h); _handlers.append(h)
        _ctx["cmddef"] = cd
        cd.execute()
    except Exception:
        _ui.messageBox("SocketBin failed:\n%s" % traceback.format_exc(), TITLE)
        _finish()


def stop(context):
    try:
        _finish()
    except Exception:
        pass
