#!/usr/bin/env bash
set -euo pipefail

INSTALL_DIR="${CODEX_TTS_INSTALL_DIR:-$HOME/.local/bin}"
LAUNCHER_PATH="$INSTALL_DIR/codex-tts"

if [ -e "$LAUNCHER_PATH" ]; then
  rm -f "$LAUNCHER_PATH"
  echo "Removed codex-tts launcher at $LAUNCHER_PATH"
else
  echo "codex-tts launcher not found at $LAUNCHER_PATH"
fi
