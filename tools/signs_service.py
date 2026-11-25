"""Hand signs from bare hands, as a separate service next to the running app
(a quick test: the app itself is not changed).

    bash tools/signs_setup.sh                    # once: its own Python + the two models
    signs/venv/bin/python tools/signs_service.py # show.sh starts it with the app

- frames: keeps the app's full-resolution recorder (/api/debug/fullres)
  running and reads the newest JPEG it writes (about 10 a second);
- the hand: MediaPipe's body pose finds the wrist on the camera's right of
  the body (the fingering hand), and a box around it goes to RTMPose-hand
  (21 keypoints, no palm detector: the hand is often blown out to white,
  which MediaPipe's palm detector misses);
- the sign: index + middle straight and apart, ring + pinky folded = ✌️;
  thumb up above the knuckles, the four fingers folded = 👍;
- a sign seen on `need` frames within `window_s`, more than the other sign,
  toggles its effect through the app's /api/fx (as the page's buttons do;
  the app passes it on to Max). The hand must leave the sign for
  `release_s` before the same sign toggles again.
"""

import argparse
import glob
import json
import os
import shutil
import threading
import time
import urllib.request
from collections import deque

import cv2
import mediapipe as mp
import numpy as np
from mediapipe.tasks import python as mpt
from mediapipe.tasks.python import vision
from rtmlib import RTMPose

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))   # the app's folder
MODELS = os.path.join(ROOT, "signs", "models")                       # fetched by tools/signs_setup.sh
SIGNS = {"V": "pingpong", "T": "overdrive"}
NAMES = {"V": "peace", "T": "thumbs up"}


def post(app, path, body=None, timeout=40):
    req = urllib.request.Request(app + path, data=json.dumps(body or {}).encode(),
                                 headers={"Content-Type": "application/json"}, method="POST")
    with urllib.request.urlopen(req, timeout=timeout) as r:
        return json.loads(r.read() or b"null")


def get(app, path):
    with urllib.request.urlopen(app + path, timeout=5) as r:
        return json.loads(r.read())


class Recorder(threading.Thread):
    """Keeps /api/debug/fullres running in 30 s chunks; remembers the folders."""

    def __init__(self, app, fps):
        super().__init__(daemon=True)
        self.app, self.fps, self.running, self.dirs = app, fps, True, []

    def run(self):
        while self.running:
            try:
                r = post(self.app, f"/api/debug/fullres?seconds=30&fps={self.fps}", timeout=45)
                if r and r.get("dir") and r["dir"] not in self.dirs:
                    self.dirs.append(r["dir"])
            except Exception as e:
                print("recorder:", e)
                time.sleep(1)


def newest_frame(clips, t_start):
    dirs = [d for d in glob.glob(os.path.join(clips, "fullres_*")) if os.path.getmtime(d) >= t_start - 1]
    if not dirs:
        return None, []
    d = max(dirs, key=os.path.getmtime)
    files = sorted(glob.glob(os.path.join(d, "*.jpg")))
    return (files[-2] if len(files) >= 2 else None), dirs   # [-1] may still be being written


def classify(k, s, cut=0.15):
    """k: 21 x 2 keypoints (wrist 0; thumb 1-4; index 5-8; middle 9-12;
    ring 13-16; pinky 17-20), s their confidences."""
    if s[[0, 4, 8, 12, 16, 20]].mean() < cut:
        return None
    w = k[0]
    size = np.linalg.norm(k[9] - w) + 1e-6

    def straight(mcp, pip, tip):
        return (np.linalg.norm(k[tip] - w) > 1.25 * np.linalg.norm(k[pip] - w)
                and np.linalg.norm(k[tip] - k[mcp]) > 0.55 * size)

    I, M, R, P = straight(5, 6, 8), straight(9, 10, 12), straight(13, 14, 16), straight(17, 18, 20)
    if I and M and not R and not P and np.linalg.norm(k[8] - k[12]) > 0.35 * size:
        return "V"
    up = k[4][1] < min(k[5][1], k[9][1], k[13][1], k[17][1]) - 0.3 * size
    if up and not I and not M and not R and not P:
        return "T"
    return "o"


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--app", default="http://127.0.0.1:8000")
    ap.add_argument("--clips", default=os.path.join(ROOT, "data", "clips"))
    ap.add_argument("--fps", type=float, default=10)
    ap.add_argument("--need", type=int, default=4, help="frames with the sign within the window")
    ap.add_argument("--window", type=float, default=2.0)
    ap.add_argument("--release", type=float, default=1.5, help="s without the sign before it may switch again")
    a = ap.parse_args()

    pose = vision.PoseLandmarker.create_from_options(vision.PoseLandmarkerOptions(
        base_options=mpt.BaseOptions(model_asset_path=os.path.join(MODELS, "pose_landmarker_full.task")),
        running_mode=vision.RunningMode.VIDEO, min_pose_detection_confidence=0.3, min_tracking_confidence=0.3))
    onnx = glob.glob(os.path.join(MODELS, "rtmpose-m_simcc-hand5*.onnx"))[0]
    hand = RTMPose(onnx, model_input_size=(256, 256))

    # wait for the app (show.sh starts both together), then turn its old
    # glove detector off, so the two don't both switch the effects
    while True:
        try:
            post(a.app, "/api/settings", {"signs": False}, timeout=5)
            break
        except Exception:
            time.sleep(2)

    t_start = time.time()
    rec = Recorder(a.app, a.fps)
    rec.start()
    seen = deque()                        # (time, sign)
    armed = {"V": True, "T": True}
    last_seen = {"V": 0.0, "T": 0.0}
    armed_at = {"V": 0.0, "T": 0.0}
    box, box_t = None, 0.0                # the last hand box, kept 1 s when the pose drops out
    done, line_t, n = None, 0.0, 0
    last_frame_t = t_start
    print("signs service: running (Ctrl-C to stop)")
    try:
        while True:
            f, dirs = newest_frame(a.clips, t_start)
            if f is None or f == done:
                # (a new recorder folder has no frame to read for a moment:
                # measure from the last frame read, not from this one)
                if time.time() - last_frame_t > 60:
                    print("no frames from the app for 60 s: it has stopped; so do the signs")
                    break
                time.sleep(0.02)
                continue
            done, last_frame_t = f, time.time()
            img = cv2.imread(f)
            if img is None:
                continue
            now = time.time()
            H, W = img.shape[:2]
            pr = pose.detect_for_video(mp.Image(image_format=mp.ImageFormat.SRGB,
                                                data=cv2.cvtColor(cv2.resize(img, (960, 540)), cv2.COLOR_BGR2RGB)),
                                       int((now - t_start) * 1000))
            if pr.pose_landmarks:
                lm = pr.pose_landmarks[0]
                wr = max((lm[15], lm[16]), key=lambda p: p.x)     # the hand on the camera's right
                el = lm[13] if wr is lm[15] else lm[14]
                cx, cy = (wr.x + 0.35 * (wr.x - el.x)) * W, (wr.y + 0.35 * (wr.y - el.y)) * H
                half = max(80.0, 0.55 * abs(lm[11].x - lm[12].x) * W)
                box, box_t = [cx - half, cy - half, cx + half, cy + half], now
            sign = None
            if box is not None and now - box_t < 1.0:
                kps, sc = hand(img, bboxes=[box])
                sign = classify(kps[0], sc[0])
            seen.append((now, sign))
            while seen and now - seen[0][0] > a.window:
                seen.popleft()
            for s in SIGNS:
                if sign == s:
                    last_seen[s] = now
                elif not armed[s] and now - last_seen[s] >= a.release:
                    armed[s], armed_at[s] = True, now
            # only frames since the sign was re-armed count (older ones belong
            # to the sign that already switched)
            counts = {s: sum(1 for t, x in seen if x == s and t >= armed_at[s]) for s in SIGNS}
            for s, other in (("V", "T"), ("T", "V")):
                if armed[s] and counts[s] >= a.need and counts[s] > counts[other]:
                    fx = SIGNS[s]
                    try:
                        cur = get(a.app, "/api/state")["projector"]["signs"][fx]
                        st = post(a.app, "/api/fx", {fx: not cur}, timeout=5)
                        print(f"{time.strftime('%H:%M:%S')}  {NAMES[s]} -> {fx} {'ON' if st[fx] else 'off'}", flush=True)
                    except Exception as e:
                        print("could not switch", fx, e)
                    armed[s] = False
                    seen.clear()
            n += 1
            if now - line_t > 1.0:
                line_t = now
                print(f"{time.strftime('%H:%M:%S')}  sees {NAMES.get(sign, sign or '-'):9s}  "
                      f"peace {counts['V']}  thumbs {counts['T']}  ({n} frames)", flush=True)
            # the recorder's JPEGs are only needed until read
            for d in dirs:
                for g in sorted(glob.glob(os.path.join(d, "*.jpg")))[:-3]:
                    try:
                        os.remove(g)
                    except OSError:
                        pass
    except KeyboardInterrupt:
        pass
    finally:
        rec.running = False
        for d in rec.dirs + newest_frame(a.clips, t_start)[1]:
            shutil.rmtree(d, ignore_errors=True)


if __name__ == "__main__":
    main()
