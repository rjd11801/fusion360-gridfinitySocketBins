SocketBin 1.3.0 - Fusion 360 script
=================================

Builds a Gridfinity socket bin from a list of your sockets (.xlsx or .csv): one pocket per socket,
inlaid size labels, adaptive wall thickness, and one two-colour 3MF for Orca Slicer / Snapmaker Orca.

Files (keep them together in a folder named SocketBin):
  SocketBin.py        the Fusion script (dialog, geometry, export)
  socketbin_core.py   reads the list, plans the layout, writes the 3MF (plain Python)
  SocketBin.manifest  tells Fusion this is a script
  README.txt          this file
  CHANGELOG.md        version history

Install: use the installer in the package (Install-SocketBin.bat on Windows, install.command on Mac),
or copy this folder to
  Windows: %APPDATA%\Autodesk\Autodesk Fusion 360\API\Scripts\SocketBin
  Mac:     ~/Library/Application Support/Autodesk/Autodesk Fusion 360/API/Scripts/SocketBin
or in Fusion press Shift+S, click the green + next to My Scripts and choose this folder.

Run: Shift+S > Scripts > SocketBin > Run. A dialog asks for the sockets file, bin name, height and other
options (defaults: total height 40 mm, max hole depth 32 mm, automatic grid, 2.85 mm walls, 3 mm floor,
adaptive walls 1.2 / 1.5 mm, export a 3MF). Your last values are remembered in socketbin_settings.json
in this folder (delete it to reset).

Sockets file columns: label, hole_diameter_mm, hole_depth_mm, and optional row (1 = front row).
Starter files and the full SocketBin User Guide are in the package (Starter Files, SocketBin User Guide).

Output (next to your sockets file, in a folder named after the bin):
  <bin name>.3mf                 Bin = extruder 1; labels + pocket floors = extruder 2
  <bin name> - build report.txt  plan, counts and any PROBLEM lines
Editable in Fusion (Modify > Change Parameters): total_height, sNN_d, sNN_depth, inlay_depth, floor_inlay, top_round.
