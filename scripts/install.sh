#!/usr/bin/env bash
set -euo pipefail

SCRIPT_DIR="$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")" && pwd)"
ROOT_DIR="$(cd -- "$SCRIPT_DIR/.." && pwd)"
INSTALL_DIR="${CODEX_TTS_INSTALL_DIR:-$HOME/.local/bin}"
PYTHON_BIN="$ROOT_DIR/.venv/bin/python"
LAUNCHER_PATH="$INSTALL_DIR/codex-tts"

if [ ! -f "$ROOT_DIR/pyproject.toml" ]; then
  echo "codex-tts install: could not find pyproject.toml under $ROOT_DIR" >&2
  exit 1
fi

if [ ! -x "$PYTHON_BIN" ]; then
  echo "codex-tts install: missing virtualenv python at $PYTHON_BIN" >&2
  echo "From the repository root run: bash scripts/bootstrap.sh" >&2
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
if ! command -v codex >/dev/null 2>&1; then
  echo "codex-tts install: warning: \`codex\` is not currently in PATH." >&2
fi
case ":${PATH:-}:" in
  *":$INSTALL_DIR:"*) ;;
  *)
    echo "Add $INSTALL_DIR to PATH to run codex-tts from any directory."
    echo "For example: export PATH=\"$INSTALL_DIR:\$PATH\""
    ;;
esac
