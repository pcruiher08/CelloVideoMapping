"""Hand signs beside the cello, from the Kinect's full-resolution colour:
✌️ (peace) and 👍 (thumbs up), shown with the fingering hand (the player's
left, the camera's right of the cello's neck) to switch effects in Max.

The cellist plays in white gloves, which hand-pose models trained on bare
hands do not take for hands (MediaPipe found none, even at 1920 x 1080). The
glove is easy to see, though: the brightest, least coloured thing beside the
neck, against the dark backdrop and the blue sleeve. So the sign is read from
the glove's silhouette, in a zone that follows the cello:

- the zone: 0.10-0.60 m to the camera's right of the cello's centre and
  0.11-0.59 m above it, at the cello's distance (in the camera's view, so a
  leaning cello does not tilt it);
- the glove: bright, unsaturated pixels there, the largest blob;
- ✌️: two separate prongs (the fingers) across a quarter or more of the
  glove's upper half; 👍: a narrow prong (under half the glove's width) on
  top of a wide fist. Anything else: no sign.

On the stage recording (109 frames at 1920 x 1080) it agreed with the eye on
98 frames, the rest being the half-second while the hand moves into or out of
a sign, and never saw a sign while the hand was down.

A sign held for `hold_s` toggles its effect; it has to be lowered before the
same sign toggles again.

Only white that was not there before counts: the zone's usual look is
learned slowly (`bg_s`, ~20 s) and the glove must differ from it. In daylight
the zone also held a white board with printed letters, the bright ceiling and
a whiteboard's edge, read as a constant ✌️ (it switched the ping-pong on by
itself); a hand raised for a sign differs from that, the scenery does not.
Blobs far bigger than a hand are not a glove either.
"""

import time

import cv2
import numpy as np

SIGNS = {"V": "pingpong", "T": "overdrive"}       # the sign -> the effect it switches


class SignWatcher:
    def __init__(self, hold_s=1.0, share=0.7, release_s=0.5, zone=((0.10, 0.60), (0.11, 0.59))):
        self.hold_s, self.share, self.release_s = hold_s, share, release_s
        self.zone_m = zone
        self.fx = {"pingpong": False, "overdrive": False}   # independent: both can be on
        self.seen = []              # (time, sign or None) over the last hold_s
        self.armed = {"V": True, "T": True}
        self.gone_since = {"V": None, "T": None}
        self.sign = None            # this frame's sign
        self.zone_px = None
        self.last_event = None
        self.bg_s, self.warm_s = 20.0, 2.0      # background time constant; no signs until learned
        self.bg = None                          # the image's usual look: grey, 1/4 size (float32)
        self.bg_t0 = self.bg_t = None

    # --- the zone and the glove -----------------------------------------------

    def zone(self, C, K, shape):
        """The search box (x0, y0, x1, y1) in image px for a cello centred at
        C (camera frame, m), K the image's intrinsics."""
        if C is None or C[2] <= 0.3:
            return None
        ppm = K[0, 0] / C[2]                          # px per metre at the cello
        cx = C[0] / C[2] * K[0, 0] + K[0, 2]
        cy = C[1] / C[2] * K[1, 1] + K[1, 2]
        (sx0, sx1), (uy0, uy1) = self.zone_m
        h, w = shape[:2]
        x0, x1 = int(cx + sx0 * ppm), int(cx + sx1 * ppm)
        y0, y1 = int(cy - uy1 * ppm), int(cy - uy0 * ppm)
        x0, y0, x1, y1 = max(0, x0), max(0, y0), min(w, x1), min(h, y1)
        if x1 - x0 < 20 or y1 - y0 < 20:
            return None
        return x0, y0, x1, y1, ppm

    @staticmethod
    def classify(region, ppm=500.0, new=None):
        """"V" (✌️), "T" (👍), "o" (a glove, no sign) or None (no glove).
        new: where the region differs from its usual look (bool, its size);
        only there can the glove be."""
        hsv = cv2.cvtColor(region, cv2.COLOR_BGR2HSV)
        v = hsv[..., 2]
        bright = max(120, int(np.percentile(v, 99.5) * 0.8))   # the glove in a darker hall too
        m = ((v > bright) & (hsv[..., 1] < 60)).astype(np.uint8)
        if new is not None:
            m &= new.astype(np.uint8)
        m = cv2.morphologyEx(m, cv2.MORPH_OPEN, np.ones((3, 3), np.uint8))
        n, lab, st, _ = cv2.connectedComponentsWithStats(m)
        if n < 2:
            return None
        i = 1 + int(np.argmax(st[1:, 4]))
        x, y, w, h, a = st[i]
        k = ppm / 500.0                                # sizes tuned at ~500 px/m
        if a < 600 * k * k or h < 40 * k or a > 15000 * k * k:
            return None                                # too small, or far bigger than a hand
        blob = lab[y:y + h, x:x + w] == i
        runs, widths = [], []
        min_run = max(2, int(round(3 * k)))
        for row in blob:
            r = np.flatnonzero(np.diff(np.r_[0, row.astype(np.int8), 0]))
            segs = [(r[j], r[j + 1]) for j in range(0, len(r), 2) if r[j + 1] - r[j] >= min_run]
            runs.append(len(segs))
            widths.append(sum(b - a for a, b in segs))
        runs, widths = np.array(runs), np.array(widths, float)
        if (runs[:max(1, int(0.55 * h))] >= 2).mean() > 0.25:
            return "V"
        wmax = widths.max()
        top = widths[:max(1, int(0.35 * h))]
        narrow = (top > 0) & (top < 0.5 * wmax)
        if narrow.mean() > 0.6 and widths[int(0.6 * h):].mean() > 0.7 * wmax:
            return "T"
        return "o"

    # --- per frame -------------------------------------------------------------

    def update(self, image, K, C, now=None):
        """One frame: `image` the full-resolution colour (BGR), K its
        intrinsics, C the cello's centre (camera frame, m). Returns
        (effect, on) when a sign toggled an effect, else None."""
        now = time.time() if now is None else now
        new = self._learn(image, now)
        z = self.zone(C, K, image.shape)
        self.zone_px = None if z is None else z[:4]
        sign = None
        if z is not None and new is not None:
            x0, y0, x1, y1, ppm = z
            q = new[y0 // 4:max(y0 // 4 + 1, y1 // 4), x0 // 4:max(x0 // 4 + 1, x1 // 4)].astype(np.uint8)
            q = cv2.resize(q, (x1 - x0, y1 - y0), interpolation=cv2.INTER_NEAREST) > 0
            c = self.classify(image[y0:y1, x0:x1], ppm, new=q)
            sign = c if c in SIGNS else None
        self.sign = sign
        self.seen = [(t, s) for t, s in self.seen if now - t <= self.hold_s] + [(now, sign)]
        event = None
        for s in SIGNS:
            if sign == s:
                self.gone_since[s] = None
            elif self.gone_since[s] is None:
                self.gone_since[s] = now
            if not self.armed[s] and self.gone_since[s] is not None and now - self.gone_since[s] >= self.release_s:
                self.armed[s] = True                    # lowered: may toggle again
            span = now - self.seen[0][0]
            got = np.mean([x == s for _, x in self.seen])
            if self.armed[s] and span >= 0.8 * self.hold_s and got >= self.share:
                fx = SIGNS[s]
                self.fx[fx] = not self.fx[fx]
                self.armed[s] = False
                event = (fx, self.fx[fx])
        if event:
            self.last_event = (now, *event)
        return event

    def _learn(self, image, now, diff=25.0):
        """Update the slowly learned usual look of the image; returns where
        this frame differs from it (bool, 1/4 size), or None while it is
        still being learned."""
        h, w = image.shape[:2]
        small = cv2.cvtColor(cv2.resize(image, (w // 4, h // 4), interpolation=cv2.INTER_AREA),
                             cv2.COLOR_BGR2GRAY).astype(np.float32)
        if self.bg is None or self.bg.shape != small.shape:
            self.bg, self.bg_t0, self.bg_t = small, now, now
            return None
        dt = max(0.0, now - self.bg_t)
        self.bg_t = now
        warming = now - self.bg_t0 < self.warm_s
        tc = 0.5 if warming else self.bg_s                 # learn fast at first, then slowly
        new = np.abs(small - self.bg) > diff
        self.bg += (1 - np.exp(-dt / tc)) * (small - self.bg)
        if warming:
            return None
        return cv2.dilate(new.astype(np.uint8), np.ones((3, 3), np.uint8)) > 0

    def hold(self, now=None):
        """0-1: how far the current sign is towards toggling."""
        now = time.time() if now is None else now
        if self.sign is None or not self.armed.get(self.sign, False) or not self.seen:
            return 0.0
        got = np.mean([x == self.sign for _, x in self.seen])
        span = now - self.seen[0][0]
        return float(min(1.0, (span / (0.8 * self.hold_s)) * min(1.0, got / self.share)))

    def set(self, fx, on):
        if fx in self.fx:
            self.fx[fx] = bool(on)

    def status(self, now=None):
        names = {"V": "peace", "T": "thumbs up"}
        return {"sign": names.get(self.sign), "hold": round(self.hold(now), 2),
                "pingpong": self.fx["pingpong"], "overdrive": self.fx["overdrive"],
                "zone": None if self.zone_px is None else [int(v) for v in self.zone_px]}
