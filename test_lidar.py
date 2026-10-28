"""Closed-loop check of the iPhone LiDAR 3D projector calibration.

A fake iPhone looks at a 3D room (wall, floor and an ellipsoid "cello")
lit by whatever the app projects through a known projector, and streams
colour + noisy 256x192 depth like the CelloDepth app. The real Pipeline
calibrates through it, and the solved projector is compared with the truth.
Also checks the stream parsing, turning portrait frames upright, and the
per-frame 3D mapping of a cello leaning and turning (vs the flat mapping).

    .venv/bin/python test_lidar.py
"""

import argparse
import tempfile
import json
import os
import struct
import sys
import time
import zlib

import cv2
import numpy as np

ROOT = os.path.dirname(os.path.abspath(__file__))
CAM = (1280, 960)
K_CAM = np.array([[1040.0, 0, 639.5], [0, 1040.0, 479.5], [0, 0, 1]])
PROJ = (1920, 1080)
K_PROJ = np.array([[2300.0, 0, 960], [0, 2300.0, 1150], [0, 0, 1]])   # lens shift: centre below the image
R_PROJ = cv2.Rodrigues(np.radians([4.0, -8.0, 1.0]))[0]
T_PROJ = np.array([0.35, 0.05, 0.02])                                   # 35 cm to the side


def scene_depth():
    """Depth (z, metres) of the room for every camera pixel."""
    u, v = np.meshgrid(np.arange(CAM[0]), np.arange(CAM[1]))
    rx, ry = (u - K_CAM[0, 2]) / K_CAM[0, 0], (v - K_CAM[1, 2]) / K_CAM[1, 1]
    z = np.full(u.shape, 3.0)                                   # wall
    with np.errstate(divide="ignore", invalid="ignore"):
        zf = np.where(ry > 0, 0.9 / ry, np.inf)                 # floor 0.9 m below the camera
    z = np.minimum(z, zf)
    # the "cello": ellipsoid centre (0, 0.15, 2.2), radii 0.25 x 0.6 x 0.15
    c, r = np.array([0.0, 0.15, 2.2]), np.array([0.25, 0.6, 0.15])
    d = np.stack([rx, ry, np.ones_like(rx)], -1) / r
    o = -c / r
    a, b, cc = (d * d).sum(-1), 2 * (d * o).sum(-1), (o * o).sum() - 1
    disc = b * b - 4 * a * cc
    t = np.where(disc > 0, (-b - np.sqrt(np.maximum(disc, 0))) / (2 * a), np.inf)
    cello = (t > 0) & (t < z)
    z = np.where(cello, t, z)
    X = np.stack([rx * z, ry * z, z], -1)
    return z.astype(np.float32), X, cello


class FakeIPhone:
    """Stands in for cellomask.iphone.IPHONE."""

    def __init__(self, pipe):
        self.pipe = pipe
        self.z, X, cello = scene_depth()
        p = cv2.projectPoints(X.reshape(-1, 1, 3), cv2.Rodrigues(R_PROJ)[0], T_PROJ, K_PROJ,
                              np.zeros(5))[0].reshape(CAM[1], CAM[0], 2)
        self.map = p.astype(np.float32)
        rng = np.random.default_rng(0)
        tex = cv2.GaussianBlur(rng.uniform(0.7, 1.0, (CAM[1], CAM[0])).astype(np.float32), (0, 0), 3)
        self.albedo = np.where(cello, 0.55, 0.75) * tex
        self.albedo = np.repeat(self.albedo[..., None], 3, 2) * np.where(cello[..., None], [0.5, 0.8, 1.0], 1.0)
        self.rng = rng
        self.current = None
        # what the projector showed a few frames ago: the real phone's image
        # lags the projector by ~100 ms (capture, encode, Wi-Fi, decode)
        self.lag = [None] * 4
        self.live, self.fps, self.connected, self.error = True, 30.0, 1, None
        self.lat, self.rtt, self.offset, self.syncs = {}, None, None, []

    def packet(self):
        light = np.zeros((CAM[1], CAM[0], 3), np.float32)
        self.lag = self.lag[1:] + [self.pipe.proj_frame]
        shown = self.lag[0]
        if shown is not None:
            light = cv2.remap(shown, self.map[..., 0], self.map[..., 1],
                              cv2.INTER_LINEAR, borderValue=0).astype(np.float32)
        img = self.albedo * (40 + 0.8 * light) + self.rng.normal(0, 2, light.shape)
        depth = cv2.resize(self.z, (256, 192), interpolation=cv2.INTER_AREA)
        depth = depth + self.rng.normal(0, 0.005, depth.shape).astype(np.float32)
        return {"bgr": np.clip(img, 0, 255).astype(np.uint8), "depth": depth,
                "conf": np.full(depth.shape, 2, np.uint8), "K": K_CAM.copy(), "size": CAM,
                "ts": time.time(), "orientation": "landscapeLeft"}

    def read(self, timeout=1.0):
        time.sleep(1 / 30)
        self.current = self.packet()
        return True, self.current["bgr"]

    def depth_frames(self, n=15, timeout=5.0):
        out = []
        for _ in range(n):
            time.sleep(1 / 30)
            out.append(self.packet())
        return out

    def lock(self, on=True, timeout=3.0):
        return True                                # exposure is fixed in this world anyway

    def release(self):
        pass


def check(name, ok, detail):
    print(f"{'PASS' if ok else 'FAIL'}  {name:34s} {detail}")
    return ok


def message(bgr, depth, K, orientation, compact=False):
    """A CelloDepth stream message, as the iPhone app builds it. `compact`:
    as the current app sends it, the JPEG at 3/4 size (K and w x h still
    describe the full image) and depth + confidence deflated."""
    small = cv2.resize(bgr, None, fx=0.75, fy=0.75, interpolation=cv2.INTER_AREA) if compact else bgr
    jpeg = cv2.imencode(".jpg", small, [cv2.IMWRITE_JPEG_QUALITY, 95])[1].tobytes()
    d16 = depth.astype(np.float16).tobytes()
    conf = np.full(depth.shape, 2, np.uint8).tobytes()
    hd = {"w": bgr.shape[1], "h": bgr.shape[0], "fx": K[0, 0], "fy": K[1, 1], "cx": K[0, 2],
          "cy": K[1, 2], "dw": depth.shape[1], "dh": depth.shape[0], "ts": 0.0,
          "orientation": orientation, "jpeg": len(jpeg), "depth": len(d16), "conf": len(conf)}
    block = d16 + conf
    if compact:
        c = zlib.compressobj(6, zlib.DEFLATED, -15)
        block = c.compress(block) + c.flush()
        hd["z"] = len(block)
    h = json.dumps(hd).encode()
    return b"CDP1" + struct.pack("<I", len(h)) + h + jpeg + block


def pose(lean, turn, dist):
    """Cello plane: centre and rotation (columns: across, down, normal away
    from the camera). lean > 0: top tilted away; turn > 0: right side away."""
    R = cv2.Rodrigues(np.radians([-lean, 0, 0]))[0] @ cv2.Rodrigues(np.radians([0, -turn, 0]))[0]
    return np.array([0.05, 0.1, dist]), R


def cello_outline(n=200):
    """A cello-ish outline in the plane (metres): x across, y up."""
    t = np.linspace(0, 2 * np.pi, n, endpoint=False)
    y = 0.38 * np.sin(t)
    x = (0.21 - 0.05 * np.cos(2 * np.pi * (y + 0.38) / 0.38) ** 2) * np.cos(t)
    return np.stack([x, y], 1)


def render_plane(lean, turn, dist):
    """Camera mask, iPhone-like depth packet and the true 3D point per pixel."""
    C, R = pose(lean, turn, dist)
    out = cello_outline()
    P = C + out[:, :1] * R[:, 0] - out[:, 1:] * R[:, 1]     # image y points down
    uv = (K_CAM @ P.T).T
    uv = uv[:, :2] / uv[:, 2:]
    mask = np.zeros((CAM[1], CAM[0]), np.uint8)
    cv2.fillPoly(mask, [np.round(uv).astype(np.int32)], 1)
    u, v = np.meshgrid(np.arange(CAM[0]), np.arange(CAM[1]))
    r = np.stack([(u - K_CAM[0, 2]) / K_CAM[0, 0], (v - K_CAM[1, 2]) / K_CAM[1, 1], np.ones(u.shape)], -1)
    nrm = R[:, 2]
    z = np.where(mask > 0, (nrm @ C) / (r @ nrm), 3.0).astype(np.float32)
    rng = np.random.default_rng(1)
    depth = cv2.resize(z, (256, 192), interpolation=cv2.INTER_AREA)
    depth = depth + rng.normal(0, 0.005, depth.shape).astype(np.float32)
    pkt = {"depth": depth, "conf": np.full(depth.shape, 2, np.uint8), "K": K_CAM.copy(),
           "size": CAM, "orientation": "landscapeLeft"}
    X = r * z[..., None]
    return mask.astype(np.float32), pkt, X


def check_tilts():
    from cellomask.cello3d import CelloPlane
    from cellomask.composite import mask_roi
    from cellomask.procam3d import Procam3D
    pc = Procam3D(K_PROJ, np.zeros(5), R_PROJ, T_PROJ, PROJ)
    rvec = cv2.Rodrigues(R_PROJ)[0]

    def truth(X):
        return cv2.projectPoints(X.reshape(-1, 1, 3), rvec, T_PROJ, K_PROJ, np.zeros(5))[0].reshape(-1, 2)

    # the flat calibration: a homography fitted with the cello upright at 2 m
    m0, _, X0 = render_plane(0, 0, 2.0)
    ys, xs = np.nonzero(m0 > 0)
    H_flat, _ = cv2.findHomography(np.stack([xs, ys], 1).astype(np.float32),
                                   truth(X0[ys, xs]).astype(np.float32), 0)
    ok, rows = True, []
    for lean, turn, dist in ((0, 0, 2.0), (20, 0, 2.0), (-15, 0, 2.0), (0, 25, 2.0),
                             (15, -20, 2.0), (0, 0, 1.5), (10, 10, 2.6)):
        mask, pkt, X = render_plane(lean, turn, dist)
        plane = CelloPlane()
        for k in range(10):                    # let the smoothing settle
            plane(mask, pkt, k / 30)
        roi = mask_roi(mask, 6)
        H = plane.homography(pc, K_CAM, roi)
        ys, xs = np.nonzero(mask > 0)
        cam = np.stack([xs, ys], 1).astype(np.float32)[::7]
        want = truth(X[ys, xs][::7])
        e3 = np.linalg.norm(cv2.perspectiveTransform(cam[:, None], H)[:, 0] - want, axis=1)
        ef = np.linalg.norm(cv2.perspectiveTransform(cam[:, None], H_flat)[:, 0] - want, axis=1)
        le, tu = plane.angles()
        rows.append((lean, turn, dist, e3.mean(), ef.mean(), le, tu))
        ok &= e3.mean() < 3.0 and abs(le - lean) < 3 and abs(tu - turn) < 3
    detail = "; ".join(f"lean {l:+d} turn {t:+d} at {d} m: 3D {a:.1f} px vs flat {b:.0f} px "
                       f"(measured {ml:+.0f}/{mt:+.0f} deg)" for l, t, d, a, b, ml, mt in rows)
    ok_q = True
    # the image's rectangle on a cello leaning back is narrower at the top
    mask, pkt, X = render_plane(25, 0, 2.0)
    plane = CelloPlane()
    for k in range(10):
        plane(mask, pkt, k / 30)
    ys, xs = np.nonzero(mask > 0)
    axis = (xs.mean(), ys.mean(), ys.ptp(), xs.ptp(), -np.pi / 2)
    q, _ = plane.quad(axis, K_CAM)
    top, bottom = np.linalg.norm(q[1] - q[0]), np.linalg.norm(q[2] - q[3])
    ok_q = top < bottom * 0.98
    print(f"      {detail}")
    return check("3D mapping follows lean / turn", ok, "mean errors in projector pixels, see above") & \
        check("image perspective on a leaning cello", ok_q,
              f"rectangle width top {top:.0f} px vs bottom {bottom:.0f} px (leaning back 25 deg)")


def room_depth(Rc=np.eye(3), tc=np.zeros(3), size=(192, 256)):
    """LiDAR-like depth of a room seen by a camera at pose (Rc, tc) in the
    reference camera's frame (X_ref = Rc X_cam + tc): back wall, side walls,
    floor and a box. Portrait 192 x 256 like the phone's rotated depth."""
    dw, dh = size
    Kd = np.array([[0.7 * dw * 1.3, 0, dw / 2 - 0.5], [0, 0.7 * dw * 1.3, dh / 2 - 0.5], [0, 0, 1]])
    u, v = np.meshgrid(np.arange(dw), np.arange(dh))
    r = np.stack([(u - Kd[0, 2]) / Kd[0, 0], (v - Kd[1, 2]) / Kd[1, 1], np.ones(u.shape)], -1)
    d = r @ Rc.T                                    # ray directions in the room
    best = np.full(u.shape, np.inf)
    for n, off, box in (((0, 0, 1), 3.2, None), ((1, 0, 0), -1.3, None), ((1, 0, 0), 1.4, None),
                        ((0, 1, 0), 1.0, None), ((0, 0, 1), 2.1, ((-0.35, 0.3), (0.0, 1.0)))):
        n = np.array(n, float)
        with np.errstate(divide="ignore", invalid="ignore"):
            t = (off - tc @ n) / (d @ n)
        hit = tc + d * t[..., None]
        ok = t > 0
        if box is not None:
            ok &= (hit[..., 0] > box[0][0]) & (hit[..., 0] < box[0][1]) & (hit[..., 1] > box[1][0]) & (hit[..., 1] < box[1][1])
        best = np.where(ok & (t < best), t, best)
    rng = np.random.default_rng(int(1000 * abs(tc).sum()) % 97)
    depth = (best + rng.normal(0, 0.004, best.shape)).astype(np.float32)   # z along the ray with r_z = 1
    W, H = 960, 1280                                # the image this depth belongs to
    K = np.array([[Kd[0, 0] * W / dw, 0, (Kd[0, 2] + 0.5) * W / dw - 0.5],
                  [0, Kd[1, 1] * H / dh, (Kd[1, 2] + 0.5) * H / dh - 0.5], [0, 0, 1]])
    return {"depth": depth, "conf": np.full(depth.shape, 2, np.uint8), "K": K, "size": (W, H),
            "orientation": "portrait"}


def check_relocate():
    from cellomask.relocate import PhoneTracker
    trk = PhoneTracker(path=os.path.join(tempfile.mkdtemp(), "ref.npz"))
    ref = room_depth()
    trk.save_ref(ref["depth"], ref["K"], ref["size"], ref["orientation"])
    ok, rows = True, []
    for ang, t in (((0, 0, 0), (0, 0, 0)), ((3, -2, 1), (0.03, -0.02, 0.01)),
                   ((0, 5, 0), (-0.05, 0, 0.04)), ((-4, 0, 2), (0, 0.04, -0.03))):
        Rc = cv2.Rodrigues(np.radians(ang))[0]
        trk.M = np.eye(4)
        trk.update(room_depth(Rc, np.array(t)))
        want = np.eye(4)
        want[:3, :3], want[:3, 3] = Rc, t
        dR = np.degrees(np.linalg.norm(cv2.Rodrigues(trk.M[:3, :3] @ Rc.T)[0]))
        dt = 100 * np.linalg.norm(trk.M[:3, 3] - np.array(t))
        rows.append(f"moved {ang} deg {tuple(100 * np.array(t))} cm -> error {dR:.2f} deg, {dt:.2f} cm")
        ok &= trk.ok and dR < 0.3 and dt < 0.5
    # the corrected projector = move points back to the calibration camera, then project
    from cellomask.procam3d import Procam3D
    pc = Procam3D(K_PROJ, np.zeros(5), R_PROJ, T_PROJ, PROJ)
    X = np.random.default_rng(2).uniform([-0.5, -0.5, 1.5], [0.5, 0.5, 2.5], (50, 3))
    a = pc.moved(trk.M).project(X)
    b = pc.project(X @ trk.M[:3, :3].T + trk.M[:3, 3])
    ok &= np.abs(a - b).max() < 1e-6
    return check("phone movement recovered", ok, "; ".join(rows))


def check_front_face():
    """The front face drops the neck and scroll, a hand held in front of
    the top, and pulls the edge in by the inset, on a leaning cello."""
    from cellomask.cello3d import CelloPlane, front_face
    mask, pkt, X = render_plane(15, 5, 1.9)
    plane = CelloPlane()
    assert plane(mask, pkt, 0.0)
    C, R = pose(15, 5, 1.9)

    def to_px(pts):
        P = C + pts[:, :1] * R[:, 0] - pts[:, 1:] * R[:, 1]
        uv = (K_CAM @ P.T).T
        return np.round(uv[:, :2] / uv[:, 2:]).astype(np.int32)

    body = mask > 0.5
    # neck (6 cm wide, 30 cm) and scroll above the body, on the same plane
    neck = np.zeros_like(mask, np.uint8)
    cv2.fillPoly(neck, [to_px(np.array([[-0.03, 0.36], [0.03, 0.36], [0.03, 0.70], [-0.03, 0.70]]))], 1)
    cv2.circle(neck, tuple(to_px(np.array([[0.0, 0.74]]))[0]), int(0.05 * K_CAM[0, 0] / 1.9), 1, -1)
    full = np.maximum(mask, neck.astype(np.float32))
    # a hand 15 cm in front of the lower bout
    hand_c = to_px(np.array([[0.08, -0.18]]))[0]
    hand = np.zeros_like(mask, np.uint8)
    cv2.circle(hand, tuple(hand_c), int(0.05 * K_CAM[0, 0] / 1.9), 1, -1)
    dh, dw = pkt["depth"].shape
    small = cv2.resize(hand, (dw, dh), interpolation=cv2.INTER_NEAREST) > 0
    pkt["depth"] = np.where(small, pkt["depth"] - 0.15, pkt["depth"]).astype(np.float32)
    face = front_face(full, plane, K_CAM, pkt["depth"], pkt["conf"], inset_mm=6.0)

    neck_lit = (face & (neck > 0) & ~body).sum() / max(1, ((neck > 0) & ~body).sum())
    hand_lit = (face & (hand > 0)).sum() / hand.sum()
    # inset: distance from the body's edge to the face's, in mm on the cello
    mm_px = 1000 * plane.C[2] / K_CAM[0, 0]
    dist_in = cv2.distanceTransform(body.astype(np.uint8), cv2.DIST_L2, 5)
    edge = face & (cv2.erode(face.astype(np.uint8), np.ones((3, 3), np.uint8)) == 0) & body
    inset = np.median(dist_in[edge]) * mm_px
    kept = (face & body & (hand == 0)).sum() / (body & (hand == 0)).sum()
    ok = neck_lit < 0.02 and hand_lit < 0.02 and 4.5 < inset < 8.5 and kept > 0.85
    ok = check("front face only", ok, f"neck lit {100 * neck_lit:.1f}%, hand lit {100 * hand_lit:.1f}%, "
               f"edge inset {inset:.1f} mm, body kept {100 * kept:.0f}%")

    # a hole where the segmentation lost the bridge, and an arm covering
    # most of the upper bout: the narrow strip left must not pass for the neck
    holed = full.copy()
    bridge = np.zeros_like(mask, np.uint8)
    cv2.fillPoly(bridge, [to_px(np.array([[-0.05, -0.02], [0.05, -0.02], [0.05, -0.06], [-0.05, -0.06]]))], 1)
    holed[bridge > 0] = 0
    arm = np.zeros_like(mask, np.uint8)
    cv2.fillPoly(arm, [to_px(np.array([[-0.3, 0.05], [0.07, 0.05], [0.07, 0.5], [-0.3, 0.5]]))], 1)
    holed[(arm > 0) & (neck == 0)] = 0
    upper = (holed > 0.5) & body & (np.arange(mask.shape[0])[:, None] < to_px(np.array([[0, 0.05]]))[0][1])
    # the axis as the tracker would hold it: from before the arm came in
    c0, c1 = to_px(np.array([[0.0, 0.0], [0.0, 0.3]]))
    axis = (c0[0], c0[1], np.arctan2(c1[1] - c0[1], c1[0] - c0[0]))
    face2 = front_face(holed, plane, K_CAM, None, None, inset_mm=6.0, axis=axis)
    core = cv2.erode((bridge > 0).astype(np.uint8), np.ones((9, 9), np.uint8)) > 0
    bridge_lit = (face2 & core).sum() / max(1, core.sum())
    upper_lit = (face2 & upper).sum() / max(1, upper.sum())
    neck_lit2 = (face2 & (neck > 0) & ~body).sum() / max(1, ((neck > 0) & ~body).sum())
    # the bow: a thin stick 10 cm in front of the upper bout, joined to the
    # player's arm (wide, beside the cello): it must not cut a band
    bowed = dict(pkt)
    stick = np.zeros_like(mask, np.uint8)
    cv2.fillPoly(stick, [to_px(np.array([[-0.45, 0.20], [0.30, 0.20], [0.30, 0.21], [-0.45, 0.21]]))], 1)
    cv2.circle(stick, tuple(to_px(np.array([[-0.4, 0.2]]))[0]), int(0.08 * K_CAM[0, 0] / 1.9), 1, -1)
    dh, dw = pkt["depth"].shape
    sd = cv2.resize(stick, (dw, dh), interpolation=cv2.INTER_NEAREST) > 0
    sd = cv2.dilate(sd.astype(np.uint8), np.ones((3, 3), np.uint8)) > 0     # smoothed depth widens it
    bowed["depth"] = np.where(sd, np.float32(1.75), pkt["depth"]).astype(np.float32)
    face3 = front_face(full, plane, K_CAM, bowed["depth"], None, inset_mm=6.0)
    under = body & (cv2.dilate(stick, np.ones((15, 15), np.uint8)) > 0)
    bow_lit = (face3 & under).sum() / max(1, under.sum())
    ok &= check("front face: the bow cuts no band", bow_lit > 0.95, f"under the bow {100 * bow_lit:.0f}% lit")
    return ok & check("front face: holes, covered upper bout", bridge_lit > 0.95 and upper_lit > 0.75
                      and neck_lit2 < 0.02,
                      f"bridge hole lit {100 * bridge_lit:.0f}%, uncovered upper bout lit "
                      f"{100 * upper_lit:.0f}%, neck lit {100 * neck_lit2:.1f}%")


def main():
    sys.path.insert(0, ROOT)
    from cellomask import iphone, server
    from cellomask.procam3d import PROCAM_PATH
    from cellomask.projector import CALIB_PATH

    ok = True
    # 1. parsing, and a 3D point lands on the same feature after turning upright
    z, X, _ = scene_depth()
    img = np.zeros((CAM[1], CAM[0], 3), np.uint8)
    P = np.array([0.3, -0.2, 2.0])
    uv = (K_CAM @ P)[:2] / P[2]
    cv2.circle(img, tuple(np.round(uv).astype(int)), 6, (255, 255, 255), -1)
    depth = cv2.resize(z, (256, 192), interpolation=cv2.INTER_AREA)
    worst = 0.0
    for o, compact in (("landscapeLeft", False), ("portrait", False), ("landscapeRight", False),
                       ("portraitUpsideDown", False), ("landscapeLeft", True), ("portrait", True)):
        pkt = iphone.parse(message(img, depth, K_CAM, o, compact))
        m = cv2.moments(cv2.cvtColor(pkt["bgr"], cv2.COLOR_BGR2GRAY))
        seen = np.array([m["m10"] / m["m00"], m["m01"] / m["m00"]])
        want = (pkt["K"] @ (P if o == "landscapeLeft" else P))[:2] / P[2]
        # the rotated K describes a rotated camera: rotate P the same way
        Rz = {"landscapeLeft": np.eye(3),
              "portrait": np.array([[0, -1, 0], [1, 0, 0], [0, 0, 1.]]),
              "landscapeRight": np.diag([-1.0, -1, 1]),
              "portraitUpsideDown": np.array([[0, 1, 0], [-1, 0, 0], [0, 0, 1.]])}[o]
        Pr = Rz @ P
        want = (pkt["K"] @ Pr)[:2] / Pr[2]
        worst = max(worst, float(np.linalg.norm(seen - want)))
    pkt = iphone.parse(message(img, depth, K_CAM, "landscapeLeft", compact=True))
    same = np.array_equal(pkt["depth"], depth.astype(np.float16).astype(np.float32)) and \
        pkt["bgr"].shape[:2] == img.shape[:2] and (pkt["conf"] == 2).all()
    ok &= check("compact stream (small JPEG, deflate)", same,
                f"depth and confidence exact, image back at {pkt['bgr'].shape[1]}x{pkt['bgr'].shape[0]}")
    ok &= check("stream parsing + orientations", worst < 1.0,
                f"projected point vs where it appears after turning upright: max {worst:.2f} px")

    # 2. per-frame 3D mapping of a leaning / turning cello (no segmentation:
    #    the mask and depth are rendered from a known cello-shaped plane)
    ok &= check_tilts()
    ok &= check_relocate()
    ok &= check_front_face()

    # 3. closed-loop 3D calibration through the real Pipeline
    backups = {p: open(p).read() for p in (CALIB_PATH, PROCAM_PATH) if os.path.exists(p)}
    try:
        sample = os.path.join(ROOT, "data", "sources", "sample-Cello-106.jpg")
        args = argparse.Namespace(source=sample, model=None, imgsz=512, width=1280,
                                  height=960, proj_size=list(PROJ))
        pipe = server.Pipeline(args)
        pipe.debug_dir = tempfile.mkdtemp(prefix="cello-test-")   # keep data/calib_debug real
        from cellomask.relocate import PhoneTracker
        pipe.phone = PhoneTracker(path=os.path.join(pipe.debug_dir, "ref.npz"))   # not the real reference
        pipe.source = None
        fake = FakeIPhone(pipe)
        server.IPHONE = fake                       # the pipeline checks for the phone source
        pipe.camera = fake
        pipe.projector_window = True
        pipe.start()
        time.sleep(1.0)
        t0 = time.time()
        r = pipe.calibrate_lidar()
        took = time.time() - t0
        ok &= check("3D calibration", r["ok"], f"{r['message'][:150]}... in {took:.0f} s")
        if r["ok"]:
            pc = pipe.procam
            K = pc.K
            ok &= check("projector lens", abs(K[0, 0] - 2300) < 25 and abs(K[0, 2] - 960) < 15 and abs(K[1, 2] - 1150) < 15,
                        f"focal {K[0, 0]:.1f} (2300), centre {K[0, 2]:.1f}, {K[1, 2]:.1f} (960, 1150)")
            pos_err = np.linalg.norm(pc.position - (-R_PROJ.T @ T_PROJ))
            ok &= check("projector position", pos_err < 0.02, f"{100 * pos_err:.2f} cm from the truth")
            # mapping of true 3D points of the room, at any depth
            _, Xall, cello = scene_depth()
            pts = Xall[::8, ::8].reshape(-1, 3)
            want = cv2.projectPoints(pts.reshape(-1, 1, 3), cv2.Rodrigues(R_PROJ)[0], T_PROJ, K_PROJ, np.zeros(5))[0].reshape(-1, 2)
            inside = (want[:, 0] >= 0) & (want[:, 0] < PROJ[0]) & (want[:, 1] >= 0) & (want[:, 1] < PROJ[1])
            err = np.linalg.norm(pc.project(pts[inside]) - want[inside], axis=1)
            ok &= check("3D mapping (wall, floor, cello)", err.mean() < 2.0,
                        f"mean {err.mean():.2f} px, 95% {np.percentile(err, 95):.2f} px (projector pixels)")
        pipe.running = False
    finally:
        for p, text in backups.items():
            open(p, "w").write(text)
        for p in (CALIB_PATH, PROCAM_PATH):
            if p not in backups and os.path.exists(p):
                os.remove(p)

    print("ALL TESTS PASSED" if ok else "SOME TESTS FAILED")
    raise SystemExit(0 if ok else 1)


if __name__ == "__main__":
    main()
