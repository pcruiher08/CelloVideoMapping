"""Camera -> projector calibration and the projector-space output.

The segmentation works in camera pixels; projection mapping needs the light
to land on the physical cello, so every frame the content is drawn in camera
space (graphics inside the cello mask, black elsewhere) and warped into
projector space with a homography H: camera -> projector.

H is found by projecting a grid of ArUco markers onto a flat board held where
the cello will be: the camera finds each marker's corners, whose projector
coordinates are known, and cv2.findHomography fits the mapping. A flat map is
exact only on that plane; the cello is curved and sits slightly in front of
or behind it, so a small manual nudge (offset, scale) is stored with it.
"""

import json
import os

import cv2
import numpy as np

ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
CALIB_PATH = os.path.join(ROOT, "data", "calibration.json")

ARUCO = cv2.aruco.DICT_4X4_50


def marker_pattern(size, cols=6, rows=4):
    """White frame with a grid of ArUco markers, plus each marker's corner
    positions in projector pixels {id: 4x2}. White around every marker is
    the quiet zone the detector needs."""
    w, h = size
    img = np.full((h, w, 3), 255, np.uint8)
    dictionary = cv2.aruco.getPredefinedDictionary(ARUCO)
    cell = min(w / cols, h / rows)
    side = int(cell * 0.62)
    ox = (w - cols * cell) / 2
    oy = (h - rows * cell) / 2
    corners = {}
    for r in range(rows):
        for c in range(cols):
            mid = r * cols + c
            x = int(ox + c * cell + (cell - side) / 2)
            y = int(oy + r * cell + (cell - side) / 2)
            m = cv2.aruco.generateImageMarker(dictionary, mid, side)
            img[y:y + side, x:x + side] = m[..., None]
            corners[mid] = np.float32([[x, y], [x + side, y], [x + side, y + side], [x, y + side]])
    return img, corners


def test_grid(size):
    """Grid with a centre cross and labelled corners, for checking alignment."""
    w, h = size
    img = np.zeros((h, w, 3), np.uint8)
    step = max(40, w // 16)
    for x in range(0, w, step):
        cv2.line(img, (x, 0), (x, h), (90, 90, 90), 1)
    for y in range(0, h, step):
        cv2.line(img, (0, y), (w, y), (90, 90, 90), 1)
    cv2.rectangle(img, (2, 2), (w - 3, h - 3), (60, 138, 224), 3)
    cv2.line(img, (w // 2, 0), (w // 2, h), (255, 255, 255), 1)
    cv2.line(img, (0, h // 2), (w, h // 2), (255, 255, 255), 1)
    for (x, y), lab in (((10, 30), "TL"), ((w - 50, 30), "TR"), ((10, h - 12), "BL"), ((w - 50, h - 12), "BR")):
        cv2.putText(img, lab, (x, y), cv2.FONT_HERSHEY_SIMPLEX, 0.8, (255, 255, 255), 2, cv2.LINE_AA)
    return img


def detect(frame, corners_by_id):
    """Matched (camera points, projector points) from one camera frame."""
    gray = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY) if frame.ndim == 3 else frame
    detector = cv2.aruco.ArucoDetector(cv2.aruco.getPredefinedDictionary(ARUCO),
                                       cv2.aruco.DetectorParameters())
    found, ids, _ = detector.detectMarkers(gray)
    cam, proj = [], []
    if ids is not None:
        for quad, mid in zip(found, ids.ravel()):
            if int(mid) in corners_by_id:
                cam.append(quad.reshape(4, 2))
                proj.append(corners_by_id[int(mid)])
    if not cam:
        return None, None, 0
    return np.concatenate(cam), np.concatenate(proj), len(cam)


def fit(cam_pts, proj_pts):
    """Homography camera -> projector and its mean reprojection error (px)."""
    H, inliers = cv2.findHomography(cam_pts, proj_pts, cv2.RANSAC, 4.0)
    if H is None:
        return None, None
    pred = cv2.perspectiveTransform(cam_pts.reshape(-1, 1, 2), H).reshape(-1, 2)
    err = float(np.linalg.norm(pred - proj_pts, axis=1)[inliers.ravel() > 0].mean())
    return H, err


class Calibration:
    """H plus the manual nudge, saved to data/calibration.json."""

    def __init__(self, H=None, proj_size=(1280, 800), cam_size=None,
                 markers=0, error=None, dx=0.0, dy=0.0, scale=1.0):
        self.H = None if H is None else np.asarray(H, np.float64)
        self.proj_size = tuple(proj_size)
        self.cam_size = None if cam_size is None else tuple(cam_size)
        self.markers = markers
        self.error = error
        self.dx, self.dy, self.scale = dx, dy, scale

    @property
    def ok(self):
        return self.H is not None

    def nudge(self):
        """The manual nudge as a projector-space matrix: scale about the
        projector centre, then shift."""
        w, h = self.proj_size
        cx, cy = w / 2, h / 2
        return np.array([[self.scale, 0, cx - self.scale * cx + self.dx],
                         [0, self.scale, cy - self.scale * cy + self.dy],
                         [0, 0, 1]], np.float64)

    def matrix(self):
        """H followed by the nudge. The nudge absorbs the cello not lying on
        the board's plane."""
        return self.nudge() @ self.H

    def warp(self, cam_img, roi=None):
        """Camera-space image -> projector frame. With `roi` (x0, y0, x1, y1:
        the only part of cam_img that is not black) just that box is warped,
        into the projector-space box it lands on; the rest stays black.
        Warping the whole 1920x1080 frame cost 11 ms per frame."""
        w, h = self.proj_size
        M = self.matrix()
        if roi is None:
            return cv2.warpPerspective(cam_img, M, (w, h), flags=cv2.INTER_LINEAR,
                                       borderValue=(0, 0, 0))
        x0, y0, x1, y1 = roi
        out = np.zeros((h, w, 3), np.uint8)
        corners = np.float32([[[x0, y0]], [[x1, y0]], [[x1, y1]], [[x0, y1]]])
        p = cv2.perspectiveTransform(corners, M)[:, 0]
        bx0, by0 = np.floor(p.min(0)).astype(int) - 1
        bx1, by1 = np.ceil(p.max(0)).astype(int) + 1
        bx0, by0, bx1, by1 = max(bx0, 0), max(by0, 0), min(bx1, w), min(by1, h)
        if bx1 <= bx0 or by1 <= by0:
            return out
        # roi pixel -> projector box pixel
        T = np.array([[1, 0, -bx0], [0, 1, -by0], [0, 0, 1]], np.float64) @ M @ \
            np.array([[1, 0, x0], [0, 1, y0], [0, 0, 1]], np.float64)
        out[by0:by1, bx0:bx1] = cv2.warpPerspective(
            np.ascontiguousarray(cam_img[y0:y1, x0:x1]), T, (bx1 - bx0, by1 - by0),
            flags=cv2.INTER_LINEAR, borderValue=(0, 0, 0))
        return out

    def to_dict(self):
        return {"H": None if self.H is None else self.H.tolist(),
                "proj_size": list(self.proj_size),
                "cam_size": None if self.cam_size is None else list(self.cam_size),
                "markers": self.markers, "error": self.error,
                "dx": self.dx, "dy": self.dy, "scale": self.scale}

    def save(self, path=CALIB_PATH):
        os.makedirs(os.path.dirname(path), exist_ok=True)
        with open(path, "w") as f:
            json.dump(self.to_dict(), f, indent=1)

    @classmethod
    def load(cls, path=CALIB_PATH):
        if not os.path.exists(path):
            return None
        with open(path) as f:
            d = json.load(f)
        return cls(**d)


# --- structured light (Gray code) ---------------------------------------------
#
# Each pattern lights the projector columns (or rows) whose Gray-code bit is
# 1; its inverse lights the rest. Comparing a camera pixel under the pattern
# and under its inverse gives that bit independently of room light and of the
# surface colour (orange wood, a dark wall). After all bits, every camera
# pixel that sees projector light knows which projector column and row lit it,
# including on the cello's curved front, so no flat board is needed.

def gray_bits(n):
    return max(1, int(np.ceil(np.log2(n))))


def gray_pattern(size, axis, bit, inverse=False):
    """Stripe image for one bit of the Gray code along x (axis 0) or y (1).
    `bit` counts from the most significant (widest stripes)."""
    w, h = size
    n = w if axis == 0 else h
    nb = gray_bits(n)
    coords = np.arange(n)
    gray = coords ^ (coords >> 1)
    on = ((gray >> (nb - 1 - bit)) & 1).astype(bool)
    if inverse:
        on = ~on
    line = np.where(on, 255, 0).astype(np.uint8)
    img = np.repeat(line[None, :], h, 0) if axis == 0 else np.repeat(line[:, None], w, 1)
    return np.repeat(img[..., None], 3, 2)


def decode_gray(pairs, nb, min_contrast=10):
    """Projector coordinate per camera pixel from (pattern, inverse) gray
    images, most significant bit first. Returns (coord float, valid bool).
    A pixel is valid where every bit had enough contrast to read."""
    gray = np.zeros(pairs[0][0].shape, np.int32)
    valid = np.ones(pairs[0][0].shape, bool)
    for p, q in pairs:
        d = p.astype(np.int16) - q.astype(np.int16)
        valid &= np.abs(d) >= min_contrast
        gray = (gray << 1) | (d > 0)
    # unused low bits (stripes too fine for the camera) were not projected:
    # shift up and take the middle of the remaining uncertainty
    missing = nb - len(pairs)
    binary = gray.copy()
    shift = gray >> 1
    while shift.any():
        binary ^= shift
        shift >>= 1
    coord = (binary << missing).astype(np.float32) + ((1 << missing) - 1) / 2
    return coord, valid


def fit_dense(px, py, valid, region=None, max_points=20000, seed=0):
    """Homography camera -> projector from decoded pixels. With `region`
    (the cello mask) only pixels on it are used, so the mapping fits the
    surface that matters rather than the wall behind."""
    use = valid if region is None else (valid & region)
    ys, xs = np.nonzero(use)
    if len(xs) < 50:
        return None, None, len(xs)
    if len(xs) > max_points:
        pick = np.random.default_rng(seed).choice(len(xs), max_points, replace=False)
        ys, xs = ys[pick], xs[pick]
    cam = np.stack([xs, ys], 1).astype(np.float32)
    proj = np.stack([px[ys, xs], py[ys, xs]], 1).astype(np.float32)
    H, inl = cv2.findHomography(cam, proj, cv2.RANSAC, 6.0)
    if H is None:
        return None, None, len(xs)
    pred = cv2.perspectiveTransform(cam[:, None], H)[:, 0]
    err = float(np.linalg.norm(pred - proj, axis=1)[inl.ravel() > 0].mean())
    return H, err, int(len(use.nonzero()[0]))


def implausible(H, px, py, use, proj_size, min_agree=0.5, tol=20.0):
    """Why a dense fit cannot be the real mapping, or None if it can.
    With weak stripes (daylight, a far projector) RANSAC still finds a small
    self-consistent subset of noise and reports a low error; the real
    mapping instead agrees with most decoded pixels, keeps the image the
    right way round (camera and projector face the same way) and puts the
    decoded area inside the projector frame."""
    ys, xs = np.nonzero(use)
    if len(xs) > 20000:
        pick = np.random.default_rng(1).choice(len(xs), 20000, replace=False)
        ys, xs = ys[pick], xs[pick]
    cam = np.stack([xs, ys], 1).astype(np.float32)
    pred = cv2.perspectiveTransform(cam[:, None], H)[:, 0]
    agree = float((np.linalg.norm(pred - np.stack([px[ys, xs], py[ys, xs]], 1), axis=1) < tol).mean())
    if agree < min_agree:
        return f"only {100 * agree:.0f}% of the decoded pixels agree with the fit"
    c = cam.mean(0)
    a, bx, by = cv2.perspectiveTransform(np.float32([[c, c + (1, 0), c + (0, 1)]]), H)[0]
    if np.cross(bx - a, by - a) <= 0:
        return "the fit mirrors the image"
    w, h = proj_size
    if not (-0.1 * w <= a[0] <= 1.1 * w and -0.1 * h <= a[1] <= 1.1 * h):
        return "the fit puts the lit area outside the projector frame"
    return None
