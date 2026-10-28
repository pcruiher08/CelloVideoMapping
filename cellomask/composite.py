"""Put a replacement image (or video frame) where the cello is.

Fit modes:

- ``warp``   the image rides on the cello: rotated to the cello's axis
             (scroll = image top), scaled to cover the oriented rectangle
- ``fill``   cover-fit into the mask's upright bounding box, no rotation
- ``window`` the image is fixed to the full frame; the cello is a window
             onto it (good for video content that should not swim around)

The mask is feathered so edges blend instead of stair-stepping, and can be
grown or shrunk a few pixels to hide halo or to cover the cello's rim.
"""

import cv2
import numpy as np


def cover_resize(img, w, h):
    """Scale to cover w x h and centre-crop, like CSS object-fit: cover."""
    ih, iw = img.shape[:2]
    s = max(w / iw, h / ih)
    r = cv2.resize(img, (max(1, round(iw * s)), max(1, round(ih * s))),
                   interpolation=cv2.INTER_AREA if s < 1 else cv2.INTER_LINEAR)
    y0 = (r.shape[0] - h) // 2
    x0 = (r.shape[1] - w) // 2
    return r[y0:y0 + h, x0:x0 + w]


def place_warp(img, roi, axis, pad=1.05):
    """Map the image onto the oriented cello rectangle, rendered only inside
    `roi` (x0, y0, x1, y1). Image top goes to the scroll end, so a portrait
    image reads upright when the cello is upright.

    The cover-fit (scale + centre crop) is folded into the affine transform,
    so this is a single warp straight from the source image."""
    x0, y0, x1, y1 = roi
    cx, cy, length, width, up = axis
    L, Wd = max(2.0, length * pad), max(2.0, width * pad)
    ih, iw = img.shape[:2]
    s = max(Wd / iw, L / ih)
    ox, oy = (iw * s - Wd) / 2, (ih * s - L) / 2     # crop, in scaled pixels
    u = np.array([np.cos(up), np.sin(up)])          # towards the scroll
    v = np.array([-u[1], u[0]])                      # across the body
    top_mid = np.array([cx - x0, cy - y0]) + u * L / 2
    # image points that land on the rectangle's TL, TR, BL corners
    src = np.float32([[ox / s, oy / s], [(ox + Wd) / s, oy / s],
                      [ox / s, (oy + L) / s]])
    dst = np.float32([top_mid - v * Wd / 2, top_mid + v * Wd / 2,
                      top_mid - v * Wd / 2 - u * L])
    M = cv2.getAffineTransform(src, dst)
    return cv2.warpAffine(img, M, (x1 - x0, y1 - y0), flags=cv2.INTER_LINEAR,
                          borderMode=cv2.BORDER_REFLECT)


def place_quad(img, roi, quad):
    """Like place_warp, onto a perspective quad: `quad` is (corners, (L, W))
    from CelloPlane.quad, the cello's rectangle as it really sits in 3D
    (TL, TR, BR, BL in camera pixels; L, W its true length and width). The
    image is cover-fitted to L x W and warped with full perspective, so it
    foreshortens with the cello's lean like paint on the wood."""
    x0, y0, x1, y1 = roi
    corners, (L, Wd) = quad
    ih, iw = img.shape[:2]
    s = max(Wd / iw, L / ih)                       # metres per image pixel, cover
    cw, ch = Wd / s, L / s
    ox, oy = (iw - cw) / 2, (ih - ch) / 2
    src = np.float32([[ox, oy], [ox + cw, oy], [ox + cw, oy + ch], [ox, oy + ch]])
    dst = corners - np.float32([x0, y0])
    M = cv2.getPerspectiveTransform(src, dst)
    return cv2.warpPerspective(img, M, (x1 - x0, y1 - y0), flags=cv2.INTER_LINEAR,
                               borderMode=cv2.BORDER_REFLECT)


def place_fill(img, roi, mask):
    """Cover-fit into the mask's upright bounding box (in roi coordinates)."""
    x0, y0, x1, y1 = roi
    out = np.zeros((y1 - y0, x1 - x0, 3), np.uint8)
    ys, xs = np.nonzero(mask[y0:y1, x0:x1] > 0.5)
    if len(xs) == 0:
        return out
    bx0, bx1, by0, by1 = xs.min(), xs.max() + 1, ys.min(), ys.max() + 1
    out[by0:by1, bx0:bx1] = cover_resize(img, bx1 - bx0, by1 - by0)
    return out


_window = {"img": None, "shape": None, "full": None}


def place_window(img, shape, roi):
    """The image covers the whole frame; return the roi part of it. The
    full-frame resize is cached while the same image is in use (holding a
    reference, so a new image can never be mistaken for the cached one)."""
    if _window["img"] is not img or _window["shape"] != shape[:2]:
        _window.update(img=img, shape=shape[:2],
                       full=cover_resize(img, shape[1], shape[0]))
    x0, y0, x1, y1 = roi
    return _window["full"][y0:y1, x0:x1]


def shape_alpha(mask, grow=0, feather=6, inward=False):
    """Soft alpha of the mask. `inward`: the soft edge lies entirely inside
    the mask, fading to ~0 at its outline (for the projector: a blur centred
    on the edge throws half of it past the cello)."""
    if inward and feather > 0:
        grow -= feather
    a = (mask > 0.5).astype(np.uint8) * 255 if grow else (mask * 255).astype(np.uint8)
    if grow:
        k = cv2.getStructuringElement(cv2.MORPH_ELLIPSE, (2 * abs(grow) + 1,) * 2)
        a = cv2.dilate(a, k) if grow > 0 else cv2.erode(a, k)
    if feather > 0:
        a = cv2.GaussianBlur(a, (0, 0), feather / 2)
    return a.astype(np.float32) / 255


def mask_roi(mask, margin):
    """Bounding box of the mask grown by `margin`, clipped to the frame.
    All per-pixel work happens inside it: the cello is usually a fraction
    of the frame, and full-frame float math was the main per-frame cost."""
    H, W = mask.shape
    rows = np.flatnonzero(mask.max(1) > 0.02)
    if not len(rows):
        return None
    cols = np.flatnonzero(mask[rows[0]:rows[-1] + 1].max(0) > 0.02)
    return (max(0, cols[0] - margin), max(0, rows[0] - margin),
            min(W, cols[-1] + 1 + margin), min(H, rows[-1] + 1 + margin))


def composite(frame, mask, img, mode="warp", axis=None, feather=6, grow=0,
              opacity=1.0, blend="normal", background=None, quad=None, inward=False):
    """Return the frame with the cello replaced. `background` optionally
    replaces everything that is *not* the cello (e.g. black for a clean
    projection matte)."""
    out = (frame if background is None else background).copy()
    if mask is None or img is None:
        return out
    roi = mask_roi(mask, 2 * feather + abs(grow) + 2)
    if roi is None:
        return out
    x0, y0, x1, y1 = roi
    if mode == "warp" and quad is not None:
        layer = place_quad(img, roi, quad)
    elif mode == "warp" and axis is not None:
        layer = place_warp(img, roi, axis)
    elif mode == "window":
        layer = place_window(img, frame.shape, roi)
    else:
        layer = place_fill(img, roi, mask)

    under = frame[y0:y1, x0:x1]
    a = shape_alpha(mask[y0:y1, x0:x1], grow, feather, inward)[..., None] * opacity
    if blend == "multiply":
        layer = (layer.astype(np.float32) * under / 255).astype(np.uint8)
    elif blend == "screen":
        layer = (255 - (255 - layer.astype(np.float32)) * (255 - under.astype(np.float32)) / 255).astype(np.uint8)
    a = np.ascontiguousarray(a[..., 0])
    out[y0:y1, x0:x1] = cv2.blendLinear(np.ascontiguousarray(layer),
                                        np.ascontiguousarray(out[y0:y1, x0:x1]),
                                        a, 1 - a)
    return out


def debug_overlay(frame, instances, mask, axis, chosen=0):
    """Camera view with every instance outlined, the used mask tinted and the
    tracked axis (arrow points at the scroll)."""
    out = frame.copy()
    roi = mask_roi(mask, 0) if mask is not None else None
    if roi is not None:
        x0, y0, x1, y1 = roi
        a = mask[y0:y1, x0:x1, None] * 0.35
        tint = np.array([0, 255, 255], np.float32)          # yellow
        out[y0:y1, x0:x1] = (out[y0:y1, x0:x1] * (1 - a) + tint * a).astype(np.uint8)
    for i, inst in enumerate(instances):
        m = (inst["mask"] > 0.5).astype(np.uint8)
        cnts, _ = cv2.findContours(m, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
        col = (0, 255, 255) if i == chosen else (255, 160, 0)
        cv2.drawContours(out, cnts, -1, col, 2, cv2.LINE_AA)
        x0, y0 = int(inst["box"][0]), int(inst["box"][1])
        cv2.putText(out, f"cello {inst['conf']:.2f}", (x0, max(14, y0 - 6)),
                    cv2.FONT_HERSHEY_SIMPLEX, 0.5, col, 1, cv2.LINE_AA)
    if axis is not None:
        cx, cy, length, width, up = axis
        u = np.array([np.cos(up), np.sin(up)])
        p0 = np.array([cx, cy]) - u * length / 2
        p1 = np.array([cx, cy]) + u * length / 2
        cv2.arrowedLine(out, tuple(p0.astype(int)), tuple(p1.astype(int)),
                        (255, 0, 255), 2, cv2.LINE_AA, tipLength=0.05)
    return out
