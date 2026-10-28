"""Video from TouchDesigner (or any app) as the image on the cello, and the
cello's state out to it over OSC.

- NDI: from another computer on the network (TouchDesigner: NDI Out TOP).
  Use wired Ethernet; Wi-Fi drops and delays frames.
- Syphon: from another app on this Mac (TouchDesigner: Syphon Spout Out
  TOP); shared on the GPU, no compression.
- OSC out: where the cello is and what is being played, every frame, so
  the visuals can follow the cello and the music (see OscOut).

The live media behave like a replacement image: frame() returns the newest
frame received (BGR), from a thread of its own, so a slow or stalled sender
never holds up the projection.
"""

import threading
import time

import cv2
import numpy as np

NDI_PREFIX = "ndi:"
SYPHON_PREFIX = "syphon:"
MAX_SIDE = 1600          # like still images: bigger only costs time


def _fit(img):
    if max(img.shape[:2]) > MAX_SIDE:
        k = MAX_SIDE / max(img.shape[:2])
        img = cv2.resize(img, None, fx=k, fy=k, interpolation=cv2.INTER_AREA)
    return img


def waiting_card(text, size=(540, 960)):
    """What the cello shows until the first frame arrives."""
    w, h = size
    img = np.full((h, w, 3), 18, np.uint8)
    for i, line in enumerate(text.split("\n")):
        cv2.putText(img, line, (24, h // 2 + 36 * i), cv2.FONT_HERSHEY_SIMPLEX, 0.9,
                    (90, 170, 230), 2, cv2.LINE_AA)
    return img


class LiveMedia:
    """A replacement fed by a receiving thread; subclasses implement _run()."""

    kind = "live"
    path = None

    def __init__(self, name, label):
        self.name = name              # the gallery name, e.g. "ndi:STUDIO (cello)"
        self.label = label
        self.latest = None
        self.frames = 0
        self.fps = 0.0
        self.size = None
        self.error = None
        self.running = True
        self._t = None
        self.thread = threading.Thread(target=self._guard, daemon=True)
        self.thread.start()

    def _got(self, bgr):
        now = time.time()
        if self._t is not None:
            self.fps = 0.9 * self.fps + 0.1 / max(now - self._t, 1e-3)
        self._t = now
        self.size = (bgr.shape[1], bgr.shape[0])
        self.latest = _fit(bgr)
        self.frames += 1

    def _guard(self):
        while self.running:
            try:
                self._run()
            except Exception as e:          # keep retrying: the sender may come back
                self.error = repr(e)
                print(f"{self.label}: {e!r}")
                time.sleep(1.0)

    def frame(self, *_, **__):
        if self.latest is None:
            return waiting_card(f"waiting for\n{self.label}" + (f"\n{self.error[:40]}" if self.error else ""))
        return self.latest

    @property
    def live(self):
        return self._t is not None and time.time() - self._t < 1.0

    def state(self):
        return {"name": self.name, "live": self.live, "fps": round(self.fps, 1),
                "size": self.size, "error": self.error}

    def close(self):
        self.running = False


# --- NDI -------------------------------------------------------------------

_finder = None
_finder_lock = threading.Lock()


def ndi_sources(wait=0.0):
    """Names of the NDI sources on the network ("HOST (stream)")."""
    global _finder
    try:
        from cyndilib.finder import Finder
    except ImportError:
        return []
    with _finder_lock:
        if _finder is None:
            _finder = Finder()
            _finder.open()
            wait = max(wait, 1.0)           # the first discovery takes a moment
        if wait:
            _finder.wait_for_sources(wait)
        return list(_finder.update_sources())


class NDIMedia(LiveMedia):
    def __init__(self, source):
        self.source = source              # before the thread starts
        super().__init__(NDI_PREFIX + source, f"NDI {source}")

    def _run(self):
        from cyndilib.receiver import Receiver
        from cyndilib.video_frame import VideoFrameSync
        from cyndilib.wrapper.ndi_recv import RecvBandwidth, RecvColorFormat

        ndi_sources()
        src = None
        while self.running and src is None:
            with _finder_lock:
                if self.source in _finder.update_sources():
                    src = _finder.get_source(self.source)
            if src is None:
                self.error = "not on the network (yet)"
                time.sleep(1.0)
        if not self.running:
            return
        rx = Receiver(color_format=RecvColorFormat.BGRX_BGRA, bandwidth=RecvBandwidth.highest,
                      recv_name="cellomask")
        vf = VideoFrameSync()
        rx.frame_sync.set_video_frame(vf)
        rx.set_source(src)
        self.error = None
        last = None
        try:
            while self.running:
                # frame sync: always the newest frame, never a growing queue
                rx.frame_sync.capture_video()
                w, h = vf.xres, vf.yres
                ts = vf.get_timestamp_posix()
                if w and h and ts != last:
                    last = ts
                    a = np.asarray(vf.get_array(), np.uint8)
                    stride = vf.get_line_stride() or w * 4
                    img = a[: h * stride].reshape(h, stride)[:, : w * 4].reshape(h, w, 4)
                    self._got(np.ascontiguousarray(img[..., :3]))
                time.sleep(0.004)
        finally:
            rx.disconnect()


# --- Syphon ----------------------------------------------------------------

def syphon_sources():
    """Names of the Syphon servers on this Mac ("App / Server")."""
    try:
        import syphon
    except ImportError:
        return []
    d = syphon.SyphonServerDirectory()
    d.run_loop_interval = 0.05
    try:
        return [f"{s.app_name} / {s.name}" if s.name else s.app_name for s in d.servers]
    finally:
        d.close()


class SyphonMedia(LiveMedia):
    def __init__(self, source):
        self.source = source              # before the thread starts
        super().__init__(SYPHON_PREFIX + source, f"Syphon {source}")

    def _run(self):
        import Metal
        import syphon
        from syphon.utils.numpy import copy_mtl_texture_to_image

        d = syphon.SyphonServerDirectory()
        d.run_loop_interval = 0.05
        desc = None
        while self.running and desc is None:
            for s in d.servers:
                if (f"{s.app_name} / {s.name}" if s.name else s.app_name) == self.source:
                    desc = s
            if desc is None:
                self.error = "not running (yet)"
                time.sleep(1.0)
        if not self.running:
            return
        client = syphon.SyphonMetalClient(desc)
        self.error = None
        try:
            while self.running and client.is_valid:
                if client.has_new_frame:
                    tex = client.new_frame_image
                    img = copy_mtl_texture_to_image(tex)
                    if tex.pixelFormat() == Metal.MTLPixelFormatRGBA8Unorm:
                        bgr = cv2.cvtColor(img, cv2.COLOR_RGBA2BGR)
                    else:
                        bgr = np.ascontiguousarray(img[..., :3])
                    self._got(bgr)
                else:
                    d.update_run_loop()          # lets the client hear about frames
        finally:
            client.stop()
            d.close()


def open_live(name):
    """The live media for a gallery name, or None if it is not one."""
    if name.startswith(NDI_PREFIX):
        return NDIMedia(name[len(NDI_PREFIX):])
    if name.startswith(SYPHON_PREFIX):
        return SyphonMedia(name[len(SYPHON_PREFIX):])
    return None


# --- OSC out ---------------------------------------------------------------

class OscOut:
    """The cello's state to TouchDesigner (OSC In CHOP / DAT), every frame.

    Addresses (all floats unless noted):
      /cello/present        1 when the cello is tracked, else 0
      /cello/x, /cello/y    centre in the camera image, 0-1 (left/top = 0)
      /cello/angle          tilt in the image, degrees from upright (+ = top right)
      /cello/size           length in the image, 0-1 of the image height
      /cello/distance       metres from the camera (3D mapping)
      /cello/lean, /cello/turn   degrees (3D: + = top away / right side away)
      /cello/covered        0-1 of the cello hidden (hands, bow)
      /tuner/freq           Hz (0 when no note)
      /tuner/note           string, e.g. "A3"
      /tuner/cents          -50..50 off the note
      /tuner/level          dB
      /vibrato/rate, /vibrato/extent   Hz, cents (0 without vibrato)
    """

    def __init__(self):
        self.client = None
        self.target = None
        self.sent = 0
        self.error = None

    def set_target(self, host, port):
        if not host:
            self.client, self.target = None, None
            return
        if (host, port) == self.target:
            return
        from pythonosc.udp_client import SimpleUDPClient
        try:
            self.client = SimpleUDPClient(host, int(port))
            self.target = (host, int(port))
            self.error = None
        except Exception as e:
            self.client, self.target, self.error = None, None, repr(e)

    def send(self, pipe, frame_shape, axis, tuner_snap):
        c = self.client
        if c is None:
            return
        h, w = frame_shape[:2]
        try:
            c.send_message("/cello/present", 1.0 if axis is not None else 0.0)
            if axis is not None:
                cx, cy, length, width, up = axis
                c.send_message("/cello/x", float(cx / w))
                c.send_message("/cello/y", float(cy / h))
                c.send_message("/cello/angle", float(np.degrees(up + np.pi / 2)))
                c.send_message("/cello/size", float(length / h))
            pl = pipe.plane_state()
            if pl:
                c.send_message("/cello/distance", float(pl["distance"]))
                c.send_message("/cello/lean", float(pl["lean"]))
                c.send_message("/cello/turn", float(pl["turn"]))
            c.send_message("/cello/covered", float(pipe.covered))
            if tuner_snap is not None:
                c.send_message("/tuner/freq", float(tuner_snap["freq"] or 0.0))
                c.send_message("/tuner/note", tuner_snap["note"] or "")
                c.send_message("/tuner/cents", float(tuner_snap["cents"] or 0.0))
                c.send_message("/tuner/level", float(tuner_snap["level"]))
                v = tuner_snap.get("vibrato") or {}
                on = bool(v.get("present"))
                c.send_message("/vibrato/rate", float(v.get("rate", 0.0)) if on else 0.0)
                c.send_message("/vibrato/extent", float(v.get("extent", 0.0)) if on else 0.0)
            self.sent += 1
        except Exception as e:                # a bad address must not stop the show
            self.error = repr(e)
