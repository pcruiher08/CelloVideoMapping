"""Closed-loop check of the projection mapping, with no projector needed.

A fake camera looks at a "room": a cello photo, lit by whatever the app
projects, seen through a known projector -> camera perspective. The test
calibrates through the real Pipeline code, then projects the cello mask as
white light and checks that, seen back through the fake camera, the light
lands on the cello.

    .venv/bin/python test_projector.py
"""

import argparse
import tempfile
import os
import sys
import time

import cv2
import numpy as np

ROOT = os.path.dirname(os.path.abspath(__file__))
PROJ = (1280, 800)
CAM = (1280, 720)
# where projector pixels land in the camera (a projector beside the camera,
# slightly to one side and below): projector -> camera
TRUE = np.array([[0.78, 0.06, 95.0], [-0.03, 0.74, 52.0], [0.00003, -0.00004, 1.0]])


class FakeCamera:
    """Room = scene photo + projector light (warped by TRUE) + noise."""

    def __init__(self, pipe, scene):
        self.pipe = pipe
        self.scene = scene.astype(np.float32)
        self.rng = np.random.default_rng(0)

    def read(self):
        time.sleep(1 / 30)
        light = np.zeros((CAM[1], CAM[0], 3), np.float32)
        if self.pipe.proj_frame is not None:
            light = cv2.warpPerspective(self.pipe.proj_frame, TRUE, CAM).astype(np.float32)
        # projector light adds to a dim room; the scene is what reflects it
        img = self.scene * 0.35 + light * (0.25 + 0.6 * self.scene / 255)
        img += self.rng.normal(0, 3, img.shape)
        return True, np.clip(img, 0, 255).astype(np.uint8)

    def release(self):
        pass


def check(name, ok, detail):
    print(f"{'PASS' if ok else 'FAIL'}  {name:34s} {detail}")
    return ok


def main():
    sys.path.insert(0, ROOT)
    from cellomask import server
    from cellomask.projector import CALIB_PATH

    backup = None
    if os.path.exists(CALIB_PATH):                 # never clobber a real calibration
        backup = open(CALIB_PATH).read()
    ok = True
    try:
        sample = os.path.join(ROOT, "data", "sources", "sample-Cello-106.jpg")
        scene = cv2.resize(cv2.imread(sample), CAM)
        board = np.full_like(scene, 235)           # a white board where the cello will be

        args = argparse.Namespace(source=sample, model=None, imgsz=512, width=1280,
                                  height=720, proj_size=list(PROJ))
        pipe = server.Pipeline(args)
        pipe.debug_dir = tempfile.mkdtemp(prefix="cello-test-")   # keep data/calib_debug real
        pipe.source = None
        cam = FakeCamera(pipe, board)
        pipe.camera = cam
        pipe.projector_window = True               # render projector frames every loop
        pipe.start()
        time.sleep(1.0)

        r = pipe.calibrate()
        ok &= check("calibration", r["ok"] and r["markers"] >= 20,
                    f"{r['message']}")
        # compare with the truth: camera -> projector is inv(TRUE)
        pts = np.random.default_rng(1).uniform([200, 150], [1000, 600], (300, 2)).astype(np.float32)
        got = cv2.perspectiveTransform(pts[:, None], pipe.calib.matrix())[:, 0]
        want = cv2.perspectiveTransform(pts[:, None], np.linalg.inv(TRUE))[:, 0]
        err = np.linalg.norm(got - want, axis=1)
        ok &= check("mapping vs ground truth", err.mean() < 2.0,
                    f"mean {err.mean():.2f} px, max {err.max():.2f} px (projector pixels)")

        # structured light, straight on the cello (no board), with daylight
        cam.scene = scene.astype(np.float32)
        pipe.proj_mode = "content"
        pipe.smoother.reset()
        time.sleep(2.0)
        region = pipe.smoother.mask > 0.5          # where the cello is, before the stripes
        t0 = time.time()
        r = pipe.calibrate_structured()
        took = time.time() - t0
        ok &= check("structured light on the cello", r["ok"] and "the cello" in r["message"],
                    f"{r['message']} in {took:.0f} s")
        # the sample shows several cellos, two of nearly the same size, so
        # "the largest" can switch between frames: measure on the one the
        # calibration was fit to
        region = np.load(os.path.join(pipe.debug_dir, "decoded.npz"))["region"]
        ys, xs = np.nonzero(region)
        pts = np.stack([xs, ys], 1)[::max(1, len(xs) // 300)].astype(np.float32)
        got = cv2.perspectiveTransform(pts[:, None], pipe.calib.matrix())[:, 0]
        want = cv2.perspectiveTransform(pts[:, None], np.linalg.inv(TRUE))[:, 0]
        err = np.linalg.norm(got - want, axis=1)
        ok &= check("structured mapping on the cello", err.mean() < 3.0,
                    f"mean {err.mean():.2f} px, max {err.max():.2f} px (projector pixels)")

        # now the cello stands where the board was; project the mask as white.
        # Only the front view: with the light kept inside the outline, the lit
        # cello and the same-size back view take turns at being the largest
        one = scene.copy()
        one[:, int(0.37 * CAM[0]):] = np.median(scene[:40].reshape(-1, 3), 0)
        cam.scene = one.astype(np.float32)
        pipe.proj_mode = "white"
        pipe.smoother.reset()
        time.sleep(2.5)
        mask = pipe.smoother.mask
        inside = covered = None
        if mask is not None:
            # what the camera sees of the projector light alone
            light = cv2.warpPerspective(pipe.proj_frame, TRUE, CAM)[..., 0] > 127
            m = mask > 0.5
            # the soft edge is feathered inwards, so the light sits just
            # inside the outline: nearly all of it on the cello, most of the
            # cello lit
            inside = (light & m).sum() / max(1, light.sum())
            covered = (light & m).sum() / max(1, m.sum())
        ok &= check("white light lands on the cello", inside is not None and inside > 0.97 and covered > 0.8,
                    "no mask" if inside is None else
                    f"{100 * inside:.1f}% of the light on the cello, {100 * covered:.0f}% of the cello lit")
        pipe.running = False
    finally:
        if backup is not None:
            open(CALIB_PATH, "w").write(backup)
        elif os.path.exists(CALIB_PATH):
            os.remove(CALIB_PATH)

    print("ALL TESTS PASSED" if ok else "SOME TESTS FAILED")
    raise SystemExit(0 if ok else 1)


if __name__ == "__main__":
    main()
