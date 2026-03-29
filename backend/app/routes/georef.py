"""
PathFinder — POST /georef

Phase 1 (stub): Returns a mock GeoJSON FeatureCollection with hardcoded
danger polygons near the provided anchor coordinates.

Phase 2 (real): Implements the 4 geometry algorithms:
  A. RDP Simplification
  B. Pixel → Lat/Lng (Equirectangular Approximation)
  C. Polygon Validation (make_valid)
  D. Cascaded Union (unary_union)
"""

from __future__ import annotations

from fastapi import APIRouter

from app.models import GeoRefRequest, GeoRefResponse, DAMAGE_CLASSES

router = APIRouter()


def _make_stub_geojson(anchor_lat: float, anchor_lng: float) -> dict:
    """Generate 3 mock danger zone polygons near the given anchor point."""
    features = []

    # Each offset is [dlat, dlng] pairs forming a small polygon near anchor
    stub_zones = [
        {
            "offsets": [
                (0.001, 0.001), (0.001, 0.003),
                (0.003, 0.003), (0.003, 0.001),
                (0.001, 0.001),
            ],
            "class_id": 3,
        },
        {
            "offsets": [
                (-0.002, -0.001), (-0.002, 0.001),
                (-0.004, 0.001), (-0.004, -0.001),
                (-0.002, -0.001),
            ],
            "class_id": 2,
        },
        {
            "offsets": [
                (0.000, -0.003), (0.000, -0.001),
                (0.002, -0.001), (0.002, -0.003),
                (0.000, -0.003),
            ],
            "class_id": 1,
        },
    ]

    for zone in stub_zones:
        cls = DAMAGE_CLASSES[zone["class_id"]]
        coords = [
            [anchor_lng + dlng, anchor_lat + dlat]
            for dlat, dlng in zone["offsets"]
        ]
        features.append({
            "type": "Feature",
            "geometry": {
                "type": "Polygon",
                "coordinates": [coords],
            },
            "properties": {
                "severity": cls["name"],
                "color": cls["color"],
                "danger_weight": cls["danger_weight"],
                "confidence": 0.88,
            },
        })

    return {"type": "FeatureCollection", "features": features}


@router.post("/georef", response_model=GeoRefResponse)
async def georef(req: GeoRefRequest):
    """
    Convert pixel-space detection masks → geo-referenced GeoJSON danger zones.

    Phase 1: Returns mock GeoJSON near the anchor point.
    Phase 2: Real geometry pipeline (RDP, equirectangular, validation, union).
    """
    geojson = _make_stub_geojson(req.anchor.lat, req.anchor.lng)
    return GeoRefResponse(**geojson)
