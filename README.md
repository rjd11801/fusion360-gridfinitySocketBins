# fusion360-gridfinitySocketBins

Fusion 360 scripts that turn a spreadsheet of your sockets into Gridfinity socket bins: round pockets, flush size labels, and optional colored pocket floors. Printable [hole sizing gauges](HoleGauges/README.md) measure the snug diameter to enter in that spreadsheet.

**Author:** Roland Diaz (GitHub [@rjd11801](https://github.com/rjd11801))

## Contents

- [SocketBin and SocketBinHoles](#which-script-to-use) — Fusion scripts that build a bin, or cut holes into a bin you already have.
- [Hole sizing gauges](HoleGauges/README.md) — 3D-printable plates, Ø6–60 mm in 0.5 mm steps, for measuring the diameter that goes in the sockets file.
- [Sockets file](#sockets-file) — spreadsheet columns the scripts read.
- [Install](#install) — Windows installer, macOS installer, or Utilities > Scripts and Add-Ins > +.

## Which script to use

| | SocketBin 1.3.0 | SocketBinHoles 1.1.0 |
|---|---|---|
| Start from | A sockets list only | A solid bin already open in Fusion, plus a sockets list |
| What it builds | A new Gridfinity bin: body, feet, pockets, colored hole floors, and labels | Pockets, labels, and optional colored hole floors cut into the body you select |
| Size | Smallest Gridfinity footprint that fits (42 mm grid, up to 6 x 3 cells by default) | Fixed by your blank. The list has to fit that top face |
| Export | One 2-part 3MF (Bin on extruder 1; labels and pocket floors on extruder 2) plus a build report | No automatic export. Export the bin and the label/floor bodies yourself |

Use **SocketBin** when you want a complete bin generated in a new design. Use **SocketBinHoles** when the bin body already exists (a Gridfinity blank you modeled or imported) and you only want the holes and labels. The two scripts install into separate folders and can sit side by side.

- [SocketBin User Guide](<SocketBin/SocketBin User Guide.md>) ([PDF](<SocketBin/SocketBin User Guide.pdf>), [HTML](<SocketBin/SocketBin User Guide.html>))
- [SocketBinHoles User Guide](<SocketBinHoles/SocketBinHoles User Guide.md>) ([PDF](<SocketBinHoles/SocketBinHoles User Guide.pdf>), [HTML](<SocketBinHoles/SocketBinHoles User Guide.html>))

Each package also has a short `START HERE.txt`.

## Hole sizing gauges

Print a gauge, drop the socket (or a bit or dowel) into the holes, and use the snug diameter as `hole_diameter_mm`. The plates are 206 × 206 × 10 mm and cover Ø6–60 mm in 0.5 mm steps: one v12 plate from Ø6 to Ø29.5 mm (with an optional set of plugs), then six extended plates from Ø30 to Ø60 mm. Labels are a second filament in the multi-material 3MF.

The 3MF files, the diameter table, and print settings (body on extruder 1, labels on extruder 4, XY hole compensation at 0, smallest holes at the bottom) are in [HoleGauges/README.md](HoleGauges/README.md).

## Requirements

- [Autodesk Fusion 360](https://www.autodesk.com/products/fusion-360/) on Windows or macOS. The scripts run in Fusion's own Python, so you do not install Python or extra packages, and the installers do not need administrator rights.
- A 3D printer that can print a 42 mm Gridfinity bin. A multi-color (multi-filament) printer is optional: the label text and pocket-floor disks are separate from the bin body, so a multi-color printer can print them in a second color, and a single-color printer prints everything in one color.
- A sockets list as `.xlsx` or `.csv`. Starter templates and example lists are in each package's `Starter Files` folder. Example sizes are placeholders. Measure your own sockets, or print the [hole sizing gauges](HoleGauges/README.md) and enter the snug hole.

## Install

Download this repository (Code > Download ZIP) or clone it:

```bash
git clone https://github.com/rjd11801/fusion360-gridfinitySocketBins.git
```

**Windows.** Double-click the installer in the package you want. No administrator rights are needed.

- `SocketBin/Install-SocketBin.bat`
- `SocketBinHoles/Install-SocketBinHoles.bat`

**macOS.** Double-click:

- `SocketBin/install.command`
- `SocketBinHoles/install.command`

If macOS says the file cannot be opened, run `chmod +x` on it in Terminal (these files are marked executable in git), or right-click the file and choose Open.

Each installer copies the inner script folder into Fusion's per-user Scripts folder:

- Windows: `%APPDATA%\Autodesk\Autodesk Fusion 360\API\Scripts`
- macOS: `~/Library/Application Support/Autodesk/Autodesk Fusion 360/API/Scripts`

**Manual add.** In Fusion 360 choose **Utilities > Scripts and Add-Ins > +** and select the inner script folder (the one that contains the `.py` and `.manifest` files):

- `SocketBin/SocketBin`
- `SocketBinHoles/SocketBinHoles`

The package folder and the script folder share a name. Fusion needs the inner folder, with `SocketBin.py` beside `SocketBin.manifest` (or `SocketBinHoles.py` beside `SocketBinHoles.manifest`).

Then press Shift+S, open the Scripts tab, pick the script, and click Run. If Fusion was already open when you used an installer, close and reopen Scripts and Add-Ins so it sees the new script.

To remove a script, run the matching uninstaller (`Uninstall-SocketBin.bat` / `uninstall.command`, or `Uninstall-SocketBinHoles.bat` / `uninstall.command`), or delete that script's folder from Fusion's Scripts folder. Designs and exported files are left alone.

## Sockets file

The first row is a header. Column names are not case sensitive; use underscores and no spaces. All sizes are millimetres. Only the first worksheet of an `.xlsx` file is read. CSV files are comma-separated UTF-8, with a dot for decimals (`12.5`).

| Column | Required | Meaning |
|---|---|---|
| `label` | yes | Text in front of the pocket, such as `10`, `5/16`, or `3/8`. Keep it short (about 4 characters). |
| `hole_diameter_mm` | yes | Pocket diameter. Also accepted: `diameter`, `hole_diameter`, `diameter_mm`. Measure the socket's widest outside diameter and add about 0.4–0.6 mm clearance, or enter the snug hole from a [hole sizing gauge](HoleGauges/README.md). |
| `hole_depth_mm` | yes | Pocket depth. Also accepted: `depth`, `hole_depth`, `depth_mm`. |
| `row` | no | Row number. `1` is the front row. Leave blank to let the script pack the row. Also accepted: `row_hint`. |

Sockets stay in file order, left to right. A row whose label is `# name: My Socket Bin` sets SocketBin's default bin name. Any label that starts with `#` is a comment, and empty rows are ignored.

```csv
# name: My Quarter Drive Set
label,hole_diameter_mm,hole_depth_mm,row
10,17.5,20,1
11,18.5,20,1
5/16,14,22,
```

Starter files (the same lists are in both packages):

- `Starter Files/sockets-template.xlsx` and `sockets-template.csv`
- `Starter Files/examples/` — sample SAE, metric, and two-row lists

How the pockets are measured, how walls adapt, and how to slice the 3MF are in the user guides linked above.
