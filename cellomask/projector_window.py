"""Projector window (pyglet, main thread).

Shows Pipeline.proj_frame, already in projector pixels. A native window
skips the browser's JPEG encode/decode and polling, which matters for how
far the light trails a moving cello.

It covers the projector screen as a borderless window, not macOS fullscreen:
a fullscreen window is a Space of its own, and with vsync its buffer swap
blocked (holding Python's GIL, so the whole app stalled) whenever Mission
Control or a desktop switch animated it, which froze the Mac's desktop. The
window is pinned instead: on every Space, left alone by Mission Control, and
paced at 60 fps by the app rather than by the display.

Keys in the window:  f  cover the screen / normal window   b  blackout on/off
                     esc  normal window                   q  quit the app

The web page's Projector section lists the screens and moves the window to
another one live (pipe.screen_request, handled here on the main thread).

Between tracked frames (~20 a second) the image is moved at the display's
60 Hz: each frame comes with the motion filters it was drawn with, and every
redraw warps it by Pipeline.display_warp for that moment, in a shader. The
light then glides with the cello instead of jumping every third refresh.
"""

import time

import numpy as np


def list_screens():
    import pyglet
    return [{"index": i, "width": s.width, "height": s.height, "x": s.x, "y": s.y}
            for i, s in enumerate(pyglet.display.get_display().get_screens())]


def pick_screen(spec):
    import pyglet
    screens = pyglet.display.get_display().get_screens()
    if spec in (None, "auto"):
        # more than one screen means the projector is extended: use the last
        idx = len(screens) - 1
    else:
        idx = max(0, min(int(spec), len(screens) - 1))
    print(f"screens: {[(s.width, s.height) for s in screens]} -> projector on #{idx}")
    if len(screens) == 1:
        print("only one screen: is the projector connected, and set to extend "
              "(not mirror) in System Settings > Displays? Using the main screen.")
    return idx, screens[idx]


# NSWindow collection behaviour: on all Spaces, stationary in Mission
# Control, out of the window cycle; and a level above normal windows (so
# TouchDesigner's own window cannot cover the projector)
_ALL_SPACES, _STATIONARY, _IGNORES_CYCLE = 1 << 0, 1 << 4, 1 << 6
_FLOATING_LEVEL = 3


def cover(win, screen):
    """Make `win` a borderless cover of `screen`, pinned (see the module doc)."""
    win.set_size(screen.width, screen.height)
    win.set_location(screen.x, screen.y)
    ns = getattr(win, "_nswindow", None)
    if ns is not None:                       # macOS
        ns.setCollectionBehavior_(_ALL_SPACES | _STATIONARY | _IGNORES_CYCLE)
        ns.setLevel_(_FLOATING_LEVEL)
    win.set_mouse_visible(False)
    win.covering = True


def uncover(win, screen):
    """A normal, movable window (for testing on one screen)."""
    ns = getattr(win, "_nswindow", None)
    if ns is not None:
        ns.setLevel_(0)
    win.set_size(screen.width // 2, screen.height // 2)
    win.set_location(screen.x + 40, screen.y + 60)
    win.set_mouse_visible(True)
    win.covering = False


# full-screen quad; each display pixel looks up the image pixel the warp
# brings to it (image pixels have a top-left origin, rows down)
_VERT = """#version 150 core
in vec2 position;
void main() { gl_Position = vec4(position, 0.0, 1.0); }
"""
_FRAG = """#version 150 core
out vec4 color;
uniform sampler2D tex;
uniform mat3 Dinv;      // display (image) pixel -> source image pixel
uniform vec2 img;       // image size
uniform vec2 fb;        // framebuffer size
void main() {
    vec2 p = vec2(gl_FragCoord.x, fb.y - gl_FragCoord.y) * img / fb - 0.5;
    vec3 q = Dinv * vec3(p, 1.0);
    vec2 s = q.xy / q.z;
    vec2 uv = vec2((s.x + 0.5) / img.x, 1.0 - (s.y + 0.5) / img.y);
    if (q.z <= 0.0 || uv.x < 0.0 || uv.y < 0.0 || uv.x > 1.0 || uv.y > 1.0)
        color = vec4(0.0, 0.0, 0.0, 1.0);
    else
        color = vec4(texture(tex, uv).rgb, 1.0);
}
"""


class Warper:
    """Draws a texture warped by a 3x3 homography (image pixels), on the GPU."""

    def __init__(self):
        import pyglet
        from pyglet import gl
        from pyglet.graphics.shader import Shader, ShaderProgram
        self.gl = gl
        self.prog = ShaderProgram(Shader(_VERT, "vertex"), Shader(_FRAG, "fragment"))
        self.quad = self.prog.vertex_list(4, gl.GL_TRIANGLE_STRIP,
                                          position=("f", (-1, -1, 1, -1, -1, 1, 1, 1)))
        self.pyglet = pyglet

    def draw(self, tex, D, img_size, fb_size):
        gl = self.gl
        Dinv = np.linalg.inv(D)
        self.prog.use()
        self.prog["tex"] = 0
        self.prog["Dinv"] = tuple(float(v) for v in Dinv.T.ravel())   # column-major
        self.prog["img"] = (float(img_size[0]), float(img_size[1]))
        self.prog["fb"] = (float(fb_size[0]), float(fb_size[1]))
        gl.glActiveTexture(gl.GL_TEXTURE0)
        gl.glBindTexture(tex.target, tex.id)
        gl.glTexParameteri(tex.target, gl.GL_TEXTURE_MAG_FILTER, gl.GL_LINEAR)
        gl.glTexParameteri(tex.target, gl.GL_TEXTURE_MIN_FILTER, gl.GL_LINEAR)
        self.quad.draw(gl.GL_TRIANGLE_STRIP)
        self.prog.stop()


def open_window(pipe, spec="auto", fullscreen=True):
    import pyglet
    idx, screen = pick_screen(spec)
    pipe.screens, pipe.screen_index = list_screens(), idx
    if fullscreen and len(pyglet.display.get_display().get_screens()) == 1:
        # no projector connected: a black window with the pointer hidden over
        # the only screen looked like a frozen Mac
        print("no second screen: opening the projector window as a normal window "
              "(connect the projector, set it to extend, and restart)")
        fullscreen = False
    # vsync off: the app paces drawing itself (see the module doc)
    win = pyglet.window.Window(width=screen.width // 2, height=screen.height // 2,
                               style=pyglet.window.Window.WINDOW_STYLE_BORDERLESS if fullscreen
                               else pyglet.window.Window.WINDOW_STYLE_DEFAULT,
                               screen=screen, vsync=False, caption="Cello projector")
    if fullscreen:
        cover(win, screen)
    else:
        uncover(win, screen)
    # draw in the projector's own pixels; a windowed test keeps the screen size
    # so the calibration is the same as fullscreen
    pipe.proj_size = (screen.width, screen.height)
    pipe.projector_window = True
    return win


def run_window(pipe, win):
    import pyglet
    from pyglet import gl

    state = {"seq": -1, "image": None, "before_blackout": "content", "drawn": -1, "bright": None,
             "listed": time.time(), "tex": None, "motion": None}
    try:
        warper = Warper()
    except Exception as e:                   # no shaders: draw unwarped, as before
        print(f"projector window: no GPU warp ({e!r}); the light moves at the tracking rate")
        warper = None

    def move(idx):
        """Cover screen `idx` (from the web page)."""
        screens = pyglet.display.get_display().get_screens()
        if not 0 <= idx < len(screens):
            return
        s = screens[idx]
        cover(win, s)
        pipe.proj_size = (s.width, s.height)
        pipe.screen_index = idx
        print(f"projector window -> screen #{idx} ({s.width}x{s.height})")

    def update(dt):
        req = pipe.screen_request
        if req is not None:
            pipe.screen_request = None
            move(req)
        if time.time() - state["listed"] > 2.0:     # a projector plugged in later shows up
            state["listed"] = time.time()
            pipe.screens = list_screens()
        if pipe.proj_seq == state["seq"] or pipe.proj_frame is None:
            return
        motion = pipe.proj_motion
        state["seq"] = pipe.proj_seq
        f = pipe.proj_frame
        # the motion that belongs to this frame (set before it), or none
        state["motion"] = motion if motion is not None and motion["seq"] == state["seq"] else None
        state["tex"] = None
        h, w = f.shape[:2]
        # BGR rows top-down as they are: GL takes BGR, and a negative pitch
        # tells pyglet the rows run downwards (half the cost of flipping and
        # reordering the channels in numpy first)
        state["image"] = pyglet.image.ImageData(w, h, "BGR", np.ascontiguousarray(f).tobytes(),
                                                pitch=-w * 3)
        # brightness only while a latency probe needs it (black -> white flash)
        state["bright"] = float(f[::16, ::16].mean()) if pipe.probe is not None else None

    @win.event
    def on_draw():
        win.clear()
        img = state["image"]
        if img is not None:
            D = None
            if warper is not None and state["motion"] is not None:
                try:
                    D = pipe.display_warp(state["motion"], time.time())
                except Exception as e:           # never let this blank the projector
                    print(f"display warp: {e!r}")
                    state["motion"] = None
            if D is not None:
                if state["tex"] is None:
                    state["tex"] = img.get_texture()
                warper.draw(state["tex"], D, (img.width, img.height), win.get_framebuffer_size())
            else:
                gl.glTexParameteri(gl.GL_TEXTURE_2D, gl.GL_TEXTURE_MAG_FILTER, gl.GL_LINEAR)
                img.blit(0, 0, width=win.width, height=win.height)
            if state["drawn"] != state["seq"]:
                state["drawn"] = state["seq"]
                pipe.mark_drawn(state["seq"], time.time(), state["bright"])

    @win.event
    def on_key_press(symbol, modifiers):
        from pyglet.window import key
        screens = pyglet.display.get_display().get_screens()
        here = screens[min(pipe.screen_index or 0, len(screens) - 1)]
        if symbol == key.F:
            (uncover if win.covering else cover)(win, here)
        elif symbol == key.ESCAPE:
            if win.covering:
                uncover(win, here)
            return pyglet.event.EVENT_HANDLED          # do not close on esc
        elif symbol == key.B:
            if pipe.proj_mode == "black":
                pipe.proj_mode = state["before_blackout"]
            else:
                state["before_blackout"] = pipe.proj_mode
                pipe.proj_mode = "black"
        elif symbol == key.Q:
            win.close()

    @win.event
    def on_close():
        pipe.running = False
        pipe.projector_window = False

    pyglet.clock.schedule_interval(update, 1 / 120)
    try:
        pyglet.app.run(interval=1 / 60)          # redraw pace, instead of vsync
    except KeyboardInterrupt:
        pass
    pipe.running = False
    time.sleep(0.1)
