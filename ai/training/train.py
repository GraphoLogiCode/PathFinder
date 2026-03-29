"""
🛡️ PathFinder — YOLO26m-seg Training Script
=============================================
Optimized for: ASUS Ascent GX10 (NVIDIA GB10 Grace Blackwell Superchip)

Hardware Profile:
  • GPU:    NVIDIA Blackwell (5th-gen Tensor Cores, FP4/FP8/FP16/FP32)
  • Memory: 128 GB unified LPDDR5x (shared CPU ↔ GPU via NVLink-C2C)
  • CPU:    20-core NVIDIA Grace (Arm v9.2-A)
  • AI:     Up to 1 PFLOP @ FP4

Usage:
  python ai/training/train.py
"""

from pathlib import Path
from ultralytics import YOLO
import torch
import sys

# ══════════════════════════════════════════════════════════════════
# PATHS — adjust to your system
# ══════════════════════════════════════════════════════════════════
PROJECT_ROOT = Path(__file__).resolve().parents[2]           # PathFinder/
DATASET_DIR  = PROJECT_ROOT / "saferoute" / "data" / "yolo_dataset"
DATA_YAML    = DATASET_DIR / "data.yaml"
WEIGHTS_DIR  = PROJECT_ROOT / "saferoute" / "ai" / "weights"
RUNS_DIR     = PROJECT_ROOT / "saferoute" / "ai" / "runs"

WEIGHTS_DIR.mkdir(parents=True, exist_ok=True)
RUNS_DIR.mkdir(parents=True, exist_ok=True)

# ══════════════════════════════════════════════════════════════════
# TRAINING HYPERPARAMETERS — Tuned for ASUS Ascent GX10
# ══════════════════════════════════════════════════════════════════
#
# The GX10 uses **unified memory** — there is NO separate VRAM.
# The full 128 GB LPDDR5x pool is accessible to both CPU and GPU
# via NVLink-C2C, so batch sizes can be pushed FAR beyond what a
# consumer GPU (8–16 GB) allows.
#
#   YOLO26 advantages over YOLO11:
#     • NMS-free: end-to-end inference, faster at demo time
#     • STAL: Small-Target-Aware Label Assignment — better for small buildings
#     • MuSGD: hybrid SGD+Muon optimizer — faster, more stable convergence
#     • ProgLoss: Progressive Loss Balancing — better multi-class training
#
#   Batch size rationale (YOLO26m-seg @ 1024×1024):
#     ~3 GB per image in batch during training (fwd + bwd + optim)
#     128 GB × 0.85 utilization ≈ 108 GB usable
#     108 / 3 ≈ 36 max → use 16 (power-of-2, conservative)
#     You can try BATCH=32 if nvidia-smi shows headroom.
#
#   Workers rationale:
#     20-core Grace CPU → 8 workers is optimal (leaves cores for
#     GPU scheduling, OS, and data augmentation overhead).
#
# ══════════════════════════════════════════════════════════════════

MODEL_NAME = "yolo26m-seg.pt"   # YOLO26 medium — NMS-free, STAL, best for GX10
EPOCHS     = 100                # GX10 trains fast — 100 epochs is very achievable
BATCH      = 32                 # Observed 45.6G/122.5G at batch=16 → batch=32 uses ~91G, safe
IMGSZ      = 1024               # Native xView2 resolution — no downscaling needed
PATIENCE   = 0                  # 0 = disable early stopping — train full EPOCHS without interruption
DEVICE     = 0                  # GB10 GPU index
WORKERS    = 10                 # 20-core Grace CPU → 10 workers (matches observed Ultralytics override)
COMPILE    = True               # torch.compile — 10–20% speedup on Blackwell after warmup
RUN_NAME   = "pathfinder-damage"


def detect_hardware():
    """Auto-detect hardware and adjust hyperparameters if not on GX10."""
    global BATCH, WORKERS, EPOCHS, PATIENCE, DEVICE

    if not torch.cuda.is_available():
        DEVICE = "cpu"
        BATCH = 4
        WORKERS = 2
        EPOCHS = 30
        print("⚠️  No GPU detected — CPU fallback (training will be very slow)")
        return

    gpu_name = torch.cuda.get_device_name(0)
    mem_bytes = torch.cuda.get_device_properties(0).total_memory
    mem_gb = mem_bytes / (1024 ** 3)

    print(f"🖥️  GPU detected: {gpu_name}")
    print(f"💾  Memory:       {mem_gb:.1f} GB")

    if mem_gb >= 96:
        # GX10-class: 128 GB unified memory
        # Observed 45.6G GPU mem at batch=16 → batch=32 uses ~91G, well within 122.5G budget
        BATCH   = 16    # yolo26m-seg @ 1024px → 32 halves steps/epoch (~30-40% faster)
        WORKERS = 10
        EPOCHS  = 10
        PATIENCE = 0    # Disabled — run full 100 epochs
        print(f"✅  GX10-class hardware confirmed")
    elif mem_gb >= 20:
        # High-end consumer (RTX 3090/4090/5090, A100, etc.)
        BATCH   = 8     # yolo26m-seg is heavier than small
        WORKERS = 6
        EPOCHS  = 80
        PATIENCE = 12
        print(f"ℹ️  High-end GPU — adjusted BATCH={BATCH}")
    elif mem_gb >= 10:
        # Mid-range GPU (RTX 3060/4060 12GB, etc.)
        BATCH   = 4     # yolo26m-seg @ 1024px is tight on 12 GB
        WORKERS = 4
        EPOCHS  = 60
        PATIENCE = 10
        print(f"ℹ️  Mid-range GPU — adjusted BATCH={BATCH}")
    else:
        # Low-end GPU (6–8 GB)
        BATCH   = 4
        WORKERS = 4
        EPOCHS  = 50
        PATIENCE = 10
        print(f"⚠️  Low-memory GPU — conservative BATCH={BATCH}")


def train():
    """Run YOLO11s-seg fine-tuning with GX10-optimized settings."""

    detect_hardware()

    print(f"\n{'═'*60}")
    print(f"  PATHFINDER — YOLO26m-seg Training")
    print(f"{'═'*60}")
    print(f"  Model:      {MODEL_NAME}")
    print(f"  Dataset:    {DATA_YAML}")
    print(f"  Epochs:     {EPOCHS}")
    print(f"  Batch:      {BATCH}")
    print(f"  Image size: {IMGSZ}")
    print(f"  Patience:   {PATIENCE}")
    print(f"  Workers:    {WORKERS}")
    print(f"  Device:     {DEVICE}")
    print(f"  Output:     {RUNS_DIR / RUN_NAME}")
    print(f"{'═'*60}\n")

    # Validate dataset exists
    if not DATA_YAML.exists():
        print(f"❌ data.yaml not found at {DATA_YAML}")
        print("   Run convert_xview2_to_yolo_seg.py first.")
        sys.exit(1)

    # Load pretrained model
    model = YOLO(MODEL_NAME)
    print(f"✅ Loaded {MODEL_NAME} ({model.task})\n")

    # ──────────────────────────────────────────────────
    # 🚀 TRAINING
    # ──────────────────────────────────────────────────
    results = model.train(
        data=str(DATA_YAML),
        epochs=EPOCHS,
        batch=BATCH,
        imgsz=IMGSZ,
        project=str(RUNS_DIR),
        name=RUN_NAME,
        device=DEVICE,
        workers=WORKERS,
        patience=PATIENCE,

        # --- Optimizer ---
        optimizer="auto",        # Ultralytics picks AdamW or SGD
        lr0=0.01,                # Initial learning rate
        lrf=0.01,                # Final LR = lr0 × lrf
        cos_lr=True,             # Cosine annealing schedule
        weight_decay=0.0005,     # Standard regularization
        warmup_epochs=3.0,       # Warmup for stable batch-32 training
        warmup_momentum=0.8,

        # --- Satellite-specific augmentations ---
        # Satellite images have no canonical "up" direction,
        # so aggressive rotation + flips are valid and critical
        hsv_h=0.015,             # Slight hue shift (sensor variation)
        hsv_s=0.4,               # Saturation jitter
        hsv_v=0.3,               # Brightness jitter (cloud shadows)
        degrees=90.0,            # Full 90° rotation bands
        translate=0.1,           # Minor translation
        scale=0.3,               # ±30% zoom — building size variation
        fliplr=0.5,              # Horizontal flip
        flipud=0.5,              # Vertical flip (valid for overhead)
        mosaic=1.0,              # Mosaic probability (great for small objects)
        mixup=0.1,               # Light mixup
        copy_paste=0.1,          # Segment copy-paste augmentation

        # --- Performance (GX10-specific) ---
        amp=True,                # Mixed-precision (Blackwell Tensor Cores)
        compile=COMPILE,         # torch.compile — fuses ops, ~10–20% faster on Blackwell after warmup
        cache="ram",             # 128 GB unified mem → cache full dataset in RAM
        rect=False,              # Keep square padding for mosaic compatibility
        close_mosaic=10,         # Disable mosaic for last 10 epochs (finer details)

        # --- Saving ---
        save=True,
        save_period=10,          # Checkpoint every 10 epochs
        plots=True,              # Generate training curves
        val=True,                # Validate every epoch
        exist_ok=True,
    )

    # ──────────────────────────────────────────────────
    # 📊 POST-TRAINING SUMMARY
    # ──────────────────────────────────────────────────
    best_pt = RUNS_DIR / RUN_NAME / "weights" / "best.pt"

    print(f"\n{'═'*60}")
    print(f"  ✅ TRAINING COMPLETE")
    print(f"{'═'*60}")
    if best_pt.exists():
        import shutil
        # Copy to deployment locations
        dst_saferoute = WEIGHTS_DIR / "best.pt"
        dst_main = PROJECT_ROOT / "ai" / "weights" / "best.pt"
        dst_main.parent.mkdir(parents=True, exist_ok=True)

        shutil.copy2(best_pt, dst_saferoute)
        shutil.copy2(best_pt, dst_main)

        size_mb = best_pt.stat().st_size / 1e6
        print(f"  Best weights: {best_pt}")
        print(f"  Size:         {size_mb:.1f} MB")
        print(f"  Copied to:    {dst_saferoute}")
        print(f"                {dst_main}")
    else:
        print(f"  ⚠️  best.pt not found at {best_pt}")

    print(f"{'═'*60}")

    return results


if __name__ == "__main__":
    train()
