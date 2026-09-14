#!/usr/bin/env bash
# autodub launcher script

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
VENV_PYTHON="$SCRIPT_DIR/.venv/bin/python"

if [ ! -f "$VENV_PYTHON" ]; then
    echo "Error: Virtual environment not found at $VENV_PYTHON"
    echo "Please set up the environment with: python3 -m venv .venv && .venv/bin/pip install -r requirements.txt"
    exit 1
fi

PYTHONPATH="$SCRIPT_DIR" "$VENV_PYTHON" -m autodub.cli "$@"
