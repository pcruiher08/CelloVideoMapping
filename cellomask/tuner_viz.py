"""Draw the live tuner graph: pitch deviation over time, as a wave.

Layout "vertical" (time runs down; "horizontal", the default, runs it left
to right like a scrolling chart, on any canvas shape):

    +--------------------------+
    |        A3   +4 c         |  note, cents, Hz
    |--------|-----------------|
    |        |   ~~            |  the trace: cents off the note (across)
    |       (|                 |  against time (down; newest at the top).
    |        |)    vibrato     |  Vibrato is the wave in it; the dashed line
    |       (|     centre      |  is its running centre, so a vibrato that
    |        |)                |  sits below the note is visible as such.
    |--------|-----------------|
    | VIBRATO 5.6 Hz  +-18 c   |
    | /\\/\\/\\/\\/\\/\\/\\/\\     |  the waveform itself (oscilloscope)
    +--------------------------+

Pure OpenCV drawing, ~2-4 ms per frame.
"""

import math

import cv2
import numpy as np

BG = (14, 11, 11)
GRID = (60, 52, 48)
TEXT = (235, 230, 226)
MUTED = (140, 130, 122)
IN_TUNE = (120, 220, 110)        # BGR green
CLOSE = (60, 200, 235)           # amber
OFF = (80, 90, 240)              # red
ACCENT = (60, 138, 224)          # the app's orange

FONT = cv2.FONT_HERSHEY_DUPLEX
NOTE_NAMES = ["C", "C#", "D", "D#", "E", "F", "F#", "G", "G#", "A", "A#", "B"]


_blank = {}


def blank(w, h):
    """Background-coloured canvas; np.full with a 3-tuple fill costs ~3 ms
    at this size, a cached copy ~0.3 ms."""
    if (w, h) not in _blank:
        _blank.clear()
        _blank[(w, h)] = np.full((h, w, 3), BG, np.uint8)
    return _blank[(w, h)].copy()


def tune_colour(c):
    a = abs(c)
    return IN_TUNE if a < 5 else CLOSE if a < 15 else OFF


def put(img, text, org, scale, colour, thick=1, anchor="left"):
    (w, h), _ = cv2.getTextSize(text, FONT, scale, thick)
    x, y = org
    if anchor == "center":
        x -= w // 2
    elif anchor == "right":
        x -= w
    cv2.putText(img, text, (int(x), int(y)), FONT, scale, colour, thick, cv2.LINE_AA)
    return w, h


def dashed(img, pts, colour, thick=1, dash=10):
    for i in range(0, len(pts) - 1, 2 * max(1, dash // 4)):
        seg = pts[i:i + max(2, dash // 4)]
        if len(seg) >= 2:
            cv2.polylines(img, [seg], False, colour, thick, cv2.LINE_AA)


def render(snap, size=(600, 1200), span=50, seconds=4.0, layout="horizontal",
           scale=1.0, header="top"):
    """Tuner graph as a BGR image of size (w, h) from PitchTracker.snapshot().

    `span` is the cents range shown either side of the note; `seconds` the
    time window of the trace. `layout` is "horizontal" (time left to right,
    newest at the right), "vertical" (time down, newest at the top) or
    "auto" (vertical on a tall canvas). `scale` enlarges text and lines.
    `header="bottom"` puts the note name under the chart instead of above."""
    w, h = size
    portrait = h >= w                       # canvas shape: sets header/footer
    vertical = layout == "vertical" or (layout == "auto" and portrait)
    img = blank(w, h)
    s = min(w, h) / 600 * scale             # text and line scale

    head = int(0.17 * h) if portrait else int(0.2 * h)
    foot = int(0.2 * h) if portrait else int(0.24 * h)
    pad = int(24 * s)
    x0, x1 = pad, w - pad
    if header == "bottom":                  # chart, then note name, then footer
        y0, y1 = pad, h - foot - head
        hy = y1 + int(10 * s)               # header band top
    else:
        y0, y1 = head, h - foot
        hy = 0

    # --- header -----------------------------------------------------------
    note, cents, freq = snap["note"], snap["cents"], snap["freq"]
    if note:
        col = tune_colour(cents)
        letter, sharp, octave = note[0], "#" in note, note[-1]
        base = hy + int(head * 0.62)
        nw, nh = put(img, letter, (w // 2 - int(14 * s), base), 3.2 * s, TEXT, max(2, int(4 * s)), "center")
        right = w // 2 - int(14 * s) + nw // 2 + int(6 * s)
        if sharp:   # a small sharp level with the letter's top; Hershey's "#" at note size is a grid
            (_, sh), _ = cv2.getTextSize("#", FONT, 1.0 * s, max(1, int(2 * s)))
            put(img, "#", (right, base - nh + sh), 1.0 * s, TEXT, max(1, int(2 * s)))
        put(img, octave, (right, base), 1.1 * s, MUTED, max(1, int(2 * s)))
        put(img, f"{cents:+.0f} c", (w // 2, hy + int(head * 0.9)), 1.0 * s, col, max(1, int(2 * s)), "center")
        put(img, f"{freq:.1f} Hz", (x1, hy + int(head * 0.9)), 0.6 * s, MUTED, 1, "right")
    else:
        msg = "no microphone" if snap.get("error") else "play a note"
        put(img, msg, (w // 2, hy + int(head * 0.6)), 1.2 * s, MUTED, max(1, int(2 * s)), "center")
    put(img, f"A4 = {snap['a4']:.0f} Hz", (x0, hy + int(head * 0.9)), 0.6 * s, MUTED, 1)

    # --- chart axes -------------------------------------------------------
    # a horizontal trace on a narrow canvas (the cello) squeezes the vibrato
    # waves together; show less time there so a cycle keeps ~40 px
    if not vertical:
        aspect = (x1 - x0) / max(1, y1 - y0)
        seconds = seconds * min(1.0, aspect / 1.2)

    # vertical: cents across, time down; horizontal: cents up, time across
    if vertical:
        v_lo, v_hi, t_lo, t_hi = x0, x1, y0, y1
    else:
        v_lo, v_hi, t_lo, t_hi = y1, y0, x1, x0     # cents up, newest at right

    def v_px(c):
        return v_lo + (np.clip(c, -span, span) + span) / (2 * span) * (v_hi - v_lo)

    def t_px(age):
        return t_lo + np.clip(age / seconds, 0, 1) * (t_hi - t_lo)

    def pt(c, age):
        return (v_px(c), t_px(age)) if vertical else (t_px(age), v_px(c))

    def pts_of(c, age):                      # vectorised pt() -> int32 Nx2
        v, t = v_px(np.asarray(c)), t_px(np.asarray(age))
        return np.stack([v, t] if vertical else [t, v], 1).astype(np.int32)

    # in-tune band and grid
    band = np.array([pt(-5, 0), pt(5, 0), pt(5, seconds), pt(-5, seconds)], np.int32)
    overlay = img.copy()
    cv2.fillPoly(overlay, [band], (40, 70, 36))
    img = cv2.addWeighted(overlay, 0.6, img, 0.4, 0)
    for c in (-50, -25, -10, 10, 25, 50):
        if abs(c) <= span:
            a, b = pt(c, 0), pt(c, seconds)
            cv2.line(img, tuple(map(int, a)), tuple(map(int, b)), GRID, 1, cv2.LINE_AA)
            lab = f"{c:+d}"
            if vertical:
                put(img, lab, (a[0], y1 + int(16 * s)), 0.42 * s, MUTED, 1, "center")
            else:   # above its line, except the top one; keeps the bottom corners for time
                dy = int(14 * s) if c == span else -int(5 * s)
                put(img, lab, (x0 + int(4 * s), a[1] + dy), 0.42 * s, MUTED, 1)
    a, b = pt(0, 0), pt(0, seconds)
    cv2.line(img, tuple(map(int, a)), tuple(map(int, b)), IN_TUNE, max(1, int(2 * s)), cv2.LINE_AA)

    # --- the trace ----------------------------------------------------------
    # Each held note is drawn against its *own* nearest note, so when the
    # player moves on, earlier notes stay on the chart showing how in tune
    # they were (measuring everything against the current note pushed them
    # off the chart). The header still tunes only the current note.
    hist = snap["hist"]
    if hist:
        a4 = snap["a4"]
        t_now = hist[-1][0]
        ts = np.array([x[0] for x in hist])
        fs = np.array([x[1] for x in hist])
        keep = t_now - ts <= seconds
        ts, fs = ts[keep], fs[keep]
        ages = t_now - ts
        with np.errstate(invalid="ignore", divide="ignore"):
            m = 69 + 12 * np.log2(fs / a4)                  # fractional midi
        voiced = np.isfinite(m)
        # a pitch cannot move 30 cents in 10 ms: that is a note change (or a
        # transition frame mixing two notes), so a new segment starts there
        cut = np.zeros(len(m), bool)
        cut[1:] = np.abs(np.diff(np.where(voiced, m, 0.0))) > 0.3
        brk = np.flatnonzero(np.diff(voiced.astype(int)) != 0) + 1
        brk = np.union1d(brk, np.flatnonzero(cut))
        segs = [r for r in np.split(np.arange(len(m)), brk) if len(r) >= 2 and voiced[r[0]]]

        k, piece = 19, 8            # centre window ~190 ms; colour pieces of 8
        glow = img.copy()
        lines, labels = [], []
        for seg in segs:
            midi = int(round(float(np.median(m[seg]))))
            c = 100 * (m[seg] - midi)
            shown = np.abs(c) <= span * 1.05                 # off-chart is a gap
            # running centre over ~one vibrato period, inside this note only;
            # only where the whole window is in it (a half window at the
            # newest end would follow the vibrato swing, not its middle)
            off = k // 2
            box = np.ones(k)
            total = np.convolve(c, box, "full")[off:off + len(c)]
            count = np.convolve(np.ones(len(c)), box, "full")[off:off + len(c)]
            centre = np.where(count >= k - 0.5, total / count, np.nan)
            ref = centre.copy()                              # carry it forward for colour
            ok = np.isfinite(ref)
            if ok.any():
                idx = np.where(ok, np.arange(len(ref)), 0)
                np.maximum.accumulate(idx, out=idx)
                ref = np.where(ok | (np.arange(len(ref)) > np.argmax(ok)), ref[idx], c)
            else:
                ref = c
            for j in range(0, len(seg) - 1, piece):
                sl = slice(j, j + piece + 1)
                vis = shown[sl]
                if vis.sum() < 2:
                    continue
                colour = tune_colour(float(np.median(ref[sl])))
                pts = pts_of(c[sl][vis], ages[seg][sl][vis])
                cv2.polylines(glow, [pts], False, colour, max(4, int(10 * s)), cv2.LINE_AA)
                lines.append((pts, colour))
            fin = np.isfinite(centre) & shown
            if fin.sum() > 1:
                lines.append((pts_of(centre[fin], ages[seg][fin]), None))
            if ages[seg[0]] - ages[seg[-1]] >= 0.25:         # label notes held a moment
                labels.append((ages[seg[0]], NOTE_NAMES[midi % 12] + str(midi // 12 - 1)))
        if lines:
            img = cv2.addWeighted(glow, 0.25, img, 0.75, 0)
        for pts, colour in lines:
            if colour is None:
                dashed(img, pts, TEXT, 1, dash=int(16 * s))
            else:
                cv2.polylines(img, [pts], False, colour, max(2, int(3 * s)), cv2.LINE_AA)
        # note names where each note starts, along the top (or right) edge
        last_px = None
        for age, name in sorted(labels, reverse=True):       # oldest first
            x, y = pt(span * 0.86, age)
            pos = x if not vertical else y
            if last_px is not None and abs(pos - last_px) < 46 * s:
                continue                                     # too close to the last label
            last_px = pos
            if vertical:
                put(img, name, (x1 - int(4 * s), y + int(5 * s)), 0.5 * s, MUTED, 1, "right")
            else:
                lx = max(x + 3 * s, x0 + 40 * s)          # clear of the "+50" scale label
                put(img, name, (int(lx), y0 + int(18 * s)), 0.5 * s, MUTED, 1)
                cv2.line(img, (int(x), y0), (int(x), y0 + int(6 * s)), MUTED, 1, cv2.LINE_AA)
        # newest point
        if segs and segs[-1][-1] == len(m) - 1:
            seg = segs[-1]
            cn = 100 * (m[seg[-1]] - round(float(np.median(m[seg]))))
            if abs(cn) <= span * 1.05:
                cv2.circle(img, tuple(map(int, pt(cn, 0))), max(4, int(7 * s)), tune_colour(cn), -1, cv2.LINE_AA)

    if vertical:
        put(img, "now", (x0 - int(2 * s), y0 - int(6 * s)), 0.42 * s, MUTED, 1)
        put(img, f"-{seconds:.0f}s", (x0 - int(2 * s), y1 - int(6 * s)), 0.42 * s, MUTED, 1)
    else:
        put(img, "now", (x1, y1 + int(18 * s)), 0.42 * s, MUTED, 1, "right")
        put(img, f"-{seconds:.1f}s".replace(".0s", "s"), (x0, y1 + int(18 * s)), 0.42 * s, MUTED, 1)

    # --- footer: vibrato readout + oscilloscope ------------------------------
    fy = h - foot + int(36 * s)
    v = snap["vibrato"]
    if v and v.get("present"):
        put(img, "VIBRATO", (x0, fy), 0.6 * s, MUTED, 1)
        put(img, f"{v['rate']:.1f} Hz   +-{v['extent']:.0f} c", (x0 + int(110 * s), fy), 0.8 * s, ACCENT, max(1, int(2 * s)))
    else:
        put(img, "VIBRATO", (x0, fy), 0.6 * s, MUTED, 1)
        put(img, "-", (x0 + int(110 * s), fy), 0.8 * s, MUTED, 1)

    wave = snap["wave"]
    oy0, oy1 = fy + int(14 * s), h - pad
    if len(wave) and oy1 - oy0 > 10:
        cv2.rectangle(img, (x0, oy0), (x1, oy1), GRID, 1)
        # trigger on a rising zero crossing so the wave stands still
        seg = wave
        if freq:
            period = snap["sr"] / freq
            show = int(min(len(wave) - 1, period * 4))
            zc = np.flatnonzero((wave[:-1] < 0) & (wave[1:] >= 0))
            zc = zc[zc < len(wave) - show]
            start = int(zc[0]) if len(zc) else 0
            seg = wave[start:start + show]
        peak = max(float(np.abs(seg).max()), 1e-4)
        xs = np.linspace(x0, x1, len(seg))
        mid = (oy0 + oy1) / 2
        ys = mid - seg / peak * (oy1 - oy0) * 0.42
        cv2.polylines(img, [np.stack([xs, ys], 1).astype(np.int32)], False,
                      ACCENT if note else MUTED, max(1, int(2 * s)), cv2.LINE_AA)
    return img


def render_cello(snap, size=(450, 1350), position=0.2, body_start=0.38,
                 pad=1.05, scale=1.35, **kw):
    """The graph laid out for a cello, as the warp texture (top = scroll).

    The graph is one block the size of the cello's body: chart on top, then
    note name and vibrato, then the waveform. The neck above is left empty;
    once masked it is a sliver that would crop anything put there.

    `body_start` is where the body begins, as a fraction of the visible
    length from the scroll end. It is measured from the mask each frame
    (AxisTracker.body_start), since in a close or cropped shot the visible
    cello is mostly body. `position` puts the in-tune line that far into the
    body (0 = its top, 1 = its bottom). `pad` is the warp's margin around the
    cello (composite.place_warp), which the texture has to allow for.

    `size` should have the visible cello's width-to-length (about 1:3 for a
    whole cello) so cover-fitting it onto the cello crops nothing.""" 
    w, h = size
    # mask fraction -> texture fraction (the texture spans length * pad)
    start = int(h * (0.5 + (np.clip(body_start, 0.0, 0.7) - 0.5) / pad))
    end = int(h * (0.5 + 0.5 / pad))
    bh = max(int(0.35 * h), end - start)
    block = render(snap, (w, bh), scale=scale, header="bottom", **kw)
    # where render(header="bottom") draws the chart's zero line in the block
    s = min(w, bh) / 600 * scale
    head, foot, top_pad = int(0.17 * bh), int(0.2 * bh), int(24 * s)
    zero = (top_pad + (bh - foot - head)) / 2
    top = int(np.clip(start + position * bh - zero, 0, h - bh))
    img = blank(w, h)
    img[top:top + bh] = block
    return img
