#!/usr/bin/env bash
# The hand-sign service's own Python environment and models (once; needs
# internet). Kept apart from the app's .venv: MediaPipe brings its own OpenCV.
#
#   bash tools/signs_setup.sh
set -euo pipefail
cd "$(dirname "$0")/.."
PY=$( [ -x .venv/bin/python ] && .venv/bin/python -c "import sys; print(sys.base_prefix + '/bin/python3')" || command -v python3 )
mkdir -p signs/models
[ -x signs/venv/bin/python ] || "$PY" -m venv signs/venv
signs/venv/bin/pip -q install --disable-pip-version-check mediapipe rtmlib onnxruntime
cd signs/models
[ -f pose_landmarker_full.task ] || curl -fsSL -o pose_landmarker_full.task \
    https://storage.googleapis.com/mediapipe-models/pose_landmarker/pose_landmarker_full/float16/latest/pose_landmarker_full.task
if ! ls rtmpose-m_simcc-hand5*.onnx >/dev/null 2>&1; then
    curl -fsSL -o hand.zip https://download.openmmlab.com/mmpose/v1/projects/rtmposev1/onnx_sdk/rtmpose-m_simcc-hand5_pt-aic-coco_210e-256x256-74fb594_20230320.zip
    unzip -q -j -o hand.zip "*end2end.onnx" -d . && mv end2end.onnx rtmpose-m_simcc-hand5_pt-aic-coco_210e-256x256-74fb594_20230320.onnx
    rm -f hand.zip
fi
echo "hand signs ready: $(ls)"
