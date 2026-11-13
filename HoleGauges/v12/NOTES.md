# Hole gauge notes

The STEP and 3MF files in this folder are **v12**: a 206 × 206 × 10 mm plate with 48 holes from Ø6 to Ø29.5 mm. How to print them is in [the gauge guide](../README.md).

The record below is the earlier **v8** build (a 266 mm plate, Ø6–37 mm), kept for its print and glyph notes. Print the v12 models in this folder; their sizes are in the gauge guide linked above.

# Hole gauge v8 — build / print notes

Locked design from `layout-plan-v8.md`. Built with CadQuery (`build/build_hole_gauge_v8.py`) from `hole-layout-v8.json`.

## Files

| File | Contents |
|------|----------|
| `hole_gauge_v8.step` | Multi-body STEP (gauge plate + 8 plugs), Fusion-compatible |
| `hole_gauge_v8.3mf` | Multi-object 3MF (same bodies) |
| `hole_gauge_v8_plate_with_plugs.stl` / `.3mf` | Single-plate nest (gauge + plugs in host holes) for one print |
| `hole_gauge_v8_plate.stl` | Gauge only |
| `hole_gauge_v8_plug_XX.stl` | Individual plugs Ø06–20 |
| `verification-v8.json` | Counts + glyph clearance checks |

## Geometry (unchanged from v8)

- Plate: 266 × 266 × 10 mm open-top shell; 2 mm floor + 2 mm outer walls; R5 outer / R3 inner vertical corners; R1 top outside edge fillet
- 63 full-depth bores Ø6.0–37.0 mm step 0.5 mm; 2 mm radial tube walls to Z=10
- 32 whole-number floor labels engraved 0.6 mm (DejaVu Sans Bold, 5 mm glyph height)
- 8 even plugs Ø6–20 mm flange-down nested in hosts D+5; stem 12 mm + flange 2 mm + 0.6 mm embossed label

## U1 print tips (0.4 mm nozzle)

- **Layer height:** 0.2 mm (three layers through 0.6 mm relief)
- **Orientation:** floor / flange on bed, cavity and stems up; **no supports**
- **Small perimeters / top surfaces:** ~20–30 mm/s for readable text
- **Ironing:** not required
- Confirm label toolpaths get ≥2 extrusion widths before printing
- Watch elephant foot / brim bridges into plug flanges (0.5 mm radial air gap)
- Measure printed plug stems with calipers; first-layer squeeze affects bore clearance

## Glyph caveats

- DejaVu Sans Bold at 5 mm actual digit height: measured mid-glyph strokes ≈ 0.94–1.27 mm (≥ 0.8 mm target)
- **Ø6 plug:** axis-aligned label fits (edge clear X ≈ 1.08 mm, Y ≈ 0.5 mm); bbox *corner* hypothetically overhangs ~0.15 mm — digits stay inside the circular stem face in practice. Inspect in slicer.
- Floor labels sit in the 5 mm inter-row lanes; do not raise character height without relayout

## Deviations from v8 plan

- None intentional. CAD uses DejaVu Sans Bold as specified. R1 applied to outer top perimeter before cavity/tubes so tube rims stay sharp.

## Verification results

- STEP body count: **9** (1 gauge + 8 plugs)
- Gauge volume ≈ **178.2 cm³** (plan estimate was 178.9 cm³ before fillets/labels)
- Plate STL watertight; bounds 0–266 × 0–266 × 0–10 mm
- Plug overall height ≈ 14.6–14.8 mm (14 mm body + 0.6 mm emboss)
