"""Add the cellos the original annotator missed.

Many Roboflow images show two or three cellos but box only one. Unlabelled
cellos teach the model that cellos are background, so this proposes extra
instances with a detector (YOLOE text prompt, or our own trained model for a
second pseudo-labelling round), keeps those that do not overlap an existing
label, masks them with SAM and appends them to the label files.

    .venv/bin/python -m cellomask.complete                      # YOLOE
    .venv/bin/python -m cellomask.complete --model runs/.../best.pt

Writes `added_preview.jpg` showing only the additions (in green) so they can
be checked; `--dry-run` writes the preview without touching labels.
"""

import argparse
import glob
import os

import cv2
import numpy as np

from .autolabel import MODELS, OUT, keep_box_part, mask_to_polygon


def label_polys(path, w, h):
    polys = []
    if os.path.exists(path):
        for line in open(path).read().splitlines():
            v = line.split()
            if len(v) > 6:
                polys.append((np.array(v[1:], float).reshape(-1, 2) * [w, h]))
    return polys


def overlap(box, poly):
    """Fraction of `box` covered by the bounding box of `poly` — IoU is too
    strict when a new box sits inside a big existing cello."""
    x0, y0 = poly.min(0)
    x1, y1 = poly.max(0)
    ix = max(0.0, min(box[2], x1) - max(box[0], x0))
    iy = max(0.0, min(box[3], y1) - max(box[1], y0))
    area = (box[2] - box[0]) * (box[3] - box[1])
    return ix * iy / area if area > 0 else 1.0


def load_detector(model_path):
    if model_path:
        from ultralytics import YOLO
        return YOLO(model_path)
    from ultralytics import YOLOE
    m = YOLOE(os.path.join(MODELS, "yoloe-26s-seg.pt"))
    m.set_classes(["cello"])
    return m


def main(argv=None):
    p = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    p.add_argument("--model", default=None,
                   help="trained YOLO-seg weights; default is YOLOE 'cello'")
    p.add_argument("--conf", type=float, default=0.35)
    p.add_argument("--max-overlap", type=float, default=0.3)
    p.add_argument("--sam", default=os.path.join(MODELS, "sam2.1_b.pt"))
    p.add_argument("--dry-run", action="store_true")
    args = p.parse_args(argv)

    from ultralytics import SAM
    det = load_detector(args.model)
    sam = SAM(args.sam)

    tiles, n_added, n_imgs = [], 0, 0
    for path in sorted(glob.glob(os.path.join(OUT, "*", "images", "*"))):
        stem = os.path.splitext(os.path.basename(path))[0]
        if stem.startswith("syn_"):      # synthetic labels are exact already
            continue
        lpath = path.replace(f"{os.sep}images{os.sep}", f"{os.sep}labels{os.sep}")
        lpath = os.path.splitext(lpath)[0] + ".txt"
        im = cv2.imread(path)
        h, w = im.shape[:2]
        existing = label_polys(lpath, w, h)

        r = det.predict(im, conf=args.conf, verbose=False)[0]
        boxes = [b for b in r.boxes.xyxy.cpu().numpy().tolist()
                 if all(overlap(b, q) <= args.max_overlap for q in existing)]
        if not boxes:
            continue

        masks = sam(im, bboxes=boxes, verbose=False)[0].masks.data.cpu().numpy()
        lines, preview = [], im.copy()
        for q in existing:
            cv2.polylines(preview, [q.astype(np.int32)], True, (255, 0, 255), 3)
        for box, m in zip(boxes, masks.astype(bool)):
            poly = mask_to_polygon(keep_box_part(m, box))
            if poly is None:
                continue
            lines.append("0 " + " ".join(f"{x:.5f} {y:.5f}"
                                         for x, y in poly / [w, h]))
            ov = preview.copy()
            cv2.fillPoly(ov, [poly.astype(np.int32)], (0, 255, 0))
            preview = cv2.addWeighted(ov, 0.45, preview, 0.55, 0)
        if not lines:
            continue
        n_added += len(lines)
        n_imgs += 1
        if not args.dry_run:
            with open(lpath, "a") as f:
                f.write("\n".join(lines) + "\n")
        t = cv2.resize(preview, (192, 192))
        cv2.putText(t, stem[:10], (4, 186), cv2.FONT_HERSHEY_SIMPLEX, 0.4,
                    (255, 255, 255), 1, cv2.LINE_AA)
        tiles.append(t)

    if tiles:
        cols = 10
        while len(tiles) % cols:
            tiles.append(np.zeros_like(tiles[0]))
        cv2.imwrite(os.path.join(OUT, "added_preview.jpg"),
                    np.vstack([np.hstack(tiles[i:i + cols])
                               for i in range(0, len(tiles), cols)]))
    print(f"{'would add' if args.dry_run else 'added'} {n_added} instances "
          f"in {n_imgs} images")


if __name__ == "__main__":
    main()
