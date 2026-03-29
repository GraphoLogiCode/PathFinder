"""
PathFinder — POST /detect

Real YOLO inference: loads best.pt at startup, runs segmentation on
uploaded satellite images, returns pixel-space polygon masks.

Accepts an optional `source` query parameter:
  - source=upload (default): clean satellite image — standard inference
  - source=region: map canvas screenshot — applies pre-processing (resize,
    CLAHE contrast enhancement) and lowers the confidence threshold to
    compensate for domain mismatch with the xBD-trained model.
"""

from __future__ import annotations

from fastapi import APIRouter, UploadFile, File, Query
from app.config import settings
from app.models import Detection, DetectionResponse, DAMAGE_CLASSES
from ultralytics import YOLO
import numpy as np
import cv2
import logging

logger = logging.getLogger("pathfinder.detect")

router = APIRouter()

# Load model once at startup
model = YOLO(settings.model_path)

# ── Pre-processing for map canvas screenshots ────────────────────────────
TARGET_SIZE = 1024  # YOLO training resolution


def _preprocess_region(img: np.ndarray) -> np.ndarray:
    """
    Pre-process a map canvas screenshot to look closer to xBD training data:
      1. Resize to 1024×1024 (the training resolution)
      2. Apply CLAHE contrast enhancement on the L channel
    """
    h, w = img.shape[:2]
    logger.info("Region pre-processing: input %dx%d", w, h)

    # Resize to square training resolution
    img = cv2.resize(img, (TARGET_SIZE, TARGET_SIZE), interpolation=cv2.INTER_LANCZOS4)

    # CLAHE on the L channel of LAB colour space
    lab = cv2.cvtColor(img, cv2.COLOR_BGR2LAB)
    clahe = cv2.createCLAHE(clipLimit=2.0, tileGridSize=(8, 8))
    lab[:, :, 0] = clahe.apply(lab[:, :, 0])
    img = cv2.cvtColor(lab, cv2.COLOR_LAB2BGR)

    return img


@router.post("/detect", response_model=DetectionResponse)
async def detect(
    file: UploadFile = File(...),
    source: str = Query("upload", description="'upload' for satellite images, 'region' for map canvas screenshots"),
):
    """
    Upload a satellite image → get pixel-space damage polygon masks.
    Runs real YOLO26s-seg inference.
    """
    contents = await file.read()
    img = np.frombuffer(contents, np.uint8)
    img = cv2.imdecode(img, cv2.IMREAD_COLOR)

    if img is None:
        logger.error("Failed to decode uploaded image (source=%s, size=%d bytes)", source, len(contents))
        return DetectionResponse(detections=[], image_size={"width": 0, "height": 0})

    # Pre-process map canvas screenshots to improve inference quality
    is_region = source == "region"
    if is_region:
        img = _preprocess_region(img)

    # The model was trained on heavily imbalanced data (37k no-damage vs 7k damage).
    # Damage classes max out at ~0.40 confidence, so we use a very low threshold
    # and apply post-inference class filtering to surface real damage.
    conf_threshold = 0.05 if is_region else 0.3
    logger.info("Running inference: source=%s, conf=%.2f, img=%dx%d", source, conf_threshold, img.shape[1], img.shape[0])

    results = model.predict(img, conf=conf_threshold, verbose=False)

    detections = []
    if results[0].masks is not None:
        for i, mask_xy in enumerate(results[0].masks.xy):
            cls_id = int(results[0].boxes.cls[i])
            conf = float(results[0].boxes.conf[i])

            if is_region:
                # Class-imbalance correction for region captures:
                # - Skip low-confidence no-damage (likely false positives due to imbalance)
                # - Keep all non-zero damage classes even at low confidence
                if cls_id == 0 and conf < 0.25:
                    continue

            cls_info = DAMAGE_CLASSES.get(cls_id, DAMAGE_CLASSES[0])
            detections.append(Detection(
                mask=mask_xy.tolist(),
                class_name=cls_info["name"],
                class_id=cls_id,
                danger_weight=cls_info["danger_weight"],
                confidence=conf,
            ))

    logger.info("Inference complete: %d detections (source=%s, breakdown=%s)",
                len(detections), source,
                {DAMAGE_CLASSES[d.class_id]['name']: sum(1 for x in detections if x.class_id == d.class_id) for d in detections})

    h, w = img.shape[:2]
    return DetectionResponse(
        detections=detections,
        image_size={"width": w, "height": h},
    )
