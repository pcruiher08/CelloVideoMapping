#!/usr/bin/env bash
# Bundle what another computer needs to run the apps into a zip:
# code, scripts, the trained model and the replacement images.
#
#   ./package.sh                  # -> dist/cellotracking-YYYYMMDD.zip
#
# Left out: .venv (rebuilt by install.sh), training data and runs, and the
# SAM / base YOLO weights (only needed to retrain; ~500 MB).
# On the other computer: unzip, cd into the folder, ./run.sh

set -euo pipefail
cd "$(dirname "$0")"

[ -f models/cello-seg.pt ] || { echo "models/cello-seg.pt missing: train first" >&2; exit 1; }

NAME="cellotracking-$(date +%Y%m%d)"
STAGE=$(mktemp -d)
DEST="$STAGE/$NAME"
mkdir -p "$DEST/models" "$DEST/data" dist

cp -R bowtrack cellomask "$DEST/"
cp README.md requirements.txt run.py test_synthetic.py test_tuner.py test_projector.py test_lidar.py test_predict.py test_shape.py test_live.py install.sh run.sh package.sh "$DEST/"
mkdir -p "$DEST/ios" && rsync -a --exclude build --exclude "*.xcodeproj" ios/CelloDepth "$DEST/ios/"
for f in config.json warp.json; do [ -f "$f" ] && cp "$f" "$DEST/"; done
cp models/cello-seg.pt "$DEST/models/"
for d in replacements sources; do [ -d "data/$d" ] && cp -R "data/$d" "$DEST/data/"; done

find "$DEST" \( -name __pycache__ -o -name .DS_Store \) -prune -exec rm -rf {} +
chmod +x "$DEST"/*.sh

OUT="$PWD/dist/$NAME.zip"
rm -f "$OUT"
(cd "$STAGE" && zip -qr "$OUT" "$NAME")
rm -rf "$STAGE"
echo "Wrote $OUT ($(du -h "$OUT" | cut -f1))"
echo "On the other computer: unzip it, cd $NAME, ./run.sh"
