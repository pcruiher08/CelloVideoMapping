"""Web app: live cello segmentation with a selectable replacement image.

    .venv/bin/python -m cellomask.server                 # built-in camera
    .venv/bin/python -m cellomask.server --source brio   # by camera name
    .venv/bin/python -m cellomask.server --source clip.mp4
    .venv/bin/python -m cellomask.server --source lidar  # iPhone CelloDepth app

Open http://127.0.0.1:8000. /output is the clean composited feed for the
projector (fullscreen it on the second display, or capture the window in
Resolume/TouchDesigner).
"""

import argparse
import os
import re
import shutil
import threading
import time

import cv2
import numpy as np

from .cello3d import CelloPlane, front_face
from .composite import composite, debug_overlay, mask_roi, shape_alpha
from .iphone import IPHONE, depth_view
from .procam3d import Procam3D, correspondences, implausible3d, solve_projector, stable_depth
from .relocate import PhoneTracker
from .projector import (Calibration, decode_gray, detect, fit, fit_dense, gray_bits, implausible,
                        gray_pattern, marker_pattern, test_grid)
from .segment import AxisTracker, MaskSmoother, Segmenter

TUNER = "live:tuner"         # replacement name of the live tuner graph

ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
REPL_DIR = os.path.join(ROOT, "data", "replacements")
SRC_DIR = os.path.join(ROOT, "data", "sources")
THUMB_DIR = os.path.join(ROOT, "data", "thumbs")
STATIC = os.path.join(os.path.dirname(__file__), "static")

IMAGE_EXT = {".jpg", ".jpeg", ".png", ".webp", ".bmp"}
VIDEO_EXT = {".mp4", ".mov", ".m4v", ".avi", ".mkv", ".webm"}

DEFAULTS = {
    "mode": "warp",          # warp | fill | window
    "rotation": "follow",    # follow | upright (warp mode)
    "blend": "normal",       # normal | multiply | screen
    "feather": 6,            # px
    "grow": 0,               # px, negative shrinks
    "opacity": 1.0,
    "conf": 0.25,            # a backlit cello scores 0.3-0.6; stray hits elsewhere lose to the largest
    "smooth": 0.35,          # mask EMA weight of the newest frame while still (rises when moving)
    "instances": "largest",  # largest | all
    "matte": False,          # black out everything but the cello
    "flip": False,
    "a4": 440.0,             # tuner reference pitch
    "tuner_span": 50,        # cents shown either side of the note
    "tuner_seconds": 4.0,    # length of the pitch trace
    "tuner_layout": "horizontal",  # horizontal (time left->right) | vertical
    "tuner_pos": 0.2,        # in-tune line within the visible body: 0 = top, 1 = bottom
    "mapping": "3d",         # 3d (iPhone depth + 3D calibration, follows lean/turn) | flat
    "surface": "front",      # front (the body's top only, from depth) | whole (the full mask)
    "inset_mm": 6.0,         # front: edge pulled in so no light reaches the ribs
}


def safe_name(name):
    base, ext = os.path.splitext(os.path.basename(name))
    base = re.sub(r"[^A-Za-z0-9._-]+", "-", base).strip("-") or "file"
    return base[:60] + ext.lower()


def unique_path(folder, name):
    path = os.path.join(folder, name)
    base, ext = os.path.splitext(name)
    i = 2
    while os.path.exists(path):
        path = os.path.join(folder, f"{base}-{i}{ext}")
        i += 1
    return path


def kind_of(path):
    ext = os.path.splitext(path)[1].lower()
    return "image" if ext in IMAGE_EXT else "video" if ext in VIDEO_EXT else None


def make_thumb(path):
    os.makedirs(THUMB_DIR, exist_ok=True)
    out = os.path.join(THUMB_DIR, os.path.basename(path) + ".jpg")
    if os.path.exists(out):
        return out
    if kind_of(path) == "video":
        cap = cv2.VideoCapture(path)
        cap.set(cv2.CAP_PROP_POS_FRAMES, 10)
        ok, img = cap.read()
        cap.release()
        if not ok:
            return None
    else:
        img = cv2.imread(path)
        if img is None:
            return None
    h, w = img.shape[:2]
    s = 240 / max(h, w)
    cv2.imwrite(out, cv2.resize(img, (int(w * s), int(h * s)), interpolation=cv2.INTER_AREA))
    return out


def seed_media():
    """A test grid (shows whether the warp is upright) and a gradient as
    starter replacements, plus a few real cello photos as test sources so
    the app is usable before there is a camera setup."""
    os.makedirs(REPL_DIR, exist_ok=True)
    os.makedirs(SRC_DIR, exist_ok=True)
    grid = os.path.join(REPL_DIR, "test-grid.png")
    if not os.path.exists(grid):
        h, w = 1200, 600
        img = np.full((h, w, 3), 30, np.uint8)
        for i in range(0, w, 50):
            cv2.line(img, (i, 0), (i, h), (90, 90, 90), 1)
        for j in range(0, h, 50):
            cv2.line(img, (0, j), (w, j), (90, 90, 90), 1)
        for j in range(h):
            img[j, :, 2] = np.clip(img[j, :, 2] + 200 * (1 - j / h), 0, 255)
            img[j, :, 0] = np.clip(img[j, :, 0] + 200 * j / h, 0, 255)
        cv2.arrowedLine(img, (w // 2, h // 2), (w // 2, 120), (255, 255, 255), 14, tipLength=0.25)
        cv2.putText(img, "TOP", (w // 2 - 95, 90), cv2.FONT_HERSHEY_DUPLEX, 2.6, (255, 255, 255), 5)
        cv2.imwrite(grid, img)
    grad = os.path.join(REPL_DIR, "aurora.png")
    if not os.path.exists(grad):
        h, w = 1200, 800
        yy, xx = np.mgrid[0:h, 0:w].astype(np.float32)
        r = 127 + 127 * np.sin(xx / 140 + yy / 300)
        g = 127 + 127 * np.sin(yy / 180 + 2)
        b = 127 + 127 * np.sin((xx + yy) / 220 + 4)
        cv2.imwrite(grad, np.dstack([b, g, r]).astype(np.uint8))
    if not os.listdir(SRC_DIR):
        val = os.path.join(ROOT, "data", "seg", "val", "images")
        if os.path.isdir(val):
            for f in sorted(os.listdir(val))[:6]:
                shutil.copy(os.path.join(val, f), os.path.join(SRC_DIR, "sample-" + f.split("_")[0] + ".jpg"))


class Media:
    """A still image or a looping video, read one frame per tick."""

    def __init__(self, path):
        self.path = path
        self.name = os.path.basename(path)
        self.kind = kind_of(path)
        self.img = cv2.imread(path) if self.kind == "image" else None
        if self.img is not None and max(self.img.shape[:2]) > 1600:
            k = 1600 / max(self.img.shape[:2])
            self.img = cv2.resize(self.img, None, fx=k, fy=k, interpolation=cv2.INTER_AREA)
        self.cap = cv2.VideoCapture(path) if self.kind == "video" else None
        self.fps = (self.cap.get(cv2.CAP_PROP_FPS) or 30) if self.cap else None
        self._t = time.time()
        self._frame = None

    def frame(self, realtime=True):
        if self.img is not None:
            return self.img
        # play at the file's own rate, regardless of how fast we are pulling
        if realtime and self._frame is not None and time.time() - self._t < 1 / self.fps:
            return self._frame
        ok, f = self.cap.read()
        if not ok:
            self.cap.set(cv2.CAP_PROP_POS_FRAMES, 0)
            ok, f = self.cap.read()
        self._t = time.time()
        if ok:
            self._frame = f
        return self._frame

    def close(self):
        if self.cap:
            self.cap.release()


class TunerMedia:
    """The live tuner graph as a replacement 'image': rendered fresh every
    frame from the microphone. Portrait for warp/fill (it rides on the cello,
    note name at the scroll), landscape to match the frame for window mode."""

    kind = "live"
    path = None

    def __init__(self, pipe):
        self.pipe = pipe
        self.name = TUNER

    def frame(self, mode="warp", shape=None):
        s = self.pipe.settings
        if mode == "window" and shape is not None:
            h, w = shape[:2]
            return safe_render(self.pipe.tuner, (960, max(2, int(960 * h / w))), s)
        # on the cello: graph over the body, neck left empty. The texture
        # takes the visible cello's own proportions: the warp cover-fits it,
        # so a 1:3 texture on a close shot of just the (squarish) body lost
        # its top and bottom.
        axis = self.pipe.axis.last
        aspect = float(np.clip(axis[2] / max(axis[3], 1.0), 1.0, 4.0)) if axis else 3.0
        return safe_render(self.pipe.tuner, (450, int(450 * aspect)), s, cello=True,
                           body_start=self.pipe.axis.body_start)

    def close(self):
        pass


def safe_render(tuner, size, s, cello=False, body_start=0.38):
    """The tuner graph, or a plain error card if drawing fails: a bug in the
    graph must never stop the video loop (which would freeze every stream)."""
    from .tuner_viz import render, render_cello
    try:
        kw = dict(span=s["tuner_span"], seconds=s["tuner_seconds"],
                  layout=s["tuner_layout"])
        if cello:
            return render_cello(tuner.snapshot(), size, position=s["tuner_pos"],
                                body_start=body_start, **kw)
        return render(tuner.snapshot(), size, **kw)
    except Exception as e:
        print(f"tuner render: {e!r}")
        img = np.full((size[1], size[0], 3), 20, np.uint8)
        cv2.putText(img, "tuner error - see server log", (20, size[1] // 2),
                    cv2.FONT_HERSHEY_SIMPLEX, 0.8, (80, 90, 240), 2, cv2.LINE_AA)
        return img


LIDAR_NAME = "iPhone LiDAR (CelloDepth app)"
LIDAR_SPECS = ("lidar", "iphone-lidar", LIDAR_NAME.lower())


def open_camera(spec, width, height):
    from bowtrack.camera import configure, pick_builtin_index, pick_by_name
    if spec.lower() in LIDAR_SPECS:
        return IPHONE, LIDAR_NAME           # streamed in by the CelloDepth app
    if spec == "auto":
        idx, name = pick_builtin_index()
    elif spec.isdigit():
        idx, name = int(spec), f"camera {spec}"
    else:
        idx, name = pick_by_name(spec)
        if idx is None:
            raise ValueError(f"no camera matching {spec!r}")
    cap = cv2.VideoCapture(idx)
    if not cap.isOpened():
        raise ValueError(f"cannot open camera {idx}")
    configure(cap, width, height, fps=60)        # the Brio does 720p60 over MJPEG
    return FrameGrabber(cap), name or f"camera {idx}"


def largest_cello(inst, overlap=0.3):
    """The largest detection merged with the others that overlap it.
    The model often returns the same cello twice, once whole and once as
    just the body; taking only the larger one sometimes kept the body alone,
    whose shape says little about which way the cello leans."""
    base = inst[0]["mask"]
    keep = base > 0.5
    merged = base
    for d in inst[1:]:
        m = d["mask"] > 0.5
        if (m & keep).sum() > overlap * max(1, m.sum()):
            merged = np.maximum(merged, d["mask"])
    return merged


class FrameGrabber:
    """Reads the camera on its own thread and hands out the newest frame.

    cap.read() blocks until the next frame arrives, which serialised the
    camera with segmentation and rendering. Here the loop takes the latest
    frame as soon as it is free (waiting only if it has already processed
    that one), and frames it was too busy for are dropped, not queued, so
    the light never trails behind a backlog."""

    def __init__(self, cap):
        self.cap = cap
        self.frame = None
        self.seq = 0
        self.taken = 0
        self.cond = threading.Condition()
        self.running = True
        threading.Thread(target=self._run, daemon=True).start()

    def _run(self):
        while self.running:
            ok, frame = self.cap.read()
            if not ok:
                time.sleep(0.01)
                continue
            with self.cond:
                self.frame = frame
                self.seq += 1
                self.cond.notify_all()

    def read(self, timeout=1.0):
        with self.cond:
            self.cond.wait_for(lambda: self.seq != self.taken or not self.running, timeout)
            if self.frame is None or self.seq == self.taken:
                return False, None
            self.taken = self.seq
            return True, self.frame

    def release(self):
        self.running = False
        time.sleep(0.05)
        self.cap.release()


class Pipeline(threading.Thread):
    def __init__(self, args):
        super().__init__(daemon=True)
        self.args = args
        self.settings = dict(DEFAULTS)
        self.seg = Segmenter(args.model, imgsz=args.imgsz)
        self.smoother = MaskSmoother()
        self.axis = AxisTracker()
        self.lock = threading.Lock()
        self.cond = threading.Condition()
        self.seg_cond = threading.Condition()
        self.seg_out = None          # (frame, detections, settings) from stage 1
        self.jpeg = {"output": None, "debug": None, "tuner": None, "projector": None, "depth": None}
        self.viewers = {"output": 0, "debug": 0, "tuner": 0, "projector": 0, "depth": 0}      # open MJPEG streams
        self.polled = {"output": 0.0, "debug": 0.0, "tuner": 0.0, "projector": 0.0, "depth": 0.0}  # last /frame request
        # projection mapping: what the projector shows, in projector pixels
        self.calib = Calibration.load()
        self.procam = Procam3D.load()  # full 3D projector model (iPhone LiDAR calibration)
        self.phone = PhoneTracker()    # how the iPhone moved since that calibration
        self.procam_live = None        # procam corrected for that movement
        self.depth_pkt = None          # iPhone packet (depth, intrinsics) of the latest frame
        self.plane = CelloPlane()      # the cello's surface from that depth
        self.plane_t = 0.0             # when the plane was last fitted
        self.view3d = None             # (K, quad) used for the current frame, or None (flat)
        self.proj_meta = {}            # proj_seq -> phone frame times, for the latency readout
        self.lat = {}                  # Mac-side latency stages, smoothed (seconds)
        self.probe = None              # dict while a latency probe runs
        self.proj_size = tuple(args.proj_size)
        self.proj_mode = "content"   # content | white | outline | grid | black | pattern
        self.proj_frame = None       # BGR image for the native projector window
        self.proj_seq = 0
        self.projector_window = False
        self.pattern = None          # (image, corners) while calibrating
        self.raw_frame = None        # latest processed camera frame (what the mask is in)
        self.raw_seq = 0
        self.calibrating = None      # progress text while a calibration runs
        self.cam_noise = 2.0         # mean frame-to-frame grey change of a still image
        self.sync_log = []           # per-capture timing of the last calibration (calib_debug/sync.json)
        # what the camera saw while calibrating (tests point this elsewhere so
        # they never overwrite a real calibration's record)
        self.debug_dir = os.path.join(ROOT, "data", "calib_debug")
        self.min_wait = 0.0          # measured camera delay x 0.8 while calibrating (iPhone)
        self.tuner = None            # PitchTracker, opened on first use
        self.mic = None              # requested input device (None = default)
        self.seq = 0
        self.fps = 0.0
        self.n_instances = 0
        self.error = None
        self.camera = None
        self.source = None
        self.source_name = None
        self.replacement = None
        self.running = True
        try:
            self.set_source(args.source)
        except ValueError as e:      # e.g. the USB camera is unplugged
            if args.source == "auto":
                raise
            if getattr(args, "projector", None) is not None:
                # the calibration belongs to one camera: projecting through
                # another would put the light in the wrong place
                raise SystemExit(f"{e}. The projector calibration was made with that camera: "
                                 "plug it in (directly into the Mac) and start again.")
            print(f"warning: {e}; using the built-in camera instead")
            self.set_source("auto")
            self.error = f"{e}: using the built-in camera. Plug it in and restart."
        default = os.path.join(REPL_DIR, "test-grid.png")
        if os.path.exists(default):
            self.set_replacement(default)

    # --- control -----------------------------------------------------------

    def set_source(self, spec):
        with self.lock:
            if self.camera is not None:
                self.camera.release()
                self.camera = None
            if self.source is not None:
                self.source.close()
                self.source = None
            path = spec if os.path.isabs(spec) else os.path.join(SRC_DIR, spec)
            if os.path.isfile(path) and kind_of(path):
                self.source = Media(path)
                self.source_name = os.path.basename(path)
            else:
                self.camera, self.source_name = open_camera(spec, self.args.width, self.args.height)
            self.smoother.reset()
            self.axis.reset()
            self.error = None

    def ensure_tuner(self):
        """Open the microphone the first time the tuner is needed, so the
        OS permission prompt only appears for people who use it."""
        if self.tuner is None:
            from .audio import PitchTracker
            self.tuner = PitchTracker(a4=self.settings["a4"])
            self.tuner.start(self.mic)
        return self.tuner

    def set_mic(self, device):
        self.mic = device
        if self.tuner is not None:
            self.tuner.start(device)
        else:
            self.ensure_tuner()

    def set_replacement(self, path):
        if path == TUNER:
            self.ensure_tuner()
            media = TunerMedia(self)
        else:
            media = Media(path)
        with self.lock:
            if self.replacement is not None:
                self.replacement.close()
            self.replacement = media

    def update(self, values):
        with self.lock:
            for k, v in values.items():
                if k in DEFAULTS:
                    self.settings[k] = type(DEFAULTS[k])(v)
            self.smoother.alpha = self.settings["smooth"]
            self.axis.follow = self.settings["rotation"] == "follow"
            if self.tuner is not None:
                self.tuner.a4 = self.settings["a4"]

    # --- loop --------------------------------------------------------------

    def read(self):
        with self.lock:
            cam, src = self.camera, self.source
            if cam is None:
                return src.frame() if src else None
        ok, frame = cam.read()        # waits for a new frame: not under the lock
        return frame if ok else None

    def segment_loop(self):
        """Stage 1, on its own thread: newest camera frame -> detections.
        Segmentation (~25 ms on the GPU) overlaps with stage 2 drawing and
        warping the previous frame, so the frame rate is set by the slower
        of the two instead of their sum."""
        while self.running:
            frame = self.read()
            with self.lock:
                s = dict(self.settings)
            if frame is None:
                time.sleep(0.05)
                continue
            if self.source is not None and self.source.kind == "image":
                time.sleep(1 / 30)           # a still image: do not spin
            h, w = frame.shape[:2]
            if w > self.args.width:          # cap work at the processing width
                frame = cv2.resize(frame, (self.args.width, int(h * self.args.width / w)),
                                   interpolation=cv2.INTER_AREA)
            if s["flip"]:
                frame = cv2.flip(frame, 1)
            try:
                inst = self.seg(frame, conf=s["conf"])
            except Exception as e:           # keep streaming even if a frame fails
                self.error = repr(e)
                inst = []
            pkt = getattr(self.camera, "current", None)   # depth + intrinsics, iPhone only
            with self.seg_cond:
                self.seg_out = (frame, inst, s, pkt)
                self.seg_cond.notify_all()

    def relocate_loop(self, period=1.0):
        """About once a second: align the room's live depth (walls, floor,
        not the cello) to the depth saved at 3D calibration, so a phone
        nudged in its mount is cancelled out instead of throwing the light
        off (see relocate.py)."""
        while self.running:
            time.sleep(period)
            pc, pkt = self.procam, self.depth_pkt
            if pc is None or pkt is None or self.phone.ref is None or self.calibrating:
                continue
            mask = self.smoother.mask
            try:
                if self.phone.update(pkt, exclude=None if mask is None else mask > 0.5):
                    self.procam_live = pc.moved(self.phone.M)
            except Exception as e:           # never stop the show over this
                print(f"relocate: {e!r}")

    def run(self):
        """Stage 2: smoothing, orientation, the projector frame and the
        browser views, for each newly segmented frame."""
        threading.Thread(target=self.segment_loop, daemon=True).start()
        threading.Thread(target=self.relocate_loop, daemon=True).start()
        self.t_prev = time.time()
        while self.running:
            with self.seg_cond:
                self.seg_cond.wait_for(lambda: self.seg_out is not None or not self.running, 1.0)
                item, self.seg_out = self.seg_out, None
            if item is None:
                continue
            try:
                self.render(*item)
            except Exception as e:           # skip a bad frame, never stop the loop
                print(f"render: {e!r}")
                time.sleep(0.05)

    def render(self, frame, inst, s, pkt):
        """One segmented frame through to the projector and the views."""
        self.depth_pkt = pkt
        with self.lock:
            repl_media = self.replacement
        if isinstance(repl_media, TunerMedia):
            repl = repl_media.frame(s["mode"], frame.shape)
        else:
            with self.lock:
                repl = repl_media.frame() if repl_media else None

        self.n_instances = len(inst)
        raw = None
        if inst:
            raw = largest_cello(inst) if s["instances"] == "largest" else \
                np.max(np.stack([d["mask"] for d in inst]), 0)
        mask = self.smoother(raw, frame.shape[:2])
        now = time.time()
        axis = self.axis(mask, now) if mask is not None else None
        quad = self.update_3d(frame, mask, axis, pkt, s, now)
        # what gets light: the front face when depth allows, else the mask
        face = self.front_mask(mask, pkt, s)
        self.face = face
        self.raw_frame = frame
        self.raw_seq += 1
        if self.projector_window or self.watched("projector"):
            try:
                pf = self.render_projector(frame, face, axis, repl, s, quad)
            except Exception as e:       # never let the projector stop the loop
                print(f"projector: {e!r}")
                pf = np.zeros((self.proj_size[1], self.proj_size[0], 3), np.uint8)
            self.proj_frame = pf
            self.proj_seq += 1
            if pkt is not None and pkt.get("t_recv"):
                now2 = time.time()
                self._stage("wait", pkt["t_read"] - pkt["t_recv"])     # queued for segmentation
                self._stage("process", now2 - pkt["t_read"])           # segment + 3D + render
                self.proj_meta[self.proj_seq] = pkt.get("t_cap_mac")
                if len(self.proj_meta) > 64:
                    self.proj_meta.pop(next(iter(self.proj_meta)))

        # the output view is only composited and encoded while someone
        # watches it (projecting does not need it)
        jo = None
        if self.watched("output") or not self.projector_window:
            bg = np.zeros_like(frame) if s["matte"] else None
            out = composite(frame, face, repl, mode=s["mode"], axis=axis,
                            feather=s["feather"], grow=s["grow"],
                            opacity=s["opacity"], blend=s["blend"], background=bg, quad=quad)
            jo = cv2.imencode(".jpg", out, [cv2.IMWRITE_JPEG_QUALITY, 85])[1].tobytes()
        # the mask view is only drawn and encoded while someone watches it
        dbg = debug_overlay(frame, inst, mask, axis) if self.watched("debug") else None

        dt = now - self.t_prev
        self.t_prev = now
        self.fps = 0.9 * self.fps + 0.1 * (1 / dt if dt > 0 else 0)
        enc = [cv2.IMWRITE_JPEG_QUALITY, 85]
        jd = cv2.imencode(".jpg", dbg, enc)[1].tobytes() if dbg is not None else None
        jp = None
        if self.watched("projector") and self.proj_frame is not None:
            jp = cv2.imencode(".jpg", self.proj_frame, enc)[1].tobytes()
        jt = None
        if self.watched("tuner"):        # the graph on its own, landscape
            self.ensure_tuner()
            g = safe_render(self.tuner, (1280, 720), s)
            jt = cv2.imencode(".jpg", g, enc)[1].tobytes()
        jz = None
        if pkt is not None and self.watched("depth"):
            jz = cv2.imencode(".jpg", depth_view(pkt), enc)[1].tobytes()
        with self.cond:
            self.jpeg = {"output": jo, "debug": jd, "tuner": jt, "projector": jp, "depth": jz}
            self.seq += 1
            self.cond.notify_all()

    # --- projection mapping --------------------------------------------------

    def update_3d(self, frame, mask, axis, pkt, s, now):
        """Fit the cello's plane from this frame's depth; returns the image's
        perspective quad (warp mode), or None when 3D cannot be used (flat
        mapping chosen, no iPhone depth, no 3D calibration, or the phone was
        turned since calibrating). self.view3d keeps (K, quad) for the
        projector."""
        self.view3d = self._update_3d(frame, mask, axis, pkt, s, now)
        return None if self.view3d is None else self.view3d[1]

    def _update_3d(self, frame, mask, axis, pkt, s, now):
        # built whole and published in one assignment by update_3d: other
        # threads (the status API) read view3d at any moment
        pc = self.procam_live or self.procam
        if s["mapping"] != "3d" or pkt is None or pc is None or mask is None:
            return None
        h, w = frame.shape[:2]
        if pc.cam_size is not None and tuple(pc.cam_size) != (w, h):
            return None                  # calibrated in another orientation / size
        K = pkt["K"]
        if tuple(pkt["size"]) != (w, h):   # the frame was scaled down for processing
            K = K.copy()
            K[:2] *= w / pkt["size"][0]
        if self.plane(mask, pkt, now):
            self.plane_t = now
        if self.plane.n is None or now - self.plane_t > 2.0:
            return None                  # no depth on the cello for a while: flat for now
        quad = None
        if axis is not None and s["rotation"] == "follow":
            try:
                quad = self.plane.quad(axis, K)
            except (FloatingPointError, ValueError, ZeroDivisionError):
                quad = None
        return (K, quad)

    def front_mask(self, mask, pkt, s):
        """The front face of the cello (cello3d.front_face) as a soft mask,
        or the mask itself without 3D or with surface "whole"."""
        if mask is None or self.view3d is None or s["surface"] != "front":
            return mask
        try:
            face = front_face(mask, self.plane, self.view3d[0], pkt["depth"], pkt["conf"],
                              inset_mm=s["inset_mm"])
        except Exception as e:               # never let it blank the projection
            print(f"front face: {e!r}")
            return mask
        return np.where(face, mask, 0).astype(np.float32)

    def render_projector(self, frame, mask, axis, repl, s, quad=None):
        """The image the projector shows. Graphics are drawn in camera space
        inside the cello mask on black, then warped into projector space:
        by the cello's 3D plane and the 3D projector model when the iPhone's
        depth is there (right at any distance, lean and turn), else by the
        flat calibration."""
        w, h = self.proj_size
        mode = self.proj_mode
        if mode == "pattern" and self.pattern is not None:
            return self.pattern[0]
        if mode == "grid":
            return test_grid((w, h))
        black = np.zeros((h, w, 3), np.uint8)
        if mode == "black":
            return black
        if (self.calib is None or not self.calib.ok) and self.view3d is None:
            g = test_grid((w, h))
            cv2.putText(g, "NOT CALIBRATED - press Calibrate in the web page", (40, h // 2 - 20),
                        cv2.FONT_HERSHEY_SIMPLEX, 1.0, (60, 138, 224), 2, cv2.LINE_AA)
            return g
        if mask is None:
            return black
        roi = mask_roi(mask, 2 * s["feather"] + abs(s["grow"]) + 6)
        if roi is None:
            return black
        if mode == "white":                  # the mask as white light: alignment check
            x0, y0, x1, y1 = roi
            cam = np.zeros_like(frame)
            a = shape_alpha(mask[y0:y1, x0:x1], s["grow"], s["feather"], inward=True)
            cam[y0:y1, x0:x1] = (a * 255).astype(np.uint8)[..., None]
        elif mode == "outline":
            cam = np.zeros_like(frame)
            cnts, _ = cv2.findContours((mask > 0.5).astype(np.uint8), cv2.RETR_EXTERNAL,
                                       cv2.CHAIN_APPROX_NONE)
            cv2.drawContours(cam, cnts, -1, (255, 255, 255), 4, cv2.LINE_AA)
        else:                                # content: the replacement, black elsewhere
            cam = composite(frame, mask, repl, mode=s["mode"], axis=axis,
                            feather=s["feather"], grow=s["grow"], opacity=s["opacity"],
                            blend=s["blend"], background=np.zeros_like(frame), quad=quad,
                            inward=True)
        if self.view3d is not None:
            K = self.view3d[0]
            H = self.plane.homography(self.procam_live or self.procam, K, roi)
            if self.calib is not None:               # the Shift / Scale nudge still applies
                H = self.calib.nudge() @ H
            return Calibration(H, self.proj_size).warp(cam, roi)
        return self.calib.warp(cam, roi)

    def _next_gray(self, last, timeout=2.0):
        """(seq, grey image) of the first camera frame newer than `last`."""
        deadline = time.time() + timeout
        while self.raw_seq == last and time.time() < deadline:
            time.sleep(0.003)
        return self.raw_seq, cv2.cvtColor(self.raw_frame, cv2.COLOR_BGR2GRAY).astype(np.float32)

    def _show_and_grab(self, img, before, n=3, timeout=2.5, min_wait=0.0):
        """Project `img` and return the mean of `n` camera frames taken once
        the camera really shows it.

        A fixed wait was not enough: camera + projector latency (and the
        BRIO's auto exposure re-settling between bright and dark patterns)
        left some frames still showing the previous pattern, so bits were
        read wrong and the fit came out rotated. Here the frame must first
        change clearly from `before` (the previous pattern's capture), then
        hold still for two frames. `min_wait`: no change sooner than this can
        be the projector (the iPhone's image trails it by ~0.4 s, and its
        exposure drifting looked like an early change)."""
        self.pattern = (img, None)
        self.proj_mode = "pattern"
        min_wait = max(min_wait, self.min_wait)
        t0 = time.time()
        seq, prev = self._next_gray(self.raw_seq)
        changed = before is None
        # "still" means changing no more than the camera's own frame-to-frame
        # noise (a fixed threshold sat below it, so every pattern waited out
        # the full timeout)
        still = 1.6 * self.cam_noise + 0.5
        need = max(6.0, 3 * still)
        log = {"t_change": None, "t_settled": None, "need": round(need, 2),
               "diffs": [], "frames": 0}
        while time.time() - t0 < timeout:
            seq, g = self._next_gray(seq)
            log["frames"] += 1
            if not changed:
                if time.time() - t0 >= min_wait:     # too early to be the projector
                    d = float(np.abs(g - before).mean())
                    log["diffs"].append(round(d, 1))
                    changed = d > need
                    if changed:
                        log["t_change"] = round(time.time() - t0, 3)
            elif np.abs(g - prev).mean() < still:    # settled
                log["t_settled"] = round(time.time() - t0, 3)
                break
            prev = g
        acc = np.zeros_like(prev)
        for _ in range(n):
            seq, g = self._next_gray(seq)
            acc += g
        log["mean"] = round(float(acc.mean() / n), 1)
        self.sync_log.append(log)
        return acc / n

    def capture_stripes(self, drop_bits=3, rel_contrast=0.18, min_range=20, dbg=None, label=""):
        """Project the Gray-code sequence and decode it: for every camera
        pixel the projector column and row that light it. The caller sets
        proj_mode back and clears `calibrating` afterwards (try/finally).
        Returns px, py (float projector coords), valid, lit, white, black."""
        w, h = self.proj_size
        white_img = np.full((h, w, 3), 255, np.uint8)
        black_img = np.zeros((h, w, 3), np.uint8)
        self.calibrating = f"{label}measuring camera noise"
        seq, g1 = self._next_gray(self.raw_seq)
        seq, g2 = self._next_gray(seq)
        seq, g3 = self._next_gray(seq)
        self.cam_noise = float(min(np.abs(g1 - g2).mean(), np.abs(g2 - g3).mean()))
        self.sync_log = [{"cam_noise": round(self.cam_noise, 3)}]
        self.min_wait = 0.0
        locked, shown = False, None
        if self.camera is IPHONE:
            # expose for the projector's full white, then hold that exposure:
            # auto exposure changing between a pattern and its inverse flips
            # bits wherever daylight competes with the projector
            self.calibrating = f"{label}locking the iPhone exposure"
            # g3 is the projector-black view: wait for the white to really
            # arrive (with before=None a stale black frame was taken as the
            # white, and every later capture ended up one pattern behind)
            shown = self._show_and_grab(white_img, g3)
            latency = self.sync_log[-1]["t_change"]
            time.sleep(1.0)
            locked = IPHONE.lock(True)
            if not locked:
                print("warning: the iPhone did not lock its exposure (update the CelloDepth app)")
            # the reference is the white as seen with the locked exposure:
            # the one from before the lock had kept drifting with auto exposure
            seq, _ = self._next_gray(self.raw_seq)
            seq, _ = self._next_gray(seq)
            seq, shown = self._next_gray(seq)
            if latency:
                self.min_wait = 0.8 * latency
        try:
            return self._capture_stripes(w, h, white_img, black_img, drop_bits, rel_contrast,
                                         min_range, dbg, label, shown)
        finally:
            if locked:
                IPHONE.lock(False)

    def _capture_stripes(self, w, h, white_img, black_img, drop_bits, rel_contrast, min_range,
                         dbg, label, shown=None):
        self.calibrating = f"{label}white / black reference"
        # `shown`: what the camera saw last, when it was not black already (the
        # exposure-lock white): wait for the change, or black grabs stale white
        black = self._show_and_grab(black_img, shown)
        white = self._show_and_grab(white_img, black)
        if dbg:
            cv2.imwrite(os.path.join(dbg, "white.jpg"), white.astype(np.uint8))
            cv2.imwrite(os.path.join(dbg, "black.jpg"), black.astype(np.uint8))
        rng = white - black
        lit = rng >= min_range
        steps = sum(gray_bits(n) - drop_bits for n in (w, h))
        coords, done, last = [], 0, white
        for axis, n in ((0, w), (1, h)):
            nb = gray_bits(n)
            pairs = []
            for bit in range(nb - drop_bits):
                done += 1
                self.calibrating = f"{label}pattern {done}/{steps}"
                a = self._show_and_grab(gray_pattern((w, h), axis, bit), last)
                b = self._show_and_grab(gray_pattern((w, h), axis, bit, True), a)
                last = b
                pairs.append((a, b))
                if dbg and bit < 2:
                    cv2.imwrite(os.path.join(dbg, f"ax{axis}_bit{bit}.jpg"), a.astype(np.uint8))
            # contrast threshold per pixel, relative to its own white-black range
            thr = np.maximum(rel_contrast * rng, 4.0)
            pairs_i = [((p - q) > 0, np.abs(p - q) >= thr) for p, q in pairs]
            coords.append(self._decode(pairs_i, nb))
        (px, vx), (py, vy) = coords
        if dbg:
            import json
            with open(os.path.join(dbg, "sync.json"), "w") as f:
                json.dump(self.sync_log, f, indent=0)
        return {"px": px, "py": py, "valid": vx & vy & lit, "lit": lit,
                "white": white, "black": black}

    def calibrate_structured(self, drop_bits=3, rel_contrast=0.18, min_range=20):
        """Gray-code structured light: stripe patterns (each with its
        inverse) tell every camera pixel which projector pixel lights it, on
        whatever surface is there: the cello itself, no board needed, and
        robust to daylight and the wood's colour. Full-white and full-black
        frames say which pixels the projector reaches at all, and each bit
        must differ by a fraction of that pixel's own range. The homography
        is fit on the cello's pixels (its mask before the patterns started)
        when there are enough, so it matches the surface that matters."""
        prev_mode = self.proj_mode if self.proj_mode != "pattern" else "content"
        dbg = self.debug_dir
        os.makedirs(dbg, exist_ok=True)
        try:
            self.proj_mode = "black"
            self.calibrating = "reading the cello position"
            time.sleep(0.8)
            region = None if self.smoother.mask is None else self.smoother.mask > 0.5
            st = self.capture_stripes(drop_bits, rel_contrast, min_range, dbg)
        finally:
            self.proj_mode = prev_mode
            self.calibrating = None
        return self._apply_stripes(st, region, dbg)

    def _apply_stripes(self, st, region, dbg):
        """Fit and save the flat camera -> projector homography from decoded
        stripes, on the cello (`region`) when enough of it decoded."""
        px, py, valid, lit = st["px"], st["py"], st["valid"], st["lit"]
        w, h = self.proj_size
        H = err = None
        used, n_used = "the cello", 0
        if region is not None and (valid & region).sum() >= 3000:
            H, err, n_used = fit_dense(px, py, valid, region)
        if H is None or err is None or err > 8:
            used = "everything the projector lights"
            H, err, n_used = fit_dense(px, py, valid)
        hue = (np.clip(px / max(w, 1), 0, 1) * 170).astype(np.uint8)
        val = np.where(valid, 255, np.where(lit, 60, 0)).astype(np.uint8)
        vis = cv2.cvtColor(np.dstack([hue, np.full_like(hue, 255), val]), cv2.COLOR_HSV2BGR)
        if region is not None:
            cnts, _ = cv2.findContours(region.astype(np.uint8), cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
            cv2.drawContours(vis, cnts, -1, (255, 255, 255), 2)
        cv2.imwrite(os.path.join(dbg, "calibration_view.jpg"), vis)
        np.savez_compressed(os.path.join(dbg, "decoded.npz"), px=px, py=py, valid=valid,
                            lit=lit, region=np.zeros_like(valid) if region is None else region)
        cover = round(100 * float(valid.mean()), 1)
        on_cello = int((valid & region).sum()) if region is not None else 0
        if H is None:
            return {"ok": False, "markers": 0, "total": 0,
                    "message": f"could not read the stripes ({cover}% of the camera image "
                               "decoded). Is the projector lighting what the camera sees? Try a darker room."}
        why = implausible(H, px, py, valid & region if used == "the cello" else valid, self.proj_size)
        if why:
            return {"ok": False, "markers": 0, "total": 0,
                    "message": f"the stripes were too faint to read reliably ({why}); "
                               "the previous calibration is kept. Darken the room "
                               "(blinds, lights) and try again."}
        hh, ww = px.shape
        self.calib = Calibration(H, self.proj_size, (ww, hh), markers=n_used,
                                 error=round(err, 2), dx=0.0, dy=0.0, scale=1.0)
        self.calib.save()
        return {"ok": True, "markers": n_used, "total": 0, "error": round(err, 2),
                "message": f"calibrated by structured light on {used}: {n_used} pixels "
                           f"({on_cello} on the cello), mean error {err:.1f} px, "
                           f"{cover}% of the camera image decoded"}

    def calibrate_lidar(self, drop_bits=3, rel_contrast=0.18, min_range=20):
        """Full 3D projector calibration with the iPhone: the stripes give
        each camera pixel's projector pixel, the LiDAR its 3D position, and
        the projector is solved like a camera from those pairs (lens and
        pose relative to the phone; see procam3d.py). The flat cello
        homography is refit from the same stripes, so the current mapping
        keeps working with the phone as the camera."""
        if self.camera is not IPHONE or not IPHONE.live:
            return {"ok": False, "markers": 0, "total": 0,
                    "message": "the iPhone is not streaming: choose the iPhone LiDAR source "
                               "and press Connect in the CelloDepth app"}
        if self.settings["flip"]:
            return {"ok": False, "markers": 0, "total": 0,
                    "message": "turn Mirror off: the 3D calibration needs the camera's real image"}
        prev_mode = self.proj_mode if self.proj_mode != "pattern" else "content"
        dbg = self.debug_dir
        os.makedirs(dbg, exist_ok=True)
        try:
            self.proj_mode = "black"
            self.calibrating = "3D: measuring depth (keep everything still)"
            time.sleep(0.8)
            region = None if self.smoother.mask is None else self.smoother.mask > 0.5
            before = IPHONE.depth_frames(15)
            st = self.capture_stripes(drop_bits, rel_contrast, min_range, dbg, label="3D: ")
            self.proj_mode = "black"
            self.calibrating = "3D: checking nothing moved"
            after = IPHONE.depth_frames(8)
        finally:
            self.proj_mode = prev_mode
            self.calibrating = None

        def fail(msg):
            return {"ok": False, "markers": 0, "total": 0, "message": msg}

        if len(before) < 5 or len(after) < 3:
            return fail("the iPhone stopped streaming during the calibration")
        hh, ww = st["px"].shape
        if {p["orientation"] for p in before + after} != {before[0]["orientation"]} or \
                tuple(before[0]["size"]) != (ww, hh):
            return fail("the iPhone was turned during the calibration; mount it and try again")
        d0, d1 = stable_depth(before), stable_depth(after)
        both = np.isfinite(d0) & np.isfinite(d1)
        if both.sum() < 1000:
            return fail("the LiDAR depth is unreliable everywhere: is the scene within ~5 m?")
        # relative: LiDAR depth wanders by ~1% between readings on its own
        moved = float(np.median(np.abs(d0[both] - d1[both]) / d0[both]))
        if moved > 0.02:
            return fail(f"the scene or the phone moved during the calibration "
                        f"({100 * moved:.1f}% of the distance); keep everything still and try again")
        K = before[0]["K"]
        X, p = correspondences(st["px"], st["py"], st["valid"], d0, K)
        if len(X) < 2000:
            return fail(f"only {len(X)} points have both stripes and depth: is the projector "
                        "lighting what the phone sees, and the room dark enough?")
        z5, z95 = np.percentile(X[:, 2], [5, 95])
        if z95 - z5 < 0.15:
            return fail("everything lit is at about the same distance: a single flat surface "
                        "cannot calibrate the projector in 3D. Include the cello in front of "
                        "the wall, the floor, or a box")
        sol = solve_projector(X, p, self.proj_size)
        why = "the fit failed" if sol is None else implausible3d(sol, self.proj_size)
        np.savez_compressed(os.path.join(dbg, "lidar.npz"), X=X, p=p, depth=d0, K=K)
        if why:
            return fail(f"3D calibration rejected ({why}); the previous one is kept")
        self.procam = Procam3D(**sol, proj_size=self.proj_size, cam_K=K, cam_size=(ww, hh))
        self.procam.save()
        # the room as the phone saw it now: the reference for noticing it move
        self.phone.save_ref(d0, K, (ww, hh), before[0]["orientation"])
        self.procam_live = None
        flat = self._apply_stripes(st, region, dbg)
        return {"ok": True, "markers": sol["n"], "total": 0, "error": round(sol["rms"], 2),
                "message": f"3D calibration: {self.procam.summary()}. "
                           f"Flat mapping: {flat['message']}"}

    @staticmethod
    def _decode(pairs, nb):
        """Projector coordinate from per-bit (is_on, readable) masks, most
        significant first; the missing low bits are filled with their middle."""
        gray = np.zeros(pairs[0][0].shape, np.int32)
        valid = np.ones(pairs[0][0].shape, bool)
        for on, ok in pairs:
            valid &= ok
            gray = (gray << 1) | on
        binary, shift = gray.copy(), gray >> 1
        while shift.any():
            binary ^= shift
            shift >>= 1
        missing = nb - len(pairs)
        return (binary << missing).astype(np.float32) + ((1 << missing) - 1) / 2, valid

    def calibrate(self, settle=1.0, tries=20):
        """Project the marker grid, find it in camera frames, fit the
        camera -> projector homography and save it. A flat white board held
        where the cello will be gives the markers a surface to land on."""
        prev = self.proj_mode if self.proj_mode != "pattern" else "content"
        self.pattern = marker_pattern(self.proj_size)
        self.proj_mode = "pattern"
        try:
            time.sleep(settle)               # projector + camera latency, exposure settling
            best = (None, None, 0, None)
            last = self.raw_seq
            deadline = time.time() + 3.0
            while time.time() < deadline and tries > 0:
                if self.raw_seq == last:
                    time.sleep(0.01)
                    continue
                last = self.raw_seq
                frame = self.raw_frame
                tries -= 1
                cam, proj, n = detect(frame, self.pattern[1])
                if n > best[2]:
                    best = (cam, proj, n, frame)
                if n == len(self.pattern[1]):
                    break
        finally:
            self.proj_mode = prev
        cam, proj, n, frame = best
        total = len(self.pattern[1])
        view = frame.copy() if frame is not None else None
        if view is not None and cam is not None:
            for q in cam.reshape(-1, 4, 2):
                cv2.polylines(view, [q.astype(np.int32)], True, (0, 255, 0), 2, cv2.LINE_AA)
        if view is not None:
            os.makedirs(self.debug_dir, exist_ok=True)
            cv2.imwrite(os.path.join(self.debug_dir, "calibration_view.jpg"), view)
        if n < 4:
            return {"ok": False, "markers": n, "total": total,
                    "message": f"found {n} of {total} markers. Is the projector showing "
                               "the pattern on a flat light surface the camera can see?"}
        H, err = fit(cam, proj)
        if H is None:
            return {"ok": False, "markers": n, "total": total, "message": "could not fit the mapping"}
        old = self.calib
        h, w = frame.shape[:2]
        self.calib = Calibration(H, self.proj_size, (w, h), markers=n, error=round(err, 2),
                                 dx=0.0, dy=0.0, scale=1.0)
        self.calib.save()
        return {"ok": True, "markers": n, "total": total, "error": round(err, 2),
                "message": f"calibrated with {n}/{total} markers, mean error {err:.1f} px"
                           + ("" if old is None else " (nudge reset)")}

    def projector_state(self):
        c = self.calib
        return {"mode": self.proj_mode, "size": list(self.proj_size),
                "calibrating": self.calibrating,
                "window": self.projector_window,
                "calibrated": bool(c and c.ok),
                "markers": c.markers if c else 0, "error": c.error if c else None,
                "dx": c.dx if c else 0.0, "dy": c.dy if c else 0.0,
                "scale": c.scale if c else 1.0,
                "procam": self.procam.summary() if self.procam else None,
                "plane": self.plane_state(),
                "latency": self.latency_state(),
                "phone": self.phone_state(),
                "iphone": {"live": IPHONE.live, "fps": round(IPHONE.fps, 1),
                           "kb": None if IPHONE.kb is None else round(IPHONE.kb),
                           **IPHONE.diag,
                           "connections": IPHONE.connected, "error": IPHONE.error}}

    def _stage(self, name, value):
        old = self.lat.get(name)
        self.lat[name] = value if old is None else 0.9 * old + 0.1 * value

    def mark_drawn(self, seq, t, bright=None):
        """Called by the projector window when it has drawn frame `seq`."""
        cap = self.proj_meta.get(seq)
        if cap is not None:
            self._stage("capture_to_drawn", t - cap)
        p = self.probe
        if p is not None and bright is not None and p.get("drawn") is None and bright > 128:
            p["drawn"] = t

    def latency_state(self):
        ip = IPHONE.lat
        out = {k: round(1000 * v, 1) for k, v in {**ip, **self.lat}.items()}
        out["clock_rtt"] = round(1000 * IPHONE.rtt, 1) if IPHONE.rtt is not None else None
        return out

    def measure_spill(self, frames=5):
        """How well the light fits the cello: project the mask as white,
        compare with black, and measure in the camera where light landed
        against the mask. Spill is light outside the mask (on the sides, the
        wall), miss is mask left dark; distances in mm on the cello."""
        if self.smoother.mask is None or self.raw_frame is None:
            return {"ok": False, "message": "no cello in view"}
        mask = self.smoother.mask > 0.5
        face = mask if getattr(self, "face", None) is None else self.face > 0.5
        prev = self.proj_mode
        wait = max(0.6, 1.5 * self.min_wait)

        def grab(mode):
            self.proj_mode = mode
            time.sleep(wait)
            seq, acc = self.raw_seq, []
            for _ in range(frames):
                seq, g = self._next_gray(seq)
                acc.append(g)
            return np.mean(acc, 0)

        try:
            dark = grab("black")
            lit_img = grab("white")
            dark2 = grab("black")
        finally:
            self.proj_mode = prev
        diff = lit_img - (dark + dark2) / 2
        if mask.shape != diff.shape:
            return {"ok": False, "message": "the camera changed during the measurement"}
        inside = np.median(diff[mask])
        lit = diff > max(8.0, 0.3 * inside)
        lit = cv2.morphologyEx(lit.astype(np.uint8), cv2.MORPH_OPEN, np.ones((3, 3), np.uint8)) > 0
        # mm per camera pixel at the cello: its distance over the focal length
        pkt = self.depth_pkt
        mm = None
        if self.plane.C is not None and pkt is not None:
            f = pkt["K"][0, 0] * mask.shape[1] / pkt["size"][0]
            mm = 1000 * self.plane.C[2] / f
        out_d = cv2.distanceTransform((~mask).astype(np.uint8), cv2.DIST_L2, 5)
        in_d = cv2.distanceTransform(mask.astype(np.uint8), cv2.DIST_L2, 5)
        spill = lit & ~mask
        miss = mask & ~lit
        # light far from the cello is something else (a reflection, a person)
        near = out_d < 80
        spill &= near
        sd, md = out_d[spill], in_d[miss]
        to_mm = (lambda x: round(float(x) * mm, 1)) if mm else (lambda x: None)
        res = {
            "ok": True,
            "coverage": round(float((lit & mask).sum() / mask.sum()), 3),
            "face_coverage": round(float((lit & face).sum() / max(1, face.sum())), 3),
            "face_vs_mask": round(float(face.sum() / mask.sum()), 3),
            "spill_px": int(spill.sum()), "spill_vs_mask": round(float(spill.sum() / mask.sum()), 3),
            "spill_p50_mm": to_mm(np.median(sd)) if len(sd) else 0,
            "spill_p95_mm": to_mm(np.percentile(sd, 95)) if len(sd) else 0,
            "miss_p95_mm": to_mm(np.percentile(md, 95)) if len(md) else 0,
            "mm_per_px": None if mm is None else round(mm, 2),
            "contrast": round(float(inside), 1),
        }
        # spill in red, missed cello in blue, good light in green
        vis = cv2.cvtColor(np.clip(dark, 0, 255).astype(np.uint8), cv2.COLOR_GRAY2BGR) // 2
        vis[lit & mask] = (0, 200, 0)
        vis[spill] = (0, 0, 255)
        vis[miss] = (255, 80, 0)
        cnts, _ = cv2.findContours(mask.astype(np.uint8), cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_NONE)
        cv2.drawContours(vis, cnts, -1, (255, 255, 255), 1)
        os.makedirs(self.debug_dir, exist_ok=True)
        cv2.imwrite(os.path.join(self.debug_dir, "spill.jpg"), vis)
        np.savez_compressed(os.path.join(self.debug_dir, "spill.npz"), mask=mask, diff=diff, dark=dark)
        return res

    def latency_probe(self, rounds=3):
        """Flash the projector black -> white and find the first iPhone frame
        whose *capture* shows it: the projector's own delay (plus exposure),
        which no timestamp can see. Uses the phone clock sync."""
        if self.camera is not IPHONE or not IPHONE.live or IPHONE.offset is None:
            return {"ok": False, "message": "needs the iPhone streaming (and a moment for clock sync)"}
        prev = self.proj_mode
        w, h = self.proj_size
        black = np.zeros((h, w, 3), np.uint8)
        white = np.full((h, w, 3), 255, np.uint8)
        results = []
        try:
            for _ in range(rounds):
                self.pattern = (black, None)
                self.proj_mode = "pattern"
                time.sleep(1.0)
                self.probe = {"drawn": None}
                IPHONE.collect = []
                t_set = time.time()
                self.pattern = (white, None)
                time.sleep(1.2)
                frames, IPHONE.collect = IPHONE.collect, None
                drawn = self.probe["drawn"]
                self.probe = None
                lum = []
                for msg, hd in frames:
                    pkt = IPHONE._decode(msg)
                    if pkt is not None and hd.get("t_cap_mac") is not None:
                        lum.append((hd["t_cap_mac"], float(pkt["bgr"][::4, ::4].mean()), hd["t_recv"]))
                if len(lum) < 5 or drawn is None:
                    continue
                lo, hi = lum[0][1], max(v for _, v, _ in lum)
                if hi - lo < 3:
                    continue
                first = next(x for x in lum if x[1] > lo + 0.5 * (hi - lo))
                results.append({"render_to_drawn": drawn - t_set,
                                "projector_and_exposure": first[0] - drawn,
                                "capture_to_mac": first[2] - first[0],
                                "total_light_change_to_mac": first[2] - t_set})
        finally:
            self.probe = None
            IPHONE.collect = None
            self.pattern = None
            self.proj_mode = prev
        if not results:
            return {"ok": False, "message": "could not see the flash: is the projector lighting what the phone sees?"}
        med = {k: round(1000 * float(np.median([r[k] for r in results])), 1) for k in results[0]}
        return {"ok": True, "rounds": len(results), "ms": med}

    def phone_state(self):
        ph = self.phone
        if ph.ref is None:
            return {"reference": False}
        cm, deg = ph.moved or (0.0, 0.0)
        return {"reference": True, "tracking": ph.ok, "moved_cm": round(cm, 1),
                "moved_deg": round(deg, 2), "inliers": None if ph.inliers is None else round(ph.inliers, 2),
                "too_far": cm > 15 or deg > 10}

    def plane_state(self):
        if self.view3d is None or self.plane.n is None:
            return None
        lean, turn = self.plane.angles()
        return {"distance": round(float(np.linalg.norm(self.plane.C)), 3),
                "lean": round(lean, 1), "turn": round(turn, 1),
                "points": self.plane.points,
                "residual_mm": round(1000 * self.plane.residual, 1) if self.plane.residual else None}

    def watched(self, view):
        return self.viewers[view] > 0 or time.time() - self.polled[view] < 1.5

    def next_frame(self, view, after, timeout=1.0):
        """(seq, jpeg) of the first frame newer than `after`, waiting up to
        `timeout`. One short request per frame: unlike an MJPEG stream it does
        not hold a connection open, and browsers allow only 6 per server, so
        a few open tabs of MJPEG left new tabs completely blank."""
        self.polled[view] = time.time()
        with self.cond:
            self.cond.wait_for(lambda: self.seq > after and self.jpeg[view] is not None,
                               timeout=timeout)
            return self.seq, self.jpeg[view]

    def frames(self, view):
        """Generator of new JPEGs for one MJPEG client (OBS, Resolume, a
        plain <img>); the web UI uses next_frame() instead."""
        last = -1
        self.viewers[view] += 1
        try:
            while self.running:
                with self.cond:
                    self.cond.wait_for(lambda: self.seq != last, timeout=1.0)
                    if self.seq == last:
                        continue
                    last = self.seq
                    data = self.jpeg[view]
                if data:
                    yield (b"--frame\r\nContent-Type: image/jpeg\r\n"
                           b"Content-Length: " + str(len(data)).encode() + b"\r\n\r\n" + data + b"\r\n")
        finally:
            self.viewers[view] -= 1


def list_media(folder):
    items = []
    for f in sorted(os.listdir(folder)):
        p = os.path.join(folder, f)
        if os.path.isfile(p) and kind_of(p):
            make_thumb(p)
            items.append({"name": f, "kind": kind_of(p)})
    return items


def build_app(pipe):
    from fastapi import Body, FastAPI, File, HTTPException, UploadFile, WebSocket, WebSocketDisconnect
    from fastapi.responses import FileResponse, StreamingResponse

    app = FastAPI(title="Cello replace")

    @app.get("/")
    def index():
        return FileResponse(os.path.join(STATIC, "index.html"))

    @app.get("/output")
    def output_page():
        return FileResponse(os.path.join(STATIC, "output.html"))

    @app.get("/stream/{view}.mjpg")
    def stream(view: str):
        if view not in pipe.jpeg:
            raise HTTPException(404)
        return StreamingResponse(pipe.frames(view),
                                 media_type="multipart/x-mixed-replace; boundary=frame")

    @app.get("/frame/{view}.jpg")
    def frame(view: str, after: int = -1):
        from fastapi import Response
        if view not in pipe.jpeg:
            raise HTTPException(404)
        seq, data = pipe.next_frame(view, after)
        if data is None:
            return Response(status_code=204, headers={"X-Seq": str(seq)})
        return Response(data, media_type="image/jpeg",
                        headers={"X-Seq": str(seq), "Cache-Control": "no-store"})

    @app.get("/api/state")
    def state():
        from bowtrack.camera import list_cameras
        return {
            "settings": pipe.settings,
            "model": pipe.seg.name,
            "open_vocab": pipe.seg.open_vocab,
            "device": pipe.seg.device,
            "fps": round(pipe.fps, 1),
            "seg_ms": round(pipe.seg.last_ms, 1),
            "instances": pipe.n_instances,
            "source": pipe.source_name,
            "replacement": pipe.replacement.name if pipe.replacement else None,
            "cameras": (list_cameras() or []) + [LIDAR_NAME],
            "replacements": list_media(REPL_DIR),
            "sources": list_media(SRC_DIR),
            "error": pipe.error,
            "tuner": tuner_state(pipe),
            "projector": pipe.projector_state(),
        }

    def tuner_state(pipe):
        if pipe.tuner is None:
            return None
        snap = pipe.tuner.snapshot()
        v = snap["vibrato"]
        return {
            "note": snap["note"],
            "cents": None if snap["cents"] is None else round(snap["cents"], 1),
            "freq": None if snap["freq"] is None else round(snap["freq"], 1),
            "vibrato": None if not (v and v.get("present")) else
                {"rate": round(v["rate"], 2), "extent": round(v["extent"], 1)},
            "level": round(snap["level"], 1),
            "gate": round(snap["gate"], 1),
            "mic": snap["device"],
            "error": snap["error"],
        }

    @app.get("/api/projector")
    def projector():
        return pipe.projector_state()

    @app.post("/api/projector")
    def projector_set(body: dict = Body(...)):
        mode = body.get("mode")
        if mode in ("content", "white", "outline", "grid", "black"):
            pipe.proj_mode = mode
        c = pipe.calib
        if c is not None and any(k in body for k in ("dx", "dy", "scale")):
            c.dx = float(body.get("dx", c.dx))
            c.dy = float(body.get("dy", c.dy))
            c.scale = float(body.get("scale", c.scale))
            c.save()
        return pipe.projector_state()

    calib_lock = threading.Lock()

    @app.post("/api/projector/calibrate")
    def projector_calibrate(body: dict = Body(default={})):
        if not calib_lock.acquire(blocking=False):
            raise HTTPException(409, "a calibration is already running")
        try:
            if body.get("method") == "markers":
                return pipe.calibrate()
            if body.get("method") == "lidar":
                return pipe.calibrate_lidar()
            return pipe.calibrate_structured()
        finally:
            calib_lock.release()

    @app.websocket("/ws/iphone")
    async def ws_iphone(ws: WebSocket):
        """The CelloDepth app streams its frames here (see cellomask/iphone.py)."""
        import asyncio
        await ws.accept()
        IPHONE.connected += 1
        IPHONE.outbox.clear()

        async def send_commands():               # exposure lock / unlock, clock pings
            last_ping = 0.0
            while True:
                if time.time() - last_ping > (0.2 if len(IPHONE.syncs) < 10 else 2.0):
                    IPHONE.ping()
                    last_ping = time.time()
                while IPHONE.outbox:
                    await ws.send_text(IPHONE.outbox.pop(0))
                await asyncio.sleep(0.02)

        sender = asyncio.create_task(send_commands())
        try:
            while True:
                msg = await ws.receive()
                if msg["type"] == "websocket.disconnect":
                    break
                if msg.get("bytes") is not None:
                    IPHONE.push(msg["bytes"])           # only stored: decoded when used
                elif msg.get("text"):
                    IPHONE.pong(msg["text"])
        except WebSocketDisconnect:
            pass
        finally:
            sender.cancel()
            IPHONE.connected -= 1

    @app.post("/api/debug/spill")
    def spill():
        with calib_lock:
            return pipe.measure_spill()

    @app.post("/api/debug/latency")
    def latency_probe():
        if not calib_lock.acquire(blocking=False):
            raise HTTPException(409, "a calibration is running")
        try:
            return pipe.latency_probe()
        finally:
            calib_lock.release()

    @app.post("/api/debug/dump3d")
    def dump3d():
        """Save the current frame, mask and iPhone depth packet for offline
        analysis (data/calib_debug/dump3d_<time>.npz)."""
        pkt, mask, frame = pipe.depth_pkt, pipe.smoother.mask, pipe.raw_frame
        if pkt is None or frame is None:
            raise HTTPException(409, "no iPhone frame")
        path = os.path.join(pipe.debug_dir, f"dump3d_{time.time():.2f}.npz")
        np.savez_compressed(path, frame=frame, mask=np.zeros(frame.shape[:2]) if mask is None else mask,
                            depth=pkt["depth"], conf=pkt["conf"], K=pkt["K"])
        return {"path": path}

    @app.get("/api/projector/view.jpg")
    def projector_view():
        path = os.path.join(pipe.debug_dir, "calibration_view.jpg")
        if not os.path.isfile(path):
            raise HTTPException(404)
        return FileResponse(path, headers={"Cache-Control": "no-store"})

    @app.get("/api/tuner")
    def tuner():
        return tuner_state(pipe)

    @app.get("/api/mics")
    def mics():
        from .audio import PitchTracker
        return {"mics": PitchTracker.input_devices(), "current": pipe.mic}

    @app.post("/api/mic")
    def choose_mic(body: dict = Body(...)):
        dev = body.get("device")
        dev = None if dev in (None, "", "default") else int(dev)
        pipe.set_mic(dev)
        return tuner_state(pipe)

    @app.post("/api/settings")
    def settings(values: dict = Body(...)):
        pipe.update(values)
        return pipe.settings

    def save_upload(file, folder):
        name = safe_name(file.filename or "upload")
        if not kind_of(name):
            raise HTTPException(400, "unsupported file type")
        path = unique_path(folder, name)
        with open(path, "wb") as f:
            shutil.copyfileobj(file.file, f)
        if make_thumb(path) is None:
            os.remove(path)
            raise HTTPException(400, "could not read that file")
        return path

    @app.post("/api/replacements")
    def upload_replacement(file: UploadFile = File(...)):
        path = save_upload(file, REPL_DIR)
        pipe.set_replacement(path)
        return {"name": os.path.basename(path)}

    @app.post("/api/replacement")
    def choose_replacement(body: dict = Body(...)):
        if body.get("name") == TUNER:
            pipe.set_replacement(TUNER)
            return {"name": TUNER}
        path = os.path.join(REPL_DIR, os.path.basename(body.get("name", "")))
        if not os.path.isfile(path):
            raise HTTPException(404)
        pipe.set_replacement(path)
        return {"name": os.path.basename(path)}

    @app.delete("/api/replacements/{name}")
    def delete_replacement(name: str):
        path = os.path.join(REPL_DIR, os.path.basename(name))
        if not os.path.isfile(path):
            raise HTTPException(404)
        if pipe.replacement and pipe.replacement.path == path:
            raise HTTPException(409, "that image is in use")
        os.remove(path)
        thumb = os.path.join(THUMB_DIR, os.path.basename(path) + ".jpg")
        if os.path.exists(thumb):
            os.remove(thumb)
        return {"ok": True}

    @app.post("/api/sources")
    def upload_source(file: UploadFile = File(...)):
        path = save_upload(file, SRC_DIR)
        pipe.set_source(path)
        return {"name": os.path.basename(path)}

    @app.post("/api/source")
    def choose_source(body: dict = Body(...)):
        # a file name inside data/sources, or a camera spec — never a path
        spec = str(body.get("spec", "auto"))
        if "/" in spec or "\\" in spec:
            raise HTTPException(400, "give a file name, not a path")
        try:
            pipe.set_source(spec)
        except ValueError as e:
            raise HTTPException(400, str(e))
        return {"source": pipe.source_name}

    @app.get("/thumbs/{name}")
    def thumb(name: str):
        path = os.path.join(THUMB_DIR, os.path.basename(name))
        if not os.path.isfile(path):
            raise HTTPException(404)
        return FileResponse(path)

    return app


def main(argv=None):
    p = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    p.add_argument("--source", default="auto",
                   help="'auto' (built-in camera), camera index, part of a "
                        "camera name, or an image/video path")
    p.add_argument("--model", default=None,
                   help="YOLO-seg weights (default models/cello-seg.pt, else YOLOE)")
    p.add_argument("--imgsz", type=int, default=512,
                   help="inference size; cello-seg.pt was trained at 512")
    p.add_argument("--width", type=int, default=1280)
    p.add_argument("--height", type=int, default=720)
    p.add_argument("--host", default="127.0.0.1")
    p.add_argument("--port", type=int, default=8000)
    p.add_argument("--projector", nargs="?", const="auto", default=None,
                   help="open the projector window: 'auto' (the last screen, i.e. "
                        "the extended projector display) or a screen index")
    p.add_argument("--windowed", action="store_true",
                   help="projector window in a normal window instead of fullscreen")
    p.add_argument("--proj-size", type=int, nargs=2, default=[1280, 800],
                   metavar=("W", "H"), help="projector resolution when no window "
                   "is open (the window uses its screen's size)")
    args = p.parse_args(argv)

    seed_media()
    pipe = Pipeline(args)
    print(f"model {pipe.seg.name} on {pipe.seg.device}; source {pipe.source_name}")
    print(f"open http://{args.host}:{args.port}  (projector feed: /output)")

    import uvicorn
    # MJPEG streams never end on their own, so without a timeout a stopped
    # server waits for them forever, keeps its connections and goes on
    # blocking the browser's 6-per-server limit
    config = uvicorn.Config(build_app(pipe), host=args.host, port=args.port,
                            log_level="warning", timeout_graceful_shutdown=2)
    server = uvicorn.Server(config)

    if args.projector is None:
        pipe.start()
        server.run()
        return

    # The projector window needs the main thread (macOS GUI rule), so the
    # web server runs in a thread instead.
    from .projector_window import open_window, run_window
    win = open_window(pipe, args.projector, fullscreen=not args.windowed)
    pipe.start()
    threading.Thread(target=server.run, daemon=True).start()
    run_window(pipe, win)
    server.should_exit = True


if __name__ == "__main__":
    main()
