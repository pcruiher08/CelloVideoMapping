"""Per-frame cello segmentation with temporal smoothing.

Uses the fine-tuned model (models/cello-seg.pt) when it exists, otherwise
falls back to YOLOE prompted with the text "cello", so the app works before
training has finished.
"""

import os
import time

import cv2
import numpy as np

from .autolabel import MODELS
from bowtrack.one_euro import OneEuroFilter

DEFAULT_MODEL = os.path.join(MODELS, "cello-seg.pt")
FALLBACK_MODEL = os.path.join(MODELS, "yoloe-26s-seg.pt")


def pick_device():
    import torch
    if torch.backends.mps.is_available():
        return "mps"
    if torch.cuda.is_available():
        return "cuda"
    return "cpu"


def unletterbox(masks, H, W):
    """Masks from the padded model input (e.g. 288x512) -> frame size H x W:
    crop the letterbox padding, then resize."""
    if not len(masks):
        return masks
    h, w = masks.shape[1:]
    g = min(h / H, w / W)
    px, py = (w - W * g) / 2, (h - H * g) / 2
    masks = masks[:, int(round(py - 0.1)):int(round(h - py + 0.1)),
                  int(round(px - 0.1)):int(round(w - px + 0.1))]
    return np.stack([cv2.resize(m, (W, H), interpolation=cv2.INTER_LINEAR)
                     for m in masks])


class Segmenter:
    def __init__(self, model_path=None, imgsz=640):
        from ultralytics import YOLO, YOLOE
        path = model_path or (DEFAULT_MODEL if os.path.exists(DEFAULT_MODEL)
                              else FALLBACK_MODEL)
        self.path = path
        self.name = os.path.basename(path)
        self.open_vocab = "yoloe" in self.name.lower()
        if self.open_vocab:
            self.model = YOLOE(path)
            self.model.set_classes(["cello"])
        else:
            self.model = YOLO(path)
        self.device = pick_device()
        self.imgsz = imgsz
        self.last_ms = 0.0

    def __call__(self, frame, conf=0.35):
        """Instances as dicts {mask: float32 HxW 0..1, box, conf}, largest
        first, at frame resolution.

        Masks come back at model resolution and are upscaled here with
        OpenCV. Ultralytics' retina_masks does the same upscale on the GPU,
        but copying N full-resolution masks back from MPS costs ~20 ms a
        frame, for edges that match to IoU 0.99."""
        t0 = time.perf_counter()
        r = self.model.predict(frame, conf=conf, imgsz=self.imgsz,
                               device=self.device, verbose=False)[0]
        if r.masks is None:
            self.last_ms = (time.perf_counter() - t0) * 1000
            return []
        masks = unletterbox(r.masks.data.float().cpu().numpy(), *frame.shape[:2])
        self.last_ms = (time.perf_counter() - t0) * 1000
        boxes = r.boxes.xyxy.cpu().numpy()
        confs = r.boxes.conf.cpu().numpy()
        out = [{"mask": m, "box": b, "conf": float(c)}
               for m, b, c in zip(masks, boxes, confs)]
        out.sort(key=lambda d: -float(d["mask"].sum()))
        return out


class MaskSmoother:
    """Adaptive exponential smoothing of the soft mask plus a short hold.

    `alpha` is the newest frame's weight while the cello is still: low, so
    the edge does not shimmer. When the mask really moves (it overlaps the
    smoothed one less), the weight rises towards 1, so the light keeps up
    with the cello instead of trailing a ghost of where it was. Like a One
    Euro filter, but on the whole shape.

    A single missed detection would otherwise blank the replacement for one
    frame, which reads as a flash on a projector. `hold` frames of the last
    good mask cover those dropouts; a real disappearance fades out after."""

    def __init__(self, alpha=0.35, hold=6, moving=0.06):
        self.alpha = alpha
        self.hold = hold
        self.moving = moving      # 1 - IoU at which the newest frame takes over
        self.mask = None
        self.missed = 0
        self.weight = alpha       # last weight used, for the status readout

    def reset(self):
        self.mask = None
        self.missed = 0

    def __call__(self, mask, shape):
        if self.mask is not None and self.mask.shape != tuple(shape):
            self.reset()                 # the camera turned: the old mask no longer fits
        if mask is None:
            self.missed += 1
            if self.mask is None:
                return None
            if self.missed > self.hold:
                self.mask *= 0.6
                if self.mask.max() < 0.05:
                    self.mask = None
            return self.mask
        self.missed = 0
        if self.mask is None or self.mask.shape != mask.shape:
            self.mask = mask.astype(np.float32)
        else:
            a, b = mask[::4, ::4] > 0.5, self.mask[::4, ::4] > 0.5
            change = 1 - (a & b).sum() / max(1, (a | b).sum())
            w = self.alpha + (1 - self.alpha) * min(1.0, change / self.moving)
            self.weight = w
            self.mask = cv2.addWeighted(mask.astype(np.float32), w, self.mask, 1 - w, 0)
        return self.mask


class AxisTracker:
    """Orientation of the cello as a rotated rectangle: centre, long-axis
    length, short-axis width and the angle of the scroll ("up") direction.

    The axis comes from PCA of the mask. Three things keep it from spinning:

    - a played cello is always scroll-up, so the axis is signed to point up
      the screen and the tilt is clamped to `max_tilt` from vertical. (A
      narrow-end heuristic for the scroll flipped back and forth whenever
      only part of the cello was visible, turning the image 180 degrees.)
    - when the mask is not clearly elongated (a sliver at the frame edge, a
      close-up of the body) its PCA axis is noise, so the angle is held and
      only position and size follow.
    - the angle has a small deadband and its own One Euro filter: steady
      when still, quick to follow when the cello turns.

    With `follow=False` the angle is locked upright."""

    def __init__(self, max_tilt=60, min_elongation=1.4, deadband=0.4):
        self.max_tilt = np.radians(max_tilt)
        self.min_elongation = min_elongation
        self.deadband = np.radians(deadband)
        self.follow = True
        self.reset()

    def reset(self):
        self.f = None
        self.angle_f = None
        self.body_f = None
        self.raw_up = None
        self.last = None
        # where the body starts, as a fraction of the visible length from the
        # scroll end; 0.38 is a whole cello, less when only part is in frame
        self.body_start = 0.38

    def __call__(self, mask, t):
        ys, xs = np.nonzero(mask[::2, ::2] > 0.5)      # half resolution is plenty
        if len(xs) < 15:
            return self.last
        step = max(1, len(xs) // 3000)                 # PCA on a subsample
        pts = np.stack([xs[::step], ys[::step]], 1).astype(np.float32) * 2
        c = pts.mean(0)
        evals, evecs = np.linalg.eigh(np.cov((pts - c).T))
        axis = evecs[:, 1]
        if axis[1] > 0:                                # point up the screen
            axis = -axis
        elongated = evals[1] > self.min_elongation ** 2 * max(evals[0], 1e-6)

        # angle measured from straight up, clamped to the allowed tilt
        up_vertical = -np.pi / 2
        if not self.follow:
            up = up_vertical
        else:
            tilt = np.clip(np.arctan2(axis[1], axis[0]) - up_vertical,
                           -self.max_tilt, self.max_tilt)
            up = up_vertical + tilt
            if self.raw_up is not None and (not elongated or abs(up - self.raw_up) < self.deadband):
                up = self.raw_up
        self.raw_up = up

        # extent along / across the chosen direction (not the PCA one, so
        # the rectangle stays consistent with the angle actually used)
        u = np.array([np.cos(up), np.sin(up)])
        v = np.array([-u[1], u[0]])
        proj, perp = (pts - c) @ u, (pts - c) @ v
        lo, hi = np.percentile(proj, 1), np.percentile(proj, 99)
        plo, phi = np.percentile(perp, 1), np.percentile(perp, 99)
        centre = c + u * (lo + hi) / 2 + v * (plo + phi) / 2
        vals = [centre[0], centre[1], hi - lo, phi - plo]
        body = self._body_start(proj, perp, lo, hi)

        if self.f is None:
            # tuned on a simulated sway at 20 fps (rotation trailed 120-180 ms
            # with the deadband at 0.8 deg and a 1 Hz angle cutoff; now ~70)
            self.f = [OneEuroFilter(min_cutoff=1.2, beta=0.02, d_cutoff=3.0) for _ in vals]
            self.angle_f = OneEuroFilter(min_cutoff=2.5, beta=4.0, d_cutoff=3.0)
            self.body_f = OneEuroFilter(min_cutoff=0.5, beta=0.5)
        smoothed = [f(x, t) for f, x in zip(self.f, vals)]
        self.last = (*smoothed, self.angle_f(up, t))
        if body is not None:
            self.body_start = float(self.body_f(body, t))
        return self.last

    @staticmethod
    def _body_start(proj, perp, lo, hi, bins=32, frac=0.6):
        """Fraction of the visible length, from the scroll end, at which the
        mask first gets at least `frac` of its widest width: the top of the
        body. Measured rather than assumed, because a close or cropped shot
        shows only part of the cello and a fixed 38% put the graphics far
        down the visible body."""
        length = hi - lo
        if length <= 0:
            return None
        f = np.clip((hi - proj) / length, 0, 0.9999)      # 0 at the scroll end
        idx = (f * bins).astype(int)
        widths = np.zeros(bins)
        for b in range(bins):
            p = perp[idx == b]
            if len(p) >= 5:
                widths[b] = np.percentile(p, 95) - np.percentile(p, 5)
        if widths.max() <= 0:
            return None
        first = int(np.argmax(widths >= frac * widths.max()))
        return first / bins
