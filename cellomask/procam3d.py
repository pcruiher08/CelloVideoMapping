"""Full 3D projector calibration from the iPhone's LiDAR depth.

The Gray-code stripes say which projector pixel lights each camera pixel;
the LiDAR says where that camera pixel is in space. Together they are 3D
points with their projector pixels, which is exactly what a camera
calibration needs: the projector is solved like a camera (intrinsics, lens
distortion, and its pose relative to the iPhone camera). The room has to be
more than one flat surface (cello + wall + floor is ideal), or depth and
focal length cannot be told apart.

With it, any camera pixel whose depth is known maps to the exact projector
pixel at any distance: no flat-plane assumption, no manual nudge.
"""

import json
import os
import time

import cv2
import numpy as np

ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
PROCAM_PATH = os.path.join(ROOT, "data", "procam3d.json")


def backproject(u, v, d, K):
    """Camera pixels with depth (metres) -> 3D points in the camera frame."""
    return np.stack([(u - K[0, 2]) * d / K[0, 0], (v - K[1, 2]) * d / K[1, 1], d], 1)


def stable_depth(packets, min_conf=2, edge=0.03):
    """Median depth over still frames, NaN where unreliable: low LiDAR
    confidence in any frame, or a depth edge (mixed foreground/background
    readings, e.g. the cello's outline against the wall)."""
    d = np.median(np.stack([p["depth"] for p in packets]), 0).astype(np.float32)
    ok = np.isfinite(d) & (d > 0.1)
    if packets[0]["conf"] is not None:
        ok &= np.min(np.stack([p["conf"] for p in packets]), 0) >= min_conf
    lo = cv2.erode(np.where(ok, d, 1e3).astype(np.float32), np.ones((3, 3)))
    hi = cv2.dilate(np.where(ok, d, 0).astype(np.float32), np.ones((3, 3)))
    ok &= (hi - lo) < edge * d
    return np.where(ok, d, np.nan)


def depth_at(depth, size):
    """Depth map resampled to the camera image size (w, h); NaN stays NaN
    (a pixel needs all its depth neighbours valid)."""
    w, h = size
    valid = np.isfinite(depth).astype(np.uint8)
    up = cv2.resize(np.nan_to_num(depth, nan=0.0), (w, h), interpolation=cv2.INTER_LINEAR)
    okv = cv2.resize(cv2.erode(valid, np.ones((2, 2), np.uint8)), (w, h), interpolation=cv2.INTER_NEAREST)
    return np.where(okv > 0, up, np.nan)


def correspondences(px, py, valid, depth, K, max_points=40000, seed=0):
    """(3D points, projector pixels) where the stripes decoded and the
    depth is reliable."""
    h, w = px.shape
    d = depth_at(depth, (w, h))
    use = valid & np.isfinite(d)
    ys, xs = np.nonzero(use)
    if len(xs) > max_points:
        pick = np.random.default_rng(seed).choice(len(xs), max_points, replace=False)
        ys, xs = ys[pick], xs[pick]
    X = backproject(xs.astype(np.float64), ys.astype(np.float64), d[ys, xs].astype(np.float64), K)
    p = np.stack([px[ys, xs], py[ys, xs]], 1).astype(np.float64)
    return X, p


def dlt(X, p):
    """3x4 projection matrix from 3D-2D pairs (normalised DLT)."""
    cX, cp = X.mean(0), p.mean(0)
    sX = np.sqrt(3) / np.mean(np.linalg.norm(X - cX, axis=1))
    sp = np.sqrt(2) / np.mean(np.linalg.norm(p - cp, axis=1))
    T3 = np.diag([sX, sX, sX, 1.0])
    T3[:3, 3] = -sX * cX
    T2 = np.diag([sp, sp, 1.0])
    T2[:2, 2] = -sp * cp
    Xn = (np.c_[X, np.ones(len(X))] @ T3.T)
    pn = (np.c_[p, np.ones(len(p))] @ T2.T)
    A = np.zeros((2 * len(X), 12))
    A[0::2, 0:4] = Xn
    A[0::2, 8:12] = -pn[:, [0]] * Xn
    A[1::2, 4:8] = Xn
    A[1::2, 8:12] = -pn[:, [1]] * Xn
    P = np.linalg.svd(A, full_matrices=False)[2][-1].reshape(3, 4)
    return np.linalg.inv(T2) @ P @ T3


def reproject(X, K, dist, R, T):
    rvec = cv2.Rodrigues(R)[0]
    return cv2.projectPoints(X.reshape(-1, 1, 3), rvec, T.reshape(3, 1), K, dist)[0].reshape(-1, 2)


def _unpack(q):
    f, cx, cy, k1 = q[:4]
    K = np.array([[f, 0, cx], [0, f, cy], [0, 0, 1]], np.float64)
    return K, np.array([k1, 0, 0, 0, 0], np.float64), cv2.Rodrigues(q[4:7])[0], q[7:10]


def refine(X, p, K, dist, R, T, iters=40):
    """Levenberg-Marquardt on focal (square pixels), lens centre, k1 and the
    pose. cv2.calibrateCamera would do this but refuses a lens centre outside
    the image, and a projector's usually is: lens shift puts it at or below
    the bottom edge."""
    q = np.r_[K[0, 0], K[0, 2], K[1, 2], dist[0], cv2.Rodrigues(R)[0].ravel(), T]
    steps = np.r_[0.5, 0.5, 0.5, 1e-4, 1e-5, 1e-5, 1e-5, 1e-5, 1e-5, 1e-5]

    def resid(q):
        return (reproject(X, *_unpack(q)) - p).ravel()

    r = resid(q)
    cost, lam = r @ r, 1e-3
    for _ in range(iters):
        J = np.empty((len(r), len(q)))
        for i, h in enumerate(steps):
            dq = np.zeros_like(q)
            dq[i] = h
            J[:, i] = (resid(q + dq) - resid(q - dq)) / (2 * h)
        A, g = J.T @ J, J.T @ r
        while True:
            delta = np.linalg.solve(A + lam * np.diag(np.diag(A)), -g)
            r2 = resid(q + delta)
            if r2 @ r2 < cost:
                q, r, lam = q + delta, r2, max(lam / 3, 1e-9)
                break
            lam *= 4
            if lam > 1e8:
                return _unpack(q)
        if (cost - r @ r) < 1e-10 * cost:
            break
        cost = r @ r
    return _unpack(q)


def solve_projector(X, p, proj_size, rounds=3):
    """Projector intrinsics, distortion and pose (X_proj = R X_cam + T) from
    3D points in the iPhone camera frame and the projector pixels lighting
    them. DLT gives the starting point, a least-squares fit refines it, and
    each round drops points far off the fit (stripe misreads, depth noise
    at edges). Returns a dict, or None."""
    if len(X) < 500:
        return None
    rng = np.random.default_rng(0)
    # the DLT start, robustly: a few hundred stray points (flying depth at
    # a chair's edge, 1-2 m off) dragged a plain DLT so far that the
    # refinement settled on a projector with its lens centre at the image's
    # edge (17 px rms on data a clean start fits to 3 px)
    keep = np.ones(len(X), bool)
    for _ in range(6):
        idx = np.flatnonzero(keep)
        sub = rng.choice(idx, min(len(idx), 6000), replace=False)
        P = dlt(X[sub], p[sub])
        q = np.c_[X, np.ones(len(X))] @ P.T
        with np.errstate(divide="ignore", invalid="ignore"):
            err = np.linalg.norm(q[:, :2] / q[:, 2:3] - p, axis=1)
        err = np.nan_to_num(err, nan=1e9)
        keep = err < max(3.0, 3 * np.median(err[keep]))
        if keep.sum() < 500:
            return None
    if np.linalg.det(P[:, :3]) < 0:
        P = -P
    K0, Rm, C = cv2.decomposeProjectionMatrix(P)[:3]
    K0 = K0 / K0[2, 2]
    C = (C[:3] / C[3]).ravel()
    R0, T0 = Rm, -Rm @ C
    f = (abs(K0[0, 0]) + abs(K0[1, 1])) / 2
    K = np.array([[f, 0, K0[0, 2]], [0, f, K0[1, 2]], [0, 0, 1]], np.float64)
    dist = np.zeros(5)
    R, T = R0, T0
    for k in range(rounds):
        err = np.linalg.norm(reproject(X, K, dist, R, T) - p, axis=1)
        # the DLT start can be far off: be lenient first, strict later
        keep = err < max(3.0, (10, 5, 3)[min(k, 2)] * np.median(err))
        if keep.sum() < 500:
            return None
        idx = np.flatnonzero(keep)
        if len(idx) > 8000:
            idx = rng.choice(idx, 8000, replace=False)
        K, dist, R, T = refine(X[idx], p[idx], K, dist, R, T)
    err = np.linalg.norm(reproject(X, K, dist, R, T) - p, axis=1)
    keep = err < max(3.0, 3 * np.median(err))
    return {"K": K, "dist": dist.ravel(), "R": R, "T": T, "rms": float(np.sqrt(np.mean(err[keep] ** 2))),
            "median": float(np.median(err)), "inliers": float(keep.mean()), "n": int(len(X))}


def implausible3d(sol, proj_size):
    """Why a solved projector cannot be real, or None. Guards against a fit
    on weak stripes or a too-flat scene."""
    w, h = proj_size
    K = sol["K"]
    if sol["inliers"] < 0.6:
        return f"only {100 * sol['inliers']:.0f}% of the points agree with the fit"
    if not (0.4 * w < K[0, 0] < 6 * w):
        return f"focal length {K[0, 0]:.0f} px is not a projector's"
    if not (-0.5 * w < K[0, 2] < 1.5 * w and -1.0 * h < K[1, 2] < 2.0 * h):
        return "the lens centre is far outside the image"
    if sol["T"][2] < -0.5 or np.linalg.norm(sol["T"]) > 10:
        return "the projector position is not plausible"
    return None


class Procam3D:
    """The solved projector, relative to the iPhone camera, saved to
    data/procam3d.json."""

    def __init__(self, K, dist, R, T, proj_size, cam_K=None, cam_size=None,
                 rms=None, median=None, inliers=None, n=0, when=None, **_):
        self.K = np.asarray(K, np.float64)
        self.dist = np.asarray(dist, np.float64).ravel()
        self.R = np.asarray(R, np.float64)
        self.T = np.asarray(T, np.float64).ravel()
        self.proj_size = tuple(proj_size)
        self.cam_K = None if cam_K is None else np.asarray(cam_K, np.float64)
        self.cam_size = None if cam_size is None else tuple(cam_size)
        self.rms, self.median, self.inliers, self.n = rms, median, inliers, n
        self.when = when or time.strftime("%Y-%m-%d %H:%M")

    def project(self, X):
        """3D points in the camera frame -> projector pixels."""
        return reproject(np.asarray(X, np.float64), self.K, self.dist, self.R, self.T)

    def moved(self, M):
        """The same projector seen from a camera that moved: M (4x4) takes
        points from the current camera into the camera at calibration."""
        R = self.R @ M[:3, :3]
        T = self.R @ M[:3, 3] + self.T
        out = Procam3D(self.K, self.dist, R, T, self.proj_size, self.cam_K, self.cam_size,
                       self.rms, self.median, self.inliers, self.n, self.when)
        return out

    @property
    def position(self):
        """Projector lens centre in the camera frame (metres)."""
        return -self.R.T @ self.T

    def summary(self):
        x, y, z = self.position
        return (f"projector focal {self.K[0, 0]:.0f} px, lens centre ({self.K[0, 2]:.0f}, {self.K[1, 2]:.0f}), "
                f"{100 * np.hypot(x, y):.0f} cm beside / {100 * z:+.0f} cm in depth from the camera; "
                f"reprojection rms {self.rms:.2f} px over {self.n} points ({100 * self.inliers:.0f}% kept)")

    def to_dict(self):
        return {"K": self.K.tolist(), "dist": self.dist.tolist(), "R": self.R.tolist(),
                "T": self.T.tolist(), "proj_size": list(self.proj_size),
                "cam_K": None if self.cam_K is None else self.cam_K.tolist(),
                "cam_size": None if self.cam_size is None else list(self.cam_size),
                "rms": self.rms, "median": self.median, "inliers": self.inliers,
                "n": self.n, "when": self.when}

    def save(self, path=PROCAM_PATH):
        os.makedirs(os.path.dirname(path), exist_ok=True)
        with open(path, "w") as f:
            json.dump(self.to_dict(), f, indent=1)

    @classmethod
    def load(cls, path=PROCAM_PATH):
        if not os.path.exists(path):
            return None
        with open(path) as f:
            return cls(**json.load(f))
