"""The 3D cello scan and the depth flood fill, on a synthetic cello: an
arched top with a raised fingerboard and a neck, in front of a wall, seen
by a Kinect-like camera (1280x720 colour, 480x270 depth with noise).

    .venv/bin/python test_model3d.py
"""

import os
import sys
import tempfile

import cv2
import numpy as np

ROOT = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, ROOT)

from cellomask.model3d import CelloModel, depth_refine  # noqa: E402
from cellomask.relocate import rodrigues  # noqa: E402

W, H, DW, DH = 1280, 720, 480, 270
K = np.array([[720.9, 0, 639.5], [0, 720.9, 359.5], [0, 0, 1]])
rng = np.random.default_rng(1)


def inside(u, v):
    """The cello's outline in its own plane (metres; v up the cello)."""
    lower = (u / 0.22) ** 2 + ((v + 0.18) / 0.20) ** 2 < 1
    upper = (u / 0.17) ** 2 + ((v - 0.17) / 0.17) ** 2 < 1
    waist = (np.abs(u) < 0.12) & (np.abs(v) < 0.06)
    neck = (np.abs(u) < 0.03) & (v > 0.3) & (v < 0.62)
    return lower | upper | waist | neck


def height(u, v):
    """Arched top, plus the fingerboard rising towards the neck."""
    arch = 0.025 * np.sqrt(np.clip(1 - (u / 0.22) ** 2 - (v / 0.4) ** 2, 0, 1))
    board = (np.abs(u) < 0.035) & (v > -0.02)
    return np.where(board, np.maximum(arch, 0.03 + 0.05 * np.clip(v, 0, 0.62) / 0.62), arch)


g = np.arange(-0.25, 0.65, 0.0015)
UU, VV = np.meshgrid(np.arange(-0.24, 0.24, 0.0015), g)
on = inside(UU, VV)
LOCAL = np.c_[UU[on], VV[on], height(UU[on], VV[on])]


def pose(t, lean=0.0, turn=0.0, roll=0.0):
    """Local (u right, v up, w towards the camera) -> camera (x right, y down, z ahead)."""
    base = np.array([[1, 0, 0], [0, -1, 0], [0, 0, -1]], float)
    R = rodrigues(np.radians([lean, 0, 0])) @ rodrigues(np.radians([0, turn, 0])) @ \
        rodrigues(np.radians([0, 0, roll])) @ base
    return R, np.asarray(t, float)


def view(R, t, hand=None, noise=0.0015):
    """(packet, true mask, visible mask) for the cello at (R, t). `hand`:
    (u, v, radius) of a hand 10 cm in front of the top."""
    X = LOCAL @ R.T + t
    zbuf = np.full((DH, DW), 3.0)                            # the wall
    u = np.round(X[:, 0] / X[:, 2] * K[0, 0] * DW / W + (K[0, 2] + 0.5) * DW / W - 0.5).astype(int)
    v = np.round(X[:, 1] / X[:, 2] * K[1, 1] * DH / H + (K[1, 2] + 0.5) * DH / H - 0.5).astype(int)
    ok = (u >= 0) & (u < DW) & (v >= 0) & (v < DH)
    np.minimum.at(zbuf, (v[ok], u[ok]), X[ok, 2])
    # true silhouette: the dense surface splatted at full resolution
    ui = np.round(X[:, 0] / X[:, 2] * K[0, 0] + K[0, 2]).astype(int)
    vi = np.round(X[:, 1] / X[:, 2] * K[1, 1] + K[1, 2]).astype(int)
    m = np.zeros((H, W), np.uint8)
    k = (ui >= 0) & (ui < W) & (vi >= 0) & (vi < H)
    m[vi[k], ui[k]] = 1
    m = cv2.morphologyEx(m, cv2.MORPH_CLOSE, np.ones((5, 5), np.uint8))
    vis = m.copy()
    if hand is not None:
        hu, hv, hr = hand
        c = np.array([hu, hv, height(np.array(hu), np.array(hv)) + 0.10]) @ R.T + t
        cxi, cyi = c[0] / c[2] * K[0, 0] + K[0, 2], c[1] / c[2] * K[1, 1] + K[1, 2]
        rp = hr / c[2] * K[0, 0]
        cv2.circle(vis, (int(cxi), int(cyi)), int(rp), 0, -1)
        yy, xx = np.mgrid[0:DH, 0:DW]
        dd = (xx - cxi * DW / W) ** 2 + (yy - cyi * DH / H) ** 2 < (rp * DW / W) ** 2
        zbuf[dd] = c[2]
    depth = (zbuf + rng.normal(0, noise, zbuf.shape)).astype(np.float32)
    pkt = {"depth": depth, "conf": np.full((DH, DW), 2, np.uint8), "K": K, "size": (W, H)}
    return pkt, m.astype(np.float32), vis.astype(np.float32)


def iou(a, b):
    a, b = a > 0.5, b > 0.5
    return float((a & b).sum()) / max(1, (a | b).sum())


def main():
    R0, t0 = pose([0.03, 0.05, 1.3])
    packets, mask0 = [], None
    for _ in range(10):
        p, mask0, _ = view(R0, t0)
        packets.append(p)
    path = os.path.join(tempfile.mkdtemp(), "cello_model.npz")
    model = CelloModel(path)
    msg = model.learn(packets, mask0, K, (W, H))
    assert msg and os.path.exists(path), msg
    print(f"learn: {msg}")
    assert CelloModel(path).learned                          # saved and loaded back

    # moved, leaning back, turned and rolled in the image: from scratch, then a few frames
    R1, t1 = pose([0.08, 0.02, 1.38], lean=7, turn=9, roll=5)
    for i in range(4):
        pkt, truth, vis = view(R1, t1)
        out = model.track(vis, pkt, K)
        assert out is not None, f"frame {i}: no fit {model.stats}"
    j = iou(out, truth)
    # the true motion of the scan: learning pose -> now
    Rt = R1 @ R0.T
    tt = t1 - Rt @ t0
    dR = model.M[:3, :3] @ Rt.T
    ang = np.degrees(np.arccos(np.clip((np.trace(dR) - 1) / 2, -1, 1)))
    centre = LOCAL.mean(0)
    off = 1000 * np.linalg.norm((model.M[:3, :3] @ (R0 @ centre + t0) + model.M[:3, 3]) - (R1 @ centre + t1))
    print(f"moved: IoU {j:.3f}, pose off by {ang:.2f} deg / {off:.1f} mm, "
          f"edge {model.stats['edge_px']:.1f} px, surface {model.stats['rms_mm']:.1f} mm")
    assert j > 0.95 and ang < 1.0 and off < 10, (j, ang, off)

    # a hand 10 cm in front of the lower bout: the light keeps the whole cello
    pkt, truth, vis = view(R1, t1, hand=(0.08, -0.2, 0.07))
    out = model.track(vis, pkt, K)
    assert out is not None, model.stats
    j_vis, j = iou(vis, truth), iou(out, truth)
    print(f"hand in front: visible mask IoU {j_vis:.3f} -> scan IoU {j:.3f}")
    assert j > 0.95 and j > j_vis + 0.02

    # following a slow sway frame to frame
    worst = 1.0
    for k in range(12):
        R, t = pose([0.08 + 0.004 * k, 0.02, 1.38 - 0.003 * k], lean=7 - 0.5 * k, turn=9 - 0.8 * k, roll=5)
        pkt, truth, vis = view(R, t)
        out = model.track(vis, pkt, K)
        assert out is not None, (k, model.stats)
        worst = min(worst, iou(out, truth))
    print(f"sway over 12 frames: worst IoU {worst:.3f}")
    assert worst > 0.95

    # depth alone (no detection, as between YOLO frames): the visible cello
    # comes from the depth fill grown from where the scan was last frame
    worst = 1.0
    for k in range(12):
        R, t = pose([0.13 - 0.01 * k, 0.02, 1.35 + 0.004 * k], lean=1 + 0.6 * k, turn=-1 + 0.7 * k, roll=5)
        pkt, truth, _ = view(R, t)
        prev = model.render(model.M, K, (W, H)).astype(np.float32)
        out = model.track(depth_refine(prev, pkt, K), pkt, K)
        assert out is not None, (k, model.stats)
        # the fit itself (the drawn shape is smoothed and trails a little by design)
        worst = min(worst, iou(model.render(model.M, K, (W, H)), truth))
    print(f"depth only, 1 cm a frame over 12 frames: worst IoU {worst:.3f}")
    assert worst > 0.93               # a harder motion than the sway above (up to 7 deg of turn)

    # lost after a fast move, held at a steep angle (unlike the stand it
    # was scanned on): it must re-lock on the first frame it is found again
    R2, t2 = pose([0.06, 0.03, 1.4], lean=20, turn=18, roll=6)
    for k in range(8):                    # lean in steps while tracked
        a = (k + 1) / 8
        R, t = pose([0.06, 0.03, 1.4], lean=20 * a, turn=18 * a, roll=6 * a)
        pkt, truth, vis = view(R, t)
        assert model.track(vis, pkt, K) is not None, (k, model.stats)
    model.ok = False                      # lost; the cello is now 15 cm away
    R3, t3 = pose([-0.09, 0.05, 1.42], lean=21, turn=17, roll=6)
    pkt, truth, vis = view(R3, t3)
    out = model.track(vis, pkt, K)
    assert out is not None, model.stats
    j = iou(out, truth)
    for _ in range(3):                    # the same frame tracked on (warm): what the scan can do here
        ref = model.track(vis, pkt, K)
    j_ref = iou(ref, truth)
    print(f"re-lock after a fast move at a steep angle: IoU {j:.3f} on the first frame "
          f"(tracked at that pose: {j_ref:.3f})")
    assert j > j_ref - 0.01

    # flood fill: a mask spilling 12 px onto the wall on the left, 10 px
    # short on the right, and missing the fingerboard strip
    pkt, truth, _ = view(R1, t1)
    bad = truth.copy()
    ys, xs = np.nonzero(truth > 0.5)
    mid = xs.mean()
    grow = cv2.dilate(truth, np.ones((25, 25), np.uint8))
    shrink = cv2.erode(truth, np.ones((21, 21), np.uint8))
    xx = np.arange(W)[None, :]
    bad = np.where(xx < mid, grow, shrink)
    c = (np.array([0, 0.25, 0.06]) @ R1.T + t1)
    cxi = int(c[0] / c[2] * K[0, 0] + K[0, 2])
    bad[:, cxi - 12:cxi + 12] = np.where(np.arange(H)[:, None] < c[1] / c[2] * K[1, 1] + K[1, 2], 0,
                                         bad[:, cxi - 12:cxi + 12])
    fixed = depth_refine(bad, pkt, K)
    print(f"flood fill: mask IoU {iou(bad, truth):.3f} -> {iou(fixed, truth):.3f}")
    assert iou(fixed, truth) > 0.93 and iou(fixed, truth) > iou(bad, truth) + 0.04
    # a person near the camera also detected as a cello (a red shirt): the
    # scan fits only the cello, and depth says the shirt is not cello-sized
    from cellomask.server import CELLO_SIZE, physical_size, size_error
    pkt, truth, vis = view(R1, t1)
    shirt = np.zeros((H, W), np.float32)
    shirt[150:600, 950:1250] = 1                          # 0.8 m away: ~0.5 x 0.33 m
    yy, xx = np.mgrid[0:DH, 0:DW]
    pkt["depth"][(yy >= 150 * DH // H) & (yy < 600 * DH // H) & (xx >= 950 * DW // W) & (xx < 1250 * DW // W)] = 0.8
    model.ok = False
    assert model.track(depth_refine(shirt, pkt, K), pkt, K) is None, "the scan must not fit the shirt"
    model.ok = False
    assert model.track(depth_refine(vis, pkt, K), pkt, K) is not None
    e_shirt = size_error(physical_size(shirt, pkt, K), CELLO_SIZE)
    e_cello = size_error(physical_size(truth, pkt, K), CELLO_SIZE)
    print(f"person vs cello: scan fits only the cello; size error {e_shirt:.2f} vs {e_cello:.2f}")
    assert e_shirt > 0.45 > e_cello
    print("ALL TESTS PASSED")


if __name__ == "__main__":
    main()
