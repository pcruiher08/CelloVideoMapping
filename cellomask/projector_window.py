"""Fullscreen projector window (pyglet, main thread).

Shows Pipeline.proj_frame, already in projector pixels, at the screen's
refresh rate. A native window skips the browser's JPEG encode/decode and
polling, which matters for how far the light trails a moving cello.

Keys in the window:  f  toggle fullscreen   b  blackout on/off
                     esc  leave fullscreen   q  quit the app
"""

import time

import numpy as np


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
    return screens[idx]


def open_window(pipe, spec="auto", fullscreen=True):
    import pyglet
    screen = pick_screen(spec)
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

    state = {"seq": -1, "image": None, "before_blackout": "content", "drawn": -1, "bright": None}

    def update(dt):
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
        elif symbol == key.ESCAPE:
            if win.fullscreen:
                win.set_fullscreen(False)
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

    win.set_mouse_visible(False)
    pyglet.clock.schedule_interval(update, 1 / 120)
    try:
        pyglet.app.run()
    except KeyboardInterrupt:
        pass
    pipe.running = False
    time.sleep(0.1)
