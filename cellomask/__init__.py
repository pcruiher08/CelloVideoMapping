"""Cello instance segmentation and image replacement."""

import os

# One BLAS thread: OpenBLAS's pool busy-waits on every core after each small
# matrix operation (the per-frame 3D plane fit), which starved segmentation
# (490% CPU, 10 fps). Set before numpy is first imported.
for _var in ("OPENBLAS_NUM_THREADS", "OMP_NUM_THREADS"):
    os.environ.setdefault(_var, "1")
