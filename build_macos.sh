#!/usr/bin/env bash
set -euo pipefail

ROOT="$(cd "$(dirname "$0")" && pwd)"
cd "$ROOT"

VERSION="1.8.0"
TMP_DIR="$(mktemp -d)"
ICONSET="$TMP_DIR/CodexShift.iconset"
ICNS="$TMP_DIR/CodexShift.icns"
trap 'rm -rf "$TMP_DIR"' EXIT

python3 -m unittest discover -s tests -v

mkdir -p "$ICONSET"
for size in 16 32 128 256 512; do
  sips -z "$size" "$size" assets/codexshift-logo.png --out "$ICONSET/icon_${size}x${size}.png" >/dev/null
  double=$((size * 2))
  sips -z "$double" "$double" assets/codexshift-logo.png --out "$ICONSET/icon_${size}x${size}@2x.png" >/dev/null
done
iconutil -c icns "$ICONSET" -o "$ICNS"

python3 -m PyInstaller --noconfirm --clean --windowed --target-arch universal2 \
  --name 'CodexShift' \
  --icon "$ICNS" \
  --add-data 'assets/codexshift-logo.png:assets' \
  --add-data 'assets/codexshift.ico:assets' \
  codex_switcher.py

codesign --force --deep --sign - dist/CodexShift.app
ditto -c -k --sequesterRsrc --keepParent dist/CodexShift.app "dist/CodexShift-v${VERSION}-macOS-Universal.zip"

echo "Build complete: $ROOT/dist/CodexShift-v${VERSION}-macOS-Universal.zip"
