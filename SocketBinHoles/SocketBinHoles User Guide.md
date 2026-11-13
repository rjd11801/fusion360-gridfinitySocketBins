# SocketBinHoles User Guide

*Version 1.1.0  -  a Fusion 360 script that cuts socket pockets and labels into a bin you already have*

## 1. What SocketBinHoles does

SocketBinHoles adds socket pockets and flush label inlays to a bin that is already open in Fusion 360: for example a solid Gridfinity blank you modelled or imported from a STEP file. You open the bin, click its large flat top face, pick your sockets list (.xlsx or .csv), and the script lays out the pockets, cuts them into that one body, and inlays a label in front of each pocket. It never creates a new bin, feet or an outer shape; the bin you selected is the only body that is cut.

- Fits the pockets into the exact top area of your blank (minus a small inset you choose), using adaptive walls: 2.85 mm between pockets when there is room, thinning to 1.2 mm between pockets and 1.5 mm at the outer edge only when needed.
- Uses your hole diameters and depths exactly. A pocket that is too deep for the blank is rejected with a clear message; nothing is silently shortened.
- Inlays a 5 mm bold label 2 mm in front of each pocket, 1 mm deep and flush with the top, as separate white label bodies.
- Optionally inlays a thin disk (default 0.6 mm) in each pocket bottom as a separate body, so it can be printed in the label color without changing the seat depth.
- Checks before cutting that every pocket is inside solid material (it will not break into a hollow bin or through a wall).
- If something goes wrong part-way, it tries to undo only what that run created.

### SocketBinHoles or SocketBin?

|  | SocketBin | SocketBinHoles |
|---|---|---|
| Starting point | A sockets list only | An existing bin design in Fusion plus a sockets list |
| Bin shape | Generated for you (Gridfinity, 42 mm pitch, feet, rounded corners) | Whatever you open; feet and exterior are left exactly as they are |
| Size | Auto-chooses the smallest Gridfinity footprint | Fixed by your blank; the list must fit it |
| Export | Writes a 3MF and build report | No automatic export; you export the bodies yourself |

The two scripts are independent. They install into separate folders and can be installed side by side.

## 2. Requirements

- Autodesk Fusion 360 (Windows or macOS). Scripts run in Fusion's own Python, so you do not install Python.
- A SOLID bin or blank design: not a hollow, open storage bin and not a mesh or surface body. The cuts need material to cut into.
- The bin's top face must be flat, face up (+Z), and be the highest surface of the body (no raised stacking lip). The body should be aligned to its component's XY axes.
- A sockets list in .xlsx or .csv (see section 7). Starter files are in the Starter Files folder.
- A multi-color printer is optional; a single-color printer simply prints the labels in the bin color.

> **Note:** Tested by its author on Windows with Fusion 360. The macOS installer follows Fusion's standard script folder but has not been tested on a Mac by the author. Always run it on a saved COPY of your design first, and check the first print.

## 3. Installing

### Windows (easiest)

1. Unzip SocketBinHoles-1.1.0.zip anywhere.
2. Double-click Install-SocketBinHoles.bat. No administrator rights are needed.
3. It copies the SocketBinHoles folder to  %APPDATA%\Autodesk\Autodesk Fusion 360\API\Scripts\SocketBinHoles . An older copy is backed up first to  %APPDATA%\Autodesk\Autodesk Fusion 360\API\SocketBinHoles-backups .
4. If Fusion is open, close and reopen the Scripts and Add-Ins window (or restart Fusion).

### macOS

1. Unzip SocketBinHoles-1.1.0.zip.
2. If double-clicking install.command says it cannot be opened, open Terminal, type  chmod +x  and a space, drag install.command into the window, and press Return.
3. Double-click install.command (if macOS blocks it, right-click it, choose Open, then Open again). It copies the script to  ~/Library/Application Support/Autodesk/Autodesk Fusion 360/API/Scripts/SocketBinHoles .

### Manual install

1. In Fusion press Shift+S (Utilities > Add-Ins > Scripts and Add-Ins).
2. On the Scripts tab click the green + next to My Scripts and choose the SocketBinHoles folder from this package (the folder that contains SocketBinHoles.py).
3. Or copy that folder yourself into Fusion's Scripts folder (paths above). Keep all its files together.

### Side by side with SocketBin

SocketBin and SocketBinHoles use separate folders and each loads its own socketbin_core.py file, so installing, updating or removing one never affects the other.

### Updating and uninstalling

Run the installer from a newer package to update. To uninstall run Uninstall-SocketBinHoles.bat (Windows) or uninstall.command (macOS), or delete the SocketBinHoles folder from the Scripts folder. Your designs are not touched.

## 4. First run walkthrough

1. Open the bin design in Fusion 360 (or import your STEP file). Save a copy first and run the script on the copy.
2. Press Shift+S, choose SocketBinHoles on the Scripts tab and click Run.
3. Read the first message and click OK. Then click the large flat TOP face of the bin. (If the bin is inside an assembly, clicking the face selects that component's body; edits apply to that component's original body and therefore to all its instances.)
4. The script checks the selection: it must be a solid body, the top must face +Z and be the highest surface of the body.
5. First input box: the measured size of the body is shown. Enter three values separated by commas: top inset, base-region height, minimum floor, in mm. Default 1,5,3 (explained in section 5).
6. Second input box: pocket-floor disk thickness in mm. Default 0.6. Enter 0 to skip the colored floors.
7. Choose your sockets .xlsx or .csv file.
8. A plan window lists the number of sockets and rows, the measured body size, the deepest hole, the floor left above the base, each row's wall thickness and any warnings. Choose Yes to cut, or No to stop without any change.
9. The script checks every pocket against the solid body, then cuts the pockets, the label pockets and the optional floor recesses, and creates the white label and floor bodies.
10. A final message reports how many pocket floors were expected, created and colored, how many holes and label solids were made, and any warnings. Save the result as a NEW design.

## 5. The inputs, one by one

| Input | Default | What it does |
|---|---|---|
| Top face | (you click it) | The large flat top face of the solid bin. It defines the surface the pockets are cut down from. The face must be planar, face +Z and be the highest part of the body (no stacking lip). |
| Top inset (first value) | 1 mm | Keeps the pockets this far in from every edge of the top face, as a safety margin for chamfers and side walls. The usable area is the body size minus twice this inset. Raise it for thick walls or large edge chamfers. It is not automatic wall detection. |
| Base-region height (second value) | 5 mm | The height at the bottom of the bin treated as base (feet). Pockets never go into this region. 5 mm is the Gridfinity foot height; check your model. |
| Minimum floor (third value) | 3 mm | Material kept above the base region under the deepest pocket. Maximum safe pocket depth = body height - base height - minimum floor (32 mm for a 40 mm tall bin with 5 and 3). |
| Pocket-floor disk thickness | 0.6 mm | A separate disk recessed into the bottom of each pocket, for printing in the label color. 0 = off. It is limited so at least 0.8 mm of original material stays above the base region; a very thin floor setting turns it off with a warning. The pocket seat depth does not change. |
| Sockets file | (you choose) | .xlsx or .csv, see section 7. |

The script rotates the layout automatically: the long side of the bin becomes the row direction. Sockets with a row number go in that row (row 1 is the front); others are packed automatically. Sockets stay in file order left to right within a row.

## 6. How the layout and checks work

- Usable area = body length and width minus twice the top inset. The exact measured size is used (it is not rounded to Gridfinity cells).
- Walls: each row keeps a 2.85 mm wall between pockets when there is room. Only if needed does it thin the walls, never below 1.2 mm between pockets and never below 1.5 mm between a pocket and the edge of the usable area (so at least 2.5 mm from the outside of the blank with the default inset).
- If a row does not fit, a message says which row, how long it needs to be, and what size blank would work. Nothing is changed.
- Depth: if any pocket is deeper than the safe depth, the script stops with a message showing the maximum safe depth and the overall height that would be required. No depths are shortened.
- Solid-blank check: before any change, each pocket (including the floor-disk recess) is tested against a temporary copy of the body. If a pocket would hit a hollow area or break through the outside, the script stops and names the socket.
- Labels are bold Arial, calibrated to about 5 mm actual letter height, inlaid 1 mm flush with the top, 2 mm in front of each pocket.

## 7. Your sockets file

The first row must be a header row. Column names (not case sensitive; underscores, no spaces):

| Column | Required | Meaning |
|---|---|---|
| label | yes | Text inlaid in front of the pocket, such as 10 or 5/16 or 3/8. Keep it short (about 4 characters). |
| hole_diameter_mm | yes | Pocket diameter in millimetres: measured socket outside diameter + about 0.5 mm clearance. Also accepted: diameter, hole_diameter, diameter_mm. |
| hole_depth_mm | yes | Pocket depth in millimetres. Also accepted: depth, hole_depth, depth_mm. |
| row | no | 1 = front row, 2 = the row behind it, and so on. Blank = packed automatically. Also accepted: row_hint. |

- A row whose label is  # name: My Bin  sets a bin name (SocketBinHoles does not need it). Any row whose label starts with # is ignored, so you can add notes.
- In .xlsx files only the first worksheet is read. CSV files must be plain UTF-8 text with commas and a dot for decimals.
- Measure the socket's widest outside diameter with calipers and add 0.4 to 0.6 mm clearance. Measure depth from the open end to where the socket should rest. Print a test first.
- The pockets can be at most the safe depth (section 5). With the defaults and a 40 mm tall bin that is 32 mm.

> **Note:** The files in Starter Files > examples contain EXAMPLE values only. Socket sizes differ between brands and styles; measure your own sockets.

### Which blank do the example lists fit?

With the default 1 mm inset and a 40 mm tall bin (5 mm base, 3 mm floor), these are the smallest Gridfinity blanks (cells long x cells deep) that SocketBinHoles' planner fits each starter list into. They were checked with the planner itself.

| Starter file | Sockets | Smallest blank that fits |
|---|---|---|
| EXAMPLE-SAE-1-4in-drive.xlsx | 10 | 3 x 2 cells (125.5 x 83.5 mm) |
| EXAMPLE-metric-3-8in-drive-shallow-10-19mm.xlsx | 10 | 6 x 1 cells (251.5 x 41.5 mm) |
| EXAMPLE-two-rows-shallow-and-deep.xlsx | 20 | 5 x 2 cells (209.5 x 83.5 mm) |
| sockets-template.xlsx | 2 | 2 x 1 cells (83.5 x 41.5 mm) |

## 8. What you get

- Pockets: one sketch per socket (named Socket hole <label>) and one cut feature per socket (named Socket <label> D<diameter> depth<depth>) in the bin's component. To change a hole later, edit its sketch (position, diameter) or its extrusion feature (depth).
- Labels: separate white bodies named Labels, Labels 02, ... (letters can be several solids, which is normal) and matching 1 mm label pockets cut into the bin. The bin keeps its own appearance.
- Pocket floors (if enabled): separate bodies named Socket floor NN <id>, recessed into the pocket bottoms.
- Label and floor bodies are put in a component named Labels when Fusion allows it. In single-component Part Design documents they stay as separate named bodies in the same component. Either way they get the same white appearance.
- A construction plane (SocketBinHoles - top) at the top face. No files are written and nothing is saved automatically.

### Printing in several colors

1. Save the result as a new design.
2. Select the original bin body AND every Labels and Socket floor body, and export them together as one multi-part 3MF (File > Export, 3MF). Keep their common positions; do not arrange the letters separately.
3. In Orca Slicer / Snapmaker Orca assign the bin to the main filament and all Labels and Socket floor parts to the label filament.
4. Use 0.2 mm layers or finer and at least 3 wall loops with a 0.4 mm nozzle (walls can be 1.2 mm).

## 9. Troubleshooting

| Message / problem | What to do |
|---|---|
| SocketBinHoles is not listed in Scripts and Add-Ins | The folder must be named SocketBinHoles and contain SocketBinHoles.py and SocketBinHoles.manifest side by side. Reopen the Scripts and Add-Ins window or restart Fusion, or add the folder with the green +. |
| "Top must face component +Z" | Align the bin so its top points up in its component, or activate that component, in a saved copy and try again. |
| "Selected face is not the highest top surface" | Choose the topmost flat face. Bins with a raised stacking lip are not supported; use a flat solid blank. |
| "Select a solid BRep body" | The selected body is a mesh or surface. Convert it to a solid first. |
| "These sockets don't fit on a ... mm rail" | The message names the row that is too long and the rail length needed. Use a bigger blank, reduce the top inset, move a socket to another row with the row column, or split the list. |
| "Bin too short: maximum safe depth ..." | A pocket is deeper than body height - base height - minimum floor. Use a taller blank, reduce the minimum floor, or shorten the depth in your list. Nothing is cut. |
| "Hole ... intersects a cavity or exterior" | The pocket would hit a hollow area or break through a wall. Use a solid blank, increase the top inset, or change the list. Nothing was cut. |
| Run failed at <stage> with a traceback | The script tries to delete only what that run created. If it says rollback is incomplete, close WITHOUT saving and reopen your saved copy. Send the full message to the person who gave you the script. |
| "Pocket floors: N expected / M created" shows a WARNING | Some floor disks failed; the listed warnings say which. The bin and the other floors are fine. Rerun on a fresh copy if you need all of them. |
| Labels are not white or are missing a color | Check the Labels and Socket floor bodies in the browser; the final message lists appearance warnings. |
| Instances of the component also changed | A component used several times shares one body, so every instance changes. Make the component independent first if you do not want that. |

## 10. Limits

- For a solid Gridfinity-style blank only; it does not fill cavities, cap an open bin or change the footprint.
- The label calibration assumes Arial Bold; font substitution may differ slightly between computers.
- Planning is from the file at run time; there is no live link to the spreadsheet.
- Not print-tested by the author on every Fusion version. Test on a copy and check your first print.

## 11. Uninstalling

- Windows: run Uninstall-SocketBinHoles.bat. macOS: run uninstall.command. Or delete the SocketBinHoles folder from the Scripts folder.
- Backups of earlier installs are in API/SocketBinHoles-backups and can be deleted.
- Designs you already changed are not affected.

## 12. Files in this package

| File | What it is |
|---|---|
| SocketBinHoles/ | The Fusion script folder: SocketBinHoles.py (dialogs and Fusion operations), holes_layout.py (fits your list to the blank), socketbin_core.py (reads the list, planner), SocketBinHoles.manifest, README.md, CHANGELOG.md. |
| Install-SocketBinHoles.bat / .ps1 | Windows installer. Optional -Target <folder> installs elsewhere (for testing). |
| Uninstall-SocketBinHoles.bat / .ps1 | Windows uninstaller. |
| install.command / uninstall.command | macOS installer and uninstaller. |
| Starter Files/ | sockets-template.xlsx and .csv and examples/ with sample lists. |
| SocketBinHoles User Guide (.pdf / .md / .html) | This guide. |

Provided as is, without warranty. Fusion 360 and Autodesk are trademarks of Autodesk, Inc. Gridfinity is a modular storage system designed by Zack Freedman.
