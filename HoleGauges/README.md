# Hole sizing gauges

Print a plate, then drop a socket, driver bit, or dowel into the holes until you find the snug one: it lifts out cleanly and does not rattle. Enter that diameter as `hole_diameter_mm` in the [SocketBin sockets file](../README.md#sockets-file). Whole-millimetre holes are labeled. Half-millimetre holes sit between those labels.

Every file in this folder is a multi-material 3MF of a 206 × 206 × 10 mm plate. Rows ascend across the plate, with the smallest holes at the bottom. The body is extruder 1 and the black inlaid labels are extruder 4 (Snapmaker U1 head 1 and head 4).

## Plates

| File | Diameters | Holes | Plugs |
|---|---|---|---|
| [hole_gauge_v12_plate_only.3mf](hole_gauge_v12_plate_only.3mf) | Ø6–29.5 mm | 48 | none |
| [hole_gauge_v12_plate_with_plugs.3mf](hole_gauge_v12_plate_with_plugs.3mf) | Ø6–29.5 mm | 48 | 8 plugs, Ø6–20 mm in steps of 2, nested in the largest holes |
| [hole_gauge_ext_plate1_30-38p5.3mf](hole_gauge_ext_plate1_30-38p5.3mf) | Ø30–38.5 mm | 18 | none |
| [hole_gauge_ext_plate2_39-44p5.3mf](hole_gauge_ext_plate2_39-44p5.3mf) | Ø39–44.5 mm | 12 | none |
| [hole_gauge_ext_plate3_45-49.3mf](hole_gauge_ext_plate3_45-49.3mf) | Ø45–49 mm | 9 | none |
| [hole_gauge_ext_plate4_49p5-53p5.3mf](hole_gauge_ext_plate4_49p5-53p5.3mf) | Ø49.5–53.5 mm | 9 | none |
| [hole_gauge_ext_plate5_54-57.3mf](hole_gauge_ext_plate5_54-57.3mf) | Ø54–57 mm | 7 | none |
| [hole_gauge_ext_plate6_57p5-60.3mf](hole_gauge_ext_plate6_57p5-60.3mf) | Ø57.5–60 mm | 6 | none |

Together the plates cover Ø6–60 mm in 0.5 mm steps. `hole_gauge_v12_plate_with_plugs.3mf` is the same 48-hole plate as `hole_gauge_v12_plate_only.3mf`, with the eight plugs added. The six extended plates have no plugs.

## How to use it

1. Print the plate that covers the size you need. Use the plate-only v12 file when you do not want the plugs.
2. Set the socket, bit, or dowel in nearby holes.
3. The snug hole is the diameter to write down. Read the whole-millimetre label beside that row; the unlabeled hole between two labels is the half millimetre.
4. Put that number in `hole_diameter_mm`.

## Printing

- Each plate is 206 × 206 × 10 mm. Print it flat, floor on the bed, with the smallest holes at the bottom.
- Body is extruder 1. Labels are extruder 4, meant for a black second filament. On a single-color printer, assign both parts to the same filament.
- Keep XY hole compensation at 0. A compensation value changes every bore, and the number on the plate no longer matches the hole you measured.
- Load the 3MF as one multi-part object and keep the body and labels in the same place.
