#!/usr/bin/env bash
# OpenRouter video client launcher (Linux).
# Sets up a venv on first run, installs deps, then runs the client.

set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
cd "$SCRIPT_DIR"

VENV_DIR=".venv"
REQ_FILE="requirements.txt"
STAMP_FILE="$VENV_DIR/.requirements.sha256"
OUTPUT_DIR="${OUTPUT_DIR:-$SCRIPT_DIR/output}"

find_python() {
    for candidate in python3.13 python3.12 python3.11 python3.10 python3; do
        if command -v "$candidate" >/dev/null 2>&1; then
            ver=$("$candidate" -c 'import sys; print("%d.%d" % sys.version_info[:2])')
            major=${ver%.*}; minor=${ver#*.}
            if [ "$major" -ge 3 ] && [ "$minor" -ge 9 ]; then
                echo "$candidate"
                return 0
            fi
        fi
    done
    return 1
}

if ! PYTHON=$(find_python); then
    echo "Error: Python 3.9+ is required but was not found." >&2
    echo "Install it via your package manager, e.g.:" >&2
    echo "  Debian/Ubuntu: sudo apt install python3 python3-venv python3-pip" >&2
    echo "  Fedora:        sudo dnf install python3 python3-pip" >&2
    echo "  Arch:          sudo pacman -S python python-pip" >&2
    exit 1
fi

if [ ! -d "$VENV_DIR" ]; then
    echo "Creating virtualenv at $VENV_DIR…"
    if ! "$PYTHON" -m venv "$VENV_DIR" 2>/dev/null; then
        echo "Error: failed to create venv. On Debian/Ubuntu install python3-venv:" >&2
        echo "  sudo apt install python3-venv" >&2
        exit 1
    fi
fi

# shellcheck disable=SC1091
source "$VENV_DIR/bin/activate"

REQ_HASH=$(sha256sum "$REQ_FILE" | awk '{print $1}')
if [ ! -f "$STAMP_FILE" ] || [ "$(cat "$STAMP_FILE" 2>/dev/null)" != "$REQ_HASH" ]; then
    echo "Installing dependencies…"
    pip install --quiet --upgrade pip
    pip install --quiet -r "$REQ_FILE"
    echo "$REQ_HASH" > "$STAMP_FILE"
fi

mkdir -p "$OUTPUT_DIR"

exec python client.py "$OUTPUT_DIR" "$@"
