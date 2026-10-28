"""Notice and cancel the iPhone moving after the 3D calibration.

The 3D calibration places the projector relative to the phone, so a phone
nudged in its mount (plugging a cable in, a knock) sends all the light to
the wrong place. The room's walls, door and floor do not move, though: the
LiDAR depth of that static background, aligned to the depth saved while
calibrating, tells exactly how the phone moved, and the mapping cancels it.

The alignment is projective point-to-plane ICP, the usual way to register
two depth images: each current point is matched to the reference pixel it
projects to, and pairs too far apart (the player, anything moved) are left
out.
"""

import os

import numpy as np

from .procam3d import ROOT

REF_PATH = os.path.join(ROOT, "data", "procam3d_ref.npz")


def depth_K(K, size, dsize):
    """Intrinsics for the depth map from those of the image it is aligned to."""
    (w, h), (dw, dh) = size, dsize
    sx, sy = dw / w, dh / h
    return np.array([[K[0, 0] * sx, 0, (K[0, 2] + 0.5) * sx - 0.5],
                     [0, K[1, 1] * sy, (K[1, 2] + 0.5) * sy - 0.5], [0, 0, 1]])


def cloud(depth, Kd):
    """Per-pixel 3D points (h, w, 3) of a depth map; NaN where unknown."""
    h, w = depth.shape
    u, v = np.meshgrid(np.arange(w), np.arange(h))
    return np.stack([(u - Kd[0, 2]) * depth / Kd[0, 0], (v - Kd[1, 2]) * depth / Kd[1, 1], depth], -1)


def normals(P):
    """Per-pixel normals from neighbouring points (NaN at gaps)."""
    dx = np.zeros_like(P)
    dy = np.zeros_like(P)
    dx[:, 1:-1] = P[:, 2:] - P[:, :-2]
    dy[1:-1] = P[2:] - P[:-2]
    n = np.cross(dx, dy)
    n /= np.linalg.norm(n, axis=-1, keepdims=True) + 1e-12
    n[n[..., 2] > 0] *= -1                       # face the camera
    return n


def rigid(rot, t):
    M = np.eye(4)
    M[:3, :3], M[:3, 3] = rot, t
    return M


def rodrigues(w):
    th = np.linalg.norm(w)
    if th < 1e-12:
        return np.eye(3)
    k = w / th
    Kx = np.array([[0, -k[2], k[1]], [k[2], 0, -k[0]], [-k[1], k[0], 0]])
    return np.eye(3) + np.sin(th) * Kx + (1 - np.cos(th)) * Kx @ Kx


def icp(points, ref_P, ref_N, Kd, M=None, iters=60, dists=(0.2, 0.08, 0.03)):
    """Rigid M (4x4) taking current-camera points into the reference camera.
    Returns (M, inlier fraction, rms metres) or None.

    Point-to-plane: a room is mostly walls, and a wall alone lets the fit
    slide along it, so the gate starts wide (the floor, seen at a grazing
    angle, must stay in to hold the vertical) and narrows to drop the
    player and other moving things. A point-to-point term, tried as well,
    pulled the fit away from the truth through the projective matching."""
    M = np.eye(4) if M is None else M.copy()
    h, w = ref_P.shape[:2]
    res = None
    phase = iters // len(dists)
    for k in range(iters):
        q = points @ M[:3, :3].T + M[:3, 3]
        u = np.round(q[:, 0] / q[:, 2] * Kd[0, 0] + Kd[0, 2]).astype(int)
        v = np.round(q[:, 1] / q[:, 2] * Kd[1, 1] + Kd[1, 2]).astype(int)
        inside = (q[:, 2] > 0.1) & (u >= 0) & (u < w) & (v >= 0) & (v < h)
        r = ref_P[v[inside], u[inside]]
        n = ref_N[v[inside], u[inside]]
        qi = q[inside]
        good = np.isfinite(r).all(1) & np.isfinite(n).all(1)
        d = np.einsum("ij,ij->i", qi - r, n)
        lim = dists[min(k // phase, len(dists) - 1)]
        good &= (np.abs(d) < lim) & (np.linalg.norm(qi - r, axis=1) < 2.5 * lim)
        if good.sum() < 200:
            return None
        qg, ng, dg = qi[good], n[good], d[good]
        A = np.c_[np.cross(qg, ng), ng]
        x = np.linalg.solve(A.T @ A + 1e-9 * np.eye(6), -A.T @ dg)
        M = rigid(rodrigues(x[:3]), x[3:]) @ M
        res = (float(good.sum()) / len(points), float(np.sqrt(np.mean(dg ** 2))))
        if k >= phase * (len(dists) - 1) and np.linalg.norm(x[:3]) < 1e-5 and np.linalg.norm(x[3:]) < 1e-5:
            break
    return M, res[0], res[1]


class PhoneTracker:
    """Keeps M (current camera -> calibration camera) up to date."""

    def __init__(self, path=REF_PATH):
        self.path = path
        self.ref = None
        self.M = np.eye(4)
        self.moved = None                # (cm, degrees) of the last accepted estimate
        self.inliers = None
        self.ok = False
        self.load()

    def load(self):
        self.ref = None
        self.M = np.eye(4)
        self.moved, self.ok = None, False
        if os.path.exists(self.path):
            r = np.load(self.path)
            self.set_ref(r["depth"], r["K"], tuple(r["size"]), str(r["orientation"]))

    def set_ref(self, depth, K, size, orientation):
        dh, dw = depth.shape
        Kd = depth_K(K, size, (dw, dh))
        P = cloud(depth, Kd)
        self.ref = {"P": P, "N": normals(P), "Kd": Kd, "size": tuple(size),
                    "orientation": orientation, "depth": depth, "K": K}
        self.M = np.eye(4)
        self.moved, self.ok = (0.0, 0.0), True

    def save_ref(self, depth, K, size, orientation):
        np.savez_compressed(self.path, depth=depth, K=K, size=np.array(size), orientation=orientation)
        self.set_ref(depth, K, size, orientation)

    def update(self, pkt, exclude=None, max_points=4000, seed=0):
        """Re-estimate from one iPhone packet. `exclude`: camera-pixel mask
        of things that move (the cello). Returns True if M was updated."""
        ref = self.ref
        if ref is None or pkt is None:
            return False
        if tuple(pkt["size"]) != ref["size"] or pkt.get("orientation") != ref["orientation"]:
            self.ok = False
            return False
        depth = pkt["depth"]
        dh, dw = depth.shape
        Kd = depth_K(pkt["K"], pkt["size"], (dw, dh))
        P = cloud(depth, Kd)
        use = np.isfinite(depth) & (depth > 0.2) & (depth < 6)
        if pkt.get("conf") is not None:
            use &= pkt["conf"] >= 2
        if exclude is not None:
            import cv2
            ex = cv2.resize(exclude.astype(np.uint8), (dw, dh), interpolation=cv2.INTER_NEAREST)
            use &= cv2.dilate(ex, np.ones((9, 9), np.uint8)) == 0
        ys, xs = np.nonzero(use)
        if len(xs) < 500:
            return False
        pick = np.random.default_rng(seed).choice(len(xs), min(max_points, len(xs)), replace=False)
        pts = P[ys[pick], xs[pick]]
        out = icp(pts, ref["P"], ref["N"], ref["Kd"], self.M)
        if out is None:
            out = icp(pts, ref["P"], ref["N"], ref["Kd"], np.eye(4))   # lost: from scratch
            if out is None:
                self.ok = False
                return False
        M, inl, rms = out
        self.inliers = inl
        if inl < 0.4 or rms > 0.02:
            self.ok = False
            return False
        self.M, self.ok = M, True
        ang = np.degrees(np.arccos(np.clip((np.trace(M[:3, :3]) - 1) / 2, -1, 1)))
        self.moved = (100 * float(np.linalg.norm(M[:3, 3])), float(ang))
        return True
