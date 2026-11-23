"""The bow tracker in its own process.

Run in the app's process, the bow tracker (~35 ms a frame of numpy and
OpenCV in Python) held the interpreter lock for much of each frame: the
cello's tracking dropped from ~22 to ~12 fps, the light lagged 330 ms
behind the cello instead of ~120 and flickered. Here it runs on its own
core; the app hands it each depth frame and the cello's pose through a pipe
and waits for the answer, which releases the lock while it waits.

    python -m cellomask.bowproc        # the worker (started by BowProcess)

Messages both ways: 4-byte little-endian length, then a pickle. Requests:
{"depth", "K", "size", "cello", "t"}; replies: the tracker's state dict.
The worker exits when its input closes (the app quit or died).
"""

import os
import pickle
import struct
import subprocess
import sys
import threading

from .procam3d import ROOT


def _send(f, obj):
    data = pickle.dumps(obj, protocol=pickle.HIGHEST_PROTOCOL)
    f.write(struct.pack("<I", len(data)))
    f.write(data)
    f.flush()


def _recv(f):
    head = f.read(4)
    if len(head) < 4:
        return None
    n = struct.unpack("<I", head)[0]
    data = f.read(n)
    if len(data) < n:
        return None
    return pickle.loads(data)


class BowProcess:
    """BowTracker.update() and .state, computed in a worker process."""

    def __init__(self):
        self.proc = None
        self.state = None
        self.lock = threading.Lock()

    def _start(self):
        self.proc = subprocess.Popen([sys.executable, "-m", "cellomask.bowproc"], cwd=ROOT,
                                     stdin=subprocess.PIPE, stdout=subprocess.PIPE)

    def update(self, pkt, K, size, cello=None, t=None):
        """As BowTracker.update; None when the bow is not found (or the
        worker failed: it is started again on the next frame)."""
        with self.lock:
            if self.proc is None or self.proc.poll() is not None:
                if self.proc is not None:
                    print(f"bow worker exited ({self.proc.returncode}); starting it again")
                self._start()
            try:
                _send(self.proc.stdin, {"depth": pkt["depth"], "K": K, "size": size, "cello": cello, "t": t})
                st = _recv(self.proc.stdout)
            except (BrokenPipeError, OSError, EOFError, pickle.UnpicklingError) as e:
                print(f"bow worker: {e!r}")
                st = None
            if st is None:                   # died mid-frame
                self.close()
                self.state = {"ok": False}
                return None
            self.state = st
            return st if st.get("ok") else None

    def close(self):
        p, self.proc = self.proc, None
        if p is None:
            return
        try:
            p.stdin.close()
            p.wait(timeout=2)
        except Exception:
            p.kill()


def main():
    from .bow import BowTracker
    bt = BowTracker()
    inp, out = sys.stdin.buffer, sys.stdout.buffer
    # nothing else may write to the reply pipe
    sys.stdout = sys.stderr
    while True:
        msg = _recv(inp)
        if msg is None:
            return
        bt.update({"depth": msg["depth"]}, msg["K"], msg["size"], msg["cello"], t=msg["t"])
        _send(out, bt.state or {"ok": False})


if __name__ == "__main__":
    os.environ.setdefault("PYTHONWARNINGS", "ignore")
    main()
