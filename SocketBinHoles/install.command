#!/bin/bash
# SocketBinHoles installer (macOS). Copies the SocketBinHoles folder next to this file into Fusion 360's Scripts folder.
# If double-clicking says the file cannot be opened: run  chmod +x install.command  in Terminal first.
# Set SOCKETBIN_TARGET=<folder> to install somewhere else (for testing).
set -e
DIR="$(cd "$(dirname "$0")" && pwd)"
SRC="$DIR/SocketBinHoles"
SCRIPTS="${SOCKETBIN_TARGET:-$HOME/Library/Application Support/Autodesk/Autodesk Fusion 360/API/Scripts}"
DEST="$SCRIPTS/SocketBinHoles"
BACKUPS="$(dirname "$SCRIPTS")/SocketBinHoles-backups"
pause() { if [ -z "$SOCKETBIN_NOPAUSE" ]; then echo; read -r -p "Press Return to close" _; fi; }
if [ ! -f "$SRC/SocketBinHoles.py" ]; then
  echo "ERROR: cannot find the SocketBinHoles folder next to this installer ($SRC)."
  echo "Unzip the whole package first, then run the installer from the unzipped folder."
  pause; exit 1
fi
echo "SocketBinHoles installer"
echo "  From: $SRC"
echo "  To:   $DEST"
mkdir -p "$SCRIPTS"
SETTINGS=""
if [ -d "$DEST" ]; then
  BAK="$BACKUPS/SocketBinHoles-$(date +%Y%m%d-%H%M%S)"
  mkdir -p "$BACKUPS"
  cp -R "$DEST" "$BAK"
  echo "  Existing install backed up to: $BAK"
  if [ -f "$DEST/socketbin_settings.json" ]; then SETTINGS="$(mktemp)"; cp "$DEST/socketbin_settings.json" "$SETTINGS"; fi
  rm -rf "$DEST"
fi
cp -R "$SRC" "$DEST"
if command -v xattr >/dev/null 2>&1; then xattr -dr com.apple.quarantine "$DEST" 2>/dev/null || true; fi
if [ -n "$SETTINGS" ]; then cp "$SETTINGS" "$DEST/socketbin_settings.json"; rm -f "$SETTINGS"; echo "  Your remembered settings were kept."; fi
echo
echo "Installed SocketBinHoles. In Fusion 360 press Shift+S, open the Scripts tab, pick SocketBinHoles and click Run."
echo "If Fusion was already open, close and reopen the Scripts and Add-Ins window first."
pause
