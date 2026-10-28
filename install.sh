#!/usr/bin/env bash
# Create .venv and install everything the cello apps need.
#
#   ./install.sh            # install, or update if requirements.txt changed
#   ./install.sh --force    # rebuild .venv from scratch
#   PYTHON=/path/to/python3.12 ./install.sh   # use a specific interpreter
#
# Works on macOS (Apple Silicon uses the GPU via MPS) and Linux (CUDA if an
# NVIDIA driver is present, otherwise CPU). Needs Python 3.10-3.13.

set -euo pipefail
cd "$(dirname "$0")"

VENV=.venv
STAMP="$VENV/.requirements.sha"

say()  { printf '\033[1;33m==>\033[0m %s\n' "$*"; }
fail() { printf '\033[1;31mxx\033[0m %s\n' "$*" >&2; exit 1; }

sha() { shasum -a 256 "$1" 2>/dev/null | cut -d' ' -f1 || sha256sum "$1" | cut -d' ' -f1; }

py_ok() {   # is $1 a Python between 3.10 and 3.13?
    "$1" -c 'import sys; sys.exit(not ((3, 10) <= sys.version_info[:2] <= (3, 13)))' 2>/dev/null
}

find_python() {
    if [ -n "${PYTHON:-}" ]; then
        py_ok "$PYTHON" || fail "PYTHON=$PYTHON is not Python 3.10-3.13"
        echo "$PYTHON"; return
    fi
    for p in python3.12 python3.11 python3.13 python3.10 python3; do
        if command -v "$p" >/dev/null && py_ok "$(command -v "$p")"; then
            command -v "$p"; return
        fi
    done
    return 1
}

if [ "${1:-}" = "--force" ]; then
    say "Removing $VENV"
    rm -rf "$VENV"
fi

if [ -f "$STAMP" ] && [ "$(cat "$STAMP")" = "$(sha requirements.txt)" ]; then
    say "Already installed (requirements.txt unchanged). Use --force to rebuild."
    exit 0
fi

# No suitable Python (a stock Mac only has Apple's 3.9): fetch a standalone
# Python 3.12 with uv. Everything stays inside .tools/ in this folder; no
# shell profile edits, no admin password.
python_via_uv() {
    local tools="$PWD/.tools"
    local uv="$tools/bin/uv"
    if [ ! -x "$uv" ]; then
        say "No Python 3.10-3.13 found; downloading uv to fetch one (into .tools/)" >&2
        command -v curl >/dev/null || fail "curl is needed to download uv"
        curl -LsSf https://astral.sh/uv/install.sh |
            env UV_INSTALL_DIR="$tools/bin" UV_NO_MODIFY_PATH=1 sh >&2 ||
            fail "could not download uv"
    fi
    say "Installing Python 3.12 (standalone, into .tools/python)" >&2
    UV_PYTHON_INSTALL_DIR="$tools/python" "$uv" python install 3.12 >&2 ||
        fail "uv could not install Python 3.12"
    UV_PYTHON_INSTALL_DIR="$tools/python" "$uv" python find 3.12
}

if [ ! -x "$VENV/bin/python" ]; then
    PY=$(find_python) || PY=$(python_via_uv)
    say "Creating $VENV with $PY ($("$PY" --version))"
    "$PY" -m venv "$VENV" || fail "venv creation failed. On Debian/Ubuntu: sudo apt install python3-venv"
fi

say "Installing Python packages (first time: several minutes, ~1 GB with PyTorch)"
"$VENV/bin/python" -m pip install --upgrade pip --quiet
"$VENV/bin/python" -m pip install -r requirements.txt

say "Checking the install"
"$VENV/bin/python" - <<'EOF' || fail "import check failed (on Linux you may need: sudo apt install libgl1 libglib2.0-0 libportaudio2)"
import cv2, fastapi, numpy, torch, ultralytics, sounddevice
dev = ("mps" if torch.backends.mps.is_available()
       else "cuda" if torch.cuda.is_available() else "cpu")
print(f"    python {__import__('sys').version.split()[0]}, torch {torch.__version__}, "
      f"ultralytics {ultralytics.__version__}, opencv {cv2.__version__}, "
      f"numpy {numpy.__version__}")
print(f"    inference device: {dev}" + ("  (no GPU found: expect a low frame rate)" if dev == "cpu" else ""))
EOF

sha requirements.txt > "$STAMP"

if [ ! -f models/cello-seg.pt ]; then
    say "Note: models/cello-seg.pt is missing. The app will fall back to the"
    say "zero-shot YOLOE model (downloaded on first run), which misses more."
    say "Copy models/cello-seg.pt from the training machine to fix this."
fi
say "Done. Start the app with ./run.sh"
