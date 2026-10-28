#!/usr/bin/env bash
# Start the projection-mapping show: the iPhone's LiDAR camera (CelloDepth
# app) as the camera, the projector window on the extended display, and the
# web page reachable from the network (the phone connects to this Mac).
#
#   ./show.sh                 # installs first if needed, like run.sh
#
# In the CelloDepth app on the iPhone, set this Mac's address and port 8000
# (it is printed below). The image on the cello, OSC and the other settings
# come back as they were last left in the web page.

set -euo pipefail
cd "$(dirname "$0")"
IP=$(ipconfig getifaddr en0 2>/dev/null || hostname -I 2>/dev/null | cut -d' ' -f1 || true)
echo "iPhone app address: ${IP:-unknown, see System Settings > Wi-Fi}:${PORT:-8000}"
echo "Projector window: q quits, Esc leaves fullscreen (connect the projector and"
echo "set it to extend BEFORE starting, or the window opens on this screen)"
exec bash ./run.sh --source lidar --projector --host 0.0.0.0 "$@"
