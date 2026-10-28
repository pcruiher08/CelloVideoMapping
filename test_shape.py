"""Shape memory check: a swaying cello with a pizzicato hand and forearm
coming in from the side over the body. The outline the light uses should
stay the whole cello (the hand gets painted), not shrink around the hand.

    .venv/bin/python test_shape.py
"""

import os
import sys

import cv2
import numpy as np

ROOT = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, ROOT)

from cellomask.shape import ShapeMemory  # noqa: E402
from test_predict import FPS, H, W, cello, motion  # noqa: E402


def arm(t, x):
    """Forearm + hand covering the lower bout from the right while plucking
    (t in 1.5-3.5 s), moving with the cello; None otherwise."""
    if not 1.5 <= t <= 3.5:
        return None
    m = np.zeros((H, W), np.uint8)
    cx, cy = W / 2 + x, H / 2 + 120
    reach = 60 + 25 * np.sin(2 * np.pi * t * 3)          # the hand going in and out
    cv2.line(m, (int(cx + 300), int(cy + 60)), (int(cx + reach), int(cy)), 1, 70)   # forearm
    cv2.circle(m, (int(cx + reach - 10), int(cy - 5)), 45, 1, -1)                   # hand
    return m > 0


def check(name, ok, detail):
    print(f"{'PASS' if ok else 'FAIL'}  {name:34s} {detail}")
    return ok


def main():
    rng = np.random.default_rng(3)
    mem = ShapeMemory()
    raw_iou, kept_iou, covered, whole_same = [], [], [], []
    for k in range(int(5 * FPS)):
        t = k / FPS
        x, a = motion(t, "sway")
        true = cello(x, a, rng) > 0.5
        hand = arm(t, x)
        seen = true & ~hand if hand is not None else true
        out, cov = mem(seen.astype(np.float32))
        o = out > 0.5
        iou = (o & true).sum() / (o | true).sum()
        if hand is not None and t > 1.6:
            raw_iou.append((seen & true).sum() / (seen | true).sum())
            kept_iou.append(iou)
            covered.append(cov)
        elif hand is None:
            whole_same.append(np.array_equal(o, seen))
    ok = True
    ok &= check("covered cello restored", np.min(kept_iou) > 0.95,
                f"IoU with the whole cello {np.mean(raw_iou):.3f} as seen -> "
                f"{np.mean(kept_iou):.3f} restored (worst {np.min(kept_iou):.3f}), "
                f"{100 * np.mean(covered):.0f}% covered on average")
    ok &= check("whole frames passed through", np.mean(whole_same) > 0.99,
                f"{100 * np.mean(whole_same):.0f}% of uncovered frames unchanged")
    print("ALL TESTS PASSED" if ok else "SOME TESTS FAILED")
    raise SystemExit(0 if ok else 1)


if __name__ == "__main__":
    main()
