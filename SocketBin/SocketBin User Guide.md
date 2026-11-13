# SocketBin User Guide

*Version 1.3.0  -  a Fusion 360 script that builds Gridfinity socket bins from a spreadsheet*

## 1. What SocketBin does

SocketBin turns a simple list of your sockets (a spreadsheet or CSV file) into a ready-to-print Gridfinity-compatible socket bin in Fusion 360. For every socket it cuts a round pocket of the right diameter and depth, inlays a size label in front of it, and lays everything out in rows. It picks the smallest bin footprint that fits (up to 6 x 3 Gridfinity cells), then writes one multi-color 3MF file that you can open directly in Orca Slicer / Snapmaker Orca (or another slicer that reads 3MF parts).

- Gridfinity 42 mm grid. The bin is cells x 42 mm minus 0.5 mm, with the standard Gridfinity feet, so it is designed to fit Gridfinity baseplates. There is no stacking lip.
- Default total height is 40 mm, measured from the bottom of the feet to the top face (this includes the 5 mm foot/base).
- One round pocket per socket, with a 5 mm tall label inlaid flush with the top, 2 mm in front of each pocket.
- A thin colored disk is inlaid in the bottom of each pocket (default 0.6 mm) so the socket seat stays at the depth you entered.
- Adaptive walls: rows keep a 2.85 mm wall between pockets when there is room and only thin down (to 1.2 mm between pockets, 1.5 mm at the outer edge) when that lets more sockets fit.
- Everything is built as a normal parametric Fusion design, so you can still change the height and each pocket's size or depth afterwards.

## 2. Requirements

- Autodesk Fusion 360 (Windows or macOS). Scripts run in Fusion's own Python, so you do not install Python.
- A 3D printer that can print 42 mm Gridfinity bins. A multi-color / multi-filament printer is optional: the 3MF has two parts (Bin and Labels) so a multi-color printer can print the labels in a second color, and a single-color printer just prints both in one color.
- A spreadsheet or CSV list of your sockets with measured sizes (see section 7). Starter files are in the Starter Files folder.
- No internet connection, extra Python packages or admin rights are needed.

> **Note:** Tested by its author on Windows with Fusion 360. The macOS installer follows Fusion's standard script folder, but has not been tested on a Mac by the author. Always check the first print before filling a whole drawer.

## 3. Installing

### Windows (easiest)

1. Unzip SocketBin-1.3.0.zip anywhere (for example your Downloads folder).
2. Double-click Install-SocketBin.bat. No administrator rights are needed.
3. It copies the SocketBin folder to  %APPDATA%\Autodesk\Autodesk Fusion 360\API\Scripts\SocketBin . If SocketBin is already installed, the old copy is backed up first (to %APPDATA%\Autodesk\Autodesk Fusion 360\API\SocketBin-backups) and your remembered settings are kept.
4. If Fusion is already open, close and reopen the Scripts and Add-Ins window (or restart Fusion) so it sees the new script.

### macOS

1. Unzip SocketBin-1.3.0.zip.
2. Open Terminal, type  chmod +x  and a space, drag install.command into the window, and press Return. (Only needed if double-clicking says the file is not executable.)
3. Double-click install.command. If macOS blocks it because it was downloaded, right-click it, choose Open, then Open again.
4. It copies SocketBin to  ~/Library/Application Support/Autodesk/Autodesk Fusion 360/API/Scripts/SocketBin  and backs up any older copy.

### Manual install (any computer)

1. In Fusion 360 press Shift+S (or choose Utilities > Add-Ins > Scripts and Add-Ins).
2. On the Scripts tab, click the green + next to My Scripts and choose the SocketBin folder from the package (the folder that contains SocketBin.py). Fusion uses it where it is.
3. Or copy the SocketBin folder yourself into Fusion's Scripts folder (paths above). The folder must be named SocketBin and contain SocketBin.py and SocketBin.manifest side by side.

### Updating and uninstalling

To update, run the installer again from the newer package. To uninstall, run Uninstall-SocketBin.bat (Windows) or uninstall.command (macOS), or simply delete the SocketBin folder from the Scripts folder. Models and exports you already made are not touched.

## 4. First run walkthrough

1. Start Fusion 360 and press Shift+S to open Scripts and Add-Ins.
2. On the Scripts tab choose SocketBin and click Run.
3. In the dialog, tick "Browse for a different sockets file..." and pick your .xlsx or .csv list (try Starter Files > examples first). The path and the number of sockets read are shown.
4. Check the Bin name. It is used for the new design and for the output folder.
5. Leave the other fields at their defaults for a first try, then press "Plan bin...".
6. A plan window shows the bin size, each row of sockets, wall thicknesses, the deepest hole, and any warnings (for example a socket that was shortened to fit). Choose Yes to build, or No to go back and change the options.
7. SocketBin creates a new design and builds the bin. This takes a few seconds to about a minute depending on the number of sockets.
8. When it finishes, a summary lists any problems and the saved files. The 3MF and a build report are in a folder named after your bin, next to your sockets file.
9. Open the 3MF in your slicer (section 9).

## 5. The dialog, field by field

Your last used values and the last sockets file are remembered between runs (stored in socketbin_settings.json inside the SocketBin folder; delete that file to return to the defaults). A Check box at the bottom of the dialog explains any invalid value in plain language, and OK stays disabled until everything is valid.

| Field | Default | What it does |
|---|---|---|
| Sockets file | (none) | Tick the Browse box to choose your .xlsx or .csv. The file name, path and socket count are shown. Old .xls files must be re-saved as .xlsx or CSV. |
| Bin name | from the file | Name of the new design and of the output folder. Defaults to the list's "# name:" line, otherwise the file name (sockets.xlsx becomes "Socket Bin"). Characters Windows does not allow in names are replaced. |
| Total height (mm) | 40 | Overall height from the bottom of the feet to the top face, including the 5 mm foot, no lip. 0 = automatic: just tall enough for the deepest hole plus the minimum floor, rounded up to a 7 mm Gridfinity unit. Must be more than 5 mm + the minimum floor. |
| Height units override | 0 | Optional. A whole number of 7 mm Gridfinity height units (6 = 42 mm). 0 means use the Total height in mm. If you enter a number here it wins over the mm value. |
| Max hole depth (mm) | 32 | No pocket will be deeper than this. Deeper sockets are shortened to it and listed in the plan. 0 turns the limit off. The height also limits depth: a pocket can never be deeper than top face minus Min floor. |
| Grid: auto | on | On: SocketBin tries every footprint from 1 x 1 up to the largest auto grid and uses the smallest that fits (it must also fit a 270 x 270 mm bed, or it warns). Off: you choose the cells yourself. |
| Grid cells long (X) / deep (Y) | 4 / 2 | Used only when Grid auto is off. X is the long direction (left to right), Y is front to back. One cell = 42 mm. |
| Wall between holes / target (mm) | 2.85 | The wall SocketBin tries to keep between pockets and between a pocket and the outer edge. About 7 perimeters of a 0.4 mm nozzle. |
| Min floor under deepest hole (mm) | 3 | Material left under the deepest pocket. Used for the automatic height and for the depth limit. |
| Adaptive walls | on | On: a row only gets thinner walls when it has to. Off: walls never go below the target wall, which gives a bigger bin. |
| Thinnest wall between holes (mm) | 1.2 | The lowest wall thickness allowed between two pockets when adaptive walls is on (about 3 perimeters of a 0.4 mm nozzle). |
| Thinnest outer wall (mm) | 1.5 | The lowest wall thickness allowed between a pocket and the outside edge of the bin. |
| Export one 3MF + build report | on | Writes <bin name>.3mf and <bin name> - build report.txt into a folder named after the bin, next to your sockets file. Off: only the Fusion design is built. |
| Advanced: pocket-floor disk thickness (mm) | 0.6 | Thickness of the colored disk inlaid in each pocket bottom. 0 turns it off. If the minimum floor is too thin to keep 0.8 mm of bin material under the disk, it is reduced or disabled and the build report says so. |
| Advanced: label text height (mm) | 5 | Height of the label digits. |
| Advanced: gap hole to label (mm) | 2 | Space between a pocket's edge and its label. |
| Advanced: label inlay depth (mm) | 1 | How deep the labels are inlaid. They sit flush with the top. |
| Advanced: largest auto grid | 6 x 3 | Cells long x cells deep that automatic grid will try. 6 x 3 is 251.5 x 125.5 mm, within the 270 mm bed of the Snapmaker U1. |

## 6. Rows, layout and what the plan tells you

- Rows run from the front of the bin (row 1, where the labels are read) to the back. Sockets in a row are placed left to right in the order they appear in your file.
- If your file has a row number for a socket it goes in that row. Sockets with no row number are packed automatically into the remaining space, largest first.
- Each row is as tall as its largest pocket plus its label line.
- The plan reports each row's wall thickness: "web 2.833 mm (adapted from 2.85)" means that row was thinned slightly to fit.
- Warnings are not errors: a label may be wider than its slot, a pocket depth may have been limited, or the bin may be close to the printer bed edge. Read them before you press Yes.

## 7. Your sockets file

### Columns

The first row of the file must be a header row. The script reads these column names (not case sensitive; use underscores, no spaces):

| Column | Required | Meaning |
|---|---|---|
| label | yes | Text engraved in front of the pocket, such as 10 or 5/16 or 3/8. Keep it short (about 4 characters). |
| hole_diameter_mm | yes | Pocket diameter in millimetres (see "How to measure"). Also accepted as: diameter, hole_diameter, diameter_mm. |
| hole_depth_mm | yes | Pocket depth in millimetres. Also accepted as: depth, hole_depth, depth_mm. |
| row | no | Row number: 1 = front row, 2 = the row behind it, and so on. Leave blank to let SocketBin pack the rows. Also accepted as: row_hint. |

Sockets appear in the bin in the same order as the list, left to right. All sizes are in millimetres.

### Naming the bin and adding comments

- A line whose label is  # name: My Socket Bin  sets the default bin name. In a CSV put it above the header row or as an ordinary row; in a spreadsheet use an ordinary row below the header with the text in the label column.
- Any row whose label starts with # is ignored, so you can add notes.
- Empty rows are ignored. Only the first worksheet of an .xlsx file is read; extra sheets (such as the notes sheet in the starter files) are ignored.
- CSV files must be plain text with commas between columns (UTF-8). Excel's "CSV UTF-8" works. Use a dot for decimals (12.5, not 12,5).

### Example (CSV)

```
# name: My Quarter Drive Set
label,hole_diameter_mm,hole_depth_mm,row
10,17.5,20,1
11,18.5,20,1
12,19.5,20,
5/16,14,22,
```

### How to measure a socket

1. Use digital calipers. Measure the outside diameter (OD) of the socket at its widest point, usually at the open (wrench) end for deep sockets, or the thickest ring for impact sockets. Measure across a few angles and take the largest.
2. Add clearance: typically +0.4 to +0.6 mm for a snug fit that still lifts out easily. The hole_diameter_mm you enter is the pocket diameter, so enter OD + clearance. (Example: a 17.0 mm socket OD becomes 17.5 mm.)
3. For depth, measure from the open end of the socket to where you want its end to rest: the socket length if it should sit fully inside, or less if you want it to stand proud. Stand the socket upright in the pocket mentally: this is the depth.
4. Remember the limits: depth is capped by Max hole depth (32 by default) and by Total height minus the minimum floor (35 mm - 3 mm = 32 mm at the 40 mm default). Longer sockets are shortened and the plan tells you which ones.
5. Print one test pocket or a small bin first, then adjust the clearance for your printer.

> **Note:** The sample lists in Starter Files > examples are EXAMPLE values only. Socket sizes differ between brands and between shallow, deep and impact styles. Measure your own sockets.

## 8. What you get

### In Fusion

- A new design with a Bin body (dark) and the labels and pocket floors as separate bodies (light), grouped in a Labels component. In designs that allow only one component, they stay as separate bodies in that component.
- Editable parameters (Modify > Change Parameters > User): total_height (mm; the top face follows as total_height - 5 mm), sNN_d and sNN_depth (pocket diameter and depth of socket NN, in list order), inlay_depth, floor_inlay and top_round. pitch, clearance, grid_x, grid_y, max_depth, min_web_target, min_web_floor and min_outer_wall are there for reference only.
- The footprint and the pocket positions are fixed once built. For a different list or footprint, run SocketBin again.

### On disk (when Export is on)

A folder named after your bin is created next to your sockets file and contains:

- <bin name>.3mf: one object with two parts. Part 1 "Bin" is assigned to filament / extruder 1 and part 2 "Labels" (the label text and the pocket-floor disks together) to filament / extruder 2.
- <bin name> - build report.txt: the plan, the sizes, a count of labels and floors created, and a PROBLEM line for anything that failed.

No STL or STEP files are written. If you need them, export from Fusion yourself.

## 9. Slicing tips (Orca Slicer / Snapmaker Orca)

1. Open the 3MF. It should load as one object with two parts, Bin and Labels (if the slicer asks whether to load several parts as one object, choose Yes).
2. Assign your main color to the Bin part and your label color to the Labels part. The Labels part is both the letters and the thin disk at the bottom of each pocket.
3. The label inlay is 1 mm deep and flush with the top, so use a layer height of 0.2 mm or finer and make sure the top solid layers are not hidden by too thick a top surface setting.
4. Walls between pockets can be as thin as 1.2 mm. Use at least 3 wall loops with a 0.4 mm nozzle, and avoid features like fuzzy skin or very high wall speeds on the pocket walls.
5. Print right side up (feet on the bed). The bin is designed to print without supports.
6. Single-color printer: just assign the same filament to both parts, or print without a color change.
7. Turn on the prime/wipe tower for color changes, and check that the bin fits your bed (the plan warns if it is close to the edge).
8. Do a first print of a small list and check sockets for fit before printing a large bin.

## 10. Troubleshooting

| Problem | What to do |
|---|---|
| SocketBin is not listed in Scripts and Add-Ins | The folder must be named SocketBin and contain SocketBin.py and SocketBin.manifest side by side (not an extra folder level). Close and reopen the Scripts and Add-Ins window or restart Fusion. Or add the folder with the green + (manual install). |
| "These sockets don't fit..." message | No footprint up to the largest auto grid can hold the sockets even with the thinnest walls. The message lists the row that overflows, the rail length needed, and the next Gridfinity size. Raise the largest auto grid in Advanced (up to 6 x 6, but check your printer bed), move a socket to a different row, split the list into two bins, or lower the wall minimums. The dialog reopens with your values. |
| Warning: label may run into its neighbours | Long labels (such as 11/32) are wider than the space beside a small pocket. Shorten the label, put fewer sockets in that row (use the row column), allow a bigger grid, or reduce the label text height in Advanced. It is only a warning: the labels are still built. |
| A socket was shortened | The plan lists it. Raise Total height, raise Max hole depth, or reduce the minimum floor. A pocket can never be deeper than top face minus minimum floor. |
| "Labels: N expected; M created" / PROBLEM lines | Open the build report (or read the final summary). A PROBLEM line names the failing step and the script line. Try again; if it repeats, send the report to the person who gave you the script. Other parts of the bin are still built. |
| Labels are in Fusion but not in the 3MF (or colors wrong) | The 3MF assigns Bin to extruder 1 and Labels to extruder 2 by part. In your slicer check the part list and set the filament for each part. The report says how many labels and floors were exported. |
| Error about a list line | The message names the line and the missing value, for example no valid hole_diameter_mm. Fix the number and run again. Use a dot as the decimal separator. |
| Old .xls file | Open it in Excel and use File > Save As > Excel Workbook (.xlsx) or CSV. |
| Dialog values keep coming back | That is the remembered-settings feature. Delete socketbin_settings.json in the SocketBin folder to return to the defaults. |
| Edited the script and nothing changed | Fusion loads the script when you press Run, but if you changed it while Fusion was running, close the Scripts and Add-Ins window and run again (or restart Fusion). |
| Message about parametric mode | Some Fusion document types do not allow switching to parametric mode. The bin is still built; the user parameters may behave differently. |
| macOS: install.command will not run | Run  chmod +x install.command  in Terminal, then double-click it; or right-click it and choose Open. |
| Windows blocks the installer | Right-click the zip before unzipping, choose Properties, tick Unblock, and unzip again. Or use the manual install. |

## 11. Uninstalling

- Windows: run Uninstall-SocketBin.bat. It asks before removing the SocketBin folder from Fusion's Scripts folder.
- macOS: run uninstall.command.
- Or delete the SocketBin folder yourself from the Scripts folder (see Installing) and restart Fusion. Backups of earlier installs are in API/SocketBin-backups and can be deleted.
- Your designs and exported files are never removed.

## 12. Files in this package

| File | What it is |
|---|---|
| SocketBin/ | The Fusion script folder: SocketBin.py (dialog and Fusion geometry), socketbin_core.py (reading the list, layout, 3MF writer), SocketBin.manifest, README.txt, CHANGELOG.md. |
| Install-SocketBin.bat / .ps1 | Windows installer. Optional: -Target <folder> installs somewhere else (for testing). |
| Uninstall-SocketBin.bat / .ps1 | Windows uninstaller. |
| install.command / uninstall.command | macOS installer and uninstaller. |
| Starter Files/ | sockets-template.xlsx and .csv (blank starting points) and examples/ with sample lists. |
| SocketBin User Guide (.pdf / .md / .html) | This guide. |

SocketBin is provided as is, without warranty. Fusion 360 and Autodesk are trademarks of Autodesk, Inc. Gridfinity is a modular storage system designed by Zack Freedman.
