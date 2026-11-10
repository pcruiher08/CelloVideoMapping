"""Draw the cello where it will be, not where the camera saw it.

From the phone capturing a frame to the projector's light changing takes
~0.35 s, so a moving cello leaves its light behind. Constant-velocity Kalman
filters on the cello's pose (position, rotation and size in the image; its
plane in 3D) estimate how fast it is moving, and the projected mask, image
and plane are moved forward by the time the light takes to arrive.

Each frame is timed at its capture (the phone's clock mapped to the Mac's),
so uneven arrival over Wi-Fi does not read as motion. A reversal of direction
still overshoots for a moment; predicting part of the delay (the "predict"
setting), damping the velocity and capping the jump keep that small.
"""

import cv2
import numpy as np


class KalmanCV:
    """Position + velocity of one value, constant-velocity model.

    q: how freely the velocity changes (acceleration noise, units/s^2 as a
       spectral density); r: the measurement noise (units, standard deviation).
    A measurement more than `gate` sigmas off the prediction restarts the
    filter: a jump (another cello picked, a cut), not motion."""

    def __init__(self, q, r, gate=8.0):
        self.q, self.r, self.gate = q, r, gate
        self.x = None              # [value, velocity]
        self.P = None
        self.t = None

    def reset(self):
        self.x = self.P = self.t = None

    def _predict(self, dt):
        F = np.array([[1.0, dt], [0.0, 1.0]])
        q = self.q
        Q = q * np.array([[dt ** 3 / 3, dt ** 2 / 2], [dt ** 2 / 2, dt]])
        return F @ self.x, F @ self.P @ F.T + Q

    def update(self, z, t):
        if self.x is None or t <= self.t or t - self.t > 1.0:
            self.x = np.array([z, 0.0])
            self.P = np.diag([self.r ** 2, (10 * self.r) ** 2])
            self.t = t
            return
        x, P = self._predict(t - self.t)
        S = P[0, 0] + self.r ** 2
        nu = z - x[0]
        if nu * nu > self.gate ** 2 * S:
            self.x = np.array([z, 0.0])
            self.P = np.diag([self.r ** 2, (10 * self.r) ** 2])
            self.t = t
            return
        k = P[:, 0] / S
        self.x = x + k * nu
        self.P = P - np.outer(k, P[0, :])
        self.t = t

    @property
    def value(self):
        return None if self.x is None else float(self.x[0])

    @property
    def velocity(self):
        return 0.0 if self.x is None else float(self.x[1])

    @property
    def trusted_velocity(self):
        """The velocity shrunk towards zero unless it clearly exceeds its own
        uncertainty: v * v^2 / (v^2 + sigma^2). On a still cello the
        estimate is pure noise (cx: ~23 px/s), which a 0.25 s prediction
        turned into ~6 px of quiver every frame; a real sway is several
        sigma and keeps nearly all of it."""
        if self.x is None:
            return 0.0
        v, s2 = float(self.x[1]), float(self.P[1, 1])
        return v * v * v / (v * v + s2)


def mask_pose(mask):
    """(cx, cy, angle from straight up in radians, log of the area's square
    root) of a mask, or None. The axis is signed to point up the image (a
    played cello is scroll-up), like the AxisTracker."""
    m = cv2.moments((mask > 0.5).astype(np.uint8), binaryImage=True)
    if m["m00"] < 50:
        return None
    cx, cy = m["m10"] / m["m00"], m["m01"] / m["m00"]
    mu20, mu02, mu11 = m["mu20"] / m["m00"], m["mu02"] / m["m00"], m["mu11"] / m["m00"]
    evals, evecs = np.linalg.eigh(np.array([[mu20, mu11], [mu11, mu02]]))
    ax = evecs[:, 1]
    if ax[1] > 0:
        ax = -ax
    angle = float(np.arctan2(ax[0], -ax[1]))      # 0 = up, + = top leaning right
    return cx, cy, angle, 0.5 * np.log(m["m00"])


class PosePredictor:
    """The cello's 2D pose in the camera image, filtered and extrapolated.

    delta(t) is the similarity transform (2x3, camera pixels) that takes the
    cello as last measured to where it will be at time t."""

    def __init__(self):
        # tuned with the simulated sway in test_predict.py: measurement noise
        # is the mask's own jitter, q how quickly a player changes speed
        # (higher q follows speed changes sooner but shakes a still cello;
        # past this the trail barely shrinks: a straight-line forecast cannot
        # follow the curve of a sway 0.35 s ahead)
        self.f = [KalmanCV(q=4e4, r=1.5),          # cx px
                  KalmanCV(q=4e4, r=1.5),          # cy px
                  KalmanCV(q=4.0, r=0.004),        # angle rad
                  KalmanCV(q=0.4, r=0.003)]        # log size
        self.t = None

    def reset(self):
        for f in self.f:
            f.reset()
        self.t = None

    def update(self, mask, t):
        p = None if mask is None else mask_pose(mask)
        if p is None:
            return False
        for f, z in zip(self.f, p):
            f.update(z, t)
        self.t = t
        return True

    def delta(self, t, damping=1.0, max_shift=0.2):
        """Transform from the last measurement to time t (None when there is
        nothing to predict from). The velocity decays with time constant
        `damping` (s), so a stale estimate fades rather than flies off; the
        shift is capped at `max_shift` of the cello's size."""
        if self.t is None or self.f[0].x is None:
            return None
        dt = max(0.0, t - self.t)
        lead = damping * (1 - np.exp(-dt / damping)) if damping > 0 else dt
        cx, cy, a, ls = (f.value for f in self.f)
        vx, vy, va, vs = (f.trusted_velocity for f in self.f)
        size = np.exp(ls)
        dx, dy = vx * lead, vy * lead
        n = np.hypot(dx, dy)
        if n > max_shift * size:
            dx, dy = dx * max_shift * size / n, dy * max_shift * size / n
        da = float(np.clip(va * lead, -0.15, 0.15))
        sc = float(np.exp(np.clip(vs * lead, -0.1, 0.1)))
        # rotate and scale about the filtered centre, then move it
        c, s_ = np.cos(da) * sc, np.sin(da) * sc
        # angle is measured from up towards the right (clockwise on screen,
        # where y points down), the same sense as a positive image rotation
        A = np.array([[c, -s_, 0.0], [s_, c, 0.0]])
        A[:, 2] = np.array([cx, cy]) - A[:, :2] @ np.array([cx, cy]) + np.array([dx, dy])
        return A


def apply_mask(A, mask):
    """The mask moved by A (2x3), same size; cheap when A is near identity."""
    if A is None or mask is None:
        return mask
    if np.abs(A - np.array([[1, 0, 0], [0, 1, 0]])).max() < 0.05:
        return mask
    h, w = mask.shape
    return cv2.warpAffine(mask, A, (w, h), flags=cv2.INTER_LINEAR, borderValue=0)


def apply_axis(A, axis):
    """The axis rectangle (cx, cy, length, width, up) moved by A."""
    if A is None or axis is None:
        return axis
    cx, cy, length, width, up = axis
    sc = float(np.hypot(A[0, 0], A[1, 0]))
    da = float(np.arctan2(A[1, 0], A[0, 0]))
    nx, ny = A @ np.array([cx, cy, 1.0])
    return (float(nx), float(ny), length * sc, width * sc, up + da)


class PlanePredictor:
    """The cello plane's centre and normal (camera frame), filtered and
    extrapolated the same way; replaces the One Euro smoothing in
    CelloPlane when prediction is on."""

    def __init__(self):
        # the normal is noisy (~0.5 deg a frame): a livelier filter turned
        # that noise into tilt speed and predicted worse than none
        self.f = [KalmanCV(q=0.5, r=0.006) for _ in range(3)] + \
                 [KalmanCV(q=3.0, r=0.02) for _ in range(3)]
        self.t = None

    def reset(self):
        for f in self.f:
            f.reset()
        self.t = None

    def update(self, C, n, t):
        for f, z in zip(self.f, np.r_[C, n]):
            f.update(float(z), t)
        self.t = t

    def at(self, t, damping=1.0):
        """(C, n) at time t, or None."""
        if self.t is None or self.f[0].x is None:
            return None
        dt = max(0.0, t - self.t)
        lead = damping * (1 - np.exp(-dt / damping)) if damping > 0 else dt
        v = np.array([f.value + f.trusted_velocity * lead for f in self.f])
        C, n = v[:3], v[3:]
        return C, n / np.linalg.norm(n)
