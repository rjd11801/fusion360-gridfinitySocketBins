# Hole gauge v12

v12 is a 206 × 206 × 10 mm plate for sizing sockets, bits, and dowels. Set the part in the holes and use the snug one: it lifts out and does not rattle. That diameter is what you enter as `hole_diameter_mm` in the SocketBin sockets file. Print with XY hole compensation at 0 so the bore stays the size on the plate.

Earlier iterations of this gauge existed. These files are v12.

The six plates in [Extended-30-60](../Extended-30-60/) continue the series. Plate 1 starts at Ø30. They cover Ø30–60 mm in 0.5 mm steps (61 holes) on the same 206 × 206 × 10 mm plate, with no plugs.

## Files

| File | Contents |
|---|---|
| `hole_gauge_v12_plate_only.3mf` | Plate and labels. Body is extruder 1, labels are extruder 4 (Snapmaker U1 head 1 and head 4). |
| `hole_gauge_v12_plate_with_plugs.3mf` | The same plate, plus eight plugs nested in the largest holes. |
| `hole_gauge_v12.step` | Plate, labels, and plugs as separate solids (`plate_body`, `label_hole_6` through `label_hole_29`, `plug_06_body` through `plug_20_body` and their labels). |

The plate-only 3MF body runs 0–206 mm in X and Y and 0–10 mm in Z. Its title is “Hole gauge v12 nominal 206mm”.

## Holes

48 bores, Ø6.0 through Ø29.5 mm in 0.5 mm steps, one of each. Rows are straight and ascend left to right. The smallest row is at the bottom (low Y); the largest is at the top.

| From the bottom | Diameters | Count |
|---|---|---|
| Row 1 | Ø6–11.5 | 12 |
| Row 2 | Ø12–16.5 | 10 |
| Row 3 | Ø17–20.5 | 8 |
| Row 4 | Ø21–24 | 7 |
| Row 5 | Ø24.5–27 | 6 |
| Row 6 | Ø27.5–29.5 | 5 |

Each bore sits in a tube whose outer diameter is the bore plus 4 mm (a 2 mm radial wall). The tubes stand on the floor and reach the top face. Neighboring tubes are 1.5 mm apart. Those are the same rules as the extended-plate generator: `TUBE = 4` and `GAP = 1.5` in `layout.py`, `FLOOR = 2` and `WALL = 2` in `build_ext.py`.

The floor is 2 mm thick (its top is at z = 2). Outer vertical corners are R5 and inner corners are R3, sharing centers 5 mm in from each edge, which is that 2 mm wall. The STEP also has radius-1 circles at z = 9, the R1 fillet `build_ext.py` puts on the top outer edge.

## Labels

Whole millimetres only, 6 through 29 (24 labels). Half-millimetre holes are unlabeled. Each label sits just above its hole, toward the top of the plate.

In the plate-only 3MF the label solids are 5.0 mm tall and 0.6 mm thick, from z = 1.4 to z = 2.0, flush with the floor. The file colors them black and assigns them to extruder 4. The extended-plate generator draws this same label style in DejaVu Sans Bold (CadQuery font size 6.6, inlay depth 0.6 mm).

## Plugs

Only `hole_gauge_v12_plate_with_plugs.3mf` (and the STEP) includes plugs. Eight of them, Plug 6, 8, 10, 12, 14, 16, 18, and 20, sit in the eight largest bores:

| Plug | Host bore |
|---|---|
| 6 | Ø26 |
| 8 | Ø26.5 |
| 10 | Ø27 |
| 12 | Ø27.5 |
| 14 | Ø28 |
| 16 | Ø28.5 |
| 18 | Ø29 |
| 20 | Ø29.5 |

Each plug mesh has a flange from z = 0 to z = 2 whose diameter is the plug size plus 4 mm, a stem of the named diameter from z = 2 to z = 14, and a 0.6 mm label on top (z = 14 to 14.6), 5.0 mm tall. Plug bodies are extruder 1 and plug labels are extruder 4.

## Extended plates

`Extended-30-60/build_ext.py` and `layout.py` generate the six continuation plates. `verification-ext.json` records them: plate 1 is Ø30–38.5 (18 holes), then Ø39–44.5 (12), Ø45–49 (9), Ø49.5–53.5 (9), Ø54–57 (7), and Ø57.5–60 (6). Each plate’s bounds in that file are 206 × 206 × 10 mm. Labels there are whole sizes only, body extruder 1 and black labels extruder 4, and there are no plugs.
