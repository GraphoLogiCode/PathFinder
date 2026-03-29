"""
PathFinder — POST /detect

Phase 1 (stub): Returns real xView2 label data — pre-extracted lng_lat polygons
from the JSON labels.  When best.pt is ready (Phase 4), swap in real YOLO
inference; the rest of the pipeline stays identical.
"""

from __future__ import annotations

import json
import random
from pathlib import Path

from fastapi import APIRouter, UploadFile, File

from app.models import Detection, DetectionResponse, DAMAGE_CLASSES

router = APIRouter()

# ---------------------------------------------------------------------------
# Embedded xView2 stub data  (hurricane-michael sample polygons)
# These are real building footprint polygons from the Guatemala Volcano
# xView2 label file, remapped with varied damage classes for demo richness.
# ---------------------------------------------------------------------------

_STUB_DETECTIONS: list[dict] = [
    {
        "mask": [
            [351.01, 0.01], [360.05, 19.41], [347.86, 25.31],
            [344.32, 17.84], [331.35, 24.13], [320.34, 3.68],
            [332.90, 0.01], [351.01, 0.01],
        ],
        "class_name": "destroyed",
        "class_id": 3,
        "danger_weight": 10,
        "confidence": 0.92,
    },
    {
        "mask": [
            [83.17, 492.90], [83.21, 492.82], [90.40, 497.24],
            [68.20, 528.14], [71.09, 530.08], [62.16, 541.66],
            [50.33, 534.42], [48.16, 537.80], [37.30, 530.80],
            [38.50, 528.14], [22.09, 517.52], [30.05, 504.97],
            [37.78, 509.56], [39.95, 505.93], [41.16, 507.62],
            [44.54, 502.56], [37.30, 497.24], [43.81, 488.07],
            [52.26, 493.38], [56.37, 487.59], [53.95, 486.38],
            [59.11, 478.64], [83.17, 492.90],
        ],
        "class_name": "major-damage",
        "class_id": 2,
        "danger_weight": 6,
        "confidence": 0.87,
    },
    {
        "mask": [
            [85.86, 473.29], [90.40, 476.48], [81.18, 491.14],
            [63.78, 480.82], [64.56, 478.12], [57.50, 471.65],
            [62.51, 463.34], [85.86, 473.29],
        ],
        "class_name": "minor-damage",
        "class_id": 1,
        "danger_weight": 3,
        "confidence": 0.78,
    },
    {
        "mask": [
            [638.08, 913.26], [641.46, 912.53], [653.53, 927.02],
            [653.53, 929.19], [625.05, 951.88], [611.77, 934.50],
            [638.08, 913.26],
        ],
        "class_name": "destroyed",
        "class_id": 3,
        "danger_weight": 10,
        "confidence": 0.95,
    },
    {
        "mask": [
            [830.24, 825.63], [834.35, 830.21], [837.49, 828.04],
            [840.38, 831.66], [827.59, 840.84], [835.07, 852.42],
            [826.38, 857.01], [816.48, 841.80], [812.38, 845.18],
            [811.90, 844.46], [808.52, 839.15], [830.24, 825.63],
        ],
        "class_name": "no-damage",
        "class_id": 0,
        "danger_weight": 1,
        "confidence": 0.81,
    },
]


@router.post("/detect", response_model=DetectionResponse)
async def detect(file: UploadFile = File(...)):
    """
    Upload a satellite image → get pixel-space damage polygon masks.

    Phase 1: Returns pre-baked xView2 polygons (real building footprints
    with simulated damage classes).
    Phase 4: Will run YOLO inference via ultralytics.
    """
    # Read the file to validate it's a real upload (but discard for stub)
    _ = await file.read()

    detections = [Detection(**d) for d in _STUB_DETECTIONS]

    return DetectionResponse(
        detections=detections,
        image_size={"width": 1024, "height": 1024},
    )
