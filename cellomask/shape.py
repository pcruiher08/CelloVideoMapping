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
        if missing < self.whole or extra > self.whole:
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
