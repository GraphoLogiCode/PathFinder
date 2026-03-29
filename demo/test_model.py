#!/usr/bin/env python3
"""
PathFinder — Trained Model Validation Test
==========================================
Verifies that a satellite image actually goes through the trained YOLO model
and returns sensible damage detections.

NO full pipeline — just raw model inference.

Usage:
    python demo/test_model.py
    python demo/test_model.py --image path/to/image.png
    python demo/test_model.py --all          # test all pre-scanned damaged images
"""

from __future__ import annotations

import argparse
import sys
import time
from pathlib import Path

# ─── Paths ───────────────────────────────────────────────────────────────────

ROOT        = Path(__file__).resolve().parent.parent
MODEL_PATH  = ROOT / "saferoute" / "ai" / "runs" / "pathfinder-damage" / "weights" / "best.pt"
IMG_DIR     = ROOT / "saferoute" / "data" / "yolo_dataset" / "val" / "images"

# Known best-damaged images (pre-scanned)
TEST_IMAGES = {
    "santa-rosa-wildfire_00000007_post_disaster.png":  "Tubbs Fire — 66 destroyed expected",
    "hurricane-harvey_00000001_post_disaster.png":     "Hurricane Harvey — 39 major-damage expected",
    "hurricane-florence_00000048_post_disaster.png":   "Hurricane Florence — 16 major-damage expected",
    "hurricane-michael_00000000_post_disaster.png":    "Hurricane Michael — 20 minor-damage expected",
}

DAMAGE_CLASSES = {
    0: {"name": "no-damage",    "color": "\033[92m",  "symbol": "🟢"},
    1: {"name": "minor-damage", "color": "\033[93m",  "symbol": "🟡"},
    2: {"name": "major-damage", "color": "\033[33m",  "symbol": "🟠"},
    3: {"name": "destroyed",    "color": "\033[91m",  "symbol": "🔴"},
}
RESET = "\033[0m"


def run_test(model, img_path: Path, label: str = "", conf: float = 0.3) -> dict:
    """Run the model on a single image and return raw results."""
    import cv2

    img = cv2.imread(str(img_path))
    if img is None:
        print(f"  ✗ Could not read image: {img_path}")
        return {}

    h, w = img.shape[:2]

    t0 = time.perf_counter()
    results = model.predict(img, conf=conf, verbose=False)
    elapsed = time.perf_counter() - t0

    # Raw counts per class
    counts: dict[str, int] = {}
    confidences: list[float] = []

    if results[0].masks is not None:
        for i, _ in enumerate(results[0].masks.xy):
            cls_id   = int(results[0].boxes.cls[i])
            conf_val = float(results[0].boxes.conf[i])
            cls_name = DAMAGE_CLASSES.get(cls_id, DAMAGE_CLASSES[0])["name"]
            counts[cls_name]  = counts.get(cls_name, 0) + 1
            confidences.append(conf_val)

    total = sum(counts.values())
    avg_conf = sum(confidences) / len(confidences) if confidences else 0.0
    damage   = sum(v for k, v in counts.items() if k != "no-damage")

    # Severity label
    if counts.get("destroyed", 0) > 0:
        sev, sev_color = "DESTROYED", "\033[91m"
    elif counts.get("major-damage", 0) > 0:
        sev, sev_color = "MAJOR DAMAGE", "\033[33m"
    elif counts.get("minor-damage", 0) > 0:
        sev, sev_color = "MINOR DAMAGE", "\033[93m"
    elif total > 0:
        sev, sev_color = "NO DAMAGE", "\033[92m"
    else:
        sev, sev_color = "NOTHING DETECTED", "\033[90m"

    print(f"\n  {'─' * 62}")
    print(f"  📸  {img_path.name}")
    if label:
        print(f"       {label}")
    print(f"  {'─' * 62}")
    print(f"  Image size : {w} × {h} px")
    print(f"  Inference  : {elapsed * 1000:.1f} ms")
    print(f"  Detections : {total} total  |  {damage} with damage")
    print(f"  Avg conf   : {avg_conf:.1%}")
    print()
    print(f"  Breakdown:")
    for cls_id in sorted(DAMAGE_CLASSES):
        cls    = DAMAGE_CLASSES[cls_id]
        n      = counts.get(cls["name"], 0)
        bar    = "█" * min(n, 40)
        color  = cls["color"] if n > 0 else "\033[90m"
        print(f"    {cls['symbol']}  {cls['name']:<14}  {color}{n:>4}  {bar}{RESET}")
    print()
    print(f"  Severity   : {sev_color}{sev}{RESET}")

    return {
        "file": img_path.name,
        "total": total,
        "damage": damage,
        "counts": counts,
        "avg_conf": avg_conf,
        "inference_ms": round(elapsed * 1000, 1),
        "severity": sev,
    }


def main():
    parser = argparse.ArgumentParser(description="PathFinder — Model Validation Test")
    parser.add_argument("--image", type=str, default=None,
                        help="Path to a specific satellite image to test")
    parser.add_argument("--all", action="store_true",
                        help="Run all pre-scanned damaged test images")
    parser.add_argument("--conf", type=float, default=0.3,
                        help="Confidence threshold (default 0.3)")
    args = parser.parse_args()

    print("""
╔══════════════════════════════════════════════════════════════════╗
║   🔬  PathFinder — Trained Model Validation Test                 ║
╚══════════════════════════════════════════════════════════════════╝
""")

    # ── Check model ──────────────────────────────────────────────────────
    if not MODEL_PATH.exists():
        print(f"  ✗ Model not found: {MODEL_PATH}")
        print(f"    Train the model first or check the path.")
        sys.exit(1)

    print(f"  ✓ Model   : {MODEL_PATH}")
    print(f"  ✓ Conf    : {args.conf}")

    # ── Load model ───────────────────────────────────────────────────────
    from ultralytics import YOLO
    t0 = time.perf_counter()
    model = YOLO(str(MODEL_PATH))
    load_time = time.perf_counter() - t0
    print(f"  ✓ Loaded  : {load_time:.2f}s")

    # Model metadata
    nc = getattr(model.model, "nc", "?")
    print(f"  ✓ Classes : {nc}")
    print()

    # ── Choose images to test ────────────────────────────────────────────
    if args.image:
        img_path = Path(args.image)
        if not img_path.is_absolute():
            # Try relative to img_dir first
            candidate = IMG_DIR / img_path
            if candidate.exists():
                img_path = candidate
        to_test = [(img_path, "Custom image")]

    elif args.all:
        to_test = []
        for fname, label in TEST_IMAGES.items():
            p = IMG_DIR / fname
            if p.exists():
                to_test.append((p, label))
            else:
                print(f"  ⚠ Not found: {fname}")

    else:
        # Default: just the most damaged image (Tubbs Fire — 66 destroyed)
        default_img = IMG_DIR / "santa-rosa-wildfire_00000007_post_disaster.png"
        if not default_img.exists():
            # Fallback to first available
            imgs = sorted(IMG_DIR.glob("*_post_disaster.png"))
            if not imgs:
                print("  ✗ No post-disaster images found in dataset.")
                sys.exit(1)
            default_img = imgs[0]
        to_test = [(default_img, "Default: highest-damage image in dataset")]

    # ── Run tests ────────────────────────────────────────────────────────
    all_results = []
    for img_path, label in to_test:
        result = run_test(model, img_path, label=label, conf=args.conf)
        if result:
            all_results.append(result)

    # ── Final verdict ────────────────────────────────────────────────────
    print(f"\n  {'═' * 62}")
    print(f"  ✅  MODEL VALIDATION COMPLETE")
    print(f"  {'═' * 62}")

    if len(all_results) > 1:
        print(f"\n  Tested {len(all_results)} images:")
        for r in all_results:
            sev_sym = "🔴" if "DESTROYED" in r["severity"] else "🟠" if "MAJOR" in r["severity"] else "🟡" if "MINOR" in r["severity"] else "🟢"
            print(f"    {sev_sym}  {r['file']:<52}  {r['inference_ms']:>6.0f} ms  dmg={r['damage']}")
    else:
        r = all_results[0] if all_results else {}
        if r:
            print(f"\n  Image     : {r['file']}")
            print(f"  Severity  : {r['severity']}")
            print(f"  Detected  : {r['damage']} damaged  +  {r['counts'].get('no-damage', 0)} no-damage")
            print(f"  Time      : {r['inference_ms']} ms")

    print(f"\n  → Model is {'working correctly ✓' if all_results else 'NOT responding ✗'}")
    print()


if __name__ == "__main__":
    main()
