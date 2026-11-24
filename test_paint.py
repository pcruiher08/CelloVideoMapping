"""Bow painting (cellomask/paint.py): the start / stop gestures, the brush
landing on the cello, and a look at the paint.

    .venv/bin/python test_paint.py [out_dir]     # writes paint_*.jpg there

A cello 2.9 m in front of the camera, facing it; a simulated player: the bow
held upright for 2 s (start), ~12 s of strokes, held pointing down (stop).
"""

import math
import os
import sys

import cv2
import numpy as np

from cellomask.paint import BowPainter

K = np.array([[520.0, 0, 480], [0, 520.0, 270], [0, 0, 1]])
C = np.array([0.0, 0.05, 2.9])
AXIS = np.array([0.0, -1.0, 0.0])           # towards the scroll (camera y points down)
N = np.array([0.0, 0.0, -1.0])              # out of the top, towards the camera
SIDE = np.cross(AXIS, N)
CELLO = {"C": C, "axis": AXIS, "n": N}


def project(P):
    return np.array([P[0] / P[2] * K[0, 0] + K[0, 2], P[1] / P[2] * K[1, 1] + K[1, 2]])


def quad(L=1.25, W=0.52):
    """As Plane.quad: the image's corners in camera px, and its size (m)."""
    c = [C + AXIS * L / 2 - SIDE * W / 2, C + AXIS * L / 2 + SIDE * W / 2,
         C - AXIS * L / 2 + SIDE * W / 2, C - AXIS * L / 2 - SIDE * W / 2]
    return np.float32([project(p) for p in c]), (L, W)


def bow(angle_deg, along, tip_x, tip_y, speed=0.0):
    """A bow state as bow.py gives it (only what the painter reads)."""
    tip = C + tip_x * SIDE + tip_y * AXIS + np.array([0, 0, -0.1])
    frog = tip - 0.6 * SIDE                    # across the strings, in the cello's plane
    return {"ok": True, "angle": angle_deg, "tilt": 0.0, "along": along, "tip": tip, "frog": frog,
            "speed": speed}


def main(out):
    os.makedirs(out, exist_ok=True)
    p = BowPainter()
    Q = quad()
    t, dt = 0.0, 1 / 30
    events = []
    fails = []

    def step(st):
        nonlocal t
        e = p.update(st, CELLO, Q, K, now=t)
        if e:
            events.append((round(t, 2), e))
        t += dt

    # 1. playing before any start gesture: nothing is painted
    for i in range(60):
        step(bow(8, -0.12, 0.3 * math.sin(i * 0.2), -0.1))
    if p.active or p.alpha.any():
        fails.append("painted before the start gesture")

    # 2. upright 1.5 s, let go, upright again 2.2 s with a 0.3 s dropout in it
    for i in range(45):
        step(bow(82, 0.28, -0.25, 0.55))
    for i in range(30):
        step(None)
    if p.active:
        fails.append("started after only 1.5 s upright")
    for i in range(66):
        step(None if 30 <= i < 39 else bow(80, 0.27, -0.25, 0.55))
    if not p.active:
        fails.append("did not start after 2.2 s upright (with a 0.3 s dropout)")

    # 3. playing: down- and up-bows sweeping across, the bow's angle rocking
    # (string crossings) and its contact moving towards the fingerboard
    t_play = t
    for i in range(360):
        s = (t - t_play)
        x = 0.38 * math.sin(2 * math.pi * s / 1.6)
        y = -0.05 + 0.22 * math.sin(2 * math.pi * s / 7.0) + 0.06 * math.sin(2 * math.pi * s / 1.1)
        v = math.cos(2 * math.pi * s / 1.6)
        step(bow(10 * math.sin(s), -0.1, x, y, speed=0.6 * v))
        if i == 120:
            cv2.imwrite(os.path.join(out, "paint_04s.jpg"), preview(p))
    cv2.imwrite(os.path.join(out, "paint_12s.jpg"), preview(p))
    painted = (p.alpha > 8).mean()
    if painted < 0.08:
        fails.append(f"only {painted:.1%} of the canvas painted after 12 s of playing")
    if p.pose is not None:
        fails.append(f"playing read as a gesture ({p.pose})")

    # 4. pointing down 2.2 s: stops, then fades out
    for i in range(66):
        step(bow(-84, -0.30, 0.1, -0.6))
    if p.active:
        fails.append("did not stop after 2.2 s pointing down")
    for i in range(int(3.2 / dt)):
        step(None)
    if p.alpha.any():
        fails.append("the painting did not fade out after stopping")

    # 5. a swapped frog / tip (angle sign flipped) still reads by where the
    # bow's middle is: upright starts
    for i in range(66):
        step(bow(-80, 0.27, -0.25, 0.55))
    if not p.active:
        fails.append("upright with frog/tip swapped did not start")

    # 5b. the eraser: paint first, then the bow flipped (along the strings,
    # leaning out, its free end at the cello) wipes where it passes; then
    # normal playing paints again
    for i in range(90):
        s = i / 30
        step(bow(5, -0.1, 0.3 * math.sin(2 * math.pi * s / 1.6), 0.1 * math.sin(s), 0.5))
    before = int((p.alpha > 8).sum())
    for i in range(90):
        s = i / 30
        st = bow(-70, 0.35, 0.3 * math.sin(2 * math.pi * s / 1.6), 0.1 * math.sin(s))
        st["tilt"] = -45.0
        st["tip"] = C + st["tip"] - C + np.array([0, 0, 0.1])           # free end at the wood
        st["frog"] = st["tip"] - 0.5 * N + 0.2 * AXIS                     # held end sticking out
        step(st)
        if i == 15 and not p.erasing:
            fails.append("the flipped bow did not switch to the eraser within 0.5 s")
    after = int((p.alpha > 8).sum())
    if after > 0.7 * before:
        fails.append(f"the eraser wiped little: {before} -> {after} painted px")
    for i in range(30):
        step(bow(5, -0.1, 0.2, 0.0, 0.5))
    if p.erasing:
        fails.append("still erasing after 1 s of normal playing")

    # 6. where the paint lands: the brush at the cello's centre is the
    # picture's centre; on the rectangle's right edge it is the right edge of
    # the part of the picture the projector shows (cover-fitted, sides cut)
    q = BowPainter()
    L, W = Q[1]
    for tx, want in ((0.0, 0.5), (W / 2 / q.reach, 1.0)):
        st = bow(0, 0, tx, 0)
        st["tip"] = C + tx * SIDE                     # on the plane itself
        pt = q.brush_point(st, CELLO, Q, K)
        if pt is None or abs(pt[0] / q.W - want) > 0.01 or abs(pt[1] / q.H - 0.5) > 0.01:
            fails.append(f"brush for tip x={tx:.2f} m at {None if pt is None else (pt / [q.W, q.H]).round(3)}, want u={want}")
    q.start()
    q.now = 0.0                                       # a fixed moment of the drift
    q.color[:] = 255
    q.alpha[:, -30:] = 255                            # paint a band at the canvas' right edge
    img = q.compose(np.zeros((1080, 720, 3), np.uint8))
    cols = np.nonzero(img.max(axis=(0, 2)) > 0)[0]
    sc = max(W / 720, L / 1080)
    right = (720 + W / sc) / 2
    drift = 0.012 * L / sc                            # the display-time drift's reach (px)
    if not len(cols) or abs(cols.max() - right) > drift + 4:
        fails.append(f"canvas edge composited at x={cols.max() if len(cols) else None}, want ~{right:.0f}")

    # 7. behind TouchDesigner's graphics: a bright patch of its picture
    # covers the paint, its black shows the paint
    q.alpha[:] = 255
    q.color[:] = (255, 0, 255)
    td = np.zeros((1080, 720, 3), np.uint8)
    td[500:580, 330:390] = (0, 200, 0)                # a bright green graphic in the middle
    img = q.compose(td, behind=True)
    if tuple(img[540, 360]) != (0, 200, 0):
        fails.append(f"behind: the bright graphic was covered by the paint ({tuple(img[540, 360])})")
    if img[300, 360].max() < 200 or img[300, 360][1] > 40:
        fails.append(f"behind: the paint did not show through the black ({tuple(img[300, 360])})")
    img = q.compose(td, behind=False)
    if img[540, 360][1] > 40:
        fails.append("on top: the paint did not cover the graphic")

    print("events:", events)
    print(f"painted after 12 s: {painted:.1%}")
    print("ALL TESTS PASSED" if not fails else "FAILED:\n  " + "\n  ".join(fails))
    return not fails


def preview(p):
    """The painting over a dim stand-in for TouchDesigner's picture."""
    bg = np.full((1080, 720, 3), 14, np.uint8)
    return p.compose(bg)


if __name__ == "__main__":
    sys.exit(0 if main(sys.argv[1] if len(sys.argv) > 1 else "paint_test") else 1)
