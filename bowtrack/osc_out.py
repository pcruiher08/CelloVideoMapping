"""Optional OSC output so videomapping tools (TouchDesigner, MadMapper,
Resolume, Processing...) can consume the tracking data live.

Messages sent per tracked frame:
  /bow/xy      nx ny          (normalized 0..1, origin top-left)
  /bow/angle   degrees        (0 = horizontal, CCW positive)
  /bow/ends    ax ay bx by    (normalized endpoints)
  /bow/speed   px_per_s
  /bow/ok      1|0
"""

from pythonosc.udp_client import SimpleUDPClient


class OSCSender:
    def __init__(self, host="127.0.0.1", port=9000):
        self.client = SimpleUDPClient(host, port)

    def send(self, st, metrics, frame_size):
        w, h = frame_size
        self.client.send_message("/bow/ok", 1 if st.ok else 0)
        if not st.ok:
            return
        self.client.send_message("/bow/xy", [st.nx, st.ny])
        self.client.send_message("/bow/angle", st.angle)
        if st.a is not None:
            self.client.send_message("/bow/ends", [
                st.a[0] / w, st.a[1] / h, st.b[0] / w, st.b[1] / h,
            ])
        self.client.send_message("/bow/speed", metrics.speed)
