"""iPhone LiDAR source: colour + depth streamed by the CelloDepth app.

The app (ios/CelloDepth) sends one WebSocket message per ARKit frame:
"CDP1", a little-endian UInt32 header length, a JSON header, then the JPEG,
the depth map (Float16 metres) and its confidence (UInt8: 0 low, 1 medium,
2 high). The intrinsics in the header are for the JPEG.

ARKit's image is always in the sensor's landscape orientation; it is turned
upright here from the phone's orientation, together with the depth and the
intrinsics, so the rest of the app sees an ordinary upright camera that also
knows how far away each pixel is.
"""

import json
import struct
import threading
import time

import cv2
import numpy as np

# turns the sensor image upright for each device orientation (the sensor's
# native landscape is the phone held with the USB port to the right)
ROTATE = {"landscapeLeft": None, "portrait": cv2.ROTATE_90_CLOCKWISE,
          "landscapeRight": cv2.ROTATE_180, "portraitUpsideDown": cv2.ROTATE_90_COUNTERCLOCKWISE}


def rotate_K(K, size, code):
    """Intrinsics after cv2.rotate(img, code) of an image of `size` (w, h)."""
    w, h = size
    fx, fy, cx, cy = K[0, 0], K[1, 1], K[0, 2], K[1, 2]
    if code is None:
        return K.copy(), (w, h)
    if code == cv2.ROTATE_180:
        return np.array([[fx, 0, w - 1 - cx], [0, fy, h - 1 - cy], [0, 0, 1]]), (w, h)
    if code == cv2.ROTATE_90_CLOCKWISE:            # (u, v) -> (h - 1 - v, u)
        return np.array([[fy, 0, h - 1 - cy], [0, fx, cx], [0, 0, 1]]), (h, w)
    return np.array([[fy, 0, cy], [0, fx, w - 1 - cx], [0, 0, 1]]), (h, w)   # CCW: (v, w - 1 - u)


def parse(msg):
    """One message -> dict(bgr, depth, conf, K, size, ts, orientation), upright."""
    if msg[:4] != b"CDP1":
        raise ValueError("not a CelloDepth frame")
    (n,) = struct.unpack("<I", msg[4:8])
    hd = json.loads(msg[8:8 + n])
    o = 8 + n
    jpeg = np.frombuffer(msg[o:o + hd["jpeg"]], np.uint8)
    o += hd["jpeg"]
    depth = np.frombuffer(msg[o:o + hd["depth"]], np.float16).reshape(hd["dh"], hd["dw"]).astype(np.float32)
    o += hd["depth"]
    conf = None
    if hd.get("conf"):
        conf = np.frombuffer(msg[o:o + hd["conf"]], np.uint8).reshape(hd["dh"], hd["dw"])
    bgr = cv2.imdecode(jpeg, cv2.IMREAD_COLOR)
    K = np.array([[hd["fx"], 0, hd["cx"]], [0, hd["fy"], hd["cy"]], [0, 0, 1]], np.float64)
    code = ROTATE.get(hd.get("orientation"), None)
    K, size = rotate_K(K, (bgr.shape[1], bgr.shape[0]), code)
    if code is not None:
        bgr = cv2.rotate(bgr, code)
        depth = cv2.rotate(depth, code)
        conf = None if conf is None else cv2.rotate(conf, code)
    return {"bgr": bgr, "depth": depth, "conf": conf, "K": K, "size": size,
            "ts": hd.get("ts", 0.0), "orientation": hd.get("orientation"),
            "locked": hd.get("locked")}


def header(msg):
    """Just the JSON header of a message (cheap: no image decoding)."""
    if msg[:4] != b"CDP1":
        raise ValueError("not a CelloDepth frame")
    (n,) = struct.unpack("<I", msg[4:8])
    return json.loads(msg[8:8 + n])


class IPhoneSource:
    """Camera-like source fed by the WebSocket endpoint. read() hands out the
    newest colour frame like FrameGrabber; `current` is the whole packet the
    last read frame came from (its depth and intrinsics).

    Messages are kept as received and decoded only when used: the phone
    sends ~40 frames a second, the pipeline takes ~15-30, and decoding every
    one (JPEG, depth, rotation) cost a CPU core that segmentation needed."""

    def __init__(self):
        self.cond = threading.Condition()
        self.raw = None             # newest message, undecoded
        self.raw_header = None
        self.current = None
        self.seq = 0
        self.taken = 0
        self.connected = 0          # open WebSocket connections
        self.last_t = 0.0
        self.fps = 0.0
        self.error = None
        self.outbox = []            # commands for the phone, sent by the WebSocket handler
        # clock sync (NTP-style ping/pong): mac time = phone time + offset;
        # the answer with the shortest round trip gives the best offset
        self.syncs = []             # recent (rtt, offset)
        self.offset = None
        self.rtt = None
        self.lat = {}               # latency stages, smoothed (seconds)
        self.collect = None         # list while a latency probe records every frame

    def ping(self):
        self.outbox.append(f"ping:{time.time():.6f}")

    def pong(self, text):
        """Reply "pong:<mac send time>:<phone time>" from the app."""
        try:
            _, t0, tp = text.split(":")
            t0, tp = float(t0), float(tp)
        except ValueError:
            return
        rtt = time.time() - t0
        self.syncs = (self.syncs + [(rtt, t0 + rtt / 2 - tp)])[-30:]
        self.rtt, self.offset = min(self.syncs)

    def _stage(self, name, value):
        old = self.lat.get(name)
        self.lat[name] = value if old is None else 0.9 * old + 0.1 * value

    def push(self, msg):
        now = time.time()
        try:
            hd = header(msg)
        except Exception as e:      # a bad frame must not drop the connection
            self.error = repr(e)
            return
        hd["t_recv"] = now
        if "t_cap" in hd:
            self._stage("arkit", hd["t_deliver"] - hd["t_cap"])       # capture -> app
            self._stage("encode", hd["t_send"] - hd["t_deliver"])     # JPEG + depth packing
            if self.offset is not None:
                hd["t_cap_mac"] = hd["t_cap"] + self.offset
                self._stage("network", now - (hd["t_send"] + self.offset))
        if self.collect is not None:
            self.collect.append((msg, hd))
        if self.last_t:
            self.fps = 0.9 * self.fps + 0.1 / max(now - self.last_t, 1e-3)
        self.last_t = now
        with self.cond:
            self.raw, self.raw_header = msg, hd
            self.seq += 1
            self.cond.notify_all()

    @property
    def live(self):
        return time.time() - self.last_t < 1.0

    def _decode(self, msg):
        try:
            return parse(msg)
        except Exception as e:
            self.error = repr(e)
            return None

    def read(self, timeout=1.0):
        with self.cond:
            self.cond.wait_for(lambda: self.seq != self.taken, timeout)
            if self.raw is None or self.seq == self.taken:
                return False, None
            self.taken = self.seq
            msg, hd = self.raw, self.raw_header
        pkt = self._decode(msg)          # outside the lock: push() never waits on it
        if pkt is None:
            return False, None
        pkt["t_recv"] = hd["t_recv"]
        pkt["t_cap_mac"] = hd.get("t_cap_mac")
        pkt["t_read"] = time.time()
        self.current = pkt
        return True, pkt["bgr"]

    def depth_frames(self, n=15, timeout=5.0):
        """The next `n` packets, for averaging depth while nothing moves."""
        out, seq, t0 = [], self.seq, time.time()
        while len(out) < n and time.time() - t0 < timeout:
            with self.cond:
                self.cond.wait_for(lambda: self.seq != seq, 0.5)
                if self.seq == seq:
                    continue
                seq, msg = self.seq, self.raw
            pkt = self._decode(msg)
            if pkt is not None:
                out.append(pkt)
        return out

    def lock(self, on=True, timeout=3.0):
        """Lock (or release) the phone's exposure, white balance and focus,
        and wait until its frames say so. False if the app cannot (an old
        app version sends no "locked" field)."""
        self.outbox.append("lock" if on else "unlock")
        t0 = time.time()
        while time.time() - t0 < timeout:
            hd = self.raw_header
            if hd is not None and hd.get("locked") is on:
                return True
            time.sleep(0.03)
        return False

    def release(self):
        pass                        # the phone keeps streaming; nothing to close


IPHONE = IPhoneSource()             # one phone per server


def depth_view(pkt, near=0.3, far=5.0):
    """Colour-coded depth for the browser (near = warm), low confidence dimmed."""
    d = pkt["depth"]
    t = np.clip((d - near) / (far - near), 0, 1)
    img = cv2.applyColorMap((255 * (1 - t)).astype(np.uint8), cv2.COLORMAP_TURBO)
    if pkt["conf"] is not None:
        img[pkt["conf"] < 2] //= 3
    h, w = pkt["bgr"].shape[:2]
    return cv2.resize(img, (w, h), interpolation=cv2.INTER_NEAREST)
