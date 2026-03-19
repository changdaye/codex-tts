#!/usr/bin/env bash
set -euo pipefail

SCRIPT_DIR="$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")" && pwd)"
ROOT_DIR="$(cd -- "$SCRIPT_DIR/.." && pwd)"
VENV_DIR="$ROOT_DIR/.venv"
PYTHON_BIN="$VENV_DIR/bin/python"
ACTIVATE_PATH="$VENV_DIR/bin/activate"

if [ -x "$PYTHON_BIN" ]; then
  echo "codex-tts bootstrap: reusing virtualenv at $VENV_DIR"
else
  python3 -m venv "$VENV_DIR"
  echo "codex-tts bootstrap: created virtualenv at $VENV_DIR"
fi

echo "Activate it with:"
echo "source \"$ACTIVATE_PATH\""

if [ -f "$ROOT_DIR/pyproject.toml" ]; then
  if "$PYTHON_BIN" -m pip install -e '.[dev]'; then
    echo "codex-tts bootstrap: installed editable package and dev dependencies"
  else
    echo "codex-tts bootstrap: dependency installation failed" >&2
    echo "After activating the venv, run: python -m pip install -e '.[dev]'" >&2
    exit 1
  fi
else
  echo "codex-tts bootstrap: no pyproject.toml found; skipped dependency installation"
fi
