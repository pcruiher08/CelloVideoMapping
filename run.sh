#!/usr/bin/env bash
# Start the cello replacement web app, installing everything first if needed.
#
#   ./run.sh                      # built-in camera
#   ./run.sh --source brio        # camera by (part of its) name
#   ./run.sh --source 0           # camera by index
#   ./run.sh --source clip.mp4    # a video file
#   PORT=8001 ./run.sh            # another port
#   NO_BROWSER=1 ./run.sh         # do not open the browser
#
# Any other flags are passed to `python -m cellomask.server` (see --help).
# Cameras plugged in after start-up get new indices: restart after hot-plugging.

set -euo pipefail
cd "$(dirname "$0")"

bash ./install.sh   # via bash: works even if a copy lost the execute bit

PORT=${PORT:-8000}
URL="http://127.0.0.1:$PORT"

port_busy() {
    if command -v lsof >/dev/null; then
        lsof -nP -iTCP:"$1" -sTCP:LISTEN >/dev/null 2>&1
    else
        (exec 3<>"/dev/tcp/127.0.0.1/$1") 2>/dev/null
    fi
}
if port_busy "$PORT"; then
    echo "Port $PORT is in use (another copy running?). Try: PORT=8001 ./run.sh" >&2
    exit 1
fi

# open the browser once the server answers
if [ -z "${NO_BROWSER:-}" ]; then
    (
        for _ in $(seq 1 120); do
            if curl -sf -o /dev/null "$URL/api/state"; then
                if command -v open >/dev/null; then open "$URL"
                elif command -v xdg-open >/dev/null; then xdg-open "$URL" >/dev/null 2>&1
                fi
                exit 0
            fi
            sleep 1
        done
    ) &
fi

echo "Starting... (up to a minute on the very first launch, ~20 s after). Ctrl-C to stop."
export OPENBLAS_NUM_THREADS=1   # see cellomask/__init__.py
exec .venv/bin/python -m cellomask.server --port "$PORT" "$@"
