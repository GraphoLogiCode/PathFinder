"""
PathFinder — POST /route

Real Valhalla routing using the public FOSSGIS demo server.
Decodes polyline6 encoded shapes and supports exclude_polygons.
"""

from __future__ import annotations

import httpx
from fastapi import APIRouter, HTTPException

from app.config import settings
from app.models import RouteRequest, RouteResponse

router = APIRouter()

# Use public Valhalla demo if local isn't available
VALHALLA_URL = settings.valhalla_url or "https://valhalla1.openstreetmap.de"


def decode_polyline6(encoded: str) -> list[list[float]]:
    """Decode Valhalla's polyline6 encoded string → [[lng, lat], ...]."""
    coords = []
    i, lat, lng = 0, 0, 0
    while i < len(encoded):
        for is_lng in (False, True):
            shift, result = 0, 0
            while True:
                b = ord(encoded[i]) - 63
                i += 1
                result |= (b & 0x1F) << shift
                shift += 5
                if b < 0x20:
                    break
            delta = ~(result >> 1) if (result & 1) else (result >> 1)
            if is_lng:
                lng += delta
            else:
                lat += delta
        coords.append([lng / 1e6, lat / 1e6])
    return coords


@router.post("/route", response_model=RouteResponse)
async def route(req: RouteRequest):
    """
    Calculate a safe route that avoids danger zones.
    Uses Valhalla routing engine (public demo or local instance).
    """
    # Extract polygon coords from GeoJSON danger_zones
    # Valhalla expects exclude_polygons as [[{lat, lon}, ...], ...]
    exclude_polygons = []
    if req.danger_zones and req.danger_zones.get("features"):
        for feature in req.danger_zones["features"]:
            geom = feature.get("geometry", {})
            geom_type = geom.get("type", "")
            coords = geom.get("coordinates", [])

            rings = []
            if geom_type == "Polygon" and coords:
                # GeoJSON Polygon: [[[lng, lat], ...]]  → take outer ring
                rings = [coords[0]]
            elif geom_type == "MultiPolygon" and coords:
                # GeoJSON MultiPolygon: [[[[lng, lat], ...]], ...]
                rings = [poly[0] for poly in coords if poly]

            for ring in rings:
                # Convert [lng, lat] → {"lat": lat, "lon": lng} for Valhalla
                valhalla_ring = [{"lat": pt[1], "lon": pt[0]} for pt in ring]
                if len(valhalla_ring) >= 3:
                    exclude_polygons.append(valhalla_ring)

    valhalla_body = {
        "locations": [
            {"lat": req.start.lat, "lon": req.start.lng},
            {"lat": req.end.lat, "lon": req.end.lng},
        ],
        "costing": req.mode,
        "directions_options": {"units": "km"},
    }
    if exclude_polygons:
        valhalla_body["exclude_polygons"] = exclude_polygons

    # Try local Valhalla first, fall back to public demo
    urls_to_try = [settings.valhalla_url, "https://valhalla1.openstreetmap.de"]

    data = None
    last_error = None

    for base_url in urls_to_try:
        if not base_url:
            continue
        try:
            async with httpx.AsyncClient(timeout=30.0) as client:
                resp = await client.post(
                    f"{base_url}/route",
                    json=valhalla_body,
                )
                resp.raise_for_status()
                data = resp.json()
                break  # Success
        except Exception as e:
            last_error = e
            continue

    # If routing with exclude_polygons failed, retry without them
    if data is None and exclude_polygons:
        valhalla_body.pop("exclude_polygons", None)
        for base_url in urls_to_try:
            if not base_url:
                continue
            try:
                async with httpx.AsyncClient(timeout=30.0) as client:
                    resp = await client.post(f"{base_url}/route", json=valhalla_body)
                    resp.raise_for_status()
                    data = resp.json()
                    break
            except Exception as e:
                last_error = e
                continue

    if data is None:
        raise HTTPException(502, f"Valhalla routing failed: {last_error}")

    # Parse Valhalla response
    trip = data.get("trip", {})
    legs = trip.get("legs", [{}])
    leg = legs[0] if legs else {}

    # Decode polyline6 shape → GeoJSON LineString
    shape = leg.get("shape", "")
    coordinates = decode_polyline6(shape) if shape else [
        [req.start.lng, req.start.lat],
        [req.end.lng, req.end.lat],
    ]

    route_feature = {
        "type": "Feature",
        "geometry": {"type": "LineString", "coordinates": coordinates},
        "properties": {"mode": req.mode},
    }

    summary = trip.get("summary", {})
    maneuvers = [
        {
            "instruction": m.get("instruction", ""),
            "distance": m.get("length", 0),
            "street_name": ", ".join(m.get("street_names", [])),
            "type": m.get("type", 0),
        }
        for m in leg.get("maneuvers", [])
    ]

    return RouteResponse(
        route=route_feature,
        summary={
            "distance_km": round(summary.get("length", 0), 2),
            "time_minutes": round(summary.get("time", 0) / 60, 1),
            "danger_zones_avoided": len(exclude_polygons),
            "mode": req.mode,
        },
        maneuvers=maneuvers,
    )
