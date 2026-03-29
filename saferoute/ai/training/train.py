#!/usr/bin/env python3
"""
train.py — YOLO11s-seg fine-tuning on xView2 building damage dataset
────────────────────────────────────────────────────────────────────

Usage:
    # Full training
    python train.py --data /path/to/yolo_dataset/data.yaml --epochs 100

    # Quick smoke test (1 epoch)
    python train.py --data /path/to/yolo_dataset/data.yaml --epochs 1

    # Resume from checkpoint
    python train.py --data /path/to/yolo_dataset/data.yaml --resume
"""

import argparse
import sys
from pathlib import Path

# Ensure project root is on path
PROJECT_ROOT = Path(__file__).resolve().parent.parent.parent
sys.path.insert(0, str(PROJECT_ROOT))

from ultralytics import YOLO


def train(
    data_yaml: str,
    epochs: int = 100,
    batch: int = 8,
    imgsz: int = 1024,
    model: str = "yolo11s-seg.pt",
    project: str = None,
    name: str = "pathfinder-damage",
    resume: bool = False,
    device: str = "0",
    workers: int = 4,
    patience: int = 20,
    lr0: float = 0.01,
    lrf: float = 0.01,
    cos_lr: bool = True,
):
    """
    Fine-tune YOLO11s-seg on xView2 building damage data.
    """
    weights_dir = PROJECT_ROOT / "ai" / "weights"
    weights_dir.mkdir(parents=True, exist_ok=True)

    if project is None:
        project = str(PROJECT_ROOT / "ai" / "runs")

    if resume:
        # Resume from last checkpoint
        last_pt = Path(project) / name / "weights" / "last.pt"
        if not last_pt.exists():
            print(f"ERROR: No checkpoint found at {last_pt}")
            sys.exit(1)
        print(f"📂 Resuming from: {last_pt}")
        yolo = YOLO(str(last_pt))
    else:
        print(f"🚀 Loading pretrained model: {model}")
        yolo = YOLO(model)

    print(f"\n{'='*60}")
    print(f"  PathFinder — YOLO11s-seg Training")
    print(f"{'='*60}")
    print(f"  Dataset:    {data_yaml}")
    print(f"  Model:      {model}")
    print(f"  Epochs:     {epochs}")
    print(f"  Batch size: {batch}")
    print(f"  Image size: {imgsz}")
    print(f"  Device:     {device}")
    print(f"  Workers:    {workers}")
    print(f"  Patience:   {patience}")
    print(f"  LR (init):  {lr0}")
    print(f"  Cosine LR:  {cos_lr}")
    print(f"{'='*60}\n")

    results = yolo.train(
        data=data_yaml,
        epochs=epochs,
        batch=batch,
        imgsz=imgsz,
        project=project,
        name=name,
        device=device,
        workers=workers,
        patience=patience,
        lr0=lr0,
        lrf=lrf,
        cos_lr=cos_lr,
        # Augmentation (tuned for satellite imagery)
        hsv_h=0.015,       # Hue augmentation (subtle for satellite)
        hsv_s=0.4,         # Saturation
        hsv_v=0.3,         # Value/brightness
        degrees=90.0,      # Rotation — satellite images have no "up"
        translate=0.1,      # Translation
        scale=0.3,          # Scale
        fliplr=0.5,         # Horizontal flip
        flipud=0.5,         # Vertical flip (valid for satellite!)
        mosaic=1.0,         # Mosaic augmentation
        mixup=0.1,          # Mixup augmentation
        copy_paste=0.1,     # Copy-paste augmentation for instance seg
        # Save settings
        save=True,
        save_period=10,     # Save checkpoint every 10 epochs
        plots=True,
        val=True,
        exist_ok=True,
    )

    # Copy best weights to ai/weights/best.pt
    best_src = Path(project) / name / "weights" / "best.pt"
    best_dst = weights_dir / "best.pt"
    if best_src.exists():
        import shutil
        shutil.copy2(best_src, best_dst)
        print(f"\n✅ Best weights copied to: {best_dst}")
    else:
        print(f"\n⚠ best.pt not found at {best_src}")

    print(f"\n{'='*60}")
    print(f"  Training complete!")
    print(f"  Results: {Path(project) / name}")
    print(f"  Best weights: {best_dst}")
    print(f"{'='*60}")

    return results


if __name__ == "__main__":
    parser = argparse.ArgumentParser(
        description="Fine-tune YOLO11s-seg on xView2 dataset"
    )
    parser.add_argument(
        "--data",
        required=True,
        help="Path to data.yaml",
    )
    parser.add_argument(
        "--epochs",
        type=int,
        default=100,
        help="Number of training epochs (default: 100)",
    )
    parser.add_argument(
        "--batch",
        type=int,
        default=8,
        help="Batch size (default: 8, reduce if OOM)",
    )
    parser.add_argument(
        "--imgsz",
        type=int,
        default=1024,
        help="Image size (default: 1024, matching xView2 native res)",
    )
    parser.add_argument(
        "--model",
        default="yolo11s-seg.pt",
        help="Base model (default: yolo11s-seg.pt)",
    )
    parser.add_argument(
        "--device",
        default="0",
        help="CUDA device (default: '0')",
    )
    parser.add_argument(
        "--workers",
        type=int,
        default=4,
        help="DataLoader workers (default: 4)",
    )
    parser.add_argument(
        "--resume",
        action="store_true",
        help="Resume training from last checkpoint",
    )
    parser.add_argument(
        "--patience",
        type=int,
        default=20,
        help="Early stopping patience (default: 20)",
    )
    parser.add_argument(
        "--lr0",
        type=float,
        default=0.01,
        help="Initial learning rate (default: 0.01)",
    )
    parser.add_argument(
        "--project",
        default=None,
        help="Project directory for outputs",
    )
    parser.add_argument(
        "--name",
        default="pathfinder-damage",
        help="Run name (default: pathfinder-damage)",
    )

    args = parser.parse_args()

    train(
        data_yaml=args.data,
        epochs=args.epochs,
        batch=args.batch,
        imgsz=args.imgsz,
        model=args.model,
        device=args.device,
        workers=args.workers,
        resume=args.resume,
        patience=args.patience,
        lr0=args.lr0,
        project=args.project,
        name=args.name,
    )
