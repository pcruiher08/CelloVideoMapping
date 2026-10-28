"""Quad warp (corner-pin) for projection mapping.

The renderer draws generative content into an off-screen buffer whose
coordinate space is the unit square. This module maps that unit square onto
an arbitrary quadrilateral on the projector, so the content lands squarely on
a physical surface that the projector sees at an angle.

Corners are stored normalized to [0, 1] in projector space, origin top-left,
in the order TL, TR, BR, BL. They are resolution independent, so a saved
calibration survives a change of projector resolution.
"""

import json
import os

import cv2
import numpy as np

# TL, TR, BR, BL — the identity quad fills the whole projector.
DEFAULT_CORNERS = [(0.0, 0.0), (1.0, 0.0), (1.0, 1.0), (0.0, 1.0)]
CORNER_NAMES = ("top-left", "top-right", "bottom-right", "bottom-left")

# The matching corners of the content square, in the SAME order (TL, TR, BR,
# BL). Content space is y-up (OpenGL's convention, and what the shaders use)
# while projector space is y-down (top-left origin, what a person expects), so
# the two squares are listed with opposite vertical order. The homography
# absorbs that flip, which keeps "top-left" meaning the visually top-left
# corner of the projection when you are nudging it.
_CONTENT_QUAD = np.array([(0.0, 1.0), (1.0, 1.0), (1.0, 0.0), (0.0, 0.0)],
                         dtype=np.float32)


class QuadWarp:
    def __init__(self, corners=None):
        self.corners = [tuple(c) for c in (corners or DEFAULT_CORNERS)]

    # ---------------- homography ----------------

    def matrix(self):
        """3x3 mapping content uv (unit square) -> projector uv."""
        dst = np.array(self.corners, dtype=np.float32)
        return cv2.getPerspectiveTransform(_CONTENT_QUAD, dst)

    def inverse(self):
        """3x3 mapping projector uv -> content uv.

        This is the direction the fragment shader needs: for each output
        pixel, find which bit of content belongs there.
        """
        return np.linalg.inv(self.matrix())

    # ---------------- editing ----------------

    def nudge(self, index, dx, dy):
        """Move one corner by (dx, dy) in normalized units, clamped a little
        outside the screen so off-screen surfaces stay reachable."""
        x, y = self.corners[index]
        self.corners[index] = (float(np.clip(x + dx, -0.5, 1.5)),
                               float(np.clip(y + dy, -0.5, 1.5)))

    def set_corner(self, index, x, y):
        self.corners[index] = (float(np.clip(x, -0.5, 1.5)),
                               float(np.clip(y, -0.5, 1.5)))

    def nearest_corner(self, x, y, max_dist=0.08):
        """Index of the corner closest to (x, y) in projector space, or None
        if the click was not near one. Used for click-and-drag calibration."""
        best, best_d = None, max_dist
        for i, (cx, cy) in enumerate(self.corners):
            d = float(np.hypot(cx - x, cy - y))
            if d < best_d:
                best, best_d = i, d
        return best

    def reset(self):
        self.corners = [tuple(c) for c in DEFAULT_CORNERS]

    # ---------------- persistence ----------------

    def save(self, path):
        with open(path, "w") as f:
            json.dump({"corners": [list(c) for c in self.corners]}, f, indent=2)

    def load(self, path):
        with open(path) as f:
            self.corners = [tuple(c) for c in json.load(f)["corners"]]

    @classmethod
    def load_or_default(cls, path):
        w = cls()
        if path and os.path.exists(path):
            try:
                w.load(path)
            except (OSError, ValueError, KeyError) as e:
                print(f"Could not read warp config {path}: {e}; using defaults.")
        return w
