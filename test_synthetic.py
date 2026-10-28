"""Headless pipeline test: render synthetic frames with two orange markers
moving like a bow stroke, and verify tracked x, y and angle against ground
truth. Run with: .venv/bin/python test_synthetic.py
"""

import numpy as np
import cv2

from bowtrack.tracker import BowTracker
from bowtrack.metrics import Metrics

W, H = 1280, 720
ORANGE_BGR = (20, 110, 240)  # typical orange gaffer under neutral light


def make_frame(cx, cy, angle_deg, length=420):
    frame = np.full((H, W, 3), (60, 55, 50), dtype=np.uint8)
    # Distractor skin-tone-ish patch to make sure min_area/HSV rejects noise.
    cv2.circle(frame, (100, 100), 3, (150, 170, 200), -1)
    dx = np.cos(np.radians(angle_deg)) * length / 2
    dy = -np.sin(np.radians(angle_deg)) * length / 2
    a = (int(cx - dx), int(cy - dy))
    b = (int(cx + dx), int(cy + dy))
    cv2.circle(frame, a, 9, ORANGE_BGR, -1)
    cv2.circle(frame, b, 9, ORANGE_BGR, -1)
    return frame, a, b


def main():
    tracker = BowTracker()
    metrics = Metrics()
    n = 120
    errs_pos, errs_ang = [], []
    t = 0.0
    for i in range(n):
        t += 1 / 30
        phase = i / n
        cx = 400 + 500 * phase              # sweep right, like a down-bow
        cy = 360 + 60 * np.sin(phase * np.pi * 2)
        ang = -20 + 35 * phase              # angle drifts through the stroke
        frame, a, b = make_frame(cx, cy, ang)
        st = tracker.update(frame, t=t)
        assert st.ok, f"lost tracking at frame {i}"
        metrics.push(st)
        if i > 10:  # skip filter warm-up
            errs_pos.append(np.hypot(st.x - cx, st.y - cy))
            # angle mod 180 (A/B identity is arbitrary on first lock)
            d = abs((st.angle - ang + 90) % 180 - 90)
            errs_ang.append(d)

    print(f"pos error  mean {np.mean(errs_pos):.2f}px  max {np.max(errs_pos):.2f}px")
    print(f"angle error mean {np.mean(errs_ang):.2f}deg max {np.max(errs_ang):.2f}deg")
    print(f"final: x={st.x:.1f} y={st.y:.1f} angle={st.angle:+.1f} "
          f"speed={metrics.speed:.0f}px/s dir={metrics.direction}")
    assert np.mean(errs_pos) < 6, "position error too high"
    assert np.mean(errs_ang) < 3, "angle error too high"
    assert metrics.speed > 100, "speed should reflect the sweep"

    # Occlusion: markers vanish for a few frames -> coast, then reacquire.
    blank = np.full((H, W, 3), (60, 55, 50), dtype=np.uint8)
    for _ in range(4):
        t += 1 / 30
        st = tracker.update(blank, t=t)
    assert st.ok and not st.fresh, "should coast through short occlusion"
    t += 1 / 30
    frame, _, _ = make_frame(900, 360, 15)
    st = tracker.update(frame, t=t)
    assert st.ok and st.fresh, "should reacquire after occlusion"

    print("ALL TESTS PASSED")


if __name__ == "__main__":
    main()
