"""
PathFinder — POST /detect-region

Accepts a map bounding box (NW + SE corners), downloads the satellite
tile from MapTiler Static API, runs YOLO best.pt on it, and returns
geo-referenced damage polygons ready for map overlay.
"""

from __future__ import annotations

import httpx
import numpy as np
import cv2
from fastapi import APIRouter, HTTPException
from pydantic import BaseModel

from app.config import settings
from app.models import Detection, DAMAGE_CLASSES
from app.routes.detect import model  # reuse already-loaded YOLO model
from app.routes.georef import run_georef  # reuse georef pipeline

router = APIRouter()


class RegionRequest(BaseModel):
    north: float
    south: float
    east: float
    west: float


class RegionResponse(BaseModel):
    detections: list[Detection]
    danger_zones: dict  # GeoJSON FeatureCollection
    image_size: dict
    bounds: dict


def _build_static_url(north: float, south: float, east: float, west: float) -> str:
    """Build MapTiler Static API URL for the given bounding box."""
    cx = (west + east) / 2
    cy = (north + south) / 2

    # Estimate zoom from bounding box width (degrees → zoom)
    lng_span = abs(east - west)
    import math
    if lng_span > 0:
        zoom = min(18, max(12, int(math.log2(360 / lng_span))))
    else:
        zoom = 16

    return (
        f"https://api.maptiler.com/maps/satellite/static/"
        f"{cx},{cy},{zoom}/1024x1024@2x.png?key={settings.maptiler_key}"
    )


@router.post("/detect-region", response_model=RegionResponse)
async def detect_region(req: RegionRequest):
    """
    1) Download satellite tile for the bounding box
    2) Run YOLO inference (best.pt)
    3) Geo-reference detections to the actual coordinates
    4) Return GeoJSON danger zones ready for map overlay
    """

    # Step 1: Download satellite tile from MapTiler
    url = _build_static_url(req.north, req.south, req.east, req.west)

    try:
        async with httpx.AsyncClient(timeout=15.0) as client:
            resp = await client.get(url)
            resp.raise_for_status()
            img_bytes = resp.content
    except Exception as e:
        raise HTTPException(502, f"Failed to download satellite tile: {e}")

    # Decode image
    img = cv2.imdecode(np.frombuffer(img_bytes, np.uint8), cv2.IMREAD_COLOR)
    if img is None:
        raise HTTPException(500, "Failed to decode satellite image")

    h, w = img.shape[:2]

    # Step 2: Run YOLO inference using the same loaded best.pt model
    results = model.predict(img, conf=0.3, verbose=False)

    detections = []
    if results[0].masks is not None:
        for i, mask_xy in enumerate(results[0].masks.xy):
            cls_id = int(results[0].boxes.cls[i])
            conf = float(results[0].boxes.conf[i])
            cls_info = DAMAGE_CLASSES.get(cls_id, DAMAGE_CLASSES[0])
            detections.append(Detection(
                mask=mask_xy.tolist(),
                class_name=cls_info["name"],
                class_id=cls_id,
                danger_weight=cls_info["danger_weight"],
                confidence=conf,
            ))

    # Step 3: Geo-reference using the bounding box center as anchor
    anchor_lat = (req.north + req.south) / 2
    anchor_lng = (req.west + req.east) / 2

    # Calculate approximate GSD (meters per pixel) from the bounding box
    from math import cos, radians
    lat_span_m = abs(req.north - req.south) * 111_320
    lng_span_m = abs(req.east - req.west) * 111_320 * cos(radians(anchor_lat))
    gsd = max(lat_span_m / h, lng_span_m / w)

    danger_zones = run_georef(
        [d.model_dump() for d in detections],
        anchor_lat, anchor_lng,
        w, h,
        scale=gsd,
    )

    return RegionResponse(
        detections=detections,
        danger_zones=danger_zones,
        image_size={"width": w, "height": h},
        bounds={"north": req.north, "south": req.south, "east": req.east, "west": req.west},
    )
