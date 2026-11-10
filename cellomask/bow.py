"""The bow, found in the depth alone (no markers), as a line in 3D.

The bow is the one long, thin, straight thing near the cello. In the
Kinect's depth it shows clearly: each depth cell keeps the nearest reading
in its block, so the 1 cm stick and hair become a line a few cells wide,
nearer than what is behind it. A morphological closing of the depth map
(wider than the bow, narrower than an arm) fills such narrow near valleys;
closing minus depth leaves the thin near objects. Of those, the points
near the cello in 3D (not the room), not on the cello's own axis (its neck,
fingerboard and endpin, known from the scan) are fitted with a straight
line by RANSAC, sized like a bow, preferring last frame's.

What it gives (camera frame, metres): the two ends, which one is the frog
(the end a hand holds: more near, non-thin surface around it), the
direction frog -> tip, and, with the cello's pose, the bow's angle to the
strings and its speed along its own length. A plain line sliding along
itself looks the same, so the speed comes from the tip's motion along the
bow (the tip end is free; the frog end is in the hand).
"""

import time

import cv2
import numpy as np

from .relocate import cloud, depth_K


class BowTracker:
    def __init__(self, kernel=9, min_proud=0.04, max_proud=3.0, near=2.0,
                 inlier=0.015, min_len=0.2, max_len=0.85, gap=0.08):
        self.gap = gap              # the longest break (hand, depth hole) still one bow (m)
        self.kernel, self.min_proud, self.max_proud = kernel, min_proud, max_proud
        self.near, self.inlier = near, inlier
        self.min_len, self.max_len = min_len, max_len
        self.rng = np.random.default_rng(0)
        self.reset()

    def reset(self):
        self.bg = None              # the room's depth with nothing moving (m)
        self.prev = None            # last detection (frog, tip)
        self.t_prev = None
        self.tip_vel = np.zeros(3)  # m/s, low-passed
        self.frog_vel = np.zeros(3)  # the bow hand's velocity (m/s, low-passed)
        self.hand = None
        self.speeds = []            # recent raw speeds along the bow (m/s)
        self.state = None           # the last result
        self.points = None          # candidate points of the last frame (debug)

    # --- detection --------------------------------------------------------------

    def candidates(self, depth, Kd, cello=None):
        """Thin near points (N x 3, camera frame) and their depth pixels."""
        valid = np.isfinite(depth) & (depth > 0.3)
        d = np.where(valid, depth, 8.0).astype(np.float32)
        k = cv2.getStructuringElement(cv2.MORPH_ELLIPSE, (self.kernel, self.kernel))
        closed = cv2.morphologyEx(d, cv2.MORPH_CLOSE, k)
        top = closed - d
        # mostly-valid neighbourhoods only: holes next to a surface fake valleys
        vfrac = cv2.blur(valid.astype(np.float32), (self.kernel, self.kernel))
        cand = valid & (top > self.min_proud) & (top < self.max_proud) & (vfrac > 0.6)
        # and in front of the room as it is when nothing moves: door frames,
        # furniture edges and the floor are thin near things too, but static
        if self.bg is not None:
            # clearly in front of it, beyond that pixel's own flicker (depth
            # steps, a door frame against the wall, flicker by centimetres
            # and passed for something new), and not on the room's own edges
            # (capped: behind a dark doorway the depth flickers by tens of
            # cm, and the bow in the air, a metre in front, was rejected)
            margin = np.clip(4 * self.bg_dev, 0.04, 0.15)
            cand &= ~(np.isfinite(self.bg) & (depth > self.bg - margin))
            cand &= ~self.bg_edges
        if cello is not None and cello.get("S") is not None:
            # over the cello, its own surface is the reference: the bow lies
            # only 3-5 cm above the top where it crosses the strings, too
            # little for the thin-object test; anything over 2 cm in front of
            # the scanned surface (fingerboard included) is not the cello
            sd = self._surface_depth(cello["S"], Kd, depth.shape)
            over = np.isfinite(sd)
            proud = sd - depth
            cand = (cand & ~over) | (over & valid & (proud > 0.02) & (proud < 0.5))
        ys, xs = np.nonzero(cand)
        if len(xs) == 0:
            return np.zeros((0, 3)), (ys, xs)
        z = depth[ys, xs].astype(np.float64)
        P = np.stack([(xs - Kd[0, 2]) * z / Kd[0, 0], (ys - Kd[1, 2]) * z / Kd[1, 1], z], 1)
        if cello is not None:
            C, axis = cello["C"], cello["axis"]
            keep = np.linalg.norm(P - C, axis=1) < self.near
            # not the endpin, along the axis below the body
            rel = P - C
            along = rel @ axis
            off = np.linalg.norm(rel - np.outer(along, axis), axis=1)
            keep &= ~((off < 0.05) & (along < cello.get("bottom", -0.4)))
            P, ys, xs = P[keep], ys[keep], xs[keep]
        return P, (ys, xs)

    @staticmethod
    def _surface_depth(S, Kd, shape):
        """The scanned cello surface (points, camera frame) as a depth map:
        nearest point per depth cell, gaps closed by a small min filter;
        inf off the cello."""
        h, w = shape
        u = np.round(S[:, 0] / S[:, 2] * Kd[0, 0] + Kd[0, 2]).astype(int)
        v = np.round(S[:, 1] / S[:, 2] * Kd[1, 1] + Kd[1, 2]).astype(int)
        ok = (u >= 0) & (u < w) & (v >= 0) & (v < h) & (S[:, 2] > 0.1)
        z = np.full((h, w), np.inf, np.float32)
        np.minimum.at(z, (v[ok], u[ok]), S[ok, 2].astype(np.float32))
        zf = np.where(np.isfinite(z), z, 100.0).astype(np.float32)
        zf = cv2.erode(zf, np.ones((5, 5), np.uint8))          # spread each point over its gap
        return np.where(zf < 99.0, zf, np.inf)

    def _ransac(self, P, iters=250):
        n = len(P)
        best = None
        hyps = []
        if self.prev is not None:
            hyps.append(self.prev)                    # last frame's bow first
        for _ in range(iters):
            i, j = self.rng.integers(0, n, 2)
            if np.linalg.norm(P[i] - P[j]) > 0.12:
                hyps.append((P[i], P[j]))
        for a, b in hyps:
            u = b - a
            L = np.linalg.norm(u)
            if L < 1e-6:
                continue
            u = u / L
            rel = P - a
            t = rel @ u
            dist = np.linalg.norm(rel - np.outer(t, u), axis=1)
            inl = dist < self.inlier
            if inl.sum() < 8:
                continue
            # scored by its longest unbroken run, not its point count: dense
            # short pieces (the cello's rim, an arm's edge) outnumbered the
            # bow's points; nothing else near the cello is 70 cm of line
            ti = np.sort(t[inl])
            cuts = np.flatnonzero(np.diff(ti) > self.gap)
            starts, ends = np.r_[0, cuts + 1], np.r_[cuts, len(ti) - 1]
            run = float((ti[ends] - ti[starts]).max())
            if best is None or run > best[0]:
                best = (run, inl)
        return best

    def _segment(self, P, inl, gap=None):
        """Refine on the inliers: direction by PCA, the extent (the longest
        run without a gap over `gap` m: stray points on the same infinite
        line stretched it past 1.5 m), and how evenly the points cover it."""
        gap = self.gap if gap is None else gap
        Q = P[inl]
        c = Q.mean(0)
        u = np.linalg.eigh(np.cov((Q - c).T))[1][:, -1]
        t = np.sort((Q - c) @ u)
        cuts = np.flatnonzero(np.diff(t) > gap)
        starts, ends = np.r_[0, cuts + 1], np.r_[cuts, len(t) - 1]
        k = int(np.argmax(ends - starts))
        run = t[starts[k]:ends[k] + 1]
        lo, hi = np.percentile(run, [1, 99]) if len(run) > 4 else (run[0], run[-1])
        L = hi - lo
        t = run
        bins = np.histogram(t, bins=max(1, int(L / 0.02)), range=(lo, hi))[0]
        cover = float((bins > 0).mean()) if len(bins) else 0.0
        return c + lo * u, c + hi * u, L, cover

    def _label_ends(self, a, b, depth, Kd, cello):
        """(frog, tip). Playing (the bow across the strings, over the body):
        the frog is in the player's right hand, on their right of the
        strings, which is the camera's left as they face it. In the air:
        as last frame (the ends do not swap in a 30th of a second), else the
        end with the hand and arm on it."""
        if cello is not None:
            C, axis, n = cello["C"], cello["axis"], cello["n"]
            mid = (a + b) / 2 - C
            if abs(mid @ axis) < 0.45 and abs(mid @ n) < 0.3:
                right = np.array([-1.0, 0.0, 0.0])            # camera's left = player's right
                right -= axis * (right @ axis) + n * (right @ n)
                if np.linalg.norm(right) > 1e-6:
                    return (a, b) if (a - b) @ right > 0 else (b, a)
        if self.prev is not None:
            pf, pt = self.prev
            if np.linalg.norm(a - pf) + np.linalg.norm(b - pt) <= np.linalg.norm(a - pt) + np.linalg.norm(b - pf):
                return a, b
            return b, a
        return self._frog_end(a, b, depth, Kd)

    def _hand(self, frog, u, depth, Kd, r=0.09):
        """The bow hand: the centre of the near surface within `r` m of the
        frog end, behind it along the bow (the fist around the frog). It
        moves with the bow as a whole, where the line's own end jumps by
        centimetres as the hand covers more or less of the stick."""
        h, w = depth.shape
        uu = frog[0] / frog[2] * Kd[0, 0] + Kd[0, 2]
        vv = frog[1] / frog[2] * Kd[1, 1] + Kd[1, 2]
        R = int(np.ceil(r * Kd[0, 0] / frog[2])) + 1
        x0, x1 = max(0, int(uu) - R), min(w, int(uu) + R + 1)
        y0, y1 = max(0, int(vv) - R), min(h, int(vv) + R + 1)
        if x1 <= x0 or y1 <= y0:
            return None
        sub = depth[y0:y1, x0:x1]
        ys, xs = np.nonzero(np.isfinite(sub) & (np.abs(sub - frog[2]) < r))
        if len(xs) < 8:
            return None
        z = sub[ys, xs].astype(np.float64)
        P = np.stack([(xs + x0 - Kd[0, 2]) * z / Kd[0, 0], (ys + y0 - Kd[1, 2]) * z / Kd[1, 1], z], 1)
        P = P[np.linalg.norm(P - frog, axis=1) < r]
        return P.mean(0) if len(P) >= 8 else None

    def _frog_end(self, a, b, depth, Kd):
        """Which end the hand holds: more near surface around it that is
        not the thin bow (the fist, the fingers)."""
        def bulk(p):
            u = int(round(p[0] / p[2] * Kd[0, 0] + Kd[0, 2]))
            v = int(round(p[1] / p[2] * Kd[1, 1] + Kd[1, 2]))
            r = max(2, int(round(0.06 * Kd[0, 0] / p[2])))
            h, w = depth.shape
            sub = depth[max(0, v - r):min(h, v + r + 1), max(0, u - r):min(w, u + r + 1)]
            return float((np.abs(sub - p[2]) < 0.06).sum())
        return (a, b) if bulk(a) >= bulk(b) else (b, a)

    def _learn_background(self, depth, res, Kd, slow=0.01, back=0.3):
        """The room's depth with nothing moving: follows slowly where the
        depth agrees with it, quickly where something moved away (the
        background is the farthest steady surface); never where the bow was
        just found, so a bow held still or sliding along itself on a long
        note is not taken for the room."""
        valid = np.isfinite(depth) & (depth > 0.3)
        if self.bg is None:
            self.bg = np.where(valid, depth, np.nan).astype(np.float32)
            self.bg_dev = np.full(depth.shape, 0.02, np.float32)
            self.bg_edges = np.zeros(depth.shape, bool)
            self.n_bg = 0
            return
        bg = self.bg
        new = valid & ~np.isfinite(bg)
        bg[new] = depth[new]
        both = valid & np.isfinite(bg)
        diff = np.where(both, depth - bg, 0)
        upd = both & (np.abs(diff) < 0.05)
        if res is not None:
            # leave the bow's own pixels out
            frog, tip = res[0], res[1]
            line = np.zeros(depth.shape, np.uint8)
            def px(p):
                return (int(round(p[0] / p[2] * Kd[0, 0] + Kd[0, 2])), int(round(p[1] / p[2] * Kd[1, 1] + Kd[1, 2])))
            cv2.line(line, px(frog), px(tip), 1, 9)
            upd &= line == 0
        bg[upd] += slow * diff[upd]
        away = both & (diff > 0.05)
        bg[away] += back * diff[away]
        # each pixel's usual flicker (mean absolute deviation, same pixels)
        dev = self.bg_dev
        dev[upd] += 0.05 * (np.abs(diff[upd]) - dev[upd])
        # the room's own depth edges, refreshed every second or so
        self.n_bg += 1
        if self.n_bg % 15 == 1:
            b = np.where(np.isfinite(bg), bg, 0).astype(np.float32)
            g = np.hypot(cv2.Sobel(b, cv2.CV_32F, 1, 0, ksize=3), cv2.Sobel(b, cv2.CV_32F, 0, 1, ksize=3)) / 8
            edge = (g > 0.04 * np.maximum(b, 0.5)) | ~np.isfinite(bg)
            self.bg_edges = cv2.dilate(edge.astype(np.uint8), np.ones((3, 3), np.uint8)) > 0

    # --- per frame ---------------------------------------------------------------

    def update(self, pkt, K, size, cello=None, t=None):
        """One frame: pkt (depth + intrinsics), K for the frame `size`
        (w, h), cello = (centre, string-axis unit vector, plane normal) in
        the camera frame, or None. Returns the state dict or None.
        cello: {"C": centre, "axis": string direction (unit), "n": plane
        normal, "S": scanned surface points, "bottom": where the body ends
        along the axis (m)}, all in the camera frame, or None."""
        t = time.time() if t is None else t
        depth = pkt["depth"]
        dh, dw = depth.shape
        Kd = depth_K(K, size, (dw, dh))
        P, _ = self.candidates(depth, Kd, cello)
        self.points = P
        res = None
        if len(P) >= 25:
            best = self._ransac(P)
            if best is not None and best[1].sum() >= 20:
                a, b, L, cover = self._segment(P, best[1])
                if self.min_len <= L <= self.max_len and cover > 0.45:
                    frog, tip = self._label_ends(a, b, depth, Kd, cello)
                    res = (frog, tip, L, int(best[1].sum()), cover)
        self._learn_background(depth, res, Kd)
        if res is None:
            self.prev = None if self.t_prev is None or t - self.t_prev > 0.3 else self.prev
            self.state = {"ok": False}
            return None
        frog, tip, L, n, cover = res
        u = (tip - frog) / max(L, 1e-6)
        hand = self._hand(frog, u, depth, Kd)
        if self.prev is not None and self.t_prev is not None and t > self.t_prev:
            dt = t - self.t_prev
            a = 1.0 / (1.0 + 1.0 / (2 * np.pi * 4.0 * dt))      # ~4 Hz low-pass
            v_tip = (tip - self.prev[1]) / dt
            if np.linalg.norm(v_tip) < 6.0:                   # faster is a misdetection
                self.tip_vel += a * (v_tip - self.tip_vel)
            # the bow hand moves with the bow as a whole (it holds the frog);
            # the line's ends jump as the hand and the cello's edge cut them
            if hand is not None and self.hand is not None:
                v = (hand - self.hand) / dt
                if np.linalg.norm(v) < 4.0:
                    self.frog_vel += a * (v - self.frog_vel)
                    self.speeds = (self.speeds + [float(-(v @ u))])[-5:]
        else:
            self.tip_vel[:] = 0
            self.frog_vel[:] = 0
        self.prev, self.t_prev = (frog, tip), t
        self.hand = hand
        st = {"ok": True, "frog": frog, "tip": tip, "dir": u, "length": float(L),
              "centre": (frog + tip) / 2, "points": int(n), "cover": cover,
              "tip_vel": self.tip_vel.copy(), "frog_vel": self.frog_vel.copy(), "hand": hand,
              # along the bow, + down-bow: the hand pulls the frog away, so
              # the bow travels frog-wards (an up-bow pushes it tip-wards)
              # (median of the last 5 frames: a stroke lasts ~0.5-1 s, a
              # misplaced hand one frame)
              "speed": float(np.median(self.speeds)) if self.speeds else 0.0}
        if cello is not None:
            C, axis, nrm = cello["C"], cello["axis"], cello["n"]
            # the bow in the cello's plane against the strings: 0 = square
            # to them; + when the tip points towards the scroll
            dp = u - nrm * (u @ nrm)
            dp /= np.linalg.norm(dp) + 1e-12
            st["angle"] = float(np.degrees(np.arcsin(np.clip(dp @ axis, -1, 1))))
            # how far the bow leans out of the cello's plane (string crossing)
            st["tilt"] = float(np.degrees(np.arcsin(np.clip(u @ nrm, -1, 1))))
            # where along the strings it crosses, from the cello's centre (m, + towards the scroll)
            st["along"] = float((st["centre"] - C) @ axis)
        self.state = st
        return st
