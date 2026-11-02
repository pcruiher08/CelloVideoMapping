"""Kinect v2 source: colour + depth from kinect/bin/cellokinect.

A drop-in for the iPhone source (iphone.py): read() hands out the newest
colour frame, `current` the packet it came from, with depth in metres on a
grid over the colour image, a confidence like the iPhone's (0 none, 1 thin,
2 solid) and the colour camera's intrinsics. The rest of the app (3D
calibration, the cello's plane, relocation) cannot tell the two apart.

The Kinect is read by a helper process (see kinect/cellokinect.cpp): the
library is C++ and its GPU depth decoding needs a process of its own.
Build it with `bash kinect/build.sh` (install.sh does).

Unlike the LiDAR, the Kinect's depth is time-of-flight with its own
infrared light: the projector does not disturb it and it works in the dark.
The depth camera sees less than the colour camera (about 70 x 60 degrees
against 84 x 54), so the left and right edges of the image have no depth.
"""

import json
import os
import struct
import subprocess
import threading
import time

import cv2
import numpy as np

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
HELPER = os.path.join(ROOT, "kinect", "bin", "cellokinect")


def confidence(depth_mm, hits, edge=0.03):
    """iPhone-style confidence: 2 for a solid reading away from depth edges
    (where time-of-flight mixes foreground and background), 1 for a thin or
    edge one, 0 for none."""
    ok = depth_mm > 0
    d = depth_mm.astype(np.float32)
    lo = cv2.erode(np.where(ok, d, 1e5).astype(np.float32), np.ones((3, 3)))
    hi = cv2.dilate(np.where(ok, d, 0).astype(np.float32), np.ones((3, 3)))
    solid = ok & (hits >= 2) & ((hi - lo) < edge * np.maximum(d, 1))
    return np.where(solid, 2, np.where(ok, 1, 0)).astype(np.uint8)


class KinectSource:
    """Camera-like source fed by the helper's stdout (see the module doc)."""

    def __init__(self, width=1280, pipeline="gl", start=True):
        self.width = width                 # colour is scaled to this width (the processing width)
        self.pipeline = pipeline
        self.cond = threading.Condition()
        self.raw = None                    # newest (header, bgr bytes, depth, hits), undecoded
        self.seq = 0
        self.taken = 0
        self.current = None
        self.info = None
        self.locked = None
        self.last_t = 0.0
        self.fps = 0.0
        self.error = None
        self.proc = None
        self.running = True
        # what the iPhone source also has, for the status and latency code
        self.connected = 0
        self.kb = None
        self.diag = {}
        self.lat = {}
        self.rtt = self.offset = None
        self.collect = None
        if start:                          # start=False: fed by hand (test_kinect.py)
            threading.Thread(target=self._run, daemon=True).start()

    # --- helper process --------------------------------------------------

    def _run(self):
        while self.running:
            if not os.access(HELPER, os.X_OK):
                self.error = "the Kinect helper is not built: run  bash kinect/build.sh"
                print(self.error)
                return
            try:
                self.proc = subprocess.Popen([HELPER, self.pipeline], stdin=subprocess.PIPE,
                                             stdout=subprocess.PIPE, bufsize=0)
                self._read(self.proc.stdout)
            except Exception as e:
                self.error = repr(e)
            if self.proc is not None:
                code = self.proc.poll()
                self._stop_proc()
                if self.running:
                    self.error = self.error or f"the Kinect helper stopped (exit {code})"
                    print(f"kinect: {self.error}; restarting in 2 s")
            self.connected = 0
            if self.running:
                time.sleep(2.0)

    @staticmethod
    def _exact(f, n):
        buf = bytearray(n)
        view, got = memoryview(buf), 0
        while got < n:
            k = f.readinto(view[got:])
            if not k:
                raise EOFError
            got += k
        return buf

    def _message(self, f):
        tag = bytes(self._exact(f, 4))
        (n,) = struct.unpack("<I", self._exact(f, 4))
        return tag, json.loads(bytes(self._exact(f, n)))

    def _read(self, f):
        tag, info = self._message(f)
        if tag != b"KV2H":
            raise ValueError(f"unexpected Kinect helper output {tag!r}")
        self.info = info
        w, h, dw, dh = info["w"], info["h"], info["dw"], info["dh"]
        self.diag = {"src": f"Kinect v2 {info['serial']}", "pipeline": info["pipeline"]}
        self.connected, self.error = 1, None
        while self.running:
            tag, hd = self._message(f)
            if tag != b"KV2F":
                raise ValueError(f"unexpected Kinect helper output {tag!r}")
            bgr = self._exact(f, w * h * 3)
            depth = self._exact(f, dw * dh * 2)
            hits = self._exact(f, dw * dh)
            now = time.time()
            hd["t_recv"] = now
            self.locked = hd.get("locked")
            if self.last_t:
                self.fps = 0.9 * self.fps + 0.1 / max(now - self.last_t, 1e-3)
            self.last_t = now
            item = (hd, bgr, depth, hits)
            if self.collect is not None:
                self.collect.append(item)
            with self.cond:
                self.raw = item
                self.seq += 1
                self.cond.notify_all()

    def _stop_proc(self):
        p, self.proc = self.proc, None
        if p is None:
            return
        try:
            p.stdin.write(b"quit\n")
            p.stdin.flush()
        except OSError:
            pass
        try:
            p.wait(timeout=4)
        except subprocess.TimeoutExpired:
            p.kill()                       # the helper gives up after 2 s itself

    def _send(self, line):
        p = self.proc
        if p is None:
            return False
        try:
            p.stdin.write(line.encode() + b"\n")
            p.stdin.flush()
            return True
        except OSError:
            return False

    # --- the iPhone source's interface ----------------------------------------

    @property
    def live(self):
        return time.time() - self.last_t < 1.0

    def _decode(self, item):
        hd, bgr, depth, hits = item
        info = self.info
        w, h, dw, dh = info["w"], info["h"], info["dw"], info["dh"]
        img = np.frombuffer(bgr, np.uint8).reshape(h, w, 3)
        K = np.array([[info["fx"], 0, info["cx"]], [0, info["fy"], info["cy"]], [0, 0, 1]], np.float64)
        if self.width and w > self.width:
            s = self.width / w
            nw, nh = self.width, int(round(h * s))
            img = cv2.resize(img, (nw, nh), interpolation=cv2.INTER_AREA)
            K[:2] *= s
            K[0, 2] = (info["cx"] + 0.5) * s - 0.5     # pixel centres, not corners
            K[1, 2] = (info["cy"] + 0.5) * s - 0.5
            w, h = nw, nh
        mm = np.frombuffer(depth, np.uint16).reshape(dh, dw)
        conf = confidence(mm, np.frombuffer(hits, np.uint8).reshape(dh, dw))
        d = np.where(mm > 0, mm.astype(np.float32) / 1000.0, np.nan).astype(np.float32)
        return {"bgr": img, "depth": d, "conf": conf, "K": K, "size": (w, h),
                "ts": hd["t"], "orientation": "kinect", "locked": hd.get("locked"),
                "t_recv": hd["t_recv"], "t_cap_mac": hd["t"]}

    def read(self, timeout=1.0):
        with self.cond:
            self.cond.wait_for(lambda: self.seq != self.taken, timeout)
            if self.raw is None or self.seq == self.taken:
                return False, None
            self.taken = self.seq
            item = self.raw
        try:
            pkt = self._decode(item)
        except Exception as e:
            self.error = repr(e)
            return False, None
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
                seq, item = self.seq, self.raw
            out.append(self._decode(item))
        return out

    def lock(self, on=True, timeout=3.0):
        """Hold (or release) the colour camera's exposure; True once the
        frames say so."""
        if not self._send("lock" if on else "unlock"):
            return False
        t0 = time.time()
        while time.time() - t0 < timeout:
            if self.locked is on:
                return True
            time.sleep(0.03)
        return False

    def release(self):
        self.running = False
        self._stop_proc()
