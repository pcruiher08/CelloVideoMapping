"""Detect two orange-tape markers on the bow and derive x, y, angle.

Pipeline per frame:
  BGR -> HSV -> inRange(orange) -> morphology -> contours -> two best blobs
  -> endpoint identity via nearest-neighbor continuity -> One Euro smoothing.

All positions are also exposed normalized to [0, 1] (origin top-left) so that
downstream consumers (metrics panel, OSC / videomapping) are resolution
independent.
"""

import json
import time
from dataclasses import dataclass, field

import cv2
import numpy as np

from .one_euro import OneEuroFilter, AngleOneEuroFilter

# Default HSV range for orange gaffer tape (OpenCV hue is 0-179).
DEFAULT_HSV_LO = (4, 110, 110)
DEFAULT_HSV_HI = (22, 255, 255)


@dataclass
class BowState:
    ok: bool = False                 # both markers found this frame (or coasting)
    fresh: bool = False              # detection this frame vs held from last
    a: tuple | None = None           # endpoint A (px, smoothed)
    b: tuple | None = None           # endpoint B (px, smoothed)
    x: float = 0.0                   # bow midpoint x (px, smoothed)
    y: float = 0.0                   # bow midpoint y (px, smoothed)
    angle: float = 0.0               # degrees, 0 = horizontal, CCW positive
    nx: float = 0.0                  # normalized midpoint [0,1]
    ny: float = 0.0
    length: float = 0.0              # marker distance in px
    t: float = field(default_factory=time.time)


class BowTracker:
    def __init__(self, hsv_lo=DEFAULT_HSV_LO, hsv_hi=DEFAULT_HSV_HI,
                 min_area=25, max_lost_frames=8):
        self.hsv_lo = np.array(hsv_lo, dtype=np.uint8)
        self.hsv_hi = np.array(hsv_hi, dtype=np.uint8)
        self.min_area = min_area
        self.max_lost_frames = max_lost_frames

        self._kernel = cv2.getStructuringElement(cv2.MORPH_ELLIPSE, (5, 5))
        self._prev_a = None
        self._prev_b = None
        self._lost = 0
        self._last_state = BowState()

        self._fx = OneEuroFilter(min_cutoff=1.2, beta=0.02)
        self._fy = OneEuroFilter(min_cutoff=1.2, beta=0.02)
        self._fangle = AngleOneEuroFilter(min_cutoff=1.0, beta=0.05)
        self.mask = None  # last binary mask, for calibration display

    # ---------------- calibration ----------------

    def sample_hsv(self, frame_bgr, x, y, radius=4):
        """Widen the HSV range to include the tape color around (x, y)."""
        h, w = frame_bgr.shape[:2]
        x0, x1 = max(0, x - radius), min(w, x + radius + 1)
        y0, y1 = max(0, y - radius), min(h, y + radius + 1)
        patch = cv2.cvtColor(frame_bgr[y0:y1, x0:x1], cv2.COLOR_BGR2HSV)
        px = patch.reshape(-1, 3).astype(np.int32)
        med = np.median(px, axis=0)
        lo = np.clip(med - (8, 60, 60), 0, 255).astype(np.uint8)
        hi = np.clip(med + (8, 145, 145), 0, [179, 255, 255]).astype(np.uint8)
        self.hsv_lo = np.minimum(self.hsv_lo, lo)
        self.hsv_hi = np.maximum(self.hsv_hi, hi)
        return med

    def reset_hsv(self):
        self.hsv_lo = np.array(DEFAULT_HSV_LO, dtype=np.uint8)
        self.hsv_hi = np.array(DEFAULT_HSV_HI, dtype=np.uint8)

    def save_config(self, path):
        with open(path, "w") as f:
            json.dump({"hsv_lo": self.hsv_lo.tolist(),
                       "hsv_hi": self.hsv_hi.tolist(),
                       "min_area": self.min_area}, f, indent=2)

    def load_config(self, path):
        with open(path) as f:
            cfg = json.load(f)
        self.hsv_lo = np.array(cfg["hsv_lo"], dtype=np.uint8)
        self.hsv_hi = np.array(cfg["hsv_hi"], dtype=np.uint8)
        self.min_area = cfg.get("min_area", self.min_area)

    # ---------------- detection ----------------

    def _detect_blobs(self, frame_bgr):
        hsv = cv2.cvtColor(frame_bgr, cv2.COLOR_BGR2HSV)
        mask = cv2.inRange(hsv, self.hsv_lo, self.hsv_hi)
        mask = cv2.morphologyEx(mask, cv2.MORPH_OPEN, self._kernel)
        mask = cv2.morphologyEx(mask, cv2.MORPH_CLOSE, self._kernel)
        self.mask = mask

        contours, _ = cv2.findContours(mask, cv2.RETR_EXTERNAL,
                                       cv2.CHAIN_APPROX_SIMPLE)
        blobs = []
        for c in contours:
            area = cv2.contourArea(c)
            if area < self.min_area:
                continue
            m = cv2.moments(c)
            if m["m00"] == 0:
                continue
            blobs.append((area, (m["m10"] / m["m00"], m["m01"] / m["m00"])))
        blobs.sort(key=lambda ab: -ab[0])
        return [c for _, c in blobs[:4]]  # a few candidates, largest first

    def _assign(self, pts):
        """Pick two points and keep A/B identity stable across frames."""
        if len(pts) < 2:
            return None, None
        if self._prev_a is None or self._prev_b is None:
            # First lock: take the two largest, A = leftmost.
            p, q = pts[0], pts[1]
            return (p, q) if p[0] <= q[0] else (q, p)
        # Choose the pair (from up to 4 candidates) minimizing distance
        # to the previous endpoints, trying both assignments.
        best, best_cost = None, float("inf")
        n = len(pts)
        for i in range(n):
            for j in range(i + 1, n):
                for p, q in ((pts[i], pts[j]), (pts[j], pts[i])):
                    cost = (np.hypot(p[0] - self._prev_a[0], p[1] - self._prev_a[1])
                            + np.hypot(q[0] - self._prev_b[0], q[1] - self._prev_b[1]))
                    if cost < best_cost:
                        best_cost, best = cost, (p, q)
        return best

    def update(self, frame_bgr, t=None):
        t = time.time() if t is None else t
        h, w = frame_bgr.shape[:2]
        pts = self._detect_blobs(frame_bgr)
        a, b = self._assign(pts)

        if a is None:
            # Lost: coast on the previous state for a few frames.
            self._lost += 1
            st = self._last_state
            st.fresh = False
            if self._lost > self.max_lost_frames:
                st.ok = False
                self._prev_a = self._prev_b = None
                self._fx.reset(); self._fy.reset(); self._fangle.reset()
            return st

        self._lost = 0
        self._prev_a, self._prev_b = a, b

        mx, my = (a[0] + b[0]) / 2.0, (a[1] + b[1]) / 2.0
        # Screen y grows downward; negate dy so CCW-positive reads naturally.
        raw_angle = np.degrees(np.arctan2(-(b[1] - a[1]), b[0] - a[0]))

        x = self._fx(mx, t)
        y = self._fy(my, t)
        angle = self._fangle(float(raw_angle), t)

        st = BowState(ok=True, fresh=True, a=a, b=b, x=x, y=y, angle=angle,
                      nx=x / w, ny=y / h,
                      length=float(np.hypot(b[0] - a[0], b[1] - a[1])), t=t)
        self._last_state = st
        return st
