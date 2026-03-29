#!/usr/bin/env python3
"""
convert_xview2_to_yolo_seg.py
─────────────────────────────
Converts xView2 dataset labels (JSON with WKT polygons) into
YOLO11-seg instance-segmentation format.

Usage:
    python convert_xview2_to_yolo_seg.py \
        --xview2-dir /path/to/train_images_labels_targets/train \
        --output-dir /path/to/yolo_dataset \
        --val-split 0.15

Output structure:
    yolo_dataset/
    ├── data.yaml
    ├── train/
    │   ├── images/   (symlinks or copies of post-disaster PNGs)
    │   └── labels/   (.txt files in YOLO seg format)
    └── val/
        ├── images/
        └── labels/
"""

import argparse
import json
import os
import re
import shutil
import random
import sys
from pathlib import Path


# ── xView2 damage subtypes → YOLO class IDs ────────────────────────
SUBTYPE_TO_CLASS = {
    "no-damage": 0,
    "minor-damage": 1,
    "major-damage": 2,
    "destroyed": 3,
}

CLASS_NAMES = ["no-damage", "minor-damage", "major-damage", "destroyed"]

# Image dimensions in xView2 (all images are 1024x1024)
IMG_W = 1024
IMG_H = 1024


def parse_wkt_polygon(wkt: str) -> list[tuple[float, float]]:
    """
    Parse a WKT POLYGON string into a list of (x, y) coordinate pairs.
    Example: "POLYGON ((x1 y1, x2 y2, ...))" → [(x1, y1), (x2, y2), ...]
    """
    # Extract the coordinate string from POLYGON ((...))
    match = re.search(r"POLYGON\s*\(\((.+?)\)\)", wkt)
    if not match:
        return []

    coord_str = match.group(1)
    coords = []
    for pair in coord_str.split(","):
        pair = pair.strip()
        parts = pair.split()
        if len(parts) == 2:
            x, y = float(parts[0]), float(parts[1])
            coords.append((x, y))

    return coords


def coords_to_yolo_seg(coords: list[tuple[float, float]]) -> str:
    """
    Convert pixel-space polygon coords to YOLO normalized format.
    YOLO seg format: x1/w y1/h x2/w y2/h ...  (all normalized 0-1)
    """
    normalized = []
    for x, y in coords:
        nx = max(0.0, min(1.0, x / IMG_W))
        ny = max(0.0, min(1.0, y / IMG_H))
        normalized.append(f"{nx:.6f} {ny:.6f}")
    return " ".join(normalized)


def process_label_file(label_path: str, is_pre_disaster: bool = False) -> list[str]:
    """
    Process a single xView2 label JSON file.
    - Post-disaster: uses subtype field → class 0-3
    - Pre-disaster: all buildings → class 0 (no-damage)
    Returns a list of YOLO segmentation lines (one per building).
    """
    with open(label_path) as f:
        data = json.load(f)

    lines = []
    xy_features = data.get("features", {}).get("xy", [])

    for feat in xy_features:
        props = feat.get("properties", {})

        if is_pre_disaster:
            # Pre-disaster: all buildings are undamaged
            class_id = 0
        else:
            # Post-disaster: use subtype
            subtype = props.get("subtype", "")
            if subtype not in SUBTYPE_TO_CLASS:
                continue  # Skip un-classified
            class_id = SUBTYPE_TO_CLASS[subtype]

        wkt = feat.get("wkt", "")
        coords = parse_wkt_polygon(wkt)

        if len(coords) < 3:
            continue  # Need at least 3 points for a valid polygon

        # Remove the closing point if it duplicates the first
        if coords[0] == coords[-1]:
            coords = coords[:-1]

        if len(coords) < 3:
            continue

        yolo_coords = coords_to_yolo_seg(coords)
        lines.append(f"{class_id} {yolo_coords}")

    return lines


def convert_dataset(
    xview2_dir: str,
    output_dir: str,
    val_split: float = 0.15,
    copy_images: bool = False,
    seed: int = 42,
    include_pre: bool = True,
):
    """
    Convert the entire xView2 dataset to YOLO segmentation format.
    Processes both post-disaster (with damage labels) and optionally
    pre-disaster (all class 0) to reduce model bias.
    """
    xview2_path = Path(xview2_dir)
    output_path = Path(output_dir)

    images_dir = xview2_path / "images"
    labels_dir = xview2_path / "labels"

    if not images_dir.exists():
        print(f"ERROR: Images directory not found: {images_dir}")
        sys.exit(1)
    if not labels_dir.exists():
        print(f"ERROR: Labels directory not found: {labels_dir}")
        sys.exit(1)

    # Find all post-disaster label files
    post_labels = sorted([
        f for f in labels_dir.iterdir()
        if f.suffix == ".json" and "post_disaster" in f.name
    ])
    # Find all pre-disaster label files
    pre_labels = sorted([
        f for f in labels_dir.iterdir()
        if f.suffix == ".json" and "pre_disaster" in f.name
    ]) if include_pre else []

    print(f"Found {len(post_labels)} post-disaster label files")
    print(f"Found {len(pre_labels)} pre-disaster label files")

    # Collect valid image-label pairs
    pairs = []
    skipped = 0
    total_buildings = 0
    class_counts = {name: 0 for name in CLASS_NAMES}

    # ── Process POST-disaster images (damage labels) ──
    for label_file in post_labels:
        img_name = label_file.stem + ".png"
        img_file = images_dir / img_name

        if not img_file.exists():
            skipped += 1
            continue

        yolo_lines = process_label_file(str(label_file), is_pre_disaster=False)

        if not yolo_lines:
            skipped += 1
            continue

        for line in yolo_lines:
            cid = int(line.split()[0])
            class_counts[CLASS_NAMES[cid]] += 1
        total_buildings += len(yolo_lines)

        pairs.append((img_file, yolo_lines, label_file.stem))

    post_count = len(pairs)

    # ── Process PRE-disaster images (all class 0 = no-damage) ──
    for label_file in pre_labels:
        img_name = label_file.stem + ".png"
        img_file = images_dir / img_name

        if not img_file.exists():
            skipped += 1
            continue

        yolo_lines = process_label_file(str(label_file), is_pre_disaster=True)

        if not yolo_lines:
            skipped += 1
            continue

        for line in yolo_lines:
            cid = int(line.split()[0])
            class_counts[CLASS_NAMES[cid]] += 1
        total_buildings += len(yolo_lines)

        pairs.append((img_file, yolo_lines, label_file.stem))

    pre_count = len(pairs) - post_count
    print(f"\nPost-disaster pairs: {post_count}")
    print(f"Pre-disaster pairs:  {pre_count}")

    print(f"Valid pairs: {len(pairs)}, Skipped: {skipped}")
    print(f"Total buildings: {total_buildings}")
    print(f"Class distribution:")
    for name, count in class_counts.items():
        pct = (count / total_buildings * 100) if total_buildings > 0 else 0
        print(f"  {name}: {count} ({pct:.1f}%)")

    # Shuffle and split
    random.seed(seed)
    random.shuffle(pairs)
    val_count = int(len(pairs) * val_split)
    val_pairs = pairs[:val_count]
    train_pairs = pairs[val_count:]

    print(f"\nTrain: {len(train_pairs)} images, Val: {len(val_pairs)} images")

    # Create output directories
    for split, split_pairs in [("train", train_pairs), ("val", val_pairs)]:
        img_out = output_path / split / "images"
        lbl_out = output_path / split / "labels"
        img_out.mkdir(parents=True, exist_ok=True)
        lbl_out.mkdir(parents=True, exist_ok=True)

        for img_file, yolo_lines, stem in split_pairs:
            # Copy or symlink image
            dst_img = img_out / img_file.name
            if copy_images:
                shutil.copy2(img_file, dst_img)
            else:
                # Use symlink (saves disk space)
                if dst_img.exists() or dst_img.is_symlink():
                    dst_img.unlink()
                try:
                    dst_img.symlink_to(img_file.resolve())
                except OSError:
                    # Fallback to copy if symlinks not supported
                    shutil.copy2(img_file, dst_img)

            # Write YOLO label file
            txt_name = img_file.stem + ".txt"
            dst_lbl = lbl_out / txt_name
            with open(dst_lbl, "w") as f:
                f.write("\n".join(yolo_lines) + "\n")

    # Generate data.yaml
    data_yaml = output_path / "data.yaml"
    yaml_content = f"""# xView2 Building Damage Assessment — YOLO Segmentation
# Auto-generated by convert_xview2_to_yolo_seg.py

path: {output_path.resolve()}
train: train/images
val: val/images

# Classes
names:
  0: no-damage
  1: minor-damage
  2: major-damage
  3: destroyed

# Class counts (from conversion)
# no-damage:    {class_counts['no-damage']}
# minor-damage: {class_counts['minor-damage']}
# major-damage: {class_counts['major-damage']}
# destroyed:    {class_counts['destroyed']}
"""
    with open(data_yaml, "w") as f:
        f.write(yaml_content)

    print(f"\n✅ Conversion complete!")
    print(f"   Output: {output_path.resolve()}")
    print(f"   data.yaml: {data_yaml.resolve()}")
    print(f"\n   Train: {len(train_pairs)} images")
    print(f"   Val:   {len(val_pairs)} images")
    print(f"   Total buildings: {total_buildings}")


def validate(output_dir: str):
    """Quick validation of the converted dataset."""
    output_path = Path(output_dir)
    data_yaml = output_path / "data.yaml"

    if not data_yaml.exists():
        print("ERROR: data.yaml not found. Run conversion first.")
        sys.exit(1)

    errors = 0
    for split in ["train", "val"]:
        img_dir = output_path / split / "images"
        lbl_dir = output_path / split / "labels"

        images = list(img_dir.glob("*.png"))
        labels = list(lbl_dir.glob("*.txt"))

        print(f"\n{split}: {len(images)} images, {len(labels)} labels")

        # Check each label file
        for lbl_file in labels[:10]:  # Spot-check first 10
            with open(lbl_file) as f:
                for i, line in enumerate(f):
                    parts = line.strip().split()
                    if not parts:
                        continue
                    class_id = int(parts[0])
                    coords = parts[1:]
                    if class_id not in range(4):
                        print(f"  ⚠ {lbl_file.name}:{i} invalid class {class_id}")
                        errors += 1
                    if len(coords) < 6:  # Need at least 3 points (x,y pairs)
                        print(f"  ⚠ {lbl_file.name}:{i} too few coords ({len(coords)})")
                        errors += 1
                    # Check coords are normalized
                    for val in coords:
                        v = float(val)
                        if v < 0 or v > 1:
                            print(f"  ⚠ {lbl_file.name}:{i} coord out of range: {v}")
                            errors += 1
                            break

    if errors == 0:
        print("\n✅ Validation passed!")
    else:
        print(f"\n⚠ Found {errors} issues")


if __name__ == "__main__":
    parser = argparse.ArgumentParser(
        description="Convert xView2 labels to YOLO segmentation format"
    )
    parser.add_argument(
        "--xview2-dir",
        required=True,
        help="Path to xView2 train/ directory (containing images/ and labels/)",
    )
    parser.add_argument(
        "--output-dir",
        required=True,
        help="Output directory for YOLO dataset",
    )
    parser.add_argument(
        "--val-split",
        type=float,
        default=0.15,
        help="Fraction of data to use for validation (default: 0.15)",
    )
    parser.add_argument(
        "--copy-images",
        action="store_true",
        help="Copy images instead of symlinking (uses more disk space)",
    )
    parser.add_argument(
        "--validate",
        action="store_true",
        help="Validate an already-converted dataset",
    )
    parser.add_argument(
        "--seed",
        type=int,
        default=42,
        help="Random seed for train/val split (default: 42)",
    )
    parser.add_argument(
        "--no-pre",
        action="store_true",
        help="Skip pre-disaster images (only use post-disaster)",
    )

    args = parser.parse_args()

    if args.validate:
        validate(args.output_dir)
    else:
        convert_dataset(
            xview2_dir=args.xview2_dir,
            output_dir=args.output_dir,
            val_split=args.val_split,
            copy_images=args.copy_images,
            seed=args.seed,
            include_pre=not args.no_pre,
        )
