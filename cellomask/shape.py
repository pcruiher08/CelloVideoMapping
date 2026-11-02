"""The cello's whole outline, also while a hand or the bow covers part of it.

The cello never changes shape, but its segmentation does: a pizzicato hand,
an arm or the bow in front of it takes a bite out of the mask, and the light
(and the image) would shrink around them. So a clean outline is kept from
frames where the cello is whole, and every frame it is fitted to what is
visible: chamfer matching of the visible outline against the kept one,
ignoring the parts of the visible outline that are not near it (those are
the edges of whatever is in front). The light then covers the whole cello,
hand and arm included.

Occlusion only ever removes cello pixels, which is how a whole frame is
told from a covered one: the mask covers almost all of the fitted outline.
"""

import cv2
import numpy as np


def fill_holes(m):
    """Binary mask with its enclosed holes filled."""
    m = m.astype(np.uint8)
    h, w = m.shape
    pad = np.zeros((h + 2, w + 2), np.uint8)
    pad[1:-1, 1:-1] = m
    flood = pad.copy()
    cv2.floodFill(flood, np.zeros((h + 4, w + 4), np.uint8), (0, 0), 1)
    return (m | (1 - flood[1:-1, 1:-1])) > 0


def close_across(mask, up, length, scale=2):
    """Fill gaps up to `length` px wide that run along the cello (direction
    `up`, radians) with cello on both sides: the black fingerboard, which
    the segmentation keeps cutting out of the upper bout as a slot. A
    closing with a line across the cello bridges them; the C-bouts and a
    hand coming in from the side have cello on one side only and stay."""
    m = mask > 0.5
    if not m.any() or length < 3:
        return mask
    ys, xs = np.nonzero(m)
    pad = int(length) + 4
    x0, y0 = max(0, xs.min() - pad), max(0, ys.min() - pad)
    x1, y1 = min(m.shape[1], xs.max() + 1 + pad), min(m.shape[0], ys.max() + 1 + pad)
    sub = m[y0:y1, x0:x1].astype(np.uint8)
    small = cv2.resize(sub, ((x1 - x0) // scale, (y1 - y0) // scale), interpolation=cv2.INTER_NEAREST)
    n = int(length / scale) | 1
    k = np.zeros((n, n), np.uint8)
    c = n // 2
    across = np.array([-np.sin(up), np.cos(up)]) * c
    cv2.line(k, (int(round(c - across[0])), int(round(c - across[1]))),
             (int(round(c + across[0])), int(round(c + across[1]))), 1, 1)
    closed = cv2.morphologyEx(small, cv2.MORPH_CLOSE, k)
    add = cv2.resize(closed & (1 - small), (x1 - x0, y1 - y0), interpolation=cv2.INTER_NEAREST) > 0
    if not add.any():
        return mask
    out = mask.astype(np.float32, copy=True)
    out[y0:y1, x0:x1][add & (sub == 0)] = 1.0
    return out


def similarity(p):
    """2x3 matrix from (tx, ty, angle, log scale): kept outline -> image."""
    tx, ty, a, ls = p
    s = np.exp(ls)
    c, sn = s * np.cos(a), s * np.sin(a)
    return np.array([[c, -sn, tx], [sn, c, ty]])


def bilinear(img, x, y):
    """Samples of img (h, w) or (h, w, c) at float coordinates."""
    h, w = img.shape[:2]
    x = np.clip(x, 0, w - 1.001)
    y = np.clip(y, 0, h - 1.001)
    x0, y0 = x.astype(int), y.astype(int)
    fx, fy = x - x0, y - y0
    if img.ndim == 3:
        fx, fy = fx[:, None], fy[:, None]
    return (img[y0, x0] * (1 - fx) * (1 - fy) + img[y0, x0 + 1] * fx * (1 - fy) +
            img[y0 + 1, x0] * (1 - fx) * fy + img[y0 + 1, x0 + 1] * fx * fy)


class ShapeMemory:
    """Keeps the cello's whole outline and restores it under occlusion.

    __call__(mask) returns (whole, covered): the mask with the covered part
    of the cello filled back in, and the fraction that was covered."""

    def __init__(self, whole=0.04, points=400, min_inliers=0.45, scale=2):
        self.whole = whole              # missing less than this = a whole frame
        self.points = points            # outline points used for the fit
        self.min_inliers = min_inliers  # fraction of them that must fit
        self.scale = scale              # works at 1/scale: ~14 ms a frame at full size
        self.reset()

    def reset(self):
        self.tpl = None                 # kept outline (binary, its own box)
        self.dt = None                  # distance to its contour, same box
        self.p = None                   # pose: kept outline -> image
        self.covered = 0.0
        self.fit_ok = False

    def _keep(self, m):
        """Store `m` (whole) as the outline, at identity pose."""
        ys, xs = np.nonzero(m)
        pad = 20
        x0, y0 = max(0, xs.min() - pad), max(0, ys.min() - pad)
        x1, y1 = min(m.shape[1], xs.max() + 1 + pad), min(m.shape[0], ys.max() + 1 + pad)
        t = m[y0:y1, x0:x1].astype(np.uint8)
        edge = np.ones_like(t)
        cnts, _ = cv2.findContours(t, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_NONE)
        cv2.drawContours(edge, cnts, -1, 0, 1)
        dt = cv2.distanceTransform(edge, cv2.DIST_L2, 3).astype(np.float32)
        gy, gx = np.gradient(dt)
        self.dt = np.dstack([dt, gx, gy])            # distance and its gradient
        self.tpl = t
        self.shape = m.shape
        self.p = np.array([float(x0), float(y0), 0.0, 0.0])   # box corner -> image

    def _fit(self, pts, p, iters=12, gates=(12, 6, 3, 1.5)):
        """Gauss-Newton on the pose so the visible outline points lie on the
        kept outline; points farther than the gate (the edges of a hand in
        front) are left out. Returns (pose, inlier fraction)."""
        phase = max(1, iters // len(gates))
        inl = 0.0
        for k in range(iters):
            gate = gates[min(k // phase, len(gates) - 1)]
            tx, ty, a, ls = p
            c, sn, e = np.cos(a), np.sin(a), np.exp(-ls)
            # image -> kept outline: u = e R(a)^T (x - t)
            Mt = e * np.array([[c, sn], [-sn, c]])
            dM = e * np.array([[-sn, c], [-c, -sn]])         # d Mt / d angle
            d = pts - [tx, ty]
            u = d @ Mt.T
            smp = bilinear(self.dt, u[:, 0], u[:, 1])
            r, g = smp[:, 0], smp[:, 1:]
            use = r < gate
            inl = float((r < 1.5).mean())
            if use.sum() < 30:
                return p, 0.0
            # d r / d (tx, ty, angle, log scale), by the chain rule through u
            J = np.stack([-(g @ Mt[:, 0]), -(g @ Mt[:, 1]),
                          np.einsum("ij,ij->i", g, d @ dM.T), -np.einsum("ij,ij->i", g, u)], 1)[use]
            step = np.linalg.solve(J.T @ J + 1e-6 * np.eye(4), J.T @ r[use])
            p = p - step
            if k >= phase * (len(gates) - 1) and np.abs(step[:2]).max() < 0.02 and np.abs(step[2:]).max() < 1e-4:
                break
        return p, inl

    def __call__(self, mask):
        if mask is None:
            return None, 0.0
        k = self.scale
        m = fill_holes(mask[::k, ::k] > 0.5)
        if m.sum() < 50:
            return mask, 0.0
        if self.tpl is not None and m.shape != self.shape:
            self.reset()                 # the camera turned
        if self.tpl is None:
            self._keep(m)
            self.covered, self.fit_ok = 0.0, True
            return mask, 0.0
        cnts, _ = cv2.findContours(m.astype(np.uint8), cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_NONE)
        pts = np.concatenate([c[:, 0] for c in cnts]).astype(np.float64)
        if len(pts) > self.points:
            pts = pts[np.linspace(0, len(pts) - 1, self.points).astype(int)]
        p, inl = self._fit(pts, self.p.copy())
        self.fit_ok = inl >= self.min_inliers
        if not self.fit_ok:
            # lost (a cut, another cello): start again from what is visible
            self._keep(m)
            self.covered = 0.0
            return mask, 0.0
        h, w = m.shape
        placed = cv2.warpAffine(self.tpl, similarity(p), (w, h), flags=cv2.INTER_NEAREST) > 0
        area = max(1, placed.sum())
        missing = (placed & ~m).sum() / area
        extra = (m & ~placed).sum() / area
        # hysteresis: once covered, whole again only when almost nothing is
        # missing (a hand biting ~3% flipped between covered and whole and
        # flickered that patch of light)
        whole = self.whole / 2 if self.covered > 0 else self.whole
        if missing < whole or extra > self.whole:
            # whole (or bigger than what was kept): this is the new outline
            self._keep(m)
            self.covered = 0.0
            return mask, 0.0
        self.p = p
        self.covered = float(missing)
        # what is visible, with the covered part filled back in (the kept
        # outline placed at full size: the same pose, scaled up)
        H, W = mask.shape
        ys, xs = np.nonzero(placed)
        x0, y0 = max(0, k * xs.min() - 2 * k), max(0, k * ys.min() - 2 * k)
        x1, y1 = min(W, k * xs.max() + 3 * k), min(H, k * ys.max() + 3 * k)
        A = k * similarity(p)
        A[:, 2] -= [x0, y0]                          # into that box only
        full = cv2.warpAffine(self.tpl.astype(np.float32), A, (x1 - x0, y1 - y0),
                              flags=cv2.INTER_LINEAR) > 0.5
        out = mask.astype(np.float32, copy=True)
        np.maximum(out[y0:y1, x0:x1], full, out=out[y0:y1, x0:x1])
        return out, self.covered


class LearnedShape:
    """The cello's outline learned once (alone and still: at Calibrate 3D or
    with the Learn button), then only fitted, every frame, to the visible
    cello edges. The light uses that outline and nothing else, so what the
    segmentation adds or loses while the cello is played (a hand over the
    upper bout, the knees beside the lower bout, the mask cut straight at a
    detection box that jumps with the hands) cannot change its shape.

    The fit is affine (chamfer matching, Gauss-Newton): besides moving and
    turning it stretches, which follows a cello leaning further back when
    played than on its stand (it gets shorter in the image). Saved to
    data/cello_shape.npz; the phone stays put, so pixels stay comparable."""

    def __init__(self, path, scale=2, points=400, min_inliers=0.35):
        self.path = path
        self.scale = scale
        self.points = points
        self.min_inliers = min_inliers
        self.tpl = self.dt = self.size = None
        self.q = None                   # image (1/scale px) -> outline: u = B x + c, as [B | c]
        self.inliers = 0.0
        self.ok = False
        self.load()

    def load(self):
        import os
        if os.path.exists(self.path):
            z = np.load(self.path)
            self._set(z["tpl"].astype(np.uint8), tuple(z["size"]))

    def _set(self, tpl, size):
        edge = np.ones_like(tpl)
        cnts, _ = cv2.findContours(tpl, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_NONE)
        cv2.drawContours(edge, cnts, -1, 0, 1)
        dt = cv2.distanceTransform(edge, cv2.DIST_L2, 3).astype(np.float32)
        gy, gx = np.gradient(dt)
        self.tpl, self.dt, self.size = tpl, np.dstack([dt, gx, gy]), size
        self.q, self.ok = None, False
        m = cv2.moments(tpl, binaryImage=True)
        self.tpl_c = np.array([m["m10"], m["m01"]]) / m["m00"]
        self.tpl_area = m["m00"]

    def learn(self, mask):
        """Learn the outline from a mask of the cello alone (full size)."""
        k = self.scale
        m = fill_holes(mask[::k, ::k] > 0.5)
        if m.sum() < 200:
            return False
        ys, xs = np.nonzero(m)
        pad = 20
        x0, y0 = max(0, xs.min() - pad), max(0, ys.min() - pad)
        x1, y1 = min(m.shape[1], xs.max() + 1 + pad), min(m.shape[0], ys.max() + 1 + pad)
        tpl = m[y0:y1, x0:x1].astype(np.uint8)
        np.savez_compressed(self.path, tpl=tpl, size=np.array(mask.shape))
        self._set(tpl, mask.shape)
        self.q = np.array([[1.0, 0, -x0], [0, 1.0, -y0]])
        return True

    def _start(self, m):
        """A first guess from the visible mask: same centre, same area."""
        mm = cv2.moments(m.astype(np.uint8), binaryImage=True)
        c = np.array([mm["m10"], mm["m01"]]) / mm["m00"]
        s = np.sqrt(self.tpl_area / mm["m00"])
        return np.array([[s, 0, self.tpl_c[0] - s * c[0]], [0, s, self.tpl_c[1] - s * c[1]]])

    def _fit(self, pts, q, iters=14, gates=(12, 6, 3, 1.5)):
        phase = max(1, iters // len(gates))
        X = np.c_[pts, np.ones(len(pts))]
        inl = 0.0
        for k in range(iters):
            gate = gates[min(k // phase, len(gates) - 1)]
            u = X @ q.T
            smp = bilinear(self.dt, u[:, 0], u[:, 1])
            r, gx, gy = smp[:, 0], smp[:, 1], smp[:, 2]
            use = r < gate
            inl = float((r < 1.5).mean())
            if use.sum() < 40:
                return q, 0.0
            # u is linear in [B | c]: d r / d q is the gradient times x
            J = np.c_[gx[:, None] * X, gy[:, None] * X][use]
            step = np.linalg.solve(J.T @ J + 1e-3 * np.eye(6), J.T @ r[use])
            q = q - step.reshape(2, 3)
            if k >= phase * (len(gates) - 1) and np.abs(step).max() < 1e-3:
                break
        return q, inl

    def __call__(self, mask):
        """The learned outline placed on this frame (full size, float), or
        None when there is none or it does not fit (then use the mask)."""
        if self.tpl is None or mask is None:
            self.ok = False
            return None
        h, w = mask.shape
        H, W = self.size
        if (h, w) != (H, W):
            # the same view processed at another resolution: fit at the learned one
            if abs(w / h - W / H) > 0.01:
                self.ok = False
                return None
            out = self(cv2.resize(mask.astype(np.float32), (W, H), interpolation=cv2.INTER_LINEAR))
            return None if out is None else cv2.resize(out, (w, h), interpolation=cv2.INTER_LINEAR)
        k = self.scale
        m = fill_holes(mask[::k, ::k] > 0.5)
        if m.sum() < 100:
            self.ok = False
            return None
        cnts, _ = cv2.findContours(m.astype(np.uint8), cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_NONE)
        pts = np.concatenate([c[:, 0] for c in cnts]).astype(np.float64)
        if len(pts) > self.points:
            pts = pts[np.linspace(0, len(pts) - 1, self.points).astype(int)]
        q, inl = self._fit(pts, self.q if self.ok and self.q is not None else self._start(m))
        det = np.linalg.det(q[:, :2])
        # the outline must still look like the cello: fitting enough of the
        # visible edge, not squashed or blown up
        self.ok = bool(inl >= self.min_inliers and 0.5 < det < 2.0)
        self.inliers = inl
        if not self.ok:
            return None
        self.q = q
        # placed at full size: output pixel x -> outline u = B (x / k) + c
        H, W = mask.shape
        A = np.linalg.inv(np.r_[q, [[0, 0, 1]]])[:2]          # outline -> image (1/k px)
        th, tw = self.tpl.shape
        corners = np.array([[0, 0, 1], [tw, 0, 1], [0, th, 1], [tw, th, 1]], np.float64) @ A.T * k
        x0, y0 = np.maximum(0, np.floor(corners.min(0)).astype(int))
        x1, y1 = np.minimum([W, H], np.ceil(corners.max(0)).astype(int) + 1)
        if x1 <= x0 or y1 <= y0:
            self.ok = False
            return None
        Mi = np.c_[q[:, :2] / k, q[:, :2] @ np.array([x0, y0]) / k + q[:, 2]]
        box = cv2.warpAffine(self.tpl.astype(np.float32), Mi, (x1 - x0, y1 - y0),
                             flags=cv2.INTER_LINEAR | cv2.WARP_INVERSE_MAP)
        out = np.zeros((H, W), np.float32)
        out[y0:y1, x0:x1] = box
        return out
