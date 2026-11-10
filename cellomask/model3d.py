"""The cello's exact shape from depth: a 3D scan of this cello, fitted every
frame, and a depth flood fill when there is no scan (or it lost the cello).

Flood fill (depth_refine): the segmentation says which pixels are cello,
roughly; the depth says exactly where its surface ends. Starting from the
mask, the cello's surface is grown over the depth while it stays smooth and
near the cello's plane, and stops at the jump to the wall behind; what the
mask spilled onto that wall is dropped. The edge then comes from the depth,
and gaps in the mask (the fingerboard, the bridge) fill in.

Scan (CelloModel): with the cello alone and still (Calibrate 3D, or Learn),
its surface points are averaged over a couple of seconds and its outline is
put on that surface in 3D, in the camera's frame. Every frame the scan is
moved rigidly (6 degrees of freedom) onto what the camera sees now:

- its surface points onto the live depth (point-to-plane, as relocate.py
  aligns the room). This fixes distance, lean and turn, but the top is
  nearly flat, so on its own it could slide along itself;
- its outline onto the edge of the visible cello in the image (2D chamfer),
  which pins that sliding and the rotation in the image.

Both in metres (image residuals scaled by distance / focal length), solved
together by Gauss-Newton from the last pose. Hands and the bow fail the
distance gates and are left out, so the light keeps the cello's whole shape
under them. The light uses the scan's outline at the fitted pose, not this
frame's mask: the shape never jitters, only its position follows the cello.
"""

import os
import time

import cv2
import numpy as np

from .cello3d import CelloPlane
from .procam3d import ROOT, stable_depth
from .relocate import cloud, depth_K, normals, rigid, rodrigues
from .shape import fill_holes

MODEL_PATH = os.path.join(ROOT, "data", "cello_model.npz")


def _to_depth(mask, dsize):
    """Frame-size mask -> boolean at depth resolution (more than half covered)."""
    return cv2.resize((mask > 0.5).astype(np.uint8) * 255, dsize, interpolation=cv2.INTER_AREA) > 127


class _Box:
    """A box around the cello in both frame and depth pixels: the work is
    done on the cello's neighbourhood, not the whole image (5-10x faster)."""

    def __init__(self, mask, fsize, dsize, pad):
        (w, h), (dw, dh) = fsize, dsize
        x, y, bw, bh = cv2.boundingRect((mask > 0.5).astype(np.uint8))
        self.empty = bw == 0 or bh == 0
        sx, sy = dw / w, dh / h
        dx0, dy0 = max(0, int(x * sx) - pad), max(0, int(y * sy) - pad)
        dx1, dy1 = min(dw, int(np.ceil((x + bw) * sx)) + pad), min(dh, int(np.ceil((y + bh) * sy)) + pad)
        self.d = (dx0, dy0, dx1, dy1)
        self.f = (int(round(dx0 / sx)), int(round(dy0 / sy)), min(w, int(round(dx1 / sx))), min(h, int(round(dy1 / sy))))

    def frame(self, a):
        x0, y0, x1, y1 = self.f
        return a[y0:y1, x0:x1]

    def depth(self, a):
        x0, y0, x1, y1 = self.d
        return None if a is None else a[y0:y1, x0:x1]

    def K(self, Kd):
        """Depth intrinsics for the box."""
        K = Kd.copy()
        K[0, 2] -= self.d[0]
        K[1, 2] -= self.d[1]
        return K


def _main_depth(depth, keep, band=0.25):
    """`keep` narrowed to the depths within `band` (m) of its median: the
    cello is most of the mask, and wall seen through its edge would pull a
    least-squares plane far off before the robust fit could drop it."""
    zc = float(np.median(depth[keep]))
    return keep & (np.abs(depth - zc) < band)


def _disc(r):
    return cv2.getStructuringElement(cv2.MORPH_ELLIPSE, (2 * r + 1,) * 2)


def depth_refine(seen, pkt, K, behind=0.10, near=0.05, ahead=0.15, grow_m=0.08, min_seed=150):
    """The visible cello with its edge from the depth (see the module doc).
    `seen`: frame-size mask; K: intrinsics at frame size. Returns the
    refined frame-size mask (float32), or `seen` when the depth cannot help.

    behind: mask pixels this far behind the cello's plane are the wall (m).
    near / ahead: the surface band grown over, behind / in front of the
    plane (the arched top and the fingerboard stand up to ~12 cm proud).
    grow_m: the most the cello can grow past the mask."""
    if seen is None or pkt is None:
        return seen
    depth, conf = pkt["depth"], pkt.get("conf")
    h, w = seen.shape
    Kd = depth_K(K, (w, h), depth.shape[::-1])
    box = _Box(seen, (w, h), depth.shape[::-1], int(grow_m * Kd[0, 0] / 0.8) + 3)
    if box.empty:
        return seen
    depth, conf, Kd, sub = box.depth(depth), box.depth(conf), box.K(Kd), box.frame(seen)
    dh, dw = depth.shape
    fh, fw = sub.shape
    valid = np.isfinite(depth) & (depth > 0.1)
    if conf is not None:
        valid &= conf >= 1
    sd = _to_depth(sub, (dw, dh))
    seed = cv2.erode(sd.astype(np.uint8), np.ones((5, 5), np.uint8)).astype(bool) & valid
    if seed.sum() < min_seed:
        return seen
    seed = _main_depth(depth, seed)
    P = cloud(np.where(valid, depth, np.nan), Kd)
    Q = P[seed]
    fit = CelloPlane.fit(Q[::max(1, len(Q) // 1500)].astype(np.float64))   # plenty for a plane
    if fit is None:
        return seen
    C, n = fit[:2]
    dist = np.einsum("ijk,k->ij", np.nan_to_num(P) - C, n)      # > 0: towards the camera
    z = np.where(valid, depth, 0).astype(np.float32)
    k3 = np.ones((3, 3), np.uint8)
    lo = cv2.erode(np.where(valid, z, 1e3).astype(np.float32), k3)
    hi = cv2.dilate(z, k3)
    smooth = (hi - lo) < np.maximum(0.02, 0.015 * z)            # no depth jump (an edge)
    cand = valid & smooth & (dist > -near) & (dist < ahead)
    # growing past the mask: only surface facing the camera like the top
    # (not the floor at the endpin, which also meets the plane)
    N = normals(P)
    facing = np.abs(np.nan_to_num(N) @ n) > 0.6
    zc = float(np.median(depth[seed]))
    r = max(1, int(round(grow_m * Kd[0, 0] / zc)))
    reach = cv2.dilate(sd.astype(np.uint8), _disc(r)) > 0
    cand &= reach & (sd | facing)
    _, lab = cv2.connectedComponents(cand.astype(np.uint8), connectivity=4)
    hit = np.unique(lab[seed & cand])
    grown = np.isin(lab, hit[hit > 0])
    off = valid & (dist < -behind) & ~grown                     # the wall through the mask's edge

    def up(b):
        return cv2.resize(b.astype(np.uint8) * 255, (fw, fh), interpolation=cv2.INTER_LINEAR) > 127

    out = np.zeros((h, w), np.float32)
    x0, y0, x1, y1 = box.f
    out[y0:y1, x0:x1] = fill_holes(((sub > 0.5) & ~up(off)) | up(grown))
    return out


class CelloModel:
    """The learned scan and its pose in the current frame (module doc).
    M: 4x4, scan (camera frame at learning) -> camera now."""

    def __init__(self, path=MODEL_PATH, points=1500):
        self.path, self.points = path, points
        self.S = self.O = None           # surface points, outline (metres, learning camera)
        self.size = None
        self.reset()
        self.load()

    def reset(self):
        self.M = np.eye(4)
        self.Ms = None                   # M smoothed (what is drawn), see _smooth
        self.lost_R = None               # rotation when last tracked: where to start when lost
        self.t_ok = None                 # when the fit last succeeded
        self.t_s = None
        self.ok = False
        self.stats = {}

    def _smooth(self, M, t, min_cutoff=1.5, beta=30.0, lever=0.3):
        """One Euro smoothing of the pose: the fit's own noise (~1-2 mm,
        a fraction of a degree) moved the drawn outline every frame, a
        quiver on a still cello. Cutoff rises with speed (m/s; rotation
        counted at `lever` m from the centre), so a moving cello is not
        held back."""
        if self.Ms is None or self.t_s is None or t - self.t_s > 0.5:
            self.Ms, self.t_s = M.copy(), t
            return self.Ms
        dt = max(t - self.t_s, 1e-3)
        D = M @ np.linalg.inv(self.Ms)
        w = cv2.Rodrigues(D[:3, :3])[0].ravel()
        tr = D[:3, 3]
        speed = (np.linalg.norm(tr) + lever * np.linalg.norm(w)) / dt
        tau = 1.0 / (2 * np.pi * (min_cutoff + beta * speed))
        a = 1.0 / (1.0 + tau / dt)
        self.Ms = rigid(rodrigues(a * w), a * tr) @ self.Ms
        self.t_s = t
        return self.Ms

    def load(self):
        if os.path.exists(self.path):
            try:
                d = np.load(self.path)
                self._set(d["S"], d["O"], d["C"], d["n"], tuple(int(v) for v in d["size"]))
            except Exception as e:
                print(f"cello scan not loaded: {e!r}")

    def _set(self, S, O, C, n, size):
        self.S, self.O = np.asarray(S, np.float64), np.asarray(O, np.float64)
        self.C0, self.n0 = np.asarray(C, np.float64), np.asarray(n, np.float64)
        self.size = size
        self.faces = {}                  # (inset mm, whole) -> outline to light (3D, scan frame)
        try:
            self._clean_shape()
        except Exception as e:           # keep the traced outline
            print(f"cello scan: outline not cleaned ({e!r})")
            self.shape2d = None
        self.reset()

    # --- the clean shape -------------------------------------------------------

    RES = 0.002                          # m per pixel of the flat shape

    def _clean_shape(self, smooth_mm=6.0):
        """The traced outline made into the cello's clean shape, once: laid
        flat in its own plane, made left-right symmetric (averaged with its
        mirror image about the best centre line; the segmentation's outline
        had bumps the instrument does not) and smoothed. The light is then
        this fixed shape moved into place every frame: no frame-to-frame
        re-cutting, no ragged edge. self.O becomes the clean outline."""
        n = self.n0 / np.linalg.norm(self.n0)
        Cr = self.O.mean(0)
        Q = self.O - Cr
        Q -= np.outer(Q @ n, n)                      # in the plane
        ev = np.linalg.eigh(Q.T @ Q)[1]
        v = ev[:, -1]                                # along the cello
        pv = Q @ v
        if pv.max() < -pv.min():                     # +v towards the scroll (the far, narrow end)
            v = -v
        u = np.cross(v, n)
        u /= np.linalg.norm(u)
        q = np.c_[Q @ u, Q @ v]
        r = self.RES
        pad = 0.05
        lo = q.min(0) - pad
        size = np.ceil((q.max(0) + pad - lo) / r).astype(int)
        m = np.zeros((size[1], size[0]), np.uint8)
        cv2.fillPoly(m, [np.round((q - lo) / r * 4).astype(np.int32)], 1, lineType=cv2.LINE_8, shift=2)

        # the mirror line: the column (and slight tilt) the shape is most symmetric about
        h, w = m.shape
        best = None
        for ang in np.radians(np.arange(-4, 4.5, 1.0)):
            R = cv2.getRotationMatrix2D((w / 2, h / 2), np.degrees(ang), 1.0)
            mr = cv2.warpAffine(m, R, (w, h), flags=cv2.INTER_NEAREST)
            xs = np.nonzero(mr.any(0))[0]
            for cx in np.arange(xs.mean() - 15, xs.mean() + 15.5, 1.0):
                f = cv2.warpAffine(mr, np.float32([[-1, 0, 2 * cx], [0, 1, 0]]), (w, h), flags=cv2.INTER_NEAREST)
                sc = (f & mr).sum() / max(1, (f | mr).sum())
                if best is None or sc > best[0]:
                    best = (sc, ang, cx)
        sym, ang, cx = best
        R = cv2.getRotationMatrix2D((w / 2, h / 2), np.degrees(ang), 1.0)
        Rinv = cv2.invertAffineTransform(R)
        mr = cv2.warpAffine(m.astype(np.float32), R, (w, h))
        mf = cv2.warpAffine(mr, np.float32([[-1, 0, 2 * cx], [0, 1, 0]]), (w, h))
        k = int(2 * round(3 * smooth_mm / 1000 / r) + 1)
        clean = cv2.GaussianBlur((mr + mf) / 2, (k, k), smooth_mm / 1000 / r) > 0.5
        clean = cv2.warpAffine(clean.astype(np.uint8), Rinv, (w, h), flags=cv2.INTER_NEAREST)
        # the body alone (no neck or scroll): what an opening with a disc of
        # 14 cm leaves, plus the parts it removed that are off the centre line
        rr = int(round(0.07 / r))
        opened = cv2.morphologyEx(clean, cv2.MORPH_OPEN, cv2.getStructuringElement(cv2.MORPH_ELLIPSE, (2 * rr + 1,) * 2))
        rest = clean & (1 - opened)
        nl, lab, stats, cents = cv2.connectedComponentsWithStats(rest, connectivity=8)
        body = clean.copy()
        axis_x = (Rinv @ np.array([cx, h / 2, 1.0]))[0]   # the centre line, in the flat shape
        for i in range(1, nl):
            on_axis = abs(cents[i][0] - axis_x) < 0.06 / r
            high = cents[i][1] * r + lo[1] > 0.0         # towards the scroll (+v)
            if stats[i, cv2.CC_STAT_AREA] * r * r > 0.003 and high and on_axis:
                cut = cv2.dilate((lab == i).astype(np.uint8), np.ones((3, 3), np.uint8)) & (1 - opened)
                body &= 1 - cut
        self.shape2d = {"clean": clean, "body": body, "lo": lo, "Cr": Cr, "u": u, "v": v, "n": n,
                        "symmetry": float(sym)}
        self.O = self._outline3d(clean)

    def _outline3d(self, m):
        """The largest outline of a flat-shape mask, as 3D points on the rim plane."""
        sh = self.shape2d
        cnts, _ = cv2.findContours(m.astype(np.uint8), cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_NONE)
        c = max(cnts, key=cv2.contourArea)[:, 0, :].astype(np.float64)
        # smoothed along its length: the grid's stair-steps (2 mm) showed
        # as a jagged edge in the light
        k = np.exp(-0.5 * (np.arange(-9, 10) / 3.0) ** 2)
        k /= k.sum()
        c = np.stack([np.convolve(np.r_[c[-9:, i], c[:, i], c[:9, i]], k, "valid") for i in range(2)], 1)
        c = c[::max(1, len(c) // 600)]
        lo, Cr, u, v = sh["lo"], sh["Cr"], sh["u"], sh["v"]
        xy = (c + 0.5) * self.RES + lo
        return Cr + np.outer(xy[:, 0], u) + np.outer(xy[:, 1], v)

    def face(self, inset_mm, whole=False):
        """The outline to light (3D, scan frame): the body without neck and
        scroll (or the whole cello), pulled in by `inset_mm`. Built once per
        setting."""
        key = (round(float(inset_mm), 1), bool(whole))
        if key not in self.faces:
            sh = self.shape2d
            if sh is None:
                return self.O
            m = sh["clean"] if whole else sh["body"]
            k = int(round(inset_mm / 1000 / self.RES))
            if k > 0:
                m = cv2.erode(m, cv2.getStructuringElement(cv2.MORPH_ELLIPSE, (2 * k + 1,) * 2))
            self.faces[key] = self._outline3d(m)
        return self.faces[key]

    def held(self, hold=0.5):
        """Lost less than `hold` s ago: the last pose still stands in (a
        dropped fit or two must not flash the raw segmentation's edge)."""
        return (not self.ok and self.t_ok is not None and self.Ms is not None
                and time.time() - self.t_ok < hold)

    def render_face(self, K, size, inset_mm, whole=False, hold=False):
        """The light's shape this frame: the clean (body or whole) outline at
        the smoothed pose, with anti-aliased edges (float 0..1, frame size).
        hold: also while held() (at the last pose)."""
        if not (self.ok or (hold and self.held())):
            return None
        M = self.M if self.Ms is None else self.Ms
        o = self.face(inset_mm, whole) @ M[:3, :3].T + M[:3, 3]
        if (o[:, 2] < 0.1).any():
            return None
        w, h = size
        px = np.c_[o[:, 0] / o[:, 2] * K[0, 0] + K[0, 2], o[:, 1] / o[:, 2] * K[1, 1] + K[1, 2]]
        out = np.zeros((h, w), np.uint8)
        cv2.fillPoly(out, [np.round(px * 16).astype(np.int32)], 255, lineType=cv2.LINE_AA, shift=4)
        return out.astype(np.float32) / 255.0

    @property
    def learned(self):
        return self.S is not None

    # --- learning ------------------------------------------------------------

    def learn(self, packets, mask, K, size, save=True):
        """Scan from still depth `packets` and the cello's frame-size `mask`
        (K at frame size). Returns a message, or None if it failed."""
        w, h = size
        if not packets or mask is None or mask.shape != (h, w):
            return None
        d = stable_depth(packets)                     # NaN where unreliable or at edges
        dh, dw = d.shape
        Kd = depth_K(K, (w, h), (dw, dh))
        P = cloud(d, Kd)
        m = fill_holes(mask > 0.5)
        md = cv2.erode(_to_depth(m, (dw, dh)).astype(np.uint8), np.ones((3, 3), np.uint8)) > 0
        ok = md & np.isfinite(d)
        if ok.sum() < 300:
            return None
        ok = _main_depth(d, ok)
        fit = CelloPlane.fit(P[ok].astype(np.float64))
        if fit is None:
            return None
        C, n = fit[:2]
        dist = np.einsum("ijk,k->ij", np.nan_to_num(P) - C, n)
        ok &= (dist > -0.06) & (dist < 0.15)          # bits of wall at the edge
        pts = P[ok]
        if len(pts) > self.points:
            pts = pts[np.random.default_rng(0).choice(len(pts), self.points, replace=False)]
        # the outline, on the surface: the plane moved to the rim's height
        # (the arched top's middle stands above its edge)
        cnts, _ = cv2.findContours(m.astype(np.uint8), cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_NONE)
        c = max(cnts, key=cv2.contourArea)[:, 0, :].astype(np.float64)
        c = c[::max(1, len(c) // 400)]
        inner = cv2.erode(md.astype(np.uint8), np.ones((5, 5), np.uint8)) > 0
        ring = md & ~inner & np.isfinite(d) & (np.abs(dist) < 0.05)
        rim = float(np.median(dist[ring])) if ring.sum() > 30 else 0.0
        rays = np.c_[(c[:, 0] - K[0, 2]) / K[0, 0], (c[:, 1] - K[1, 2]) / K[1, 1], np.ones(len(c))]
        Cr = C + rim * n
        O = rays * ((n @ Cr) / (rays @ n))[:, None]
        if save:
            os.makedirs(os.path.dirname(self.path), exist_ok=True)
            np.savez_compressed(self.path, S=pts, O=O, C=C, n=n, size=np.array(size), K=K)
        self._set(pts, O, C, n, (w, h))
        return f"cello scanned in 3D ({len(pts)} surface points, {len(O)} on the outline)"

    # --- tracking ------------------------------------------------------------

    def render(self, M, K, size):
        """The scan's outline at pose M, filled: the whole cello (frame size)."""
        w, h = size
        o = self.O @ M[:3, :3].T + M[:3, 3]
        if (o[:, 2] < 0.1).any():
            return None
        px = np.c_[o[:, 0] / o[:, 2] * K[0, 0] + K[0, 2], o[:, 1] / o[:, 2] * K[1, 1] + K[1, 2]]
        out = np.zeros((h, w), np.uint8)
        cv2.fillPoly(out, [np.round(px * 4).astype(np.int32)], 1, lineType=cv2.LINE_8, shift=2)
        return out

    def dimensions(self):
        """(length, width) of the scanned cello in metres."""
        Q = self.O - self.O.mean(0)
        ax = np.linalg.eigh(Q.T @ Q)[1][:, ::-1]
        return tuple(float(np.ptp(Q @ ax[:, i])) for i in range(2))

    def plane(self):
        """(C, n) of the scan's plane at the current (smoothed) pose."""
        M = self.M if self.Ms is None else self.Ms
        R, t = M[:3, :3], M[:3, 3]
        return R @ self.C0 + t, R @ self.n0

    def track(self, visible, pkt, K):
        """Fit the scan to this frame; the whole cello's mask (float32, frame
        size) or None when it does not fit (the caller falls back)."""
        if self.S is None or visible is None or pkt is None:
            self.ok = False
            return None
        h, w = visible.shape
        if abs(w / h - self.size[0] / self.size[1]) > 0.01:   # another orientation; a scaled view is fine
            self.ok = False
            return None
        depth, conf = pkt["depth"], pkt.get("conf")
        Kd = depth_K(K, (w, h), depth.shape[::-1])
        vis = visible > 0.5
        # the visible cello's box, with room for it to have moved since
        box = _Box(vis, (w, h), depth.shape[::-1], 8)
        if box.empty:
            self.ok = False
            return None
        depth, conf, Kd, sub = box.depth(depth), box.depth(conf), box.K(Kd), box.frame(vis)
        dh, dw = depth.shape
        valid = np.isfinite(depth) & (depth > 0.1)
        if conf is not None:
            valid &= conf >= 1
        vd = _to_depth(sub, (dw, dh))
        # live surface: the visible cello and a little around it (not the
        # player's knees and body further out at the same distance)
        region = (cv2.dilate(vd.astype(np.uint8), np.ones((5, 5), np.uint8)) > 0) & valid
        if region.sum() < 200:
            self.ok = False
            return None
        P = cloud(np.where(region, depth, np.nan), Kd)
        N = normals(P)
        # the visible outline, at half resolution, with each pixel's nearest
        # edge pixel; `half` maps frame pixels to it and back
        fh, fw = sub.shape
        ws, hs = max(1, fw // 2), max(1, fh // 2)
        half = (box.f[0], box.f[1], fw / ws, fh / hs)
        small = cv2.resize(sub.astype(np.uint8), (ws, hs), interpolation=cv2.INTER_NEAREST)
        edge = small & (1 - cv2.erode(small, np.ones((3, 3), np.uint8)))
        ey, ex = np.nonzero(edge)
        if len(ex) < 50:
            self.ok = False
            return None
        _, lab = cv2.distanceTransformWithLabels(1 - edge, cv2.DIST_L2, 5, labelType=cv2.DIST_LABEL_PIXEL)
        near = np.zeros((lab.max() + 1, 2))
        near[lab[ey, ex]] = np.c_[(ex + 0.5) * half[2] - 0.5 + half[0], (ey + 0.5) * half[3] - 0.5 + half[1]]

        if self.ok:
            starts = [self.M]
            iters, g3s, g2s = 6, (0.02, 0.008), (12.0, 5.0)    # from last frame's pose: close already
        else:
            # lost: the scan moved onto the visible cello, turned as when it
            # was last tracked (the player holds it at their own angle, not
            # the stand's it was scanned at), else as when it was scanned
            cl = P[np.isfinite(P).all(-1) & vd].mean(0) if (vd & region).sum() > 50 else None
            if cl is None:
                return None
            starts = []
            for R in ([self.lost_R] if self.lost_R is not None else []) + [np.eye(3)]:
                starts.append(rigid(R, cl - self.S.mean(0) @ R.T))
            iters, g3s, g2s = 30, (0.15, 0.05, 0.015, 0.008), (80.0, 30.0, 12.0, 5.0)
        for M in starts:
            M, st = self._fit(M, P, N, Kd, near, lab, half, K, iters, g3s, g2s)
            if st is not None and st["in3d"] > 0.3 and st["in2d"] > 0.3 and st["rms_mm"] < 12:
                break
        out = None
        if st is not None and st["in3d"] > 0.3 and st["in2d"] > 0.3 and st["rms_mm"] < 12:
            out = self.render(M, K, (w, h))
            # occlusion only removes cello: what is visible must be inside
            if out is not None:
                st["inside"] = float((out[vis] > 0).mean()) if vis.any() else 0.0
                if st["inside"] < 0.85:
                    out = None
        self.stats = st or {}
        if out is None:
            self.ok = False
            return None
        if not self.ok:
            self.Ms = None                   # found again: do not glide over from where it was lost
        self.M, self.ok = M, True
        self.t_ok = time.time()
        self.lost_R = M[:3, :3]
        Ms = self._smooth(M, time.time())
        if Ms is not M:
            out = self.render(Ms, K, (w, h))
        return out.astype(np.float32)

    def _fit(self, M, P, N, Kd, near, lab, half, K, iters, g3s, g2s):
        dh, dw = P.shape[:2]
        hs, ws = lab.shape
        fx, fy, cx, cy = K[0, 0], K[1, 1], K[0, 2], K[1, 2]
        phase = max(1, iters // len(g3s))
        st = None
        for k in range(iters):
            ph = min(k // phase, len(g3s) - 1)
            g3, g2 = g3s[ph], g2s[ph]
            R, t = M[:3, :3], M[:3, 3]
            # surface: point-to-plane against the live depth it projects onto
            q = self.S @ R.T + t
            u = np.round(q[:, 0] / q[:, 2] * Kd[0, 0] + Kd[0, 2]).astype(int)
            v = np.round(q[:, 1] / q[:, 2] * Kd[1, 1] + Kd[1, 2]).astype(int)
            ins = (q[:, 2] > 0.1) & (u >= 0) & (u < dw) & (v >= 0) & (v < dh)
            qi = q[ins]
            r, nn = P[v[ins], u[ins]], N[v[ins], u[ins]]
            good = np.isfinite(r).all(1) & np.isfinite(nn).all(1)
            d = np.einsum("ij,ij->i", qi - np.nan_to_num(r), np.nan_to_num(nn))
            good &= (np.abs(d) < g3) & (np.linalg.norm(qi - np.nan_to_num(r), axis=1) < 2.5 * g3)
            qg, ng = qi[good], nn[good]
            A3 = np.c_[np.cross(qg, ng), ng]
            b3 = d[good]
            # outline: to the nearest visible edge in the image, in metres
            o = self.O @ R.T + t
            X, Y, Z = o[:, 0], o[:, 1], o[:, 2]
            px, py = X / Z * fx + cx, Y / Z * fy + cy
            xh = (px - half[0] + 0.5) / half[2] - 0.5
            yh = (py - half[1] + 0.5) / half[3] - 0.5
            inb = (xh > -0.5) & (xh < ws - 0.5) & (yh > -0.5) & (yh < hs - 0.5)
            xi = np.clip(xh.round().astype(int), 0, ws - 1)
            yi = np.clip(yh.round().astype(int), 0, hs - 1)
            e = near[lab[yi, xi]]
            rx, ry = px - e[:, 0], py - e[:, 1]
            good2 = (Z > 0.1) & (np.hypot(rx, ry) < g2) & inb
            X, Y, Z, rx, ry = X[good2], Y[good2], Z[good2], rx[good2], ry[good2]
            s = Z / fx                                   # metres per pixel there
            iz, xz, yz = 1 / Z, X / Z, Y / Z
            Jx = fx * np.c_[-xz * yz, 1 + xz ** 2, -yz, iz, np.zeros_like(Z), -xz * iz]
            Jy = fy * np.c_[-1 - yz ** 2, xz * yz, xz, np.zeros_like(Z), iz, -yz * iz]
            A = np.r_[A3, Jx * s[:, None], Jy * s[:, None]]
            b = np.r_[b3, rx * s, ry * s]
            st = {"in3d": float(good.sum()) / len(self.S), "in2d": float(good2.sum()) / len(self.O),
                  "rms_mm": 1000 * float(np.sqrt(np.mean(b3 ** 2))) if len(b3) else 99.0,
                  "edge_px": float(np.sqrt(np.mean(rx ** 2 + ry ** 2))) if len(rx) else 99.0}
            if len(b3) < 100 or len(rx) < 30:
                return M, None
            x = np.linalg.solve(A.T @ A + 1e-9 * np.eye(6), -A.T @ b)
            M = rigid(rodrigues(x[:3]), x[3:]) @ M
            if ph == len(g3s) - 1 and np.linalg.norm(x[:3]) < 1e-4 and np.linalg.norm(x[3:]) < 1e-4:
                break
        return M, st
