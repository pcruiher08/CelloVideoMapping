"""Motion prediction check: a cello swaying in front of a camera whose light
arrives `LATENCY` s late. Compares the light without prediction and with the
Kalman prediction (cellomask/predict.py): how far it trails a moving cello,
how much it overshoots when the cello turns back, how much it jitters when
the cello is still.

    .venv/bin/python test_predict.py
"""

import os
import sys

import cv2
import numpy as np

ROOT = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, ROOT)

from cellomask.predict import PlanePredictor, PosePredictor, apply_mask  # noqa: E402

FPS = 30
LATENCY = 0.35          # capture -> light, measured on the rig (s)
H, W = 960, 720


def outline():
    t = np.linspace(0, 2 * np.pi, 160, endpoint=False)
    y = 0.38 * np.sin(t)
    x = (0.21 - 0.05 * np.cos(2 * np.pi * (y + 0.38) / 0.38) ** 2) * np.cos(t)
    return np.stack([x, -y], 1) * 700


OUT = outline()


def cello(x, angle, rng):
    """Mask of the cello at horizontal offset x (px) and tilt angle (rad),
    with segmentation-like edge jitter."""
    c, s = np.cos(angle), np.sin(angle)
    pts = OUT @ np.array([[c, s], [-s, c]]) + [W / 2 + x, H / 2]
    pts += rng.normal(0, 1.5, pts.shape)
    m = np.zeros((H, W), np.uint8)
    cv2.fillPoly(m, [np.round(pts).astype(np.int32)], 1)
    return m.astype(np.float32)


def motion(t, kind):
    """(x px, angle rad) of the cello at time t."""
    if kind == "still":
        return 0.0, 0.0
    if kind == "sway":            # a player's sway: +-60 px (~13 cm), 2.5 s period
        return 60 * np.sin(2 * np.pi * t / 2.5), 0.08 * np.sin(2 * np.pi * t / 2.5)
    if kind == "jerk":            # quick move and stop: 80 px in 0.3 s
        u = np.clip((t - 1.5) / 0.3, 0, 1)
        return 80 * (3 * u ** 2 - 2 * u ** 3), 0.0


def run(kind, lead, seconds=5.0):
    """Mean / max distance (px, along x) between where the light lands and
    the cello, and IoU, over the run after a warm-up."""
    rng = np.random.default_rng(1)
    pred = PosePredictor()
    errs, ious = [], []
    for k in range(int(seconds * FPS)):
        t = k / FPS
        x, a = motion(t, kind)
        m = cello(x, a, rng)
        pred.update(m, t)
        if t < 1.0:
            continue
        lit = apply_mask(pred.delta(t + lead), m) if lead > 0 else m
        xt, at = motion(t + LATENCY, kind)
        true = cello(xt, at, rng)
        a_, b_ = lit > 0.5, true > 0.5
        ious.append((a_ & b_).sum() / (a_ | b_).sum())
        errs.append(np.nonzero(a_)[1].mean() - np.nonzero(b_)[1].mean())
    e = np.abs(np.array(errs))
    return e.mean(), e.max(), float(np.mean(ious)), float(np.std(errs))


def check(name, ok, detail):
    print(f"{'PASS' if ok else 'FAIL'}  {name:34s} {detail}")
    return ok


def main():
    ok = True
    rows = {}
    for lead in (0.0, 0.15, 0.25, 0.35):
        rows[lead] = {k: run(k, lead) for k in ("still", "sway", "jerk")}
        r = rows[lead]
        print(f"lead {lead:.2f} s: sway trail {r['sway'][0]:5.1f} px (IoU {r['sway'][2]:.3f}), "
              f"move-and-stop {r['jerk'][0]:4.1f} px mean, still jitter {r['still'][3]:.2f} px")
    base, best = rows[0.0], rows[0.25]
    # a straight-line forecast cannot follow the curve of a sway 0.35 s
    # ahead, so about half the trail is what is to be had
    ok &= check("prediction shrinks the sway trail", best["sway"][0] < 0.6 * base["sway"][0],
                f"{base['sway'][0]:.1f} -> {best['sway'][0]:.1f} px mean, "
                f"IoU {base['sway'][2]:.3f} -> {best['sway'][2]:.3f}")
    # the first 0.35 s of a sudden move cannot be foreseen; after it the
    # light must not overshoot the stop by much
    ok &= check("quick move and stop", best["jerk"][0] <= 1.3 * base["jerk"][0],
                f"mean {base['jerk'][0]:.1f} -> {best['jerk'][0]:.1f} px")
    ok &= check("still cello stays still", best["still"][3] < 1.0,
                f"jitter {best['still'][3]:.2f} px")

    # the plane: a cello leaning back and forth +-8 deg, 3 s period
    pp = PlanePredictor()
    rng = np.random.default_rng(2)
    errs0, errs1 = [], []

    def normal(t):
        a = np.radians(8) * np.sin(2 * np.pi * t / 3)
        return np.array([0.0, np.sin(a), -np.cos(a)])

    for k in range(5 * FPS):
        t = k / FPS
        n = normal(t) + rng.normal(0, 0.01, 3)
        pp.update(np.array([0.05, 0.1, 1.9]), n / np.linalg.norm(n), t)
        if t < 1.0:
            continue
        want = normal(t + LATENCY)
        got = pp.at(t + 0.25)[1]
        errs1.append(np.degrees(np.arccos(np.clip(got @ want, -1, 1))))
        errs0.append(np.degrees(np.arccos(np.clip(normal(t) @ want, -1, 1))))
    ok &= check("plane tilt predicted", np.mean(errs1) < 0.85 * np.mean(errs0),
                f"tilt error {np.mean(errs0):.2f} -> {np.mean(errs1):.2f} deg mean")

    print("ALL TESTS PASSED" if ok else "SOME TESTS FAILED")
    raise SystemExit(0 if ok else 1)


if __name__ == "__main__":
    main()
