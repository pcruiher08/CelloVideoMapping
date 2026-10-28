"""Turn the Roboflow box labels into YOLO-seg polygons with SAM 2.1.

The Roboflow cello dataset only has bounding boxes. SAM takes each box as a
prompt and returns the cello's mask; the largest contour of that mask becomes
the polygon label. A contact sheet of every result is written next to the
dataset so bad masks can be spotted and listed in `rejects.txt`.

    .venv/bin/python -m cellomask.autolabel
"""

import argparse
import glob
import os
import random
import shutil

import cv2
import numpy as np

ROOT = os.path.join(os.path.dirname(__file__), "..")
RAW = os.path.join(ROOT, "data", "raw", "cello", "train")
OUT = os.path.join(ROOT, "data", "seg")
MODELS = os.path.join(ROOT, "models")


def read_boxes(label_path, w, h):
    boxes = []
    for line in open(label_path).read().splitlines():
        v = line.split()
        if len(v) != 5:
            continue
        cx, cy, bw, bh = (float(x) for x in v[1:])
        boxes.append([(cx - bw / 2) * w, (cy - bh / 2) * h,
                      (cx + bw / 2) * w, (cy + bh / 2) * h])
    return boxes


def mask_to_polygon(mask, eps_frac=0.002, merge_parts=False, min_part=0.02):
    """Largest outer contour, lightly simplified. Holes (the gap between
    strings and fingerboard, say) are dropped: the replacement should cover
    the whole instrument silhouette.

    With `merge_parts`, every piece above `min_part` of the total area is kept
    and joined into one polygon by zero-width bridges (what Ultralytics does
    for multi-part COCO segments) — needed when an arm splits a cello in two.
    """
    cnts, _ = cv2.findContours(mask.astype(np.uint8), cv2.RETR_EXTERNAL,
                               cv2.CHAIN_APPROX_NONE)
    if not cnts:
        return None
    if merge_parts:
        total = sum(cv2.contourArea(c) for c in cnts)
        cnts = [c for c in cnts if cv2.contourArea(c) >= min_part * total]
    else:
        cnts = [max(cnts, key=cv2.contourArea)]
    parts = []
    for c in cnts:
        c = cv2.approxPolyDP(c, eps_frac * cv2.arcLength(c, True), True).reshape(-1, 2)
        if len(c) >= 3:
            parts.append(c)
    if not parts:
        return None
    if len(parts) == 1:
        return parts[0]
    from ultralytics.data.converter import merge_multi_segment
    return np.concatenate(merge_multi_segment([p.reshape(-1).tolist() for p in parts]))


def keep_box_part(mask, box):
    """SAM sometimes bleeds outside the prompt box (into the case, the
    player); clip to a slightly padded box."""
    x0, y0, x1, y1 = box
    pw, ph = 0.03 * (x1 - x0), 0.03 * (y1 - y0)
    clip = np.zeros_like(mask)
    clip[max(0, int(y0 - ph)):int(y1 + ph), max(0, int(x0 - pw)):int(x1 + pw)] = 1
    return mask & clip


def main(argv=None):
    p = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    p.add_argument("--sam", default=os.path.join(MODELS, "sam2.1_b.pt"))
    p.add_argument("--val", type=float, default=0.15)
    p.add_argument("--seed", type=int, default=0)
    args = p.parse_args(argv)

    from ultralytics import SAM
    sam = SAM(args.sam)

    rejects_path = os.path.join(OUT, "rejects.txt")
    rejects = set()
    if os.path.exists(rejects_path):
        rejects = {l.strip() for l in open(rejects_path) if l.strip()}

    images = sorted(glob.glob(os.path.join(RAW, "images", "*")))
    random.Random(args.seed).shuffle(images)
    n_val = int(len(images) * args.val)
    split = {p: ("val" if i < n_val else "train") for i, p in enumerate(images)}

    for s in ("train", "val"):
        for d in ("images", "labels"):
            os.makedirs(os.path.join(OUT, s, d), exist_ok=True)

    tiles = []
    written = 0
    for path in sorted(images):
        stem = os.path.splitext(os.path.basename(path))[0]
        if stem in rejects:
            continue
        im = cv2.imread(path)
        h, w = im.shape[:2]
        boxes = read_boxes(os.path.join(RAW, "labels", stem + ".txt"), w, h)
        if not boxes:
            continue
        res = sam(im, bboxes=boxes, verbose=False)[0]
        masks = res.masks.data.cpu().numpy().astype(bool)

        lines, preview = [], im.copy()
        for box, m in zip(boxes, masks):
            m = keep_box_part(m, box)
            poly = mask_to_polygon(m)
            if poly is None:
                continue
            norm = poly / [w, h]
            lines.append("0 " + " ".join(f"{x:.5f} {y:.5f}" for x, y in norm))
            overlay = preview.copy()
            cv2.fillPoly(overlay, [poly.astype(np.int32)], (255, 0, 255))
            preview = cv2.addWeighted(overlay, 0.45, preview, 0.55, 0)
            cv2.polylines(preview, [poly.astype(np.int32)], True, (255, 0, 255), 3)

        s = split[path]
        shutil.copy(path, os.path.join(OUT, s, "images", os.path.basename(path)))
        with open(os.path.join(OUT, s, "labels", stem + ".txt"), "w") as f:
            f.write("\n".join(lines) + "\n")
        written += 1

        t = cv2.resize(preview, (192, 192))
        cv2.putText(t, stem[:10], (4, 186), cv2.FONT_HERSHEY_SIMPLEX, 0.4,
                    (255, 255, 255), 1, cv2.LINE_AA)
        tiles.append(t)

    with open(os.path.join(OUT, "data.yaml"), "w") as f:
        f.write(f"path: {os.path.abspath(OUT)}\ntrain: train/images\n"
                f"val: val/images\nnames:\n  0: cello\n")

    cols = 12
    while len(tiles) % cols:
        tiles.append(np.zeros_like(tiles[0]))
    sheet = np.vstack([np.hstack(tiles[i:i + cols])
                       for i in range(0, len(tiles), cols)])
    cv2.imwrite(os.path.join(OUT, "masks_preview.jpg"), sheet)
    print(f"{written} images labelled -> {OUT} "
          f"({sum(1 for v in split.values() if v == 'val')} val)")


if __name__ == "__main__":
    main()
