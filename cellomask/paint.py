"""Painting on the cello with the bow.

The bow's tip is a brush: flattened onto the cello's plane around its centre
(scaled so a stroke sweeps across the body), it lays thick, streaky ribbons
of paint, many fine bristles in blues, violets and magentas with cyan
highlights, that pile up on the cello like a canvas. A slow flow field drags
the wet paint, so the strokes smear and swirl as they build up.

The canvas lives in the same image space as TouchDesigner's picture (the
rectangle laid on the cello's plane, Pipeline.update_3d's quad), and is
composited on top of it before the projector warp: the paint stays where it
was put on the wood while the cello moves, leans and turns.

Gestures (the bow found in the depth, bow.py):
- start: the bow held upright beside the cello (along the strings, its
  middle above the cello's centre) for `hold_s` seconds;
- stop: held pointing down (along the strings, its middle below the centre)
  for `hold_s` seconds; the painting then fades out over `fade_s`.
Playing never looks like either: the bow crosses the strings nearly square.
Which way the bow points comes from where its middle is, not from telling the
frog from the tip, so a swapped frog/tip does not swap start and stop.
"""

import math
import time

import cv2
import numpy as np

# BGR palette, cycled: deep indigo, violet, blue, magenta, cyan, violet
PALETTE = np.array([
    (90, 12, 40), (220, 40, 140), (255, 90, 40), (200, 60, 230),
    (255, 220, 60), (240, 70, 170),
], np.float32)


def _key_lut():
    """Brightness of TouchDesigner's picture -> how much of it covers the
    paint (0-255): none below ~6, all from ~26, smooth between."""
    k = np.clip((np.arange(256, dtype=np.float32) - 6) / 20, 0, 1)
    return np.round(k * k * (3 - 2 * k) * 255).astype(np.uint8)


_KEY_LUT = _key_lut()


def palette(x):
    """Colour at phase x (wraps every 1.0), BGR float."""
    n = len(PALETTE)
    f = (x % 1.0) * n
    i = int(f) % n
    t = f - int(f)
    t = t * t * (3 - 2 * t)
    return PALETTE[i] * (1 - t) + PALETTE[(i + 1) % n] * t


class BowPainter:
    def __init__(self, size=(500, 1200), hold_s=2.0, fade_s=3.0, vertical_deg=55.0,
                 above_m=0.10, gap_s=0.5, reach=0.6, bristles=44, smooth=0.3, seed=0):
        self.W, self.H = size
        self.smooth = smooth            # brush position: weight of the newest frame
        self.hold_s, self.fade_s = hold_s, fade_s
        self.vertical_deg, self.above_m, self.gap_s = vertical_deg, above_m, gap_s
        self.reach = reach              # tip offset from the cello's centre -> brush offset
        self.n_bristles = bristles
        self.rng = np.random.default_rng(seed)
        self.color = np.zeros((self.H, self.W, 3), np.uint8)
        self.alpha = np.zeros((self.H, self.W), np.uint8)
        self.active = False
        self.fading_since = None
        self.pose = None                # the gesture being held: "up" | "down" | None
        self.pose_t0 = None
        self.pose_seen = None           # last time the held pose was seen
        self.trail = []                 # recent brush points (canvas px, time)
        self.brush_uv = None
        self.width = 0.0
        self.phase = self.rng.random()
        self.t_prev = None
        self._stroke_seed()

    # --- control -------------------------------------------------------------

    def start(self):
        if self.fading_since is not None:     # a new painting on a clean canvas
            self.clear()
        self.active, self.fading_since = True, None
        self.trail = []

    def stop(self, now=None):
        if self.active:
            self.active = False
            self.fading_since = time.time() if now is None else now
        self.trail = []

    def clear(self):
        self.color[:] = 0
        self.alpha[:] = 0
        self.fading_since = None
        self.trail = []

    def status(self, now=None):
        now = time.time() if now is None else now
        hold = 0.0
        if self.pose is not None and self.pose_t0 is not None:
            hold = min(1.0, (now - self.pose_t0) / self.hold_s)
        return {"active": self.active, "fading": self.fading_since is not None,
                "pose": self.pose, "hold": round(hold, 2),
                "brush": None if self.brush_uv is None else [round(v, 3) for v in self.brush_uv],
                "painted": round(float((self.alpha > 8).mean()) * 100, 1)}

    # --- gestures ------------------------------------------------------------

    def _gesture(self, st, now):
        """The pose this frame ("up" / "down" / None) and the hold timer."""
        pose = None
        if st and st.get("ok") and "angle" in st and "along" in st:
            if abs(st["angle"]) >= self.vertical_deg:
                if st["along"] > self.above_m:
                    pose = "up"
                elif st["along"] < -self.above_m:
                    pose = "down"
        if pose is not None:
            if pose != self.pose:
                self.pose, self.pose_t0 = pose, now
            self.pose_seen = now
        elif self.pose is not None and (self.pose_seen is None or now - self.pose_seen > self.gap_s):
            self.pose, self.pose_t0 = None, None        # let go (short dropouts do not reset it)
        if self.pose is not None and now - self.pose_t0 >= self.hold_s:
            fired = self.pose
            self.pose, self.pose_t0 = None, None        # needs a fresh hold to fire again
            if fired == "up" and not self.active:
                self.start()
                return "start"
            if fired == "down" and self.active:
                self.stop(now)
                return "stop"
        return None

    # --- the brush -----------------------------------------------------------

    @staticmethod
    def _image_from_camera(quad, size):
        """Homography camera px -> canvas px, from the image's corners in the
        camera (TL, TR, BR, BL)."""
        W, H = size
        dst = np.float32([[0, 0], [W, 0], [W, H], [0, H]])
        return cv2.getPerspectiveTransform(np.float32(quad), dst)

    def brush_point(self, st, cello, quad, K):
        """Canvas px of the brush for this bow state, or None. `quad` is the
        image's rectangle on the cello (Plane.quad): its corners in camera px
        (TL, TR, BR, BL) and its size in metres; the canvas is that rectangle."""
        if quad is None or cello is None or K is None or not st or not st.get("ok"):
            return None
        quad, self.fit = quad
        C, axis, n = cello["C"], cello["axis"], cello["n"]
        side = np.cross(axis, n)
        rel = st["tip"] - C
        x, y = rel @ side, rel @ axis
        P = C + self.reach * (x * side + y * axis)           # on the cello's plane
        if P[2] <= 0.05:
            return None
        px = np.array([P[0] / P[2] * K[0, 0] + K[0, 2], P[1] / P[2] * K[1, 1] + K[1, 2], 1.0])
        q = self._image_from_camera(quad, (self.W, self.H)) @ px
        if abs(q[2]) < 1e-9:
            return None
        u, v = q[0] / q[2], q[1] / q[2]
        if not (-0.2 * self.W < u < 1.2 * self.W and -0.2 * self.H < v < 1.2 * self.H):
            return None
        return np.array([u, v])

    def _stroke_seed(self):
        """Per-stroke bristle character: brightness (some nearly black, for the
        streaks), colour offset and a little jitter across the ribbon."""
        n = self.n_bristles
        b = self.rng.uniform(0.35, 1.0, n)
        b[self.rng.random(n) < 0.18] = 0.08          # dark gaps between the streaks
        b[0] = b[-1] = 1.0                           # bright, glossy edges
        self.b_bright = b
        self.b_hue = self.rng.normal(0, 0.06, n)
        self.b_jit = self.rng.normal(0, 0.12, n)
        self.b_wave = self.rng.uniform(0, 2 * math.pi, n)     # each bristle wanders a little
        self.s_len = 0.0                                     # the stroke's length so far (px)
        self.ends = None                                     # each bristle's last point (n x 2)
        self.w_prev = None

    def _lay(self, pts, nrm, width, hue, now):
        """A ribbon of thin bristles along the canvas points `pts` (N x 2),
        `nrm` the unit normals there (smooth across the stroke's pieces).
        Each bristle carries on from exactly where it ended, and the width
        changes gradually along the piece: no steps where pieces meet."""
        if len(pts) < 2 or width < 1:
            return
        seg = np.r_[0, np.cumsum(np.linalg.norm(np.diff(pts, axis=0), axis=1))] + self.s_len
        self.s_len = float(seg[-1])
        w0 = width if self.w_prev is None else self.w_prev
        wid = np.linspace(w0, width, len(pts))
        self.w_prev = width
        n = self.n_bristles
        thick = 1 if width / n < 1.6 else 2
        ends = np.zeros((n, 2))
        ramp = np.linspace(1, 0, len(pts))[:, None] ** 2    # blend from the old end over the piece
        for i in range(n):
            # where the bristle sits across the ribbon, wandering slowly along it
            frac = (i / (n - 1)) - 0.5 + self.b_jit[i] / n + 0.012 * np.sin(seg * 0.03 + self.b_wave[i])
            b = pts + nrm * (frac * wid)[:, None]
            if self.ends is not None:
                b = b + (self.ends[i] - b[0]) * ramp
            ends[i] = b[-1]
            line = np.round(b * 4).astype(np.int32)                       # 2 bits of sub-pixel
            col = palette(hue + self.b_hue[i] + 0.04 * math.sin(i * 1.7 + now)) * self.b_bright[i]
            if i in (0, 1, n - 2, n - 1):
                col = col * 0.55 + 255 * 0.45                          # glossy edges
            cv2.polylines(self.color, [line], False, tuple(float(c) for c in col), thick,
                          cv2.LINE_AA, shift=2)
            cv2.polylines(self.alpha, [line], False, 255, thick + 1, cv2.LINE_AA, shift=2)
        self.ends = ends

    def _flow_maps(self, now, w, h):
        """A slowly turning flow field (display px), for showing the canvas
        through: the paint seems to drift and swirl, but the canvas itself is
        never resampled, so it stays crisp."""
        gh, gw = 7, 5
        t = now * 0.25
        yy, xx = np.mgrid[0:gh, 0:gw].astype(np.float32)
        ang = (np.sin(xx * 1.3 + t) + np.cos(yy * 0.9 - 1.3 * t) + np.sin((xx + yy) * 0.7 + 0.5 * t)) * 1.6
        amp = 0.012 * h * (0.6 + 0.4 * math.sin(now * 0.4))
        fx = cv2.resize((np.cos(ang) * amp).astype(np.float32), (w, h), interpolation=cv2.INTER_CUBIC)
        fy = cv2.resize((np.sin(ang) * amp).astype(np.float32), (w, h), interpolation=cv2.INTER_CUBIC)
        sx, sy = self.W / w, self.H / h
        if getattr(self, "_grid_wh", None) != (w, h):
            gy, gx = np.mgrid[0:h, 0:w].astype(np.float32)
            self._grid, self._grid_wh = (gx, gy), (w, h)
        gx, gy = self._grid
        return (gx - fx) * sx, (gy - fy) * sy

    # --- per frame -----------------------------------------------------------

    def update(self, st, cello, quad, K, now=None):
        """One tracked frame. Returns "start" / "stop" when a gesture fired."""
        now = time.time() if now is None else now
        dt = 0.0 if self.t_prev is None else min(0.2, now - self.t_prev)
        self.t_prev = now
        fired = self._gesture(st, now)
        if self.fading_since is not None:
            k = now - self.fading_since
            if k >= self.fade_s:
                self.clear()
            elif dt > 0:
                self.alpha = (self.alpha.astype(np.float32) * max(0.0, 1 - dt / max(self.fade_s - k + dt, 1e-3))
                              ).astype(np.uint8)
        self.now = now
        self.brush_uv = None
        if not self.active:
            self.trail = []
            return fired
        # (painting goes on while a gesture may be being held: a steep bow
        # is also a way of drawing; a stroke made while holding to stop fades
        # with the rest)
        p = self.brush_point(st, cello, quad, K)
        if p is None:
            if self.trail and now - self.trail[-1][1] > 0.3:
                self.trail = []                    # the bow lost: the next stroke starts fresh
            return fired
        if self.trail and now - self.trail[-1][1] > 0.3:
            self.trail = []
        if not self.trail:
            self._stroke_seed()
            self.p_smooth = p
        else:
            # the tracker's frame-to-frame jitter, magnified by the brush,
            # crumpled the strokes into tight curls: ~0.1 s of smoothing
            self.p_smooth = self.p_smooth + self.smooth * (p - self.p_smooth)
        p = self.p_smooth.copy()
        self.brush_uv = (p[0] / self.W, p[1] / self.H)
        self.trail = (self.trail + [(p, now)])[-5:]
        # thickness from how fast the brush moves across the canvas
        if len(self.trail) >= 2:
            (p0, t0), (p1, t1) = self.trail[-2], self.trail[-1]
            v = np.linalg.norm(p1 - p0) / max(t1 - t0, 1e-3)
            target = np.clip(12 + v * 0.11, 12, 135)          # (canvas px: 500 x 1200)
            self.width += 0.3 * (target - self.width)
            # warm on the down-bow, cool on the up-bow, drifting with time
            spd = float(st.get("speed", 0.0)) if st else 0.0
            self.phase += dt * 0.03
            shift = 0.12 if spd > 0.05 else -0.12 if spd < -0.05 else 0.0
            self.shift = getattr(self, "shift", 0.0) + 0.15 * (shift - getattr(self, "shift", 0.0))
            pts, nrm = self._smooth()
            self._lay(pts, nrm, self.width, self.phase + self.shift, now)
        return fired

    @staticmethod
    def _catmull(p0, p1, p2, p3, t):
        return 0.5 * ((2 * p1) + (-p0 + p2) * t + (2 * p0 - 5 * p1 + 4 * p2 - p3) * t ** 2
                      + (-p0 + 3 * p1 - 3 * p2 + p3) * t ** 3)

    def _smooth(self, per=14):
        """The newest piece of the stroke as Catmull-Rom points through the
        last brush positions (a 30 Hz bow makes round strokes), and the
        normals there, taken from the curve over the last few pieces so they
        turn smoothly from one piece to the next."""
        P = [p for p, _ in self.trail]
        P = [P[0] - (P[1] - P[0])] + P + [P[-1] + (P[-1] - P[-2])]      # end tangents
        t = np.linspace(0, 1, per)[:, None]
        pieces = [self._catmull(P[k - 1], P[k], P[k + 1], P[k + 2], t) for k in range(1, len(P) - 2)]
        curve = np.concatenate(pieces)
        d = np.gradient(curve, axis=0)
        d = cv2.GaussianBlur(d.reshape(-1, 1, 2), (1, 9), 0).reshape(-1, 2) if len(d) >= 9 else d
        nrm = np.stack([-d[:, 1], d[:, 0]], 1)
        nrm /= np.linalg.norm(nrm, axis=1, keepdims=True) + 1e-9
        return curve[-per:], nrm[-per:]

    def compose(self, image, behind=False):
        """`image` (TouchDesigner's picture, BGR) with the painting, seen
        through the drifting flow field. behind: the painting goes under
        TouchDesigner's graphics. Its picture comes without transparency, so
        its dark parts count as see-through: the paint shows where the
        picture is black, its bright graphics cover the paint (softly in
        between). Without a picture, the painting on black at 720 x 1080."""
        if not self.alpha.any():
            return image
        if image is None:
            image = np.zeros((1080, 720, 3), np.uint8)
        ih, iw = image.shape[:2]
        # the part of the picture that lands on the cello's rectangle: the
        # projector cover-fits it there (Pipeline._content_direct, composite)
        ox, oy, cw, ch = 0, 0, iw, ih
        fit = getattr(self, "fit", None)
        if fit is not None:
            L, Wd = fit
            sc = max(Wd / iw, L / ih)
            cw, ch = int(round(Wd / sc)), int(round(L / sc))
            ox, oy = (iw - cw) // 2, (ih - ch) // 2
        mx, my = self._flow_maps(getattr(self, "now", time.time()), cw, ch)
        col = cv2.remap(self.color, mx, my, cv2.INTER_LINEAR, borderMode=cv2.BORDER_CONSTANT)
        a = cv2.remap(self.alpha, mx, my, cv2.INTER_LINEAR, borderMode=cv2.BORDER_CONSTANT)
        a = a.astype(np.float32) / 255
        out = image.copy()
        roi = out[oy:oy + ch, ox:ox + cw]
        painted = cv2.blendLinear(col, roi, a, 1 - a)
        if behind:
            # how much of TouchDesigner's picture is there, by its brightness
            # (black = see-through, from ~25 of 255 fully there)
            b, g, r = cv2.split(roi)
            k = cv2.LUT(cv2.max(cv2.max(b, g), r), _KEY_LUT).astype(np.float32) * (1 / 255)
            painted = cv2.blendLinear(roi, painted, k, 1 - k)
        out[oy:oy + ch, ox:ox + cw] = painted
        return out
