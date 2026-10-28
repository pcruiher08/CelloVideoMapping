"""Synthetic stage composites to close the gap between catalogue photos and
a live performance.

The Roboflow images are mostly cellos on white backgrounds, upright and
unoccluded. On stage the cello is tilted towards the player, partly hidden
by hands, arms and the bow, and lit by a spotlight against a dark room. Each
composite cuts real cellos out by their SAM mask and pastes them onto a
procedural stage background with:

- the tilt of a played cello (lean of -35..+10 degrees, scale 0.4..1.1 of
  frame height)
- arm / hand / bow occluders, which are *subtracted from the mask*: the
  replacement image must not paint over the player's hands
- spotlight falloff, colour temperature and exposure jitter, sensor noise,
  slight motion blur

Only the training split is touched; validation stays real photos.

    .venv/bin/python -m cellomask.synth --n 600
"""

import argparse
import glob
import os
import random

import cv2
import numpy as np

from .autolabel import OUT, mask_to_polygon

SYN_PREFIX = "syn_"


def load_cutouts(split_dir, max_side=900):
    """(bgra crop, area) for every labelled instance in the split."""
    cuts = []
    for path in sorted(glob.glob(os.path.join(split_dir, "images", "*"))):
        if os.path.basename(path).startswith(SYN_PREFIX):
            continue
        lp = os.path.splitext(path.replace("/images/", "/labels/"))[0] + ".txt"
        im = cv2.imread(path)
        h, w = im.shape[:2]
        for line in open(lp).read().splitlines():
            v = line.split()
            if len(v) < 7:
                continue
            poly = (np.array(v[1:], float).reshape(-1, 2) * [w, h]).astype(np.int32)
            m = np.zeros((h, w), np.uint8)
            cv2.fillPoly(m, [poly], 255)
            x, y, bw, bh = cv2.boundingRect(poly)
            if bw < 40 or bh < 40:
                continue
            crop = np.dstack([im[y:y + bh, x:x + bw], m[y:y + bh, x:x + bw]])
            s = max_side / max(bw, bh)
            if s < 1:
                crop = cv2.resize(crop, None, fx=s, fy=s, interpolation=cv2.INTER_AREA)
            cuts.append(crop)
    return cuts


def stage_background(rng, w, h):
    """Dark room with one or two soft spotlights, a floor gradient and a
    little texture — a cheap stand-in for a concert hall or studio."""
    base = rng.uniform(0, 45)
    tint = np.array([rng.uniform(0.6, 1.2) for _ in range(3)])
    yy, xx = np.mgrid[0:h, 0:w].astype(np.float32)
    light = np.full((h, w), base, np.float32)
    for _ in range(rng.randint(1, 2)):
        cx, cy = rng.uniform(0.2, 0.8) * w, rng.uniform(0.1, 0.6) * h
        r = rng.uniform(0.25, 0.7) * max(w, h)
        light += rng.uniform(60, 200) * np.exp(-((xx - cx) ** 2 + (yy - cy) ** 2) / (2 * r * r))
    floor_y = rng.uniform(0.6, 0.9) * h
    light += np.clip((yy - floor_y) / h, 0, None) * rng.uniform(0, 160)
    noise = cv2.GaussianBlur(np.random.default_rng(rng.randint(0, 1 << 30))
                             .normal(0, 1, (h // 8, w // 8)).astype(np.float32), (0, 0), 2)
    light += cv2.resize(noise, (w, h)) * rng.uniform(0, 18)
    return np.clip(light[..., None] * tint, 0, 255).astype(np.uint8)


def paste(canvas, crop, rng):
    h, w = canvas.shape[:2]
    target_h = rng.uniform(0.4, 1.1) * h
    s = target_h / max(crop.shape[:2])
    crop = cv2.resize(crop, None, fx=s, fy=s, interpolation=cv2.INTER_LINEAR)
    angle = rng.uniform(-35, 10) if rng.random() < 0.8 else rng.uniform(-90, 90)
    if rng.random() < 0.5:
        crop = crop[:, ::-1]
        angle = -angle
    ch, cw = crop.shape[:2]
    M = cv2.getRotationMatrix2D((cw / 2, ch / 2), angle, 1.0)
    cos, sin = abs(M[0, 0]), abs(M[0, 1])
    nw, nh = int(ch * sin + cw * cos), int(ch * cos + cw * sin)
    M[0, 2] += nw / 2 - cw / 2
    M[1, 2] += nh / 2 - ch / 2
    crop = cv2.warpAffine(np.ascontiguousarray(crop), M, (nw, nh), flags=cv2.INTER_LINEAR)

    # allow the cello to run off the frame edges, as it does in close shots
    x = int(rng.uniform(-0.2 * nw, w - 0.8 * nw))
    y = int(rng.uniform(-0.15 * nh, h - 0.75 * nh))
    x0, y0 = max(0, x), max(0, y)
    x1, y1 = min(w, x + nw), min(h, y + nh)
    if x1 <= x0 or y1 <= y0:
        return None
    c = crop[y0 - y:y1 - y, x0 - x:x1 - x]
    a = cv2.GaussianBlur(c[..., 3], (3, 3), 0).astype(np.float32)[..., None] / 255
    roi = canvas[y0:y1, x0:x1].astype(np.float32)
    canvas[y0:y1, x0:x1] = (c[..., :3] * a + roi * (1 - a)).astype(np.uint8)
    inst = np.zeros((h, w), np.uint8)
    inst[y0:y1, x0:x1] = (c[..., 3] > 127).astype(np.uint8)
    return inst


def occlude(canvas, masks, rng):
    """Arms, hands and a bow drawn over the cellos. Arms and hands remove
    pixels from every instance mask they cover."""
    h, w = canvas.shape[:2]
    occ = np.zeros((h, w), np.uint8)
    skin = [(rng.uniform(60, 200), rng.uniform(80, 210), rng.uniform(110, 240))
            for _ in range(2)]
    for i in range(rng.randint(0, 2)):                       # arms / sleeves
        col = skin[i] if rng.random() < 0.5 else tuple(rng.uniform(5, 90) for _ in range(3))
        p0 = (int(rng.uniform(0, w)), int(rng.uniform(0, h)))
        p1 = (int(rng.uniform(0, w)), int(rng.uniform(0, h)))
        thick = int(rng.uniform(0.04, 0.09) * min(h, w))
        cv2.line(canvas, p0, p1, col, thick, cv2.LINE_AA)
        cv2.line(occ, p0, p1, 255, thick)
        cv2.circle(canvas, p1, int(thick * 0.8), skin[i], -1, cv2.LINE_AA)   # hand
        cv2.circle(occ, p1, int(thick * 0.8), 255, -1)
    if rng.random() < 0.6:                                    # bow
        p0 = (int(rng.uniform(-0.2, 0.4) * w), int(rng.uniform(0, h)))
        p1 = (int(rng.uniform(0.6, 1.2) * w), int(rng.uniform(0, h)))
        t = max(2, int(0.006 * min(h, w)))
        cv2.line(canvas, p0, p1, (20, 35, 60), t, cv2.LINE_AA)
        cv2.line(canvas, (p0[0], p0[1] + t), (p1[0], p1[1] + t), (200, 210, 215), max(1, t // 2), cv2.LINE_AA)
        # the bow is not cut out of the mask: a 2-3 px line is below what the
        # 160x160 mask head can resolve, and it would only add label noise
    for m in masks:
        m[occ > 0] = 0


def photometric(canvas, rng):
    img = canvas.astype(np.float32)
    img *= np.array([rng.uniform(0.75, 1.25) for _ in range(3)])   # white balance
    img = img * rng.uniform(0.5, 1.4) + rng.uniform(-20, 20)       # exposure
    img += np.random.default_rng(rng.randint(0, 1 << 30)).normal(0, rng.uniform(0, 8), img.shape)
    img = np.clip(img, 0, 255).astype(np.uint8)
    if rng.random() < 0.3:                                         # motion blur
        k = rng.choice([5, 7, 9])
        kern = np.zeros((k, k), np.float32)
        kern[k // 2] = 1 / k
        kern = cv2.warpAffine(kern, cv2.getRotationMatrix2D((k / 2 - .5, k / 2 - .5), rng.uniform(0, 180), 1), (k, k))
        img = cv2.filter2D(img, -1, kern / max(kern.sum(), 1e-6))
    return img


def main(argv=None):
    p = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    p.add_argument("--n", type=int, default=600)
    p.add_argument("--size", type=int, default=960)
    p.add_argument("--seed", type=int, default=1)
    p.add_argument("--clean", action="store_true", help="remove previous syn_* first")
    args = p.parse_args(argv)
    rng = random.Random(args.seed)

    split = os.path.join(OUT, "train")
    if args.clean:
        for f in glob.glob(os.path.join(split, "*", SYN_PREFIX + "*")):
            os.remove(f)
    cuts = load_cutouts(split)
    print(f"{len(cuts)} cello cutouts")

    previews = []
    for i in range(args.n):
        aspect = rng.choice([(16, 9), (4, 3), (3, 4), (1, 1)])
        w = args.size
        h = int(w * aspect[1] / aspect[0])
        canvas = stage_background(rng, w, h)
        masks = []
        for _ in range(1 if rng.random() < 0.75 else rng.randint(2, 3)):
            inst = paste(canvas, rng.choice(cuts), rng)
            if inst is None:
                continue
            for prev in masks:          # a later cello hides earlier ones
                prev[inst > 0] = 0
            masks.append(inst)
        if not masks:
            continue
        occlude(canvas, masks, rng)
        canvas = photometric(canvas, rng)

        lines = []
        for m in masks:
            if m.sum() < 0.003 * w * h:
                continue
            poly = mask_to_polygon(m, merge_parts=True)
            if poly is not None:
                lines.append("0 " + " ".join(f"{x / w:.5f} {y / h:.5f}" for x, y in poly))
        stem = f"{SYN_PREFIX}{i:04d}"
        cv2.imwrite(os.path.join(split, "images", stem + ".jpg"), canvas,
                    [cv2.IMWRITE_JPEG_QUALITY, rng.randint(70, 95)])
        with open(os.path.join(split, "labels", stem + ".txt"), "w") as f:
            f.write("\n".join(lines) + ("\n" if lines else ""))

        if len(previews) < 40:
            pv = canvas.copy()
            for ln in lines:
                pts = (np.array(ln.split()[1:], float).reshape(-1, 2) * [w, h]).astype(np.int32)
                ov = pv.copy()
                cv2.fillPoly(ov, [pts], (0, 255, 0))
                pv = cv2.addWeighted(ov, 0.4, pv, 0.6, 0)
            previews.append(cv2.resize(pv, (240, 240)))

    cols = 8
    while len(previews) % cols:
        previews.append(np.zeros_like(previews[0]))
    cv2.imwrite(os.path.join(OUT, "synth_preview.jpg"),
                np.vstack([np.hstack(previews[i:i + cols]) for i in range(0, len(previews), cols)]))
    print(f"wrote {args.n} composites to {split}")


if __name__ == "__main__":
    main()
