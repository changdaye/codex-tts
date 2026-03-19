#!/usr/bin/env bash
set -euo pipefail

SCRIPT_DIR="$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")" && pwd)"
ROOT_DIR="$(cd -- "$SCRIPT_DIR/.." && pwd)"
INSTALL_DIR="${CODEX_TTS_INSTALL_DIR:-$HOME/.local/bin}"
PYTHON_BIN="$ROOT_DIR/.venv/bin/python"
LAUNCHER_PATH="$INSTALL_DIR/codex-tts"

if [ ! -x "$PYTHON_BIN" ]; then
  echo "codex-tts install: missing virtualenv python at $PYTHON_BIN" >&2
  echo "Create it first with: python3 -m venv \"$ROOT_DIR/.venv\"" >&2
  exit 1
fi

mkdir -p "$INSTALL_DIR"

cat > "$LAUNCHER_PATH" <<EOF
#!/bin/sh

ROOT="$ROOT_DIR"

if [ -n "\${PYTHONPATH:-}" ]; then
  export PYTHONPATH="\$ROOT/src:\$PYTHONPATH"
else
  export PYTHONPATH="\$ROOT/src"
fi

exec "\$ROOT/.venv/bin/python" -m codex_tts.cli "\$@"
EOF

chmod +x "$LAUNCHER_PATH"

echo "Installed codex-tts to $LAUNCHER_PATH"
case ":${PATH:-}:" in
  *":$INSTALL_DIR:"*) ;;
  *)
    echo "Add $INSTALL_DIR to PATH to run codex-tts from any directory."
    ;;
esac
