"""Rolling history and derived metrics (velocity, bow direction)."""

import time
from collections import deque

import numpy as np


class Metrics:
    def __init__(self, seconds=6.0, fps_hint=30):
        self.maxlen = int(seconds * fps_hint * 2)
        self.t = deque(maxlen=self.maxlen)
        self.x = deque(maxlen=self.maxlen)
        self.y = deque(maxlen=self.maxlen)
        self.angle = deque(maxlen=self.maxlen)
        self.window = seconds
        self.speed = 0.0          # px/s of the midpoint
        self.axial_vel = 0.0      # signed velocity along the bow axis (px/s)
        self.direction = "-"      # "DOWN" / "UP" / "-"

    def push(self, st):
        self.t.append(st.t)
        self.x.append(st.x)
        self.y.append(st.y)
        self.angle.append(st.angle)
        self._update_velocity(st)

    def _update_velocity(self, st):
        # Velocity over a ~100 ms window to stay stable at webcam noise levels.
        tnow = st.t
        i = len(self.t) - 1
        j = i
        while j > 0 and tnow - self.t[j - 1] < 0.1:
            j -= 1
        dt = self.t[i] - self.t[j]
        if dt <= 0:
            return
        dx = (self.x[i] - self.x[j]) / dt
        dy = (self.y[i] - self.y[j]) / dt
        self.speed = float(np.hypot(dx, dy))
        # Project motion onto the bow axis (unit vector at st.angle).
        ux = np.cos(np.radians(st.angle))
        uy = -np.sin(np.radians(st.angle))   # screen y is flipped
        self.axial_vel = float(dx * ux + dy * uy)
        if abs(self.axial_vel) < 15:  # px/s dead zone
            self.direction = "-"
        else:
            # Toward B = "down-bow" by convention (frog->tip travel).
            self.direction = "DOWN" if self.axial_vel > 0 else "UP"

    def recent(self, series):
        """Return (times, values) clipped to the display window."""
        if not self.t:
            return np.array([]), np.array([])
        tnow = self.t[-1]
        ts = np.array(self.t)
        vs = np.array(series)
        keep = ts >= tnow - self.window
        return ts[keep], vs[keep]

    def clear(self):
        for d in (self.t, self.x, self.y, self.angle):
            d.clear()
        self.speed = self.axial_vel = 0.0
        self.direction = "-"


class FPSCounter:
    def __init__(self, n=30):
        self.times = deque(maxlen=n)

    def tick(self):
        self.times.append(time.time())

    @property
    def fps(self):
        if len(self.times) < 2:
            return 0.0
        dt = self.times[-1] - self.times[0]
        return (len(self.times) - 1) / dt if dt > 0 else 0.0
