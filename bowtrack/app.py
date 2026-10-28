"""Main loop: capture -> track -> metrics -> overlay window (+ optional OSC)."""

import argparse
import os
import time
from collections import deque

import cv2

from .tracker import BowTracker
from .metrics import Metrics, FPSCounter
from . import viz

CONFIG_PATH = os.path.join(os.path.dirname(__file__), "..", "config.json")
WINDOW = "Cello Bow Tracker"


def parse_args(argv=None):
    p = argparse.ArgumentParser(description="Cello bow tracker (orange tape markers)")
    p.add_argument("--source", default="auto",
                   help="'auto' = built-in Mac camera (default), a camera "
                        "index, part of a camera name (e.g. 'brio'), or a "
                        "path to a video file")
    p.add_argument("--width", type=int, default=1280)
    p.add_argument("--height", type=int, default=720)
    p.add_argument("--flip", action="store_true",
                   help="mirror the image horizontally (webcam selfie view)")
    p.add_argument("--fps", type=int, default=None,
                   help="requested capture framerate, e.g. 90 with "
                        "--width 1280 --height 720 on a Brio 4K")
    p.add_argument("--no-mjpg", action="store_true",
                   help="do not request MJPEG (raw formats cannot sustain "
                        "high framerates over USB)")
    p.add_argument("--lock-exposure", action="store_true",
                   help="try to disable auto exposure and auto white balance, "
                        "which otherwise drift as projected light hits the scene")
    p.add_argument("--osc", action="store_true", help="send OSC messages")
    p.add_argument("--osc-host", default="127.0.0.1")
    p.add_argument("--osc-port", type=int, default=9000)
    from .mapping import add_args as add_mapping_args
    add_mapping_args(p)
    return p.parse_args(argv)


def open_source(args):
    src = args.source
    if src == "auto":
        from .camera import pick_builtin_index
        idx, name = pick_builtin_index()
        print(f"Using camera {idx}: {name or 'unknown (fallback)'}")
        src = str(idx)
    elif not src.isdigit() and not os.path.exists(src):
        # Not an index and not a file: treat it as part of a camera name.
        from .camera import pick_by_name, list_cameras
        idx, name = pick_by_name(src)
        if idx is None:
            raise SystemExit(f"No camera matching {src!r}. Available: "
                             f"{list_cameras() or '(enumeration unavailable)'}")
        print(f"Using camera {idx}: {name}")
        src = str(idx)

    if src.isdigit():
        from .camera import configure
        cap = cv2.VideoCapture(int(src))
        info = configure(cap, args.width, args.height, fps=args.fps,
                         mjpg=not args.no_mjpg,
                         lock_exposure=args.lock_exposure)
        fps_txt = f"{info['fps']:.0f} fps" if info["fps"] else "fps not reported"
        cc_txt = info["fourcc"] or "fourcc not reported"
        print(f"Capture: {info['width']}x{info['height']}, {fps_txt}, {cc_txt} "
              "(AVFoundation reports neither reliably)")
        if info["locked"] is not None:
            print(f"  exposure/WB lock attempted -> {info['locked']} "
                  "(AVFoundation may ignore these)")
    else:
        cap = cv2.VideoCapture(src)
    if not cap.isOpened():
        raise SystemExit(f"Could not open video source: {src!r}. "
                         "On macOS, grant camera access to your terminal in "
                         "System Settings > Privacy & Security > Camera.")
    if src.isdigit():
        # macOS/AVFoundation: the first reads can fail while the camera
        # warms up — retry for a couple of seconds before giving up.
        for _ in range(40):
            ok, _ = cap.read()
            if ok:
                break
            time.sleep(0.05)
        else:
            cap.release()
            raise SystemExit(f"Camera {src} opened but produced no frames.")
        if args.fps:
            # The requested rate means nothing until measured, so when the
            # user asks for a specific framerate, tell them what they got.
            from .camera import measure_fps
            print(f"  measured delivered rate: {measure_fps(cap, 40):.1f} fps")
    return cap


def main(argv=None):
    args = parse_args(argv)
    cap = open_source(args)

    if args.map:
        from . import mapping
        mapping.run(args, cap)
        return

    tracker = BowTracker()
    if os.path.exists(CONFIG_PATH):
        tracker.load_config(CONFIG_PATH)
        print(f"Loaded HSV config from {os.path.abspath(CONFIG_PATH)}")

    metrics = Metrics()
    fps = FPSCounter()
    trail = deque(maxlen=90)
    osc = None
    if args.osc:
        from .osc_out import OSCSender
        osc = OSCSender(args.osc_host, args.osc_port)
        print(f"OSC -> {args.osc_host}:{args.osc_port}")

    calibrating = False
    show_mask = False
    clicks = []

    cv2.namedWindow(WINDOW)

    def on_mouse(event, x, y, flags, param):
        if event == cv2.EVENT_LBUTTONDOWN and calibrating:
            clicks.append((x, y))

    cv2.setMouseCallback(WINDOW, on_mouse)
    print("Keys: c calibrate (then click the tape), m mask view, "
          "r reset trail/HSV, s save config, q quit")

    misses = 0
    while True:
        ok, frame = cap.read()
        if not ok:
            misses += 1
            if misses > 30:
                print("End of stream / camera read failed.")
                break
            time.sleep(0.02)
            continue
        misses = 0
        if args.flip:
            frame = cv2.flip(frame, 1)

        h, w = frame.shape[:2]

        # Calibration clicks are in window coords == frame coords (left side).
        while clicks:
            cx, cy = clicks.pop(0)
            if cx < w:
                med = tracker.sample_hsv(frame, cx, cy)
                print(f"Sampled HSV {med} -> range "
                      f"{tracker.hsv_lo.tolist()}..{tracker.hsv_hi.tolist()}")

        st = tracker.update(frame)
        if st.ok:
            metrics.push(st)
            trail.append((int(st.x), int(st.y)))
        if osc:
            osc.send(st, metrics, (w, h))

        fps.tick()

        if show_mask and tracker.mask is not None:
            display = cv2.cvtColor(tracker.mask, cv2.COLOR_GRAY2BGR)
        else:
            display = frame
        display = viz.draw_overlay(display, st, metrics, list(trail))
        panel = viz.draw_panel(h, st, metrics, fps.fps,
                               tracker.hsv_lo, tracker.hsv_hi, calibrating)
        cv2.imshow(WINDOW, viz.compose(display, panel))

        key = cv2.waitKey(1) & 0xFF
        if key == ord("q") or key == 27:
            break
        elif key == ord("c"):
            calibrating = not calibrating
            print("Calibration", "ON — click the orange tape in the image"
                  if calibrating else "OFF")
        elif key == ord("m"):
            show_mask = not show_mask
        elif key == ord("r"):
            trail.clear()
            metrics.clear()
            tracker.reset_hsv()
            print("Reset trail, metrics and HSV range to defaults.")
        elif key == ord("s"):
            tracker.save_config(CONFIG_PATH)
            print(f"Saved config to {os.path.abspath(CONFIG_PATH)}")

    cap.release()
    cv2.destroyAllWindows()


if __name__ == "__main__":
    main()
