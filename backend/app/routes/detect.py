"""
PathFinder — POST /detect

Real YOLO inference: loads best.pt at startup, runs segmentation on
uploaded satellite images, returns pixel-space polygon masks.
"""

from __future__ import annotations

from fastapi import APIRouter, UploadFile, File
from app.config import settings
from app.models import Detection, DetectionResponse, DAMAGE_CLASSES
from ultralytics import YOLO
import numpy as np
import cv2

router = APIRouter()

# Load model once at startup
model = YOLO(settings.model_path)


@router.post("/detect", response_model=DetectionResponse)
async def detect(file: UploadFile = File(...)):
    """
    Upload a satellite image → get pixel-space damage polygon masks.
    Runs real YOLO26s-seg inference.
    """
    contents = await file.read()
    img = np.frombuffer(contents, np.uint8)
    img = cv2.imdecode(img, cv2.IMREAD_COLOR)

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

    h, w = img.shape[:2]
    return DetectionResponse(
        detections=detections,
        image_size={"width": w, "height": h},
    )
