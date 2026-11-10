"""The bow tracker (cellomask/bow.py) on a synthetic depth scene: a wall at
3 m, a 1 cm bow 1.8 m away with a fist at the frog, bowed along its own
length one way, then the other. It must be found, at the right length and
angle, with the speed's sign and size right (+ = down-bow).

    .venv/bin/python test_bow.py
"""

import os
import sys

import cv2
import numpy as np

ROOT = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, ROOT)

from cellomask.bow import BowTracker  # noqa: E402

W, H, DW, DH = 960, 540, 480, 270
K = np.array([[540.0, 0, 479.5], [0, 540.0, 269.5], [0, 0, 1]])
Kd = np.array([[270.0, 0, 239.5], [0, 270.0, 134.5], [0, 0, 1]])


def scene(frog, tip, rng):
    """Depth (m, 270x480) of the wall, the bow from `frog` to `tip` and a
    fist at the frog, nearest wins per cell, with noise."""
    d = np.full((DH, DW), 3.0, np.float32)

    def px(p):
        return (int(round(p[0] / p[2] * Kd[0, 0] + Kd[0, 2])), int(round(p[1] / p[2] * Kd[1, 1] + Kd[1, 2])))
    bow = np.zeros((DH, DW), np.uint8)
    cv2.line(bow, px(frog), px(tip), 1, 3)
    z = (frog[2] + tip[2]) / 2
    d[bow > 0] = z
    fist = np.zeros((DH, DW), np.uint8)
    cv2.circle(fist, px(frog), int(0.045 * Kd[0, 0] / frog[2]), 1, -1)
    d[fist > 0] = frog[2] - 0.02
    return (d + rng.normal(0, 0.003, d.shape)).astype(np.float32)


def main():
    rng = np.random.default_rng(0)
    bt = BowTracker()
    u = np.array([1.0, 0.0, 0.0])                     # the bow lies across the image, frog on the left
    cello = {"C": np.array([0.1, 0.05, 2.0]), "axis": np.array([0.0, -1.0, 0.0]), "n": np.array([0.0, 0.0, -1.0])}
    fps = 20.0
    found, speeds, angles, lengths = 0, [], [], []
    # a still room first, for the background
    for k in range(10):
        bt.update({"depth": np.full((DH, DW), 3.0, np.float32) + rng.normal(0, 0.003, (DH, DW)).astype(np.float32)},
                  K, (W, H), None, t=k / fps)
    pos = -0.15
    for k in range(60):
        v = 0.5 if k < 30 else -0.5                    # + : the bow travels frog-wards (down-bow)
        pos += -v / fps                                # frog-wards = -u
        frog = np.array([pos - 0.2, 0.05, 1.8])
        tip = frog + 0.7 * u
        st = bt.update({"depth": scene(frog, tip, rng)}, K, (W, H), cello, t=1.0 + k / fps)
        if st is None:
            continue
        found += 1
        lengths.append(st["length"])
        angles.append(st["angle"])
        if 8 <= k < 28 or 38 <= k < 58:
            speeds.append((np.sign(v), st["speed"]))
    sp = np.array(speeds)
    down = sp[sp[:, 0] > 0, 1]
    up = sp[sp[:, 0] < 0, 1]
    print(f"found {found}/60 frames, length median {np.median(lengths):.2f} m, angle median {np.median(angles):+.1f} deg")
    print(f"speed: down-bow median {np.median(down):+.2f} m/s, up-bow median {np.median(up):+.2f} m/s (true +-0.50)")
    ok = (found >= 55 and abs(np.median(lengths) - 0.7) < 0.08 and abs(np.median(angles)) < 3
          and 0.35 < np.median(down) < 0.65 and -0.65 < np.median(up) < -0.35)
    print("ALL TESTS PASSED" if ok else "SOME TESTS FAILED")
    raise SystemExit(0 if ok else 1)


if __name__ == "__main__":
    main()
