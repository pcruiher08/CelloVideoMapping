"""Fullscreen projector window (pyglet, main thread).

Shows Pipeline.proj_frame, already in projector pixels, at the screen's
refresh rate. A native window skips the browser's JPEG encode/decode and
polling, which matters for how far the light trails a moving cello.

Keys in the window:  f  toggle fullscreen   b  blackout on/off
                     esc  leave fullscreen   q  quit the app

The web page's Projector section lists the screens and moves the window to
another one live (pipe.screen_request, handled here on the main thread).
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


def open_window(pipe, spec="auto", fullscreen=True):
    import pyglet
    idx, screen = pick_screen(spec)
    pipe.screens, pipe.screen_index = list_screens(), idx
    if fullscreen and len(pyglet.display.get_display().get_screens()) == 1:
        # no projector connected: a black fullscreen window with the pointer
        # hidden over the only screen looked like a frozen Mac
        print("no second screen: opening the projector window as a normal window "
              "(connect the projector, set it to extend, and restart)")
        fullscreen = False
    if fullscreen:
        win = pyglet.window.Window(screen=screen, fullscreen=True, vsync=True,
                                   caption="Cello projector")
    else:
        win = pyglet.window.Window(width=screen.width // 2, height=screen.height // 2,
                                   screen=screen, resizable=True, vsync=True,
                                   caption="Cello projector")
    # draw in the projector's own pixels; a windowed test keeps the screen size
    # so the calibration is the same as fullscreen
    pipe.proj_size = (screen.width, screen.height)
    pipe.projector_window = True
    return win


def run_window(pipe, win):
    import pyglet
    from pyglet import gl

    state = {"seq": -1, "image": None, "before_blackout": "content", "drawn": -1, "bright": None,
             "listed": time.time()}

    def move(idx):
        """Fullscreen on screen `idx` (from the web page)."""
        screens = pyglet.display.get_display().get_screens()
        if not 0 <= idx < len(screens):
            return
        s = screens[idx]
        win.set_fullscreen(True, screen=s)
        win.set_mouse_visible(False)
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
        state["seq"] = pipe.proj_seq
        f = pipe.proj_frame
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
            gl.glTexParameteri(gl.GL_TEXTURE_2D, gl.GL_TEXTURE_MAG_FILTER, gl.GL_LINEAR)
            img.blit(0, 0, width=win.width, height=win.height)
            if state["drawn"] != state["seq"]:
                state["drawn"] = state["seq"]
                pipe.mark_drawn(state["seq"], time.time(), state["bright"])

    @win.event
    def on_key_press(symbol, modifiers):
        from pyglet.window import key
        if symbol == key.F:
            win.set_fullscreen(not win.fullscreen)
            win.set_mouse_visible(not win.fullscreen)
        elif symbol == key.ESCAPE:
            if win.fullscreen:
                win.set_fullscreen(False)
                win.set_mouse_visible(True)
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

    win.set_mouse_visible(not win.fullscreen)     # hidden only on the projector
    pyglet.clock.schedule_interval(update, 1 / 120)
    try:
        pyglet.app.run()
    except KeyboardInterrupt:
        pass
    pipe.running = False
    time.sleep(0.1)
