"""Camera selection by device name on macOS.

OpenCV's AVFoundation backend only takes a numeric index, and the index order
changes as iPhone Continuity Cameras appear and disappear. We enumerate the
same device list via AVFoundation (pyobjc) so we can map a *name* to the
current index and reliably pick the built-in Mac camera.
"""


def list_cameras():
    """Return camera names in OpenCV index order, or None if unavailable.

    This has to reproduce OpenCV's own enumeration, which differs from the
    order AVFoundation hands out:

    - OpenCV cannot open Continuity (iPhone) or Desk View cameras without an
      Info.plist entry, so they are not in its index space at all;
    - OpenCV sorts the devices it can open by uniqueID.

    Verified 2026-10-20 with a Logitech BRIO (uniqueID 0x1000...) and the
    FaceTime camera (47B4...): OpenCV index 0 delivered the BRIO's 1920x1080
    and index 1 the FaceTime's 1552x1552 square format, while the discovery
    session listed FaceTime first — so name lookups opened the wrong camera.
    """
    try:
        import AVFoundation as AVF
    except ImportError:
        return None
    types = []
    for tname in ("AVCaptureDeviceTypeBuiltInWideAngleCamera",
                  "AVCaptureDeviceTypeExternal",
                  "AVCaptureDeviceTypeExternalUnknown"):
        t = getattr(AVF, tname, None)
        if t is not None and t not in types:
            types.append(t)
    sess = (AVF.AVCaptureDeviceDiscoverySession.
            discoverySessionWithDeviceTypes_mediaType_position_(
                types, AVF.AVMediaTypeVideo, 0))
    devices = sorted(sess.devices(), key=lambda d: str(d.uniqueID()))
    return [str(d.localizedName()) for d in devices]


def pick_builtin_index():
    """Index of the built-in Mac camera, avoiding iPhone/Continuity cameras.

    Returns (index, name). Falls back to (0, None) if enumeration is
    unavailable (non-mac / pyobjc missing).
    """
    names = list_cameras()
    if not names:
        return 0, None
    for i, name in enumerate(names):
        low = name.lower()
        if "facetime" in low or "built-in" in low:
            return i, name
    for i, name in enumerate(names):
        if "iphone" not in name.lower():
            return i, name
    return 0, names[0]


def pick_by_name(substring):
    """(index, name) of the first camera whose name contains `substring`
    (case-insensitive), or (None, None) if nothing matches."""
    names = list_cameras()
    if not names:
        return None, None
    s = substring.lower()
    for i, name in enumerate(names):
        if s in name.lower():
            return i, name
    return None, None


def configure(cap, width, height, fps=None, mjpg=True, lock_exposure=False):
    """Set capture format and report what the device actually negotiated.

    The order matters: FOURCC must be set before the frame size, or the
    driver picks a raw format first and then refuses the high-framerate
    modes. Uncompressed 1080p60 exceeds USB bandwidth, so without MJPEG a
    Brio silently drops to single-digit framerates.

    macOS/AVFoundation ignores several UVC controls, so everything here is
    best-effort and the returned dict reports what really stuck.
    """
    import cv2

    if mjpg:
        cap.set(cv2.CAP_PROP_FOURCC, cv2.VideoWriter.fourcc(*"MJPG"))
    cap.set(cv2.CAP_PROP_FRAME_WIDTH, width)
    cap.set(cv2.CAP_PROP_FRAME_HEIGHT, height)
    if fps:
        cap.set(cv2.CAP_PROP_FPS, fps)

    locked = None
    if lock_exposure:
        # 0.25 means "manual" for the V4L2/UVC convention; AVFoundation may
        # ignore it entirely, which is why we read the value back.
        cap.set(cv2.CAP_PROP_AUTO_EXPOSURE, 0.25)
        cap.set(cv2.CAP_PROP_AUTO_WB, 0)
        locked = {"auto_exposure": cap.get(cv2.CAP_PROP_AUTO_EXPOSURE),
                  "auto_wb": cap.get(cv2.CAP_PROP_AUTO_WB)}

    # AVFoundation does not report FPS or FOURCC back: it returns 1 and -1.
    # Report None rather than those, so the caller does not print nonsense —
    # measure_fps() is the honest source for the rate actually delivered.
    raw_fourcc = int(cap.get(cv2.CAP_PROP_FOURCC))
    tag = "".join(chr((raw_fourcc >> 8 * i) & 0xFF) for i in range(4))
    reported_fps = cap.get(cv2.CAP_PROP_FPS)
    return {
        "width": int(cap.get(cv2.CAP_PROP_FRAME_WIDTH)),
        "height": int(cap.get(cv2.CAP_PROP_FRAME_HEIGHT)),
        "fps": reported_fps if reported_fps > 1 else None,
        "fourcc": tag if tag.isprintable() and tag.isascii() else None,
        "locked": locked,
    }


def measure_fps(cap, n=60):
    """Actual delivered framerate — the only number that matters, since the
    reported CAP_PROP_FPS is frequently what was asked for, not what arrives."""
    import time
    for _ in range(5):          # discard warm-up frames
        cap.read()
    t0 = time.time()
    got = 0
    for _ in range(n):
        if cap.read()[0]:
            got += 1
    dt = time.time() - t0
    return got / dt if dt > 0 else 0.0
