"""
PathFinder — POST /route

Phase 1 (stub): Returns a mock route as a GeoJSON LineString connecting
start → end with an intermediate waypoint, plus fake summary data.

Phase 3 (real): Proxies to Valhalla on the DGX Spark, includes polyline6
decoding and exclude_polygons support.
"""

from __future__ import annotations

from fastapi import APIRouter

from app.models import RouteRequest, RouteResponse

router = APIRouter()


@router.post("/route", response_model=RouteResponse)
async def route(req: RouteRequest):
    """
    Calculate a safe route that avoids danger zones.

    Phase 1: Returns a straight-line mock route.
    Phase 3: Calls Valhalla with exclude_polygons.
    """
    # Build a mock route — straight line from start to end with a midpoint
    mid_lat = (req.start.lat + req.end.lat) / 2
    mid_lng = (req.start.lng + req.end.lng) / 2

    # Slight offset to simulate route deviation around a danger zone
    mid_lat += 0.002
    mid_lng += 0.001

    route_feature = {
        "type": "Feature",
        "geometry": {
            "type": "LineString",
            "coordinates": [
                [req.start.lng, req.start.lat],
                [mid_lng, mid_lat],
                [req.end.lng, req.end.lat],
            ],
        },
        "properties": {
            "mode": req.mode,
        },
    }

    # Approximate distance (very rough — for stub only)
    import math

    dlat = req.end.lat - req.start.lat
    dlng = req.end.lng - req.start.lng
    dist_deg = math.sqrt(dlat**2 + dlng**2)
    dist_km = dist_deg * 111.32  # rough conversion

    # Estimate time based on mode
    speed_kmh = {"pedestrian": 5, "bicycle": 15, "auto": 50}.get(req.mode, 5)
    time_minutes = (dist_km / speed_kmh) * 60

    summary = {
        "distance_km": round(dist_km, 2),
        "time_minutes": round(time_minutes, 1),
        "mode": req.mode,
        "danger_zones_avoided": 0 if not req.danger_zones else len(
            req.danger_zones.get("features", [])
        ),
    }

    maneuvers = [
        {
            "instruction": f"Start heading toward destination",
            "distance_km": round(dist_km / 2, 2),
            "type": "start",
        },
        {
            "instruction": f"Arrive at destination",
            "distance_km": round(dist_km / 2, 2),
            "type": "arrive",
        },
    ]

    return RouteResponse(
        route=route_feature,
        summary=summary,
        maneuvers=maneuvers,
    )
