#!/usr/bin/env bash
# Start the projection-mapping show: the Kinect v2 as the camera, the
# projector window on the extended display, and the web page reachable from
# the network.
#
#   ./show.sh                 # installs first if needed, like run.sh
#   SOURCE=lidar ./show.sh    # the iPhone (CelloDepth app) instead of the Kinect
#
# With the iPhone, set this Mac's address and port 8000 in the CelloDepth app
# (it is printed below). The image on the cello, OSC and the other settings
# come back as they were last left in the web page.

set -euo pipefail
cd "$(dirname "$0")"
SOURCE=${SOURCE:-kinect}
IP=$(ipconfig getifaddr en0 2>/dev/null || hostname -I 2>/dev/null | cut -d' ' -f1 || true)
if [ "$SOURCE" = kinect ]; then
    [ -x kinect/bin/cellokinect ] || bash kinect/build.sh
    echo "Camera: Kinect v2 (USB 3 port, its power adapter plugged in)"
else
    echo "iPhone app address: ${IP:-unknown, see System Settings > Wi-Fi}:${PORT:-8000}"
fi
echo "Web page: http://${IP:-localhost}:${PORT:-8000}"
echo "Projector window: f cover / uncover the screen, b blackout, q quits (connect the projector and"
echo "set it to extend BEFORE starting, or the window opens on this screen)"
exec bash ./run.sh --source "$SOURCE" --projector --host 0.0.0.0 "$@"
