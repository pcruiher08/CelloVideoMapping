"""TouchDesigner links, checked on this Mac alone: an NDI sender and a
Syphon server made here stand in for TouchDesigner's NDI Out / Syphon Spout
Out TOPs; the app's receivers must show their frames (right colours, right
size, keeping up). OSC out is caught by a local OSC server standing in for
TouchDesigner's OSC In CHOP.

    .venv/bin/python test_live.py
"""

import os
import sys
import threading
import time
from fractions import Fraction

import numpy as np

ROOT = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, ROOT)

from cellomask.live import NDIMedia, OscOut, SyphonMedia, ndi_sources, syphon_sources  # noqa: E402

W, H = 640, 360


def pattern(k):
    """BGR test frame: left half blue, right half orange, a bar that moves."""
    img = np.zeros((H, W, 3), np.uint8)
    img[:, : W // 2] = (200, 60, 20)
    img[:, W // 2:] = (30, 140, 240)
    x = (k * 7) % W
    img[:, x:x + 10] = 255
    return img


def check(name, ok, detail):
    print(f"{'PASS' if ok else 'FAIL'}  {name:34s} {detail}", flush=True)
    return ok


def received_ok(media, seconds=4.0):
    """(ok, detail): frames arrive, right size, right colours, keeping up."""
    t0 = time.time()
    while media.frames < 30 and time.time() - t0 < seconds + 6:
        time.sleep(0.05)
    f = media.latest
    if f is None:
        return False, f"no frame ({media.error})"
    left = f[:, : f.shape[1] // 4].reshape(-1, 3).mean(0)
    right = f[:, -f.shape[1] // 4:].reshape(-1, 3).mean(0)
    colours = np.abs(left - (200, 60, 20)).max() < 12 and np.abs(right - (30, 140, 240)).max() < 12
    return (f.shape[:2] == (H, W) and colours and media.fps > 20,
            f"{f.shape[1]}x{f.shape[0]}, {media.fps:.0f} fps, colours {'right' if colours else 'WRONG'}")


def check_ndi():
    from cyndilib.sender import Sender
    from cyndilib.video_frame import VideoSendFrame
    from cyndilib.wrapper.ndi_structs import FourCC

    vf = VideoSendFrame()
    vf.set_resolution(W, H)
    vf.set_frame_rate(Fraction(30, 1))
    vf.set_fourcc(FourCC.BGRA)
    sender = Sender("cellomask-test")
    sender.set_video_frame(vf)
    stop = threading.Event()

    def send():
        k = 0
        with sender:
            while not stop.is_set():
                bgra = np.dstack([pattern(k), np.full((H, W), 255, np.uint8)])
                sender.write_video(bgra.ravel())
                k += 1
                time.sleep(1 / 30)

    th = threading.Thread(target=send, daemon=True)
    th.start()
    try:
        name = None
        t0 = time.time()
        while name is None and time.time() - t0 < 8:
            name = next((n for n in ndi_sources(wait=1.0) if "cellomask-test" in n), None)
        if name is None:
            return check("NDI in", False, "the test sender was not found on the network")
        media = NDIMedia(name)
        ok, detail = received_ok(media)
        media.close()
        return check("NDI in", ok, f"{name}: {detail}")
    finally:
        stop.set()
        th.join(2)


def check_syphon():
    import syphon
    from syphon.utils.numpy import copy_image_to_mtl_texture
    from syphon.utils.raw import create_mtl_texture

    server = syphon.SyphonMetalServer("cellomask-test")
    tex = create_mtl_texture(server.device, W, H)          # RGBA
    stop = threading.Event()

    def send():
        k = 0
        while not stop.is_set():
            rgba = np.dstack([pattern(k)[..., ::-1], np.full((H, W), 255, np.uint8)])
            copy_image_to_mtl_texture(np.ascontiguousarray(rgba), tex)
            server.publish_frame_texture(tex)
            k += 1
            time.sleep(1 / 30)

    th = threading.Thread(target=send, daemon=True)
    th.start()
    try:
        name = None
        t0 = time.time()
        while name is None and time.time() - t0 < 8:
            name = next((n for n in syphon_sources() if n.endswith("cellomask-test")), None)
            time.sleep(0.2)
        if name is None:
            return check("Syphon in", False, "the test server was not found")
        media = SyphonMedia(name)
        ok, detail = received_ok(media)
        media.close()
        return check("Syphon in", ok, f"{name}: {detail}")
    finally:
        stop.set()
        th.join(2)
        server.stop()


def check_osc():
    from pythonosc.dispatcher import Dispatcher
    from pythonosc.osc_server import ThreadingOSCUDPServer

    got = {}
    d = Dispatcher()
    d.set_default_handler(lambda addr, *args: got.__setitem__(addr, args[0] if args else None))
    srv = ThreadingOSCUDPServer(("127.0.0.1", 0), d)
    port = srv.server_address[1]
    threading.Thread(target=srv.serve_forever, daemon=True).start()

    class FakePipe:
        covered = 0.12

        def plane_state(self):
            return {"distance": 1.9, "lean": 15.0, "turn": -3.0}

    osc = OscOut()
    osc.set_target("127.0.0.1", port)
    snap = {"freq": 220.0, "note": "A3", "cents": -4.0, "level": -20.0,
            "vibrato": {"present": True, "rate": 5.5, "extent": 18.0}}
    axis = (480.0, 640.0, 900.0, 400.0, -np.pi / 2 + np.radians(10))
    osc.send(FakePipe(), (1280, 960, 3), axis, snap)
    time.sleep(0.3)
    srv.shutdown()
    want = {"/cello/present": 1.0, "/cello/x": 0.5, "/cello/y": 0.5, "/cello/angle": 10.0,
            "/cello/distance": 1.9, "/cello/lean": 15.0, "/cello/covered": 0.12,
            "/tuner/freq": 220.0, "/tuner/note": "A3", "/vibrato/rate": 5.5}
    bad = [k for k, v in want.items()
           if k not in got or (abs(got[k] - v) > 1e-3 if isinstance(v, float) else got[k] != v)]
    return check("OSC out", not bad, f"{len(got)} addresses received" + (f", wrong: {bad}" if bad else ""))


def main():
    ok = True
    ok &= check_osc()
    ok &= check_syphon()
    ok &= check_ndi()
    print("ALL TESTS PASSED" if ok else "SOME TESTS FAILED", flush=True)
    os._exit(0 if ok else 1)          # NDI / Syphon keep native threads around


if __name__ == "__main__":
    main()
