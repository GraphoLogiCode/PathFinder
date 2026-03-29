"""
PathFinder — POST /georef

Real geo-referencing pipeline with 4 geometry algorithms:
  A. RDP Simplification (reduce polygon vertices ~90%)
  B. Pixel → Lat/Lng (Equirectangular Approximation)
  C. Polygon Validation (make_valid)
  D. Cascaded Union (unary_union — merge overlapping polygons)
"""

from __future__ import annotations

from math import cos, radians

from fastapi import APIRouter
from shapely.geometry import Polygon, mapping
from shapely.validation import make_valid
from shapely.ops import unary_union

from app.models import GeoRefRequest, GeoRefResponse, DAMAGE_CLASSES

router = APIRouter()


def pixel_to_latlng(
    px_x: float, px_y: float,
    center_x: float, center_y: float,
    anchor_lat: float, anchor_lng: float,
    scale: float,
) -> tuple[float, float]:
    """Equirectangular approximation: pixel coords → lat/lng."""
    dx_meters = (px_x - center_x) * scale
    dy_meters = (center_y - px_y) * scale  # Y is flipped in image coords
    lat = anchor_lat + (dy_meters / 111_320)
    lng = anchor_lng + (dx_meters / (111_320 * cos(radians(anchor_lat))))
    return lat, lng


def run_georef(
    detections_data: list[dict],
    anchor_lat: float,
    anchor_lng: float,
    img_width: int,
    img_height: int,
    scale: float = 2.07,
) -> dict:
    """
    Standalone geo-referencing pipeline. Converts pixel-space detection masks
    into a GeoJSON FeatureCollection with lat/lng coordinates.

    Can be called from the /georef endpoint or directly from /detect-region.
    """
    center_x = img_width / 2
    center_y = img_height / 2

    # Group features by severity class for union
    class_features: dict[int, list] = {}

    for det in detections_data:
        mask = det.get("mask", [])
        if len(mask) < 3:
            continue

        poly = Polygon(mask)
        poly = poly.simplify(tolerance=2.0, preserve_topology=True)
        if not poly.is_valid:
            poly = make_valid(poly)
        if poly.is_empty:
            continue

        geo_coords = []
        for x, y in poly.exterior.coords:
            lat, lng = pixel_to_latlng(
                x, y, center_x, center_y, anchor_lat, anchor_lng, scale
            )
            geo_coords.append([lng, lat])

        geo_poly = Polygon(geo_coords)
        if geo_poly.is_empty:
            continue

        cls_id = det.get("class_id", 0)
        if cls_id not in class_features:
            class_features[cls_id] = []
        class_features[cls_id].append(geo_poly)

    features = []
    for cls_id, polys in class_features.items():
        merged = unary_union(polys)
        cls_info = DAMAGE_CLASSES.get(cls_id, DAMAGE_CLASSES[0])
        geoms = merged.geoms if merged.geom_type == "MultiPolygon" else [merged]
        for geom in geoms:
            features.append({
                "type": "Feature",
                "geometry": mapping(geom),
                "properties": {
                    "severity": cls_info["name"],
                    "class_id": cls_id,
                    "danger_weight": cls_info["danger_weight"],
                    "color": cls_info["color"],
                    "confidence": 0.85,
                },
            })

    return {"type": "FeatureCollection", "features": features}


@router.post("/georef", response_model=GeoRefResponse)
async def georef(req: GeoRefRequest):
    """
    Convert pixel-space detection masks → geo-referenced GeoJSON danger zones.
    """
    dets = [d.model_dump() for d in req.detections]
    center_x, center_y = req.image_center_px
    result = run_georef(
        dets,
        req.anchor.lat,
        req.anchor.lng,
        int(center_x * 2),  # img width ≈ 2 * center_x
        int(center_y * 2),  # img height ≈ 2 * center_y
        req.scale,
    )
    return GeoRefResponse(**result)

