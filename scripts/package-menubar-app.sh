#!/usr/bin/env bash
set -euo pipefail

SCRIPT_DIR="$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")" && pwd)"
ROOT_DIR="$(cd -- "$SCRIPT_DIR/.." && pwd)"
PACKAGE_DIR="$ROOT_DIR/macos/CodexTTSMenuBar"
INFO_TEMPLATE="$PACKAGE_DIR/AppResources/Info.plist.template"
DIST_DIR="$ROOT_DIR/dist"
APP_NAME="CodexTTS.app"
APP_DIR="$DIST_DIR/$APP_NAME"
APP_CONTENTS="$APP_DIR/Contents"
APP_MACOS="$APP_CONTENTS/MacOS"
APP_RESOURCES="$APP_CONTENTS/Resources"
ZIP_PATH="$DIST_DIR/CodexTTS.app.zip"

if [ ! -f "$INFO_TEMPLATE" ]; then
  echo "package-menubar-app: missing Info.plist template at $INFO_TEMPLATE" >&2
  exit 1
fi

swift build --package-path "$PACKAGE_DIR"
BIN_DIR="$(swift build --package-path "$PACKAGE_DIR" --show-bin-path)"
BIN_PATH="$BIN_DIR/CodexTTSMenuBar"

if [ ! -x "$BIN_PATH" ]; then
  echo "package-menubar-app: missing built executable at $BIN_PATH" >&2
  exit 1
fi

mkdir -p "$APP_MACOS" "$APP_RESOURCES"
rm -rf "$APP_DIR"
mkdir -p "$APP_MACOS" "$APP_RESOURCES"

APP_VERSION="$(awk -F ' = ' '/^version = / { gsub(/"/, "", $2); print $2; exit }' "$ROOT_DIR/pyproject.toml")"
APP_BUILD="$(git -C "$ROOT_DIR" rev-parse --short HEAD)"

cp "$BIN_PATH" "$APP_MACOS/CodexTTSMenuBar"
chmod +x "$APP_MACOS/CodexTTSMenuBar"
sed \
  -e "s/__APP_VERSION__/$APP_VERSION/g" \
  -e "s/__APP_BUILD__/$APP_BUILD/g" \
  "$INFO_TEMPLATE" > "$APP_CONTENTS/Info.plist"
printf 'APPL????' > "$APP_CONTENTS/PkgInfo"

plutil -lint "$APP_CONTENTS/Info.plist" >/dev/null

if command -v codesign >/dev/null 2>&1; then
  codesign --force --deep --sign - "$APP_DIR" >/dev/null 2>&1 || true
fi

rm -f "$ZIP_PATH"
ditto -c -k --sequesterRsrc --keepParent "$APP_DIR" "$ZIP_PATH"

echo "Packaged app:"
echo "  $APP_DIR"
echo "Packaged zip:"
echo "  $ZIP_PATH"
