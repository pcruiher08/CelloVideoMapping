#!/usr/bin/env bash
# Bundle what another computer needs to run the apps into a zip:
# code, scripts, the trained model, the replacement images, and this rig's
# calibrations (projector, iPhone, the learned cello outline) and settings.
#
#   ./package.sh                  # -> dist/cellotracking-YYYYMMDD.zip
#   ./package.sh --live "syphon:TouchDesigner / visuales_cello" --osc 127.0.0.1
#                                 # preset the image on the cello and the OSC
#                                 # target for the other Mac (here: TouchDesigner
#                                 # running on it, sending over Syphon)
#
# The calibrations hold as long as the projector and the iPhone stay where
# they were; if either moved, press Calibrate 3D on the other Mac.
# Older zips in dist/ are removed.
# Left out: .venv (rebuilt by install.sh), training data and runs, and the
# SAM / base YOLO weights (only needed to retrain; ~500 MB).
# On the other computer: unzip, cd into the folder, ./run.sh

set -euo pipefail
cd "$(dirname "$0")"

LIVE=""; OSC=""
while [ $# -gt 0 ]; do
    case "$1" in
        --live) LIVE="$2"; shift 2 ;;
        --osc) OSC="$2"; shift 2 ;;
        *) echo "unknown option $1" >&2; exit 1 ;;
    esac
done

[ -f models/cello-seg.pt ] || { echo "models/cello-seg.pt missing: train first" >&2; exit 1; }

NAME="cellotracking-$(date +%Y%m%d)"
STAGE=$(mktemp -d)
DEST="$STAGE/$NAME"
mkdir -p "$DEST/models" "$DEST/data" dist

cp -R bowtrack cellomask "$DEST/"
cp README.md requirements.txt run.py test_synthetic.py test_tuner.py test_projector.py test_lidar.py test_predict.py test_shape.py test_live.py test_kinect.py install.sh run.sh show.sh package.sh "$DEST/"
mkdir -p "$DEST/kinect" && cp kinect/build.sh kinect/cellokinect.cpp "$DEST/kinect/"   # built by install.sh
mkdir -p "$DEST/ios" && rsync -a --exclude build --exclude "*.xcodeproj" ios/CelloDepth "$DEST/ios/"
for f in config.json warp.json; do [ -f "$f" ] && cp "$f" "$DEST/"; done
cp models/cello-seg.pt "$DEST/models/"
for d in replacements sources; do [ -d "data/$d" ] && cp -R "data/$d" "$DEST/data/"; done
# this rig's calibrations, learned outline and settings
for f in calibration.json procam3d.json procam3d_ref.npz cello_shape.npz settings.json; do
    [ -f "data/$f" ] && cp "data/$f" "$DEST/data/"
done
if [ -n "$LIVE$OSC" ]; then
    .venv/bin/python - "$DEST/data/settings.json" "$LIVE" "$OSC" <<'EOF'
import json, os, sys
path, live, osc = sys.argv[1:]
data = json.load(open(path)) if os.path.exists(path) else {"settings": {}}
if live:
    data["replacement"] = live
if osc:
    data.setdefault("settings", {})["osc_host"] = osc
json.dump(data, open(path, "w"), indent=1)
print(f"preset: image {data.get('replacement')}, OSC to {data['settings'].get('osc_host') or 'off'}")
EOF
fi

find "$DEST" \( -name __pycache__ -o -name .DS_Store \) -prune -exec rm -rf {} +
chmod +x "$DEST"/*.sh

OUT="$PWD/dist/$NAME.zip"
rm -f dist/cellotracking-*.zip
(cd "$STAGE" && zip -qr "$OUT" "$NAME")
rm -rf "$STAGE"
echo "Wrote $OUT ($(du -h "$OUT" | cut -f1))"
echo "On the other computer: unzip it, cd $NAME, ./show.sh (or ./run.sh)"
