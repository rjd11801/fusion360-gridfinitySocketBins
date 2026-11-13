#!/bin/bash
# SocketBin uninstaller (macOS). Removes the SocketBin folder from Fusion 360's Scripts folder.
# Your designs and exported files are not touched. Set SOCKETBIN_TARGET=<folder> and SOCKETBIN_YES=1 for testing.
SCRIPTS="${SOCKETBIN_TARGET:-$HOME/Library/Application Support/Autodesk/Autodesk Fusion 360/API/Scripts}"
DEST="$SCRIPTS/SocketBin"
pause() { if [ -z "$SOCKETBIN_NOPAUSE" ]; then echo; read -r -p "Press Return to close" _; fi; }
if [ ! -d "$DEST" ]; then echo "SocketBin is not installed at $DEST. Nothing to do."; pause; exit 0; fi
if [ ! -f "$DEST/SocketBin.manifest" ]; then echo "The folder $DEST does not look like SocketBin (no SocketBin.manifest). Not removing it."; pause; exit 1; fi
if [ -z "$SOCKETBIN_YES" ]; then
  read -r -p "Remove $DEST ? (y/N) " a
  case "$a" in y|Y|yes|YES) ;; *) echo "Cancelled."; pause; exit 0;; esac
fi
rm -rf "$DEST"
echo "SocketBin removed. Backups of earlier installs (if any) are in $(dirname "$SCRIPTS")/SocketBin-backups."
pause
