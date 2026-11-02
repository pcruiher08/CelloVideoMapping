"""The cello's surface in 3D, every frame, from the iPhone's LiDAR depth.

A plane fitted to the depth inside the segmentation mask gives the cello's
distance, lean and turn. With the 3D projector model (procam3d) that plane
fixes the exact camera -> projector mapping for the cello's current pose,
which replaces the flat calibration: that one is only right at the depth and
angle the cello had while calibrating.

The plane also gives the replacement image its perspective: it is laid on
the cello's plane, so it foreshortens as the cello leans, rather than only
being clipped by the silhouette.
"""

import copy

import cv2
import numpy as np

from bowtrack.one_euro import OneEuroFilter

from .procam3d import backproject


class CelloPlane:
    """Robust plane through the cello's front, smoothed over time:
    centre C (metres, camera frame) and unit normal n pointing at the camera."""

    def __init__(self, min_points=60):
        self.min_points = min_points
        self.reset()

    def reset(self):
        self.C = self.n = None
        self.raw = None
        self.f = None
        self.points = 0
        self.residual = None

    def __call__(self, mask, pkt, t):
        """Update from the frame's mask (camera pixels) and its iPhone packet.
        Returns True if the plane was fitted on this frame (otherwise the
        last one is kept, for the caller to hold briefly)."""
        if mask is None or pkt is None:
            return False
        depth, conf, K = pkt["depth"], pkt["conf"], pkt["K"]
        dh, dw = depth.shape
        h, w = mask.shape
        # the mask at depth resolution, shrunk so the cello's outline (where
        # LiDAR mixes cello and background) is left out
        m = cv2.resize((mask > 0.5).astype(np.uint8), (dw, dh), interpolation=cv2.INTER_AREA)
        m = cv2.erode(m, np.ones((3, 3), np.uint8))
        ok = (m > 0) & np.isfinite(depth) & (depth > 0.1)
        if conf is not None:
            ok &= conf >= 1
        ys, xs = np.nonzero(ok)
        if len(xs) < self.min_points:
            return False
        u = (xs + 0.5) * w / dw - 0.5
        v = (ys + 0.5) * h / dh - 0.5
        P = backproject(u, v, depth[ys, xs].astype(np.float64), K)
        fit = self.fit(P)
        if fit is None:
            return False
        C, n, res, kept = fit
        if abs(n[0]) > 0.94 or abs(n[1]) > 0.94:
            return False                 # over 70 degrees from facing the camera: not the cello's front
        self.observe(C, n, t, res, kept)
        return True

    def observe(self, C, n, t, res=None, kept=0):
        """A measured plane (from the fit above, or the fitted 3D scan,
        model3d.py) through the smoothing."""
        self.raw = (C, n)                # unsmoothed, for the motion predictor
        if self.f is None:
            # slow when still (no shimmer), quick when the cello moves. beta
            # is per unit of speed: m/s for the centre, rad/s for the normal,
            # so each opens up at a real sway (a single small beta kept the
            # tilt ~120 ms behind a slowly leaning cello)
            self.f = [OneEuroFilter(min_cutoff=2.0, beta=30.0, d_cutoff=3.0) for _ in range(3)] + \
                     [OneEuroFilter(min_cutoff=2.0, beta=12.0, d_cutoff=3.0) for _ in range(3)]
        s = [f(x, t) for f, x in zip(self.f, np.r_[C, n])]
        self.C = np.array(s[:3])
        n = np.array(s[3:])
        self.n = n / np.linalg.norm(n)
        self.points, self.residual = kept, res
        return True

    @staticmethod
    def fit(P, rounds=3):
        """Least-squares plane, dropping points far off it each round (the
        bow, a hand, the fingerboard standing proud of the top)."""
        keep = np.ones(len(P), bool)
        for _ in range(rounds):
            Q = P[keep]
            if len(Q) < 30:
                return None
            C = Q.mean(0)
            # smallest eigenvector of the 3x3 covariance: same plane as an
            # SVD of all points, without waking BLAS's thread pool every frame
            n = np.linalg.eigh(np.cov((Q - C).T))[1][:, 0]
            d = (P - C) @ n
            mad = np.median(np.abs(d[keep])) + 1e-4
            keep = np.abs(d) < max(3 * 1.4826 * mad, 0.01)
        if n @ C > 0:                      # face the camera
            n = -n
        return C, n, float(np.sqrt(np.mean(d[keep] ** 2))), int(keep.sum())

    def moved(self, C, n):
        """A copy of this plane at another centre and normal (a prediction)."""
        p = copy.copy(self)
        p.C, p.n = np.asarray(C, np.float64), np.asarray(n, np.float64)
        return p

    def point(self, uv, K):
        """Camera pixels -> 3D points on the plane."""
        uv = np.asarray(uv, np.float64).reshape(-1, 2)
        r = np.c_[(uv[:, 0] - K[0, 2]) / K[0, 0], (uv[:, 1] - K[1, 2]) / K[1, 1], np.ones(len(uv))]
        return r * ((self.n @ self.C) / (r @ self.n))[:, None]

    def angles(self):
        """(lean back, turn) in degrees relative to facing the camera:
        positive lean = top tilted away, positive turn = right side away."""
        n = -self.n                         # pointing away from the camera
        # top away: that normal tips down (+y); right side away: it tips left
        lean = np.degrees(np.arctan2(n[1], n[2]))
        turn = np.degrees(np.arctan2(-n[0], n[2]))
        return float(lean), float(turn)

    def homography(self, procam, K, roi):
        """Camera -> projector mapping for points on the plane, fitted on a
        grid over `roi` (so the projector's lens distortion is included)."""
        x0, y0, x1, y1 = roi
        gx, gy = np.meshgrid(np.linspace(x0, x1, 7), np.linspace(y0, y1, 7))
        uv = np.stack([gx.ravel(), gy.ravel()], 1)
        p = procam.project(self.point(uv, K))
        H, _ = cv2.findHomography(uv.astype(np.float32), p.astype(np.float32), 0)
        return H

    def quad(self, axis, K, pad=1.05):
        """The 2D axis rectangle (cx, cy, length, width, up) laid on the
        plane: the camera-pixel corners (TL, TR, BR, BL; TL = scroll end,
        image left) of a true rectangle on the cello's surface. On a cello
        leaning back it is a trapezoid, narrower at the top."""
        cx, cy, length, width, up = axis
        u2 = np.array([np.cos(up), np.sin(up)])        # towards the scroll, in the image
        v2 = np.array([-u2[1], u2[0]])
        c = np.array([cx, cy])
        ends = self.point(np.array([c + u2 * length / 2, c - u2 * length / 2,
                                    c - v2 * width / 2, c + v2 * width / 2]), K)
        top, bottom, left, right = ends
        C3 = (top + bottom) / 2
        u3 = top - bottom
        L = np.linalg.norm(u3) * pad
        u3 /= np.linalg.norm(u3)
        v3 = right - left
        v3 -= u3 * (v3 @ u3)                             # square the rectangle on the plane
        Wd = np.linalg.norm(right - left) * pad
        v3 /= np.linalg.norm(v3)
        corners = np.array([C3 + u3 * L / 2 - v3 * Wd / 2, C3 + u3 * L / 2 + v3 * Wd / 2,
                            C3 - u3 * L / 2 + v3 * Wd / 2, C3 - u3 * L / 2 - v3 * Wd / 2])
        uv = (K @ corners.T).T
        return (uv[:, :2] / uv[:, 2:3]).astype(np.float32), (L, Wd)


def front_face(mask, plane, K, depth=None, conf=None, inset_mm=6.0, body_only=True,
               proud=0.06, min_proud_cm2=20.0, proud_mm=60.0, neck_mm=140.0, min_neck_cm2=60.0, scale=4,
               axis=None, neck_off_mm=60.0):
    """The part of the mask that is the cello's front face, for projecting on.

    - holes in the mask (where the segmentation lost the bridge, or the bow
      crossed) are filled: the top is there under them.
    - body_only: the neck and scroll are cut off. They are narrower than a
      disc of `neck_mm`, which the body (upper bout ~34 cm, waist ~23 cm) is
      not, so an opening with that disc leaves the body; only large removed
      pieces centred on the cello's long axis (within `neck_off_mm`) are
      dropped. `axis` is (cx, cy, up angle) in image pixels, from the
      AxisTracker; without it the mask's own. A strip of upper bout left
      narrow by an arm covering the rest is off to the side, and stays.
    - proud: depth more than this (metres) in front of the cello's plane is
      not the top (a hand, the bow, the fingerboard towards the nut), when
      it covers at least `min_proud_cm2` and is at least `proud_mm` wide
      (a hand, 8 cm and up; not the bow: its stick, 3-5 cm wide in the
      smoothed depth, cut a flickering band across the upper bout), judged
      on the cello only. The arched top and fingerboard
      already stand ~3 cm off the plane: at 4 cm one noisy depth frame
      blanked a patch of the lower bout.
    - inset_mm: the edge is pulled in so the light never reaches the ribs
      or the wall past them, whatever the segmentation and calibration error.

    Sizes in mm become pixels with the cello's distance. Works on the mask's
    bounding box at 1/`scale` resolution: the shapes are large."""
    m = mask > 0.5
    if plane.C is None or not m.any():
        return m
    h, w = m.shape
    mm_px = 1000 * plane.C[2] / K[0, 0]           # mm per image pixel at the cello
    ys, xs = np.nonzero(m)
    pad = int(20 / mm_px) + 4
    x0, y0 = max(0, xs.min() - pad), max(0, ys.min() - pad)
    x1, y1 = min(w, xs.max() + 1 + pad), min(h, ys.max() + 1 + pad)
    sub = m[y0:y1, x0:x1].astype(np.uint8)
    # fill enclosed holes: whatever the background flood from the border
    # cannot reach (the box has a margin, so its border is background)
    flood = sub.copy()
    cv2.floodFill(flood, np.zeros((y1 - y0 + 2, x1 - x0 + 2), np.uint8), (0, 0), 1)
    sub |= 1 - flood
    small = cv2.resize(sub, ((x1 - x0) // scale + 1, (y1 - y0) // scale + 1), interpolation=cv2.INTER_AREA)
    mm_s = mm_px * scale
    keep = sub.copy()
    if body_only:
        # found at low resolution, cut at full: the body's edge stays exact
        r = max(1, int(neck_mm / mm_s / 2))
        body = cv2.morphologyEx(small, cv2.MORPH_OPEN,
                                cv2.getStructuringElement(cv2.MORPH_ELLIPSE, (2 * r + 1,) * 2))
        if body.any():
            rest = (small > 0) & (body == 0)
            n, lab, stats, cents = cv2.connectedComponentsWithStats(rest.astype(np.uint8), connectivity=8)
            big = np.flatnonzero(stats[1:, cv2.CC_STAT_AREA] * (mm_s / 10) ** 2 > min_neck_cm2) + 1
            # only pieces whose middle is on the long axis (the neck runs
            # along it; a leftover strip of upper bout is off to one side)
            if axis is None:
                mm = cv2.moments(sub, binaryImage=True)
                c = np.array([mm["m10"], mm["m01"]]) / max(mm["m00"], 1)
                ev = np.linalg.eigh(np.array([[mm["mu20"], mm["mu11"]], [mm["mu11"], mm["mu02"]]]))[1][:, 1]
                up = np.arctan2(ev[1], ev[0])
            else:
                c, up = np.array([axis[0] - x0, axis[1] - y0]), axis[2]
            c = c / scale
            across = np.array([-np.sin(up), np.cos(up)])
            big = big[np.abs((cents[big] - c) @ across) < neck_off_mm / mm_s]
            if len(big):
                drop = np.isin(lab, big).astype(np.uint8)
                drop = cv2.resize(drop, (x1 - x0, y1 - y0), interpolation=cv2.INTER_NEAREST)
                body_full = cv2.resize(body, (x1 - x0, y1 - y0), interpolation=cv2.INTER_NEAREST)
                # grown over the low-res blockiness, but never into the body
                drop = cv2.dilate(drop, np.ones((2 * scale + 1,) * 2, np.uint8)) & (1 - body_full)
                keep &= 1 - drop
    if depth is not None and proud:
        dh, dw = depth.shape
        u, v = np.meshgrid((np.arange(dw) + 0.5) * w / dw - 0.5, (np.arange(dh) + 0.5) * h / dh - 0.5)
        r = np.stack([(u - K[0, 2]) / K[0, 0], (v - K[1, 2]) / K[1, 1], np.ones_like(u)], -1)
        on_plane = (plane.n @ plane.C) / (r @ plane.n)
        ahead = np.isfinite(depth) & (on_plane - depth > proud)
        if conf is not None:
            ahead &= conf >= 1
        # judged on the cello only: the bow joins up with the player's arm
        # outside it, which is wide, and took the thin stick along
        on = cv2.resize(m.astype(np.uint8), (dw, dh), interpolation=cv2.INTER_NEAREST)
        ahead = ahead.astype(np.uint8) & on
        n, lab, stats, _ = cv2.connectedComponentsWithStats(ahead, connectivity=8)
        mm_d = mm_px * w / dw                                         # one depth pixel at the cello, mm
        small = np.flatnonzero(stats[1:, cv2.CC_STAT_AREA] * (mm_d / 10) ** 2 < min_proud_cm2) + 1
        # thin ones (the bow) have no room for a proud_mm disc anywhere
        k = max(1, int(round(proud_mm / mm_d)))
        wide = cv2.morphologyEx(ahead, cv2.MORPH_OPEN, cv2.getStructuringElement(cv2.MORPH_ELLIPSE, (k, k)))
        thin = np.setdiff1d(np.arange(1, n), np.unique(lab[wide > 0]))
        ahead[np.isin(lab, np.union1d(small, thin))] = 0
        ahead = cv2.resize(ahead, (w, h), interpolation=cv2.INTER_NEAREST)[y0:y1, x0:x1]
        ahead = cv2.dilate(ahead, cv2.getStructuringElement(cv2.MORPH_ELLIPSE, (2 * int(15 / mm_px) + 1,) * 2))
        keep &= 1 - ahead
    if inset_mm > 0:
        k = int(round(inset_mm / mm_px))
        if k > 0:
            keep = cv2.erode(keep, cv2.getStructuringElement(cv2.MORPH_ELLIPSE, (2 * k + 1,) * 2))
    out = np.zeros_like(m)
    out[y0:y1, x0:x1] = keep > 0
    return out
