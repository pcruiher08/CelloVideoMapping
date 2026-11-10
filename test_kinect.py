"""Kinect v2 source, checked without the Kinect: a made-up helper stream
(the format kinect/cellokinect.cpp writes) must come out as an iPhone-style
packet: colour at the processing width with matching intrinsics, depth in
metres with NaN for no reading, and a confidence that drops at depth edges.

    .venv/bin/python test_kinect.py           # offline
    .venv/bin/python test_kinect.py --live    # also a few seconds of the real Kinect
"""

import io
import json
import os
import struct
import sys
import time

import numpy as np

ROOT = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, ROOT)

from cellomask.kinect import KinectSource  # noqa: E402

W, H, DW, DH = 1920, 1080, 480, 270


def message(tag, hd, *payload):
    j = json.dumps(hd).encode()
    return tag + struct.pack("<I", len(j)) + j + b"".join(p.tobytes() for p in payload)


def stream(frames=3):
    info = {"w": W, "h": H, "fx": 1081.37, "fy": 1081.37, "cx": 959.5, "cy": 539.5,
            "dw": DW, "dh": DH, "serial": "test", "firmware": "0", "pipeline": "gl"}
    out = [message(b"KV2H", info)]
    for k in range(frames):
        bgr = np.zeros((H, W, 3), np.uint8)
        bgr[:, : W // 2] = (200, 60, 20)
        mm = np.full((DH, DW), 2500, np.uint16)          # a wall at 2.5 m
        mm[60:210, 180:300] = 1200                        # a box at 1.2 m in front of it
        mm[:, :40] = 0                                    # the depth camera's narrower view
        hits = np.where(mm > 0, 3, 0).astype(np.uint8)
        if k == frames - 1:                               # depth only: the colour camera had nothing new
            out.append(message(b"KV2F", {"seq": k, "t": time.time(), "locked": False, "color": False}, mm, hits))
        else:
            out.append(message(b"KV2F", {"seq": k, "t": time.time(), "locked": False, "color": True},
                               bgr, mm, hits))
    return io.BytesIO(b"".join(out))


def offline():
    k = KinectSource(width=1280, start=False)             # no helper process
    try:
        k._read(stream())
    except EOFError:
        pass
    assert k.seq == 3, k.seq
    ok, img = k.read(timeout=0.1)
    pkt = k.current
    assert ok and img.shape == (720, 1280, 3), img.shape
    assert pkt["new_color"] is False, "the last frame came without colour"
    assert tuple(img[10, 10]) == (200, 60, 20) and tuple(img[10, 1270]) == (0, 0, 0)
    K = pkt["K"]
    assert abs(K[0, 0] - 1081.37 * 2 / 3) < 0.01 and abs(K[0, 2] - 639.5) < 0.01 and abs(K[1, 2] - 359.5) < 0.01, K
    d, c = pkt["depth"], pkt["conf"]
    assert d.shape == (DH, DW) and np.isnan(d[:, :40]).all() and (c[:, :40] == 0).all()
    assert abs(d[100, 250] - 1.2) < 1e-6 and abs(d[20, 400] - 2.5) < 1e-6
    assert c[100, 250] == 2 and c[20, 400] == 2
    assert c[60, 250] == 1 and c[100, 180] == 1, "the box's outline must not count as solid"
    print("offline: packet ok (1280x720, K scaled, depth in m, NaN + conf 0 outside, edges conf 1, "
          "a depth-only frame reuses the last colour)")


def live(seconds=5):
    k = KinectSource(width=1280)
    t0, n = time.time(), 0
    while time.time() - t0 < seconds + 3:
        ok, _ = k.read()
        n += ok
    pkt, fps, err = k.current, k.fps, k.error
    locked = k.lock(True) and k.lock(False)
    k.release()
    assert pkt is not None, f"no Kinect frames ({err})"
    valid = float(np.isfinite(pkt["depth"]).mean())
    print(f"live: {n} frames, {fps:.1f} fps, depth on {100 * valid:.0f}% of the image, exposure lock {locked}")
    assert fps > 20 and valid > 0.2 and locked


if __name__ == "__main__":
    offline()
    if "--live" in sys.argv:
        live()
    print("all ok")
