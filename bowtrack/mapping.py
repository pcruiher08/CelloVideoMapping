"""Videomapping runtime: tracker in a worker thread, GL renderer on screen.

The camera runs at ~30 fps and the projector at 60; decoupling them into a
worker thread plus a vsynced draw loop keeps the projection smooth even when
a frame arrives late or a detection is missed.

Usage:
    .venv/bin/python run.py --map                 # windowed, current screen
    .venv/bin/python run.py --map --fullscreen    # on the projector

Calibrate the orange HSV range first with the normal tracker view
(`python run.py`, press c), then come here to align the projected quad.
"""

import argparse
import os
import threading
import time
from dataclasses import dataclass

from .metrics import Metrics
from .tracker import BowTracker
from .warp import QuadWarp, CORNER_NAMES

# moderngl, pyglet and .render are imported inside run() so that the plain
# tracker (`python run.py`) keeps working without the GL stack installed.

WARP_PATH = os.path.join(os.path.dirname(__file__), "..", "warp.json")
CONFIG_PATH = os.path.join(os.path.dirname(__file__), "..", "config.json")

FINE, COARSE = 0.002, 0.02


@dataclass
class RenderFrame:
    """Bow state in the renderer's terms: content uv, y up, normalized speed."""
    ok: bool = False
    a: tuple = (0.5, 0.5)
    b: tuple = (0.5, 0.5)
    angle: float = 0.0     # radians
    speed: float = 0.0     # fraction of frame width per second
    time: float = 0.0


class TrackerThread(threading.Thread):
    """Owns the capture device and the tracker; publishes RenderFrames."""

    def __init__(self, cap, osc=None, flip=False):
        super().__init__(daemon=True)
        self.cap = cap
        self.osc = osc
        self.flip = flip
        self.tracker = BowTracker()
        if os.path.exists(CONFIG_PATH):
            self.tracker.load_config(CONFIG_PATH)
            print(f"Loaded HSV config from {os.path.abspath(CONFIG_PATH)}")
        else:
            print("No config.json — using default orange HSV range. "
                  "Run `python run.py` and press c to calibrate the tape.")
        self.metrics = Metrics()
        self._lock = threading.Lock()
        self._frame = RenderFrame()
        self._stop_event = threading.Event()
        self.t0 = time.time()

    @property
    def frame(self):
        with self._lock:
            return self._frame

    def stop(self):
        self._stop_event.set()

    def run(self):
        import cv2
        misses = 0
        while not self._stop_event.is_set():
            ok, img = self.cap.read()
            if not ok:
                misses += 1
                if misses > 60:
                    print("Camera read failed repeatedly; tracker thread exiting.")
                    break
                time.sleep(0.02)
                continue
            misses = 0
            if self.flip:
                img = cv2.flip(img, 1)

            h, w = img.shape[:2]
            st = self.tracker.update(img)
            if st.ok:
                self.metrics.push(st)
            if self.osc:
                self.osc.send(st, self.metrics, (w, h))

            if st.ok and st.a is not None:
                # Camera space is y-down; GL content space is y-up.
                a = (st.a[0] / w, 1.0 - st.a[1] / h)
                b = (st.b[0] / w, 1.0 - st.b[1] / h)
                f = RenderFrame(ok=True, a=a, b=b,
                                angle=st.angle * 3.14159265 / 180.0,
                                speed=self.metrics.speed / max(w, 1),
                                time=time.time() - self.t0)
            else:
                f = RenderFrame(ok=False, time=time.time() - self.t0)

            with self._lock:
                self._frame = f

        self.cap.release()


def build_window(screen_index, fullscreen, size):
    import pyglet
    display = pyglet.display.get_display()
    screens = display.get_screens()
    if screen_index is None:
        # More than one screen means the projector is extended: use the last.
        screen_index = len(screens) - 1 if len(screens) > 1 else 0
    screen_index = max(0, min(screen_index, len(screens) - 1))
    screen = screens[screen_index]
    print(f"Screens: {[(s.width, s.height) for s in screens]} -> using #{screen_index}")
    if len(screens) == 1:
        print("Only one screen detected. If the projector is mirroring, turn "
              "mirroring off in System Settings > Displays to get a second "
              "screen to project onto.")

    cfg = pyglet.gl.Config(major_version=3, minor_version=3,
                           forward_compatible=True, double_buffer=True,
                           depth_size=0)
    if fullscreen:
        return pyglet.window.Window(screen=screen, fullscreen=True, config=cfg,
                                    caption="Bow Mapping")
    return pyglet.window.Window(width=size[0], height=size[1], screen=screen,
                                config=cfg, resizable=True, caption="Bow Mapping")


HELP = """\
Mapping keys
  c            calibration mode (grid + draggable corner handles)
  drag         grab a corner handle with the mouse — fastest way to kill
               a keystone trapezoid
  1 2 3 4      select corner: TL, TR, BR, BL
  arrows       nudge selected corner (hold shift for coarse steps)
  g            toggle grid on its own
  s            save warp.json          r  reset warp to full screen
  [ ]          shorter / longer trails
  f            toggle fullscreen       q / esc  quit\
"""


def run(args, cap):
    import moderngl
    import pyglet
    from .render import BowRenderer

    osc = None
    if args.osc:
        from .osc_out import OSCSender
        osc = OSCSender(args.osc_host, args.osc_port)
        print(f"OSC -> {args.osc_host}:{args.osc_port}")

    tracker_thread = TrackerThread(cap, osc=osc, flip=args.flip)
    tracker_thread.start()

    win = build_window(args.screen, args.fullscreen, (args.map_width, args.map_height))
    ctx = moderngl.create_context()
    print(f"GL: {ctx.info['GL_VERSION']} on {ctx.info['GL_RENDERER']}")

    warp = QuadWarp.load_or_default(WARP_PATH)
    if os.path.exists(WARP_PATH):
        print(f"Loaded warp from {os.path.abspath(WARP_PATH)}")
    renderer = BowRenderer(ctx, content_size=(args.content_width, args.content_height))

    state = {"corner": 0, "calibrating": False, "dragging": None}

    def to_projector_uv(x, y):
        """pyglet window coords (y up) -> projector uv (y down), which is the
        space the warp corners live in."""
        return x / max(win.width, 1), 1.0 - y / max(win.height, 1)
    print(HELP)

    @win.event
    def on_draw():
        renderer.render(tracker_thread.frame, ctx.screen,
                        win.get_framebuffer_size(), warp,
                        handles=state["calibrating"], selected=state["corner"])

    @win.event
    def on_mouse_press(x, y, button, modifiers):
        if not state["calibrating"]:
            return
        px, py = to_projector_uv(x, y)
        i = warp.nearest_corner(px, py)
        if i is not None:
            state["dragging"] = i
            state["corner"] = i
            print(f"Dragging corner {i + 1} ({CORNER_NAMES[i]})")

    @win.event
    def on_mouse_drag(x, y, dx, dy, buttons, modifiers):
        if state["dragging"] is not None:
            warp.set_corner(state["dragging"], *to_projector_uv(x, y))

    @win.event
    def on_mouse_release(x, y, button, modifiers):
        state["dragging"] = None

    @win.event
    def on_key_press(symbol, modifiers):
        key = pyglet.window.key
        step = COARSE if modifiers & key.MOD_SHIFT else FINE

        if symbol in (key.Q, key.ESCAPE):
            pyglet.app.exit()
        elif symbol == key.C:
            state["calibrating"] = not state["calibrating"]
            renderer.show_grid = state["calibrating"]
            print(f"Calibration {'ON' if state['calibrating'] else 'OFF'}"
                  + (f" — corner {state['corner'] + 1} "
                     f"({CORNER_NAMES[state['corner']]})" if state["calibrating"] else ""))
        elif symbol == key.G:
            renderer.show_grid = not renderer.show_grid
        elif symbol in (key._1, key._2, key._3, key._4):
            state["corner"] = (key._1, key._2, key._3, key._4).index(symbol)
            print(f"Corner {state['corner'] + 1}: {CORNER_NAMES[state['corner']]}")
        elif symbol in (key.LEFT, key.RIGHT, key.UP, key.DOWN):
            dx = -step if symbol == key.LEFT else step if symbol == key.RIGHT else 0.0
            dy = -step if symbol == key.UP else step if symbol == key.DOWN else 0.0
            warp.nudge(state["corner"], dx, dy)
        elif symbol == key.S:
            warp.save(WARP_PATH)
            print(f"Saved warp to {os.path.abspath(WARP_PATH)}")
        elif symbol == key.R:
            warp.reset()
            print("Warp reset to full screen.")
        elif symbol == key.BRACKETLEFT:
            renderer.fade = min(0.4, renderer.fade * 1.3)
            print(f"fade {renderer.fade:.3f} (shorter trails)")
        elif symbol == key.BRACKETRIGHT:
            renderer.fade = max(0.004, renderer.fade / 1.3)
            print(f"fade {renderer.fade:.3f} (longer trails)")
        elif symbol == key.F:
            win.set_fullscreen(not win.fullscreen)

    @win.event
    def on_close():
        tracker_thread.stop()

    try:
        pyglet.app.run()
    finally:
        tracker_thread.stop()
        tracker_thread.join(timeout=1.0)
        renderer.release()


def add_args(p: argparse.ArgumentParser):
    g = p.add_argument_group("videomapping (--map)")
    g.add_argument("--map", action="store_true",
                   help="run the projection-mapping renderer instead of the "
                        "OpenCV preview window")
    g.add_argument("--fullscreen", action="store_true",
                   help="open the mapping window fullscreen on the projector")
    g.add_argument("--screen", type=int, default=None,
                   help="screen index for the mapping window "
                        "(default: the last screen, i.e. the projector)")
    g.add_argument("--map-width", type=int, default=1920,
                   help="windowed mapping window width")
    g.add_argument("--map-height", type=int, default=1080,
                   help="windowed mapping window height")
    g.add_argument("--content-width", type=int, default=1920,
                   help="internal render resolution width")
    g.add_argument("--content-height", type=int, default=1080,
                   help="internal render resolution height")
