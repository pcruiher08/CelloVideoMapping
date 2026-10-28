"""Shape checks: a swaying cello with a pizzicato hand and forearm coming in
from the side over the body. The outline the light uses should stay the
whole cello (the hand gets painted), not shrink around the hand.

Then the learned outline: learned from the cello alone, fitted while it is
played leaning further back, with what the segmentation really does while
both hands are over the upper bout (the knees bleeding into the mask, its
top cut straight at a detection box that jumps with the hands).

    .venv/bin/python test_shape.py
"""

import os
import sys

import cv2
import numpy as np

ROOT = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, ROOT)

from cellomask.shape import LearnedShape, ShapeMemory  # noqa: E402
from test_predict import FPS, H, W, OUT, cello, motion  # noqa: E402


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


def played(x, angle, squash, rng):
    """The cello at offset x, tilt angle, height scaled by `squash` (leaning
    further back than on its stand)."""
    c, sn = np.cos(angle), np.sin(angle)
    pts = OUT * [1.0, squash]
    pts = pts @ np.array([[c, sn], [-sn, c]]) + [W / 2 + x, H / 2]
    pts += rng.normal(0, 1.5, pts.shape)
    m = np.zeros((H, W), np.uint8)
    cv2.fillPoly(m, [np.round(pts).astype(np.int32)], 1)
    return m > 0


def check_learned():
    import tempfile
    rng = np.random.default_rng(4)
    ls = LearnedShape(os.path.join(tempfile.mkdtemp(), "shape.npz"))
    ls.learn(played(-30, 0.0, 1.0, rng).astype(np.float32))       # on the stand
    ls = LearnedShape(ls.path)                                     # and back from disk
    raw_iou, iou, tops, raw_tops = [], [], [], []
    for k in range(int(4 * FPS)):
        t = k / FPS
        x, a = motion(t, "sway")
        true = played(x, a, 0.88, rng)
        seen = true.copy()
        ys, xs = np.nonzero(true)
        top, cx = ys.min(), xs.mean()
        # both hands over the upper bout, the mask cut at a box edge that jumps
        cut = top + int(60 + 25 * np.sin(2 * np.pi * t * 4) + rng.normal(0, 6))
        seen[:cut] = False
        cv2.circle(seen.view(np.uint8), (int(cx + 40), cut + 30), 40, 0, -1)
        # the knees, bleeding into the mask beside the lower bout
        for side in (-1, 1):
            cv2.circle(seen.view(np.uint8), (int(cx + side * 150), int(ys.max() - 90)), 45, 1, -1)
        out = ls(seen.astype(np.float32))
        if out is None:
            iou.append(0.0)
            continue
        o = out > 0.5
        iou.append((o & true).sum() / (o | true).sum())
        raw_iou.append((seen & true).sum() / (seen | true).sum())
        tops.append(np.nonzero(o.any(1))[0].min() - top)
        raw_tops.append(np.nonzero(seen.any(1))[0].min() - top)
    return check("learned outline under hands + knees", np.min(iou) > 0.95 and np.std(tops) < 2.0,
                 f"IoU {np.mean(raw_iou):.3f} as seen -> {np.mean(iou):.3f} fitted (worst {np.min(iou):.3f}); "
                 f"top edge jumps {np.std(raw_tops):.1f} px as seen -> {np.std(tops):.1f} px")


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
    ok &= check_learned()
    print("ALL TESTS PASSED" if ok else "SOME TESTS FAILED")
    raise SystemExit(0 if ok else 1)


if __name__ == "__main__":
    main()
