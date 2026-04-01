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
from io import BytesIO
from PIL import Image as PILImage
from PIL.ExifTags import TAGS, GPSTAGS

logger = logging.getLogger("pathfinder.detect")

router = APIRouter()

# Load model once at startup
model = YOLO(settings.model_path)

# ── Known GPS coordinates for xBD disaster dataset images ────────────────
# Satellite images from xBD are PNGs (no EXIF support), so we match the
# disaster name in the filename to look up real-world coordinates.
DISASTER_GPS_CATALOG: dict[str, dict[str, float]] = {
    "tubbs-fire":          {"lat": 38.4404, "lng": -122.7141},  # Santa Rosa, CA
    "santa-rosa-wildfire": {"lat": 38.4404, "lng": -122.7141},  # Same event
    "hurricane-harvey":    {"lat": 29.7604, "lng": -95.3698},   # Houston, TX
    "hurricane-florence":  {"lat": 34.2257, "lng": -78.0447},   # Wilmington, NC
    "hurricane-michael":   {"lat": 30.1588, "lng": -85.6602},   # Mexico Beach, FL
    "hurricane-matthew":   {"lat": 18.1942, "lng": -73.7508},   # Les Cayes, Haiti
    "guatemala-volcano":   {"lat": 14.4734, "lng": -90.8810},   # San Miguel Los Lotes
    "palu-tsunami":        {"lat": -0.8917, "lng": 119.8707},   # Palu, Indonesia
    "mexico-earthquake":   {"lat": 19.4326, "lng": -99.1332},   # Mexico City
    "midwest-flooding":    {"lat": 41.2565, "lng": -95.9345},   # Nebraska/Iowa
    "socal-fire":          {"lat": 34.2746, "lng": -119.2290},  # Ventura, CA
}

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


def _extract_gps(raw_bytes: bytes) -> dict | None:
    """
    Extract GPS lat/lng from EXIF metadata embedded in the image.
    Returns {"lat": float, "lng": float} or None if no GPS data found.
    """
    try:
        pil_img = PILImage.open(BytesIO(raw_bytes))
        exif_data = pil_img._getexif()
        if not exif_data:
            return None

        # Find the GPSInfo tag
        gps_info = None
        for tag_id, value in exif_data.items():
            tag_name = TAGS.get(tag_id, tag_id)
            if tag_name == "GPSInfo":
                gps_info = {}
                for gps_tag_id, gps_value in value.items():
                    gps_tag_name = GPSTAGS.get(gps_tag_id, gps_tag_id)
                    gps_info[gps_tag_name] = gps_value
                break

        if not gps_info:
            return None

        # Convert DMS (degrees, minutes, seconds) → decimal degrees
        def dms_to_decimal(dms_tuple, ref: str) -> float:
            degrees = float(dms_tuple[0])
            minutes = float(dms_tuple[1])
            seconds = float(dms_tuple[2])
            decimal = degrees + (minutes / 60.0) + (seconds / 3600.0)
            if ref in ("S", "W"):
                decimal = -decimal
            return decimal

        lat_dms = gps_info.get("GPSLatitude")
        lat_ref = gps_info.get("GPSLatitudeRef", "N")
        lng_dms = gps_info.get("GPSLongitude")
        lng_ref = gps_info.get("GPSLongitudeRef", "E")

        if lat_dms and lng_dms:
            lat = dms_to_decimal(lat_dms, lat_ref)
            lng = dms_to_decimal(lng_dms, lng_ref)
            logger.info("Extracted GPS from EXIF: lat=%.6f, lng=%.6f", lat, lng)
            return {"lat": lat, "lng": lng}

    except Exception as e:
        logger.debug("No EXIF GPS data: %s", e)

    return None


def _extract_gps_from_filename(filename: str) -> dict | None:
    """
    Match disaster name in the filename against the known GPS catalog.
    xBD filenames follow pattern: disaster-name_00000XXX_post_disaster.png
    Demo filenames follow: 01_tubbs-fire_66-destroyed.png
    """
    name_lower = filename.lower()
    for disaster_key, coords in DISASTER_GPS_CATALOG.items():
        if disaster_key in name_lower:
            logger.info("GPS from filename '%s' → %s (%.4f, %.4f)",
                        filename, disaster_key, coords["lat"], coords["lng"])
            return coords
    return None


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
                # - Skip very low-confidence no-damage (background noise)
                # - Keep moderate-confidence no-damage to show intact buildings
                # - Keep all non-zero damage classes even at low confidence
                if cls_id == 0 and conf < 0.10:
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

    # Extract GPS coordinates: try filename → EXIF → None
    gps_location = None
    if not is_region:
        # 1. Try matching disaster name in filename to known GPS catalog
        upload_name = file.filename or ""
        gps_location = _extract_gps_from_filename(upload_name)

        # 2. Fall back to EXIF metadata (JPEG/TIFF images with GPS tags)
        if not gps_location:
            gps = _extract_gps(contents)
            if gps:
                gps_location = gps

    h, w = img.shape[:2]

    # Estimate Ground Sample Distance (meters per pixel).
    # xBD satellite imagery (Maxar DigitalGlobe) is ~0.3 m/px at 1024×1024.
    # For other resolutions, scale proportionally.
    gsd = 0.3 * (1024.0 / max(w, h))

    return DetectionResponse(
        detections=detections,
        image_size={"width": w, "height": h},
        gps_location=gps_location,
        gsd=round(gsd, 6),
    )
