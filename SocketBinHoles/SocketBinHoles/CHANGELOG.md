# SocketBinHoles changelog

## 1.1.0 — 2026-11-09
- Adaptive walls are ON by default: each row keeps the target web (2.85 mm) when space allows, and only shrinks as needed.
- Interior webs between sockets may shrink down to 1.2 mm (~3 perimeters at a 0.4 mm nozzle).
- Outer walls (pocket edge to usable rail edge) have a hard minimum of 1.5 mm, independent of interior webs.
- When a row still cannot fit at those floors, Fusion shows a plain human-readable message (rail length needed, per-row overflow, next Gridfinity size) instead of a Python traceback. Technical detail stays in the exception text/log.
- Single version source: `socketbin_core.VERSION` (also written into the `.manifest` and shown in run dialogs).

## 1.0.0
- Initial SocketBinHoles release: holes + flush labels on an existing solid Gridfinity blank; optional pocket-floor inlays.
