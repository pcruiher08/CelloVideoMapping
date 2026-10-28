"""Fine-tune YOLO26-seg on the cello masks (real + synthetic).

    .venv/bin/python -m cellomask.train                 # yolo26s-seg, 80 epochs
    .venv/bin/python -m cellomask.train --model yolo26n-seg.pt --epochs 40

The best weights are copied to models/cello-seg.pt, which the web app loads
by default.
"""

import argparse
import os
import shutil

from .autolabel import MODELS, OUT

ROOT = os.path.join(os.path.dirname(__file__), "..")


def main(argv=None):
    p = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    p.add_argument("--model", default="yolo26s-seg.pt")
    p.add_argument("--epochs", type=int, default=80)
    p.add_argument("--imgsz", type=int, default=640)
    p.add_argument("--batch", type=int, default=16)
    p.add_argument("--device", default="mps")
    p.add_argument("--name", default="cello-seg")
    args = p.parse_args(argv)

    from ultralytics import YOLO
    model = YOLO(os.path.join(MODELS, args.model))
    model.train(
        data=os.path.join(OUT, "data.yaml"),
        epochs=args.epochs, imgsz=args.imgsz, batch=args.batch,
        device=args.device, project=os.path.join(ROOT, "runs"),
        name=args.name, exist_ok=True, patience=25, workers=4,
        # One class whose look is stable (wood, f-holes, scroll) but whose
        # pose and context vary: lean on geometric and copy-paste aug, keep
        # hue shifts small so it does not learn "anything orange".
        degrees=20, translate=0.15, scale=0.6, shear=2.0, perspective=0.0005,
        fliplr=0.5, mosaic=1.0, mixup=0.05, copy_paste=0.4,
        hsv_h=0.015, hsv_s=0.6, hsv_v=0.5, close_mosaic=10,
        plots=True,
    )
    best = os.path.join(ROOT, "runs", args.name, "weights", "best.pt")
    shutil.copy(best, os.path.join(MODELS, "cello-seg.pt"))
    print(f"best weights -> {os.path.join(MODELS, 'cello-seg.pt')}")


if __name__ == "__main__":
    main()
