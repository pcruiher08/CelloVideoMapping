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
                 inlier=0.03, min_len=0.2, max_len=0.85, gap=0.12, max_range=6.0):
        self.gap = gap
        self.max_range = max_range              # the longest break (hand, depth hole) still one bow (m)
        self.kernel, self.min_proud, self.max_proud = kernel, min_proud, max_proud
        self.near, self.inlier = near, inlier
        self.min_len, self.max_len = min_len, max_len
        self.rng = np.random.default_rng(0)
        self.reset()

    def reset(self):
        self.bg = None              # the room's depth with nothing moving (m)
        self.t_first = None         # the first frame's time
        self.prev_on_cello = False  # the last bow found lay across the cello
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
        dense = vfrac > 0.6
        cand = valid & (top > self.min_proud) & (top < self.max_proud) & dense
        # in front of nothing (a black backdrop gives no depth, nor does the
        # room beyond the Kinect's range): no surface around to stand out
        # from, and the bow over it was lost past the cello's edge. A run of
        # depth with neighbours at its own distance there, not a lone speckle
        # (also where it stands out by more than max_proud: what is "behind"
        # it is the missing depth, filled in as far away)
        cand |= valid & (~dense | (top >= self.max_proud)) & (self._similar_neighbours(depth, valid) >= 3)
        # what is not the room nor the cello (the bow, a hand, the player):
        # where the bow hand is looked for
        fg = valid.copy()
        # and in front of the room as it is when nothing moves: door frames,
        # furniture edges and the floor are thin near things too, but static
        if self.bg is not None:
            # clearly in front of it, beyond that pixel's own flicker (depth
            # steps, a door frame against the wall, flicker by centimetres
            # and passed for something new), and not on the room's own edges
            # (capped: behind a dark doorway the depth flickers by tens of
            # cm, and the bow in the air, a metre in front, was rejected)
            margin = np.clip(4 * self.bg_dev, 0.04, 0.15)
            room = np.isfinite(self.bg) & (depth > self.bg - margin)
            cand &= ~room
            cand &= ~self.bg_edges
            fg &= ~room
        if cello is not None and cello.get("S") is not None:
            # over the cello, its own surface is the reference: the bow lies
            # only 3-5 cm above the top where it crosses the strings, too
            # little for the thin-object test; anything over 2 cm in front of
            # the scanned surface (fingerboard included) is not the cello
            sd = self._surface_depth(cello["S"], Kd, depth.shape)
            over = np.isfinite(sd)
            proud = sd - depth
            cand = (cand & ~over) | (over & valid & (proud > 0.02) & (proud < 0.5))
            fg = (fg & ~over) | (over & valid & (proud > 0.02))
        self.fg = fg
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
            # and nothing below the body's lower end: the floor far behind a
            # stage reads in sparse, flickering specks the room never learns,
            # and with the stage's front edge they lined up into a "bow"
            # below the cello (a third of the frames). Played, the bow is
            # always above it; only a bow pointed at the floor is lost
            keep &= along > cello.get("bottom", -0.4)
            # nor the strings, fingerboard and neck: raised above the top
            # and as long and straight as a bow, along the centre line (the
            # bow crossing them loses ~8 cm there, which `gap` bridges)
            n = cello["n"]
            side = np.cross(axis, n)
            keep &= ~((np.abs(rel @ side) < 0.04) & (np.abs(rel @ n) < 0.12))
            P, ys, xs = P[keep], ys[keep], xs[keep]
        return P, (ys, xs)

    @staticmethod
    def _similar_neighbours(depth, valid, tol=0.05):
        """Per pixel: how many of its 8 neighbours have depth within `tol` m."""
        d = np.where(valid, depth, -10.0).astype(np.float32)
        p = np.pad(d, 1, constant_values=-10.0)
        h, w = d.shape
        n = np.zeros(d.shape, np.uint8)
        for dy in (0, 1, 2):
            for dx in (0, 1, 2):
                if dy == 1 and dx == 1:
                    continue
                n += np.abs(p[dy:dy + h, dx:dx + w] - d) < tol
        return n

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

    @staticmethod
    def _runs(t, inl, gap):
        """Per hypothesis (row): the longest stretch of its inliers' positions
        `t` along it without a break over `gap`, and where it starts and
        ends. All rows at once (a loop over 250 lines cost ~20 ms a frame)."""
        h, n = t.shape
        T = np.sort(np.where(inl, t, np.inf), axis=1)
        ok = np.isfinite(T)
        brk = np.ones((h, n), bool)
        brk[:, 1:] = ~(np.diff(T, axis=1) <= gap)
        start = np.maximum.accumulate(np.where(brk, np.arange(n), 0), axis=1)
        T0 = np.take_along_axis(T, start, 1)
        run = np.where(ok, T - T0, -1.0)
        k = run.argmax(1)
        rows = np.arange(h)
        return run[rows, k], T0[rows, k], T[rows, k]

    def _ransac(self, P, iters=250):
        n = len(P)
        hyps = []
        if self.prev is not None:
            hyps.append(self.prev)                    # last frame's bow first
        i, j = self.rng.integers(0, n, (2, iters))
        far = np.linalg.norm(P[i] - P[j], axis=1) > 0.12
        hyps += list(zip(P[i[far]], P[j[far]]))
        if not hyps:
            return None
        A = np.array([a for a, _ in hyps])
        U = np.array([b for _, b in hyps]) - A
        L = np.linalg.norm(U, axis=1)
        keep = L > 1e-6
        A, U = A[keep], U[keep] / L[keep, None]
        rel = P[None] - A[:, None]                   # hyps x points x 3
        t = np.einsum("hnk,hk->hn", rel, U)
        dist = np.linalg.norm(rel - t[..., None] * U[:, None], axis=2)
        inl = dist < self.inlier
        # scored by its longest unbroken run, not its point count: dense
        # short pieces (the cello's rim, an arm's edge) outnumbered the
        # bow's points; nothing else near the cello is 70 cm of line
        run, _, _ = self._runs(t, inl, self.gap)
        run[inl.sum(1) < 8] = -1
        k = int(run.argmax())
        if run[k] < 0:
            return None
        return float(run[k]), inl[k]

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

    def _fit_image(self, P, iters=250, px_tol=2.0, fx=None):
        """The bow as a line found in the image, its depth from the nearest
        readings along it: (a, b, length, cover, inliers) or None.

        At ~3 m the stick is thinner than one depth pixel, and its depth
        blends with what is behind it (the edge filter, which would drop
        those pixels, is off so the bow is seen at all): over a board 30 cm
        behind it read 10 cm too far, over the cello 5 cm, over nothing
        not at all. A straight 3D line through that bent "bow" broke it in
        pieces. Across the image it is sharp, and blending only ever pushes
        the depth away, so the nearest readings along it are the bow."""
        a2 = P[:, :2] / P[:, 2:3]                     # normalised image coordinates
        z = P[:, 2]
        tol = px_tol / fx
        zm = float(np.median(z))
        gap = self.gap / zm                           # m -> normalised units, about
        n = len(P)
        hyps = []
        if self.prev is not None:
            hyps.append(tuple(self.prev))
        i, j = self.rng.integers(0, n, (2, iters))
        far = np.linalg.norm(a2[i] - a2[j], axis=1) * zm > 0.12
        hyps += list(zip(P[i[far]], P[j[far]]))
        if not hyps:
            return None
        Q0 = np.array([q for q, _ in hyps])
        Q1 = np.array([q for _, q in hyps])
        p0, p1 = Q0[:, :2] / Q0[:, 2:3], Q1[:, :2] / Q1[:, 2:3]
        d = p1 - p0
        L = np.linalg.norm(d, axis=1)
        keep = L > 1e-9
        Q0, Q1, p0, d, L = Q0[keep], Q1[keep], p0[keep], d[keep] / L[keep, None], L[keep]
        rel = a2[None] - p0[:, None]                 # hyps x points x 2
        t = np.einsum("hnk,hk->hn", rel, d)
        across = rel[..., 0] * -d[:, 1:2] + rel[..., 1] * d[:, 0:1]
        # near the line across the image, and at about its depth (1/z
        # affine along it): from a little nearer to 15 cm farther, the
        # blending's side; things that only line up in the image (the
        # floor, a stand, specks) are at other depths
        w = 1 / Q0[:, 2:3] + (1 / Q1[:, 2:3] - 1 / Q0[:, 2:3]) * t / L[:, None]
        zl = 1 / np.maximum(w, 1e-3)
        inl = (np.abs(across) < tol) & (z[None] > zl - 0.05) & (z[None] < zl + 0.15)
        run, lo, hi = self._runs(t, inl, gap)
        run[inl.sum(1) < 8] = -1
        k = int(run.argmax())
        if run[k] < 0:
            return None
        best = (float(run[k]), p0[k], d[k], inl[k], lo[k], hi[k])
        _, p0, d, inl, lo, hi = best
        # refit the direction on the run's points
        t = (a2 - p0) @ d
        sel = inl & (t >= lo) & (t <= hi)
        if sel.sum() < 8:
            return None
        c = a2[sel].mean(0)
        d = np.linalg.eigh(np.cov((a2[sel] - c).T))[1][:, -1]
        t = (a2[sel] - c) @ d
        # depth along it: 1/z is affine in the image position along a 3D
        # line; fitted to the nearer readings of each stretch
        w = 1.0 / z[sel]
        nb = max(2, int(np.ptp(t) * zm / 0.03))
        edges = np.linspace(t.min(), t.max() + 1e-9, nb + 1)
        bt, bw, bn = [], [], []
        for k in range(nb):
            m = (t >= edges[k]) & (t < edges[k + 1])
            if m.sum() >= 2:
                bt.append(t[m].mean())
                bw.append(np.percentile(w[m], 80))      # nearer: larger 1/z
                bn.append(m.sum())
        if len(bt) < 2:
            return None
        bt, bw, bn = map(np.asarray, (bt, bw, bn))
        A = np.c_[bt, np.ones_like(bt)]
        coef = np.linalg.lstsq(A * np.sqrt(bn)[:, None], bw * np.sqrt(bn), rcond=None)[0]
        res = bw - A @ coef
        keep = np.abs(res) < 3 * np.median(np.abs(res)) + 1e-4   # one pass of outlier removal
        if keep.sum() >= 2:
            coef = np.linalg.lstsq(A[keep] * np.sqrt(bn[keep])[:, None], bw[keep] * np.sqrt(bn[keep]), rcond=None)[0]

        def at(tt):
            q = c + tt * d
            ww = coef[0] * tt + coef[1]
            return np.array([q[0], q[1], 1.0]) / max(ww, 1e-3)
        lo, hi = np.percentile(t, [1, 99])
        a, b = at(lo), at(hi)
        L = float(np.linalg.norm(b - a))
        # how evenly the points cover it (2 cm bins)
        tt = np.linspace(lo, hi, max(2, int(L / 0.02)) + 1)
        cover = float((np.histogram(t, bins=tt)[0] > 0).mean())
        return a, b, L, cover, int(sel.sum())

    def _on_cello(self, res, cello):
        """Whether a found bow lies across the cello (near the strings, not
        along them): the bow at rest there is kept out of the room. Only
        that one: anything found still elsewhere (a stand's leg, an edge)
        protected itself as "the bow" and never became room. Remembered
        for the frames it is missed."""
        on = False
        if res is not None and cello is not None:
            frog, tip = res[0], res[1]
            C, axis, n = cello["C"], cello["axis"], cello["n"]
            mid = (frog + tip) / 2 - C
            u = (tip - frog) / (np.linalg.norm(tip - frog) + 1e-9)
            on = abs(mid @ axis) < 0.45 and abs(mid @ n) < 0.3 and abs(u @ axis) < 0.85
        if res is not None:
            self.prev_on_cello = on
        return on

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
        # only what is in front of the room and the cello: with no hand on
        # the bow (at rest on the strings) the cello and the wall around the
        # frog end made a "hand" that wandered as the end did, a speed of up
        # to 1 m/s for a still bow
        fg = getattr(self, "fg", None)
        near = np.isfinite(sub) & (np.abs(sub - frog[2]) < r)
        if fg is not None and fg.shape == depth.shape:
            near &= fg[y0:y1, x0:x1]
        ys, xs = np.nonzero(near)
        if len(xs) < 20:
            return None
        z = sub[ys, xs].astype(np.float64)
        P = np.stack([(xs + x0 - Kd[0, 2]) * z / Kd[0, 0], (ys + y0 - Kd[1, 2]) * z / Kd[1, 1], z], 1)
        rel = P - frog
        P = P[(np.linalg.norm(rel, axis=1) < r) &
              (np.linalg.norm(rel - np.outer(rel @ u, u), axis=1) > 0.02)]   # not the stick itself
        return P.mean(0) if len(P) >= 20 else None

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
        # surfaces and their edges (not a thin thing in front of nothing)
        k = np.ones((self.kernel, self.kernel), np.uint8)
        surface = valid & (cv2.dilate((cv2.blur(valid.astype(np.float32), (self.kernel, self.kernel)) > 0.6)
                                      .astype(np.uint8), k) > 0)
        on_bow = np.zeros(depth.shape, bool)
        if res is None and self.prev_on_cello:
            res = self.prev              # missed for a moment: still there (prev lapses after 0.3 s)
        if res is not None:
            # leave the bow's own pixels out
            frog, tip = res[0], res[1]
            line = np.zeros(depth.shape, np.uint8)
            def px(p):
                return (int(round(p[0] / p[2] * Kd[0, 0] + Kd[0, 2])), int(round(p[1] / p[2] * Kd[1, 1] + Kd[1, 2])))
            u = (tip - frog) / (np.linalg.norm(tip - frog) + 1e-9)
            # well past its ends: a bow at rest is often found only in part,
            # and with only that part kept out, the rest became room after
            # ~10 s, the part found shrank, and with it what was kept out
            cv2.line(line, px(frog - 0.5 * u), px(tip + 0.5 * u), 1, 9)
            on_bow = line > 0
        if self.bg is None:
            # the first frame's surfaces, but not the bow if it is already
            # there: the show started with the bow at rest on the strings,
            # and the room took it in from then on
            self.bg = np.where(valid & surface & ~on_bow, depth, np.nan).astype(np.float32)
            self.bg_dev = np.full(depth.shape, 0.02, np.float32)
            self.bg_edges = np.zeros(depth.shape, bool)
            self.bg_new = np.where(valid, depth, np.nan).astype(np.float32)
            self.bg_n = valid.astype(np.int32)
            self.bg_gone = np.zeros(depth.shape, np.int32)
            self.n_bg = 0
            return
        bg = self.bg
        # the room took in the bow (it lay still from the start, or was
        # missed for long): wherever along the bow's line the room is at
        # the depth seen now, it is the bow, not room; forget it there, so
        # the whole bow is found again from any part of it
        took = on_bow & np.isfinite(bg) & valid & (np.abs(depth - bg) < 0.05)
        bg[took] = np.nan
        # where the room had no depth, a reading becomes room only once it
        # has held still: taken at once, the bow over a black backdrop was
        # room from its first frame on. A surface after `adopt` frames; a
        # thin thing in front of nothing (a stand's leg, the scroll) only
        # after ~10 s, so a bow at rest is not taken in. And room that stays
        # without depth for `adopt` frames is forgotten (a bow taken in by
        # mistake does not hide that spot for good)
        adopt = 45
        adopt_n = np.where(surface, adopt, 150)
        known = np.isfinite(bg)
        same = valid & (np.abs(depth - self.bg_new) < 0.05)
        self.bg_new = np.where(valid & ~same, depth, self.bg_new)
        self.bg_n = np.where(same, self.bg_n + 1, np.where(valid, 1, 0)).astype(np.int32)
        # held still under the bow does not count: once found missing for a
        # frame, the stretch of bow already "still long enough" became room
        self.bg_n[on_bow] = 0
        new = ~known & (self.bg_n >= adopt_n) & ~on_bow
        bg[new] = self.bg_new[new]
        self.bg_gone = np.where(known & ~valid, self.bg_gone + 1, 0).astype(np.int32)
        bg[self.bg_gone >= adopt] = np.nan
        both = valid & np.isfinite(bg)
        diff = np.where(both, depth - bg, 0)
        upd = both & (np.abs(diff) < 0.05) & ~on_bow
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
            # (the room's own edges only: where it has no depth at all, a
            # black backdrop, the bow must still be seen)
            edge = (g > 0.04 * np.maximum(b, 0.5)) & np.isfinite(bg)
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
        # nothing until the cello is tracked (up to 5 s): at the show's
        # start its scan is not fitted yet, the bow on the strings was not
        # told from the cello, and the room, first taken then, took it in
        self.t_first = t if self.t_first is None else self.t_first
        if self.bg is None and cello is None and t - self.t_first < 5.0:
            self.state = {"ok": False}
            return None
        # beyond the Kinect's range is no reading: a black backdrop came back
        # at 16-18 m, wrapped and flickering by metres, which hid the bow
        # held in front of it (it stood out "too far" and the flicker made
        # the whole backdrop an edge of the room)
        depth = pkt["depth"]
        depth = np.where(depth < self.max_range, depth, np.nan).astype(np.float32)
        dh, dw = depth.shape
        Kd = depth_K(K, size, (dw, dh))
        P, _ = self.candidates(depth, Kd, cello)
        self.points = P
        res = None
        if len(P) >= 25:
            # two fits, the longer that passes: the image line handles a bow
            # whose depth blends with what is behind it (a still bow on a
            # stage 3 m away, half found by the 3D line); the 3D line finds
            # it more often while it swings through the air
            fits = [self._fit_image(P, fx=Kd[0, 0])]
            best = self._ransac(P)
            if best is not None and best[1].sum() >= 20:
                fits.append((*self._segment(P, best[1]), int(best[1].sum())))
            fits = [f for f in fits if f is not None and f[4] >= 20 and
                    self.min_len <= f[2] <= self.max_len and f[3] > 0.45]
            if fits:
                a, b, L, cover, n_in = max(fits, key=lambda f: f[2])
                frog, tip = self._label_ends(a, b, depth, Kd, cello)
                res = (frog, tip, L, n_in, cover)
        self._learn_background(depth, res if self._on_cello(res, cello) else None, Kd)
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
            elif hand is None:
                # no hand on it: not being drawn (a stale median kept the
                # last stroke's speed on a bow put down)
                self.speeds = (self.speeds + [0.0])[-5:]
                self.frog_vel *= 1 - a
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
