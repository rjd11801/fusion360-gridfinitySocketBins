# SocketBinHoles — existing Fusion bin only

Independent of SocketBin (which generates whole bins). This script never generates feet or resizes the source bin.

## Install on Windows
Copy this entire folder to:
`%APPDATA%\Autodesk\Autodesk Fusion 360\API\Scripts\SocketBinHoles\`

Keep these together: `SocketBinHoles.py`, `SocketBinHoles.manifest`, `socketbin_core.py`, `holes_layout.py`, `README.md`.
In Fusion: Utilities → Scripts and Add-Ins → Scripts → SocketBinHoles → Run.
If it is not listed, use the + / Add control and select the folder.

## Use
1. Open your existing bin design (or import the STEP). SAVE A COPY before running.
2. Select the large planar TOP face of the solid blank. Occurrence selections are resolved to their native component, so edits affect that component's instances.
3. The body must be aligned to its component XY axes and top facing +Z. A raised stacking lip or tilted bin is rejected. Align the model in a saved copy if necessary.
4. Review measured body dimensions. Enter `top inset,base height,floor minimum` in mm. Defaults `1,5,3`: a 1 mm top perimeter exclusion, 5 mm base region from the bottom, and 3 mm material ABOVE that region. Increase inset for your actual sidewalls/chamfers. These are safety assumptions, not automatic wall detection.
5. Pick sockets .xlsx or .csv. Columns match SocketBin: label, hole_diameter_mm, hole_depth_mm, optional row. Hinted rows and list order are retained; long dimension is automatically the row direction.
6. Review the plan, then confirm. Hole diameters/depths are used exactly; too-deep holes are REJECTED, never shortened. A temporary-BRep intersection test rejects holes that would intersect an existing cavity or break through the exterior.
7. The original selected body receives hole cuts and 1 mm flush text pockets. White text solids remain separately named Labels, Labels 02, etc. Disconnected characters may be multiple solids (normal in CAD). No other body is a cut participant. Original bin appearance is retained.
8. Save as a new Fusion design. To print in multiple colors, select original bin plus ALL Labels bodies and export together as a multi-part 3MF; in Snapmaker Orca retain their common positions and assign the label parts to white. Do not auto-arrange the individual letters separately.

Labels are bold Arial, calibrated to about 5 mm actual glyph height. Font substitution can differ slightly between systems. Features and sketches remain in the existing design, not a new bin generator. Hole positions/diameters can be edited in their sketches; depths in extrusion features. Planning is file-driven, not a live spreadsheet link.

## Limits and recovery
- Intended for a solid Gridfinity top/blank, NOT a hollow open storage bin. It does not fill cavities, cap an open bin or modify its footprint.
- Default base region 5 mm must be checked against your model.
- Original bodies in repeated component occurrences are shared: all instances update. Make the component independent first if that is not wanted.
- On failure the script attempts to delete only this run's features/sketches/plane in reverse order. If rollback is incomplete, close WITHOUT saving and reopen your saved copy. First test on a copy.
- No auto-export, automatic saving, or printer compensation.
- Python syntax and pure-Python planning have been tested. Fusion's adsk runtime and a printed result have NOT been tested outside the author's setup. Send the complete error message if your Fusion version rejects an API call.


## Label-coloured socket floors
After the existing safety dialog, enter pocket-floor inlay thickness (default **0.6 mm**, **0 = off**).
The tool recesses a separate disk into each existing pocket floor: diameter and seating depth do not change.
The existing minimum-floor safety setting caps the inlay to leave at least 0.8 mm of original material above the base region; very thin settings disable it with a warning.
Solid-blank preflight includes the inlay region as well as the hole, before edits begin.
Text and floor bodies move into a Labels component, then receive the SAME white label appearance at body level.
Export the selected original bin plus every Labels-component body together, retaining common coordinates;
assign the floor disks to the same filament as the text. This script still does not auto-export or bundle printer settings.
The completion dialog reports expected/created/colored floor counts, even without exporting. Warnings identify failed disks or appearances.
On an individual floor failure its recess and disk are rolled back; other successful floors remain and a warning is shown.
Python/static checks only: the added features have not been tested in Fusion or printed.

PART DESIGN COMPATIBILITY
Creating a Labels component is optional. In single-component Part Design documents,
text and floor inlays remain separate named bodies in the existing component;
label appearance is still assigned directly to each body. Component-grouping failure
does not roll back the holes or floors. Assembly designs may use a Labels component.
SocketBin automatic 3MF export groups text and floor meshes from body lists, not
component membership, so both document types retain the same label filament mapping.
SocketBinHoles manual export: select the original bin plus ALL Labels and Socket floor
bodies together, retain common coordinates, and assign floors the same filament as text.
