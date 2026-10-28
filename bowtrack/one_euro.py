"""One Euro filter — low-lag adaptive smoothing for noisy tracking signals.

Reference: Casiez, Roussel, Vogel (CHI 2012). Low cutoff kills jitter when the
signal is slow; the cutoff opens up when the signal moves fast, so there is no
visible lag on fast bow strokes.
"""

import math


class OneEuroFilter:
    def __init__(self, freq=30.0, min_cutoff=1.0, beta=0.007, d_cutoff=1.0):
        self.freq = freq
        self.min_cutoff = min_cutoff
        self.beta = beta
        self.d_cutoff = d_cutoff
        self._x_prev = None
        self._dx_prev = 0.0
        self._t_prev = None

    @staticmethod
    def _alpha(cutoff, dt):
        tau = 1.0 / (2.0 * math.pi * cutoff)
        return 1.0 / (1.0 + tau / dt)

    def reset(self):
        self._x_prev = None
        self._dx_prev = 0.0
        self._t_prev = None

    def __call__(self, x, t):
        if self._x_prev is None:
            self._x_prev = x
            self._t_prev = t
            return x
        dt = max(t - self._t_prev, 1e-6)
        self._t_prev = t

        dx = (x - self._x_prev) / dt
        a_d = self._alpha(self.d_cutoff, dt)
        dx_hat = a_d * dx + (1.0 - a_d) * self._dx_prev
        self._dx_prev = dx_hat

        cutoff = self.min_cutoff + self.beta * abs(dx_hat)
        a = self._alpha(cutoff, dt)
        x_hat = a * x + (1.0 - a) * self._x_prev
        self._x_prev = x_hat
        return x_hat


class AngleOneEuroFilter(OneEuroFilter):
    """One Euro filter for angles in degrees, unwrapping across the ±180 seam."""

    def __call__(self, angle_deg, t):
        if self._x_prev is not None:
            # Unwrap: shift the incoming angle to the branch nearest the state.
            while angle_deg - self._x_prev > 180.0:
                angle_deg -= 360.0
            while angle_deg - self._x_prev < -180.0:
                angle_deg += 360.0
        out = super().__call__(angle_deg, t)
        # Re-wrap both output and internal state to (-180, 180].
        wrapped = ((out + 180.0) % 360.0) - 180.0
        self._x_prev += wrapped - out
        return wrapped
