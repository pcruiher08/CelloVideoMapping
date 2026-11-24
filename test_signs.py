"""Hand signs (cellomask/signs.py): the glove's silhouette read as ✌️ / 👍,
the 1 s hold, and lowering the hand before the same sign toggles again.

    .venv/bin/python test_signs.py

Synthetic white-glove silhouettes on a dark stage, 500 px per metre at the
cello (the stage's full-resolution Kinect image).
"""

import sys

import cv2
import numpy as np

from cellomask.signs import SignWatcher

K = np.array([[1060.0, 0, 960], [0, 1060.0, 540], [0, 0, 1]])
C = np.array([0.0, 0.1, 2.12])               # 500 px/m at the cello


def frame(sign):
    """A dark frame with a white glove beside the neck making `sign`."""
    img = np.full((1080, 1920, 3), (60, 40, 20), np.uint8)       # dark blue backdrop
    cx, cy = 960 + int(0.32 * 500), 593 - int(0.36 * 500)        # inside the zone
    white = (235, 238, 240)
    if sign in ("V", "T", "fist"):
        cv2.ellipse(img, (cx, cy + 30), (32, 30), 0, 0, 360, white, -1)          # the fist / palm
    if sign == "V":
        for dx, ang in ((-14, -14), (14, 14)):                                     # two fingers, apart
            pts = cv2.ellipse2Poly((cx + dx + int(ang * 1.2), cy - 30), (8, 38), ang, 0, 360, 5)
            cv2.fillPoly(img, [pts], white)
    if sign == "T":
        cv2.ellipse(img, (cx - 6, cy - 22), (9, 30), 0, 0, 360, white, -1)          # the thumb, up
    return img


def main():
    fails = []
    w = SignWatcher()
    z = w.zone(C, K, (1080, 1920))
    for sign, want in (("V", "V"), ("T", "T"), ("fist", "o"), (None, None)):
        x0, y0, x1, y1, ppm = z
        got = w.classify(frame(sign)[y0:y1, x0:x1], ppm)
        if got != want:
            fails.append(f"{sign}: read as {got!r}, want {want!r}")

    def run(sign, secs, t):
        ev = []
        for i in range(int(secs * 30)):
            e = w.update(frame(sign), K, C, now=t + i / 30)
            if e:
                ev.append(e)
        return ev, t + secs

    t = 0.0
    ev, t = run(None, 3.0, t)                  # the empty zone, learned as the usual look
    if ev:
        fails.append(f"an empty zone toggled something: {ev}")
    ev, t = run("V", 0.6, t)
    if ev:
        fails.append(f"toggled after only 0.6 s of peace: {ev}")
    ev, t = run("V", 0.8, t)
    if ev != [("pingpong", True)]:
        fails.append(f"peace held 1.4 s: {ev}, want ping-pong on")
    ev, t = run("V", 2.0, t)
    if ev:
        fails.append(f"peace kept up toggled again without lowering the hand: {ev}")
    ev, t = run(None, 0.7, t)
    ev, t = run("T", 1.4, t)
    if ev != [("overdrive", True)]:
        fails.append(f"thumbs up held 1.4 s: {ev}, want overdrive on")
    ev, t = run(None, 0.7, t)
    ev, t = run("V", 1.4, t)
    if ev != [("pingpong", False)]:
        fails.append(f"peace again after lowering: {ev}, want ping-pong off")
    ev, t = run("fist", 2.0, t)
    if ev:
        fails.append(f"a fist toggled something: {ev}")

    # scenery: a white board with printed letters in the zone from the
    # start (daylight on the stage) reads like a glove, but it was always
    # there: never a sign
    b = SignWatcher()
    board = frame(None)
    x0, y0, x1, y1, _ = b.zone(C, K, (1080, 1920))
    cv2.rectangle(board, (x0 - 40, y0 - 40), (x0 + 150, y1 + 60), (240, 240, 240), -1)
    for k in range(6):
        cv2.putText(board, "ALTO NO", (x0 - 30, y0 + 30 + 40 * k), cv2.FONT_HERSHEY_SIMPLEX, 1.1, (40, 40, 200), 3)
    evs = [b.update(board, K, C, now=i / 30) for i in range(30 * 8)]
    if any(evs):
        fails.append(f"a white board in the zone toggled: {[e for e in evs if e]}")
    # and a real sign in front of that board still works
    hand = board.copy()
    cx, cy = x0 + 205, y0 + 120                # clear of the board (white on white is invisible)
    cv2.ellipse(hand, (cx, cy + 30), (32, 30), 0, 0, 360, (235, 238, 240), -1)
    for dx, ang in ((-14, -14), (14, 14)):
        cv2.fillPoly(hand, [cv2.ellipse2Poly((cx + dx + int(ang * 1.2), cy - 30), (8, 38), ang, 0, 360, 5)],
                     (235, 238, 240))
    evs = [b.update(hand, K, C, now=8 + i / 30) for i in range(45)]
    if [e for e in evs if e] != [("pingpong", True)]:
        fails.append(f"peace beside the board: {[e for e in evs if e]}, want ping-pong on")

    # a white shirt: the sleeve comes into the zone with the hand (one white
    # blob running into the zone's edge), and the bow sweeps through it while
    # playing: neither is a sign
    c = SignWatcher()
    for i in range(90):
        c.update(frame(None), K, C, now=i / 30)                    # the empty zone learned
    zx0, zy0, zx1, zy1, _ = c.zone(C, K, (1080, 1920))
    evs = []
    for i in range(30 * 4):
        img = frame("V")
        cx, cy = 960 + int(0.32 * 500), 593 - int(0.36 * 500)
        cv2.line(img, (zx0 - 60, zy1 + 60), (cx, cy + 40), (238, 238, 238), 55)   # the white sleeve
        swing = int(120 * np.sin(i / 30 * 2 * np.pi / 1.5))
        a, b = (zx0 - 200, zy1 - 40 + swing), (zx1 + 200, zy0 + 60 - swing)
        cv2.line(img, a, b, (230, 230, 230), 6)                                  # the bow, moving
        evs.append(c.update(img, K, C, now=3 + i / 30, bow=(a, b)))
    if any(evs):
        fails.append(f"white sleeve + moving bow toggled: {[e for e in evs if e]}")

    print("ALL TESTS PASSED" if not fails else "FAILED:\n  " + "\n  ".join(fails))
    return not fails


if __name__ == "__main__":
    sys.exit(0 if main() else 1)
