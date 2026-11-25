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
# hand signs (✌️ ping-pong, 👍 overdrive) from bare hands: a service of its
# own beside the app (tools/signs_service.py, its log in data/signs.log)
if [ "${SIGNS:-1}" = 1 ]; then
    [ -x signs/venv/bin/python ] || bash tools/signs_setup.sh || echo "hand signs: setup failed (needs internet); the show runs without them"
    if [ -x signs/venv/bin/python ]; then
        pkill -f tools/signs_service.py 2>/dev/null || true
        signs/venv/bin/python -u tools/signs_service.py > data/signs.log 2>&1 &
        echo "Hand signs: on (log: data/signs.log; SIGNS=0 ./show.sh to leave them off)"
    fi
fi
# tracked at 960x540: the 3D calibration and scan are in metres, so they
# hold at any resolution, and every mask step costs ~half of 1280x720
# caffeinate: no display sleep, idle sleep or screen saver while the show
# runs (left idle, the Mac locked itself and its lock screen covered the
# projector)
exec caffeinate -dimsu bash ./run.sh --source "$SOURCE" --projector --host 0.0.0.0 --width 960 --height 540 "$@"
