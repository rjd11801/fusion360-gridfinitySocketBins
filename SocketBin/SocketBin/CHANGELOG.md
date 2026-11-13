# SocketBin changelog

## 1.3.0
- Command dialog with separate inputs (sockets file, bin name, total height, height units override, max hole depth, grid, walls, floor, adaptive walls, export, Advanced group). Inputs are validated with plain-language messages. Last values are remembered in socketbin_settings.json.
- Plan confirmation unchanged; "No" or a "will not fit" message reopens the dialog with your values.

## 1.2.1
- Export is one 3MF (bin = extruder 1; label solids + pocket floors = Labels part, extruder 2) plus a build report. No STL or STEP files.
- Label solids are extruded one text at a time and cut with a single combine-cut. Dialogs and the report show "Labels: N expected; N created"; failed steps include the script line.

## 1.2.0
- Default total height 40 mm (height_mm); Gridfinity units still available as an override. total_height Fusion parameter drives the bin (top_z = total_height - 5 mm).
- Max hole depth option (default 32 mm); clamped sockets are listed in the plan and report.

## 1.1.0
- Adaptive walls (target 2.85 mm, down to 1.2 mm between holes and 1.5 mm at the outer edge), plain-language "will not fit" message, single version source.

## 1.0
- First release.
