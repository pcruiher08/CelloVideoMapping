"""Visual overlay + side metrics panel, all drawn with OpenCV."""

import numpy as np
import cv2

PANEL_W = 340
ORANGE = (0, 140, 255)
CYAN = (255, 220, 80)
GREEN = (120, 220, 120)
WHITE = (235, 235, 235)
GREY = (110, 110, 110)
DARK = (28, 24, 22)
RED = (80, 80, 240)

FONT = cv2.FONT_HERSHEY_SIMPLEX


def draw_overlay(frame, st, metrics, trail):
    """Draw bow line, endpoints, angle readout and motion trail on the frame."""
    if st.ok and st.a is not None:
        a = (int(st.a[0]), int(st.a[1]))
        b = (int(st.b[0]), int(st.b[1]))
        color = ORANGE if st.fresh else GREY
        cv2.line(frame, a, b, color, 2, cv2.LINE_AA)
        cv2.circle(frame, a, 7, CYAN, 2, cv2.LINE_AA)
        cv2.circle(frame, b, 7, GREEN, 2, cv2.LINE_AA)
        cv2.putText(frame, "A", (a[0] + 10, a[1] - 10), FONT, 0.5, CYAN, 1, cv2.LINE_AA)
        cv2.putText(frame, "B", (b[0] + 10, b[1] - 10), FONT, 0.5, GREEN, 1, cv2.LINE_AA)

        mid = (int(st.x), int(st.y))
        cv2.drawMarker(frame, mid, WHITE, cv2.MARKER_CROSS, 14, 2)

        # Angle arc around the midpoint.
        cv2.ellipse(frame, mid, (34, 34), 0, 0, -st.angle, WHITE, 1, cv2.LINE_AA)
        cv2.line(frame, mid, (mid[0] + 44, mid[1]), GREY, 1, cv2.LINE_AA)
        cv2.putText(frame, f"{st.angle:+.1f} deg", (mid[0] + 14, mid[1] + 26),
                    FONT, 0.55, WHITE, 1, cv2.LINE_AA)

    # Midpoint trail (fading).
    n = len(trail)
    for i in range(1, n):
        f = i / n
        col = tuple(int(c * f) for c in ORANGE)
        cv2.line(frame, trail[i - 1], trail[i], col, 2, cv2.LINE_AA)
    return frame


def _sparkline(panel, ts, vs, y0, h, label, color, vmin=None, vmax=None, unit=""):
    x0, x1 = 14, PANEL_W - 14
    y1 = y0 + h
    cv2.rectangle(panel, (x0, y0), (x1, y1), (50, 46, 44), 1)
    cv2.putText(panel, label, (x0, y0 - 6), FONT, 0.45, GREY, 1, cv2.LINE_AA)
    if len(ts) < 2:
        return y1
    if vmin is None:
        vmin, vmax = float(np.min(vs)), float(np.max(vs))
        if vmax - vmin < 1e-3:
            vmax = vmin + 1e-3
    tmin, tmax = ts[0], ts[-1]
    if tmax - tmin < 1e-6:
        return y1
    px = (x0 + (ts - tmin) / (tmax - tmin) * (x1 - x0)).astype(int)
    py = (y1 - (np.clip(vs, vmin, vmax) - vmin) / (vmax - vmin) * (h - 4) - 2).astype(int)
    pts = np.stack([px, py], axis=1).reshape(-1, 1, 2)
    cv2.polylines(panel, [pts], False, color, 1, cv2.LINE_AA)
    cv2.putText(panel, f"{vs[-1]:.1f}{unit}", (x1 - 78, y0 + 16),
                FONT, 0.5, color, 1, cv2.LINE_AA)
    return y1


def draw_panel(h, st, metrics, fps, hsv_lo, hsv_hi, calibrating):
    panel = np.full((h, PANEL_W, 3), DARK, dtype=np.uint8)
    cv2.putText(panel, "BOW TRACKER", (14, 30), FONT, 0.7, WHITE, 2, cv2.LINE_AA)
    status = ("TRACKING" if st.fresh else "COASTING") if st.ok else "LOST"
    scolor = GREEN if st.fresh else (ORANGE if st.ok else RED)
    cv2.putText(panel, status, (14, 56), FONT, 0.55, scolor, 1, cv2.LINE_AA)
    cv2.putText(panel, f"{fps:.1f} fps", (PANEL_W - 100, 56),
                FONT, 0.5, GREY, 1, cv2.LINE_AA)

    y = 84
    rows = [
        ("x", f"{st.x:7.1f} px   ({st.nx:.3f})", CYAN),
        ("y", f"{st.y:7.1f} px   ({st.ny:.3f})", CYAN),
        ("angle", f"{st.angle:+7.1f} deg", WHITE),
        ("speed", f"{metrics.speed:7.0f} px/s", GREEN),
        ("bow dir", f"{metrics.direction:>7}", ORANGE),
    ]
    for name, val, col in rows:
        cv2.putText(panel, name, (14, y), FONT, 0.5, GREY, 1, cv2.LINE_AA)
        cv2.putText(panel, val, (100, y), FONT, 0.5, col, 1, cv2.LINE_AA)
        y += 26

    y += 14
    ts, xs = metrics.recent(metrics.x)
    y = _sparkline(panel, ts, xs, y, 56, "x (px)", CYAN) + 30
    ts, ys_ = metrics.recent(metrics.y)
    y = _sparkline(panel, ts, ys_, y, 56, "y (px)", CYAN) + 30
    ts, an = metrics.recent(metrics.angle)
    y = _sparkline(panel, ts, an, y, 56, "angle (deg)", WHITE,
                   vmin=-90, vmax=90) + 30

    # HSV range + help.
    cv2.putText(panel, f"HSV lo {tuple(int(v) for v in hsv_lo)}", (14, y),
                FONT, 0.42, GREY, 1, cv2.LINE_AA); y += 18
    cv2.putText(panel, f"HSV hi {tuple(int(v) for v in hsv_hi)}", (14, y),
                FONT, 0.42, GREY, 1, cv2.LINE_AA); y += 26
    if calibrating:
        cv2.putText(panel, "CALIBRATE: click the tape", (14, y),
                    FONT, 0.5, ORANGE, 1, cv2.LINE_AA); y += 20

    help_lines = ["c calibrate   m mask   r reset", "s save cfg    q quit"]
    for line in help_lines:
        y = min(y, h - 40)
        cv2.putText(panel, line, (14, h - 40 + help_lines.index(line) * 18),
                    FONT, 0.42, GREY, 1, cv2.LINE_AA)
    return panel


def compose(frame, panel):
    return np.hstack([frame, panel])
