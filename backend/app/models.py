"""
PathFinder — Pydantic v2 Schemas

Shared contracts between backend and frontend, matching the v3 architecture.
"""

from __future__ import annotations

from pydantic import BaseModel, Field


# ---------------------------------------------------------------------------
# Damage classification constants
# ---------------------------------------------------------------------------

DAMAGE_CLASSES: dict[int, dict] = {
    0: {"name": "no-damage",    "color": "#22c55e", "danger_weight": 1},
    1: {"name": "minor-damage", "color": "#eab308", "danger_weight": 3},
    2: {"name": "major-damage", "color": "#f97316", "danger_weight": 6},
    3: {"name": "destroyed",    "color": "#ef4444", "danger_weight": 10},
}


# ---------------------------------------------------------------------------
# Core schemas
# ---------------------------------------------------------------------------

class LatLng(BaseModel):
    lat: float
    lng: float


class Detection(BaseModel):
    """A single detected damage polygon in pixel-space."""
    mask: list[list[float]]
    class_name: str
    class_id: int
    danger_weight: float
    confidence: float


class DetectionResponse(BaseModel):
    """Response from POST /detect."""
    detections: list[Detection]
    image_size: dict


# ---------------------------------------------------------------------------
# Geo-referencing
# ---------------------------------------------------------------------------

class GeoRefRequest(BaseModel):
    """Request body for POST /georef."""
    detections: list[Detection]
    anchor: LatLng
    scale: float = Field(description="Ground Sample Distance in meters/pixel")
    image_center_px: list[float] = Field(
        description="[x, y] pixel coordinates of the image center"
    )


class GeoRefResponse(BaseModel):
    """GeoJSON FeatureCollection of geo-referenced danger zones."""
    type: str = "FeatureCollection"
    features: list[dict]


# ---------------------------------------------------------------------------
# Routing
# ---------------------------------------------------------------------------

class RouteRequest(BaseModel):
    """Request body for POST /route."""
    start: LatLng
    end: LatLng
    danger_zones: dict | None = None
    mode: str = "pedestrian"


class RouteResponse(BaseModel):
    """Response from POST /route."""
    route: dict  # GeoJSON Feature (LineString)
    summary: dict
    maneuvers: list[dict]


# ---------------------------------------------------------------------------
# Missions (persistence)
# ---------------------------------------------------------------------------

class MissionCreate(BaseModel):
    """Payload for creating a new mission."""
    name: str
    detections: list[Detection] | None = None
    danger_zones: dict | None = None
    route: dict | None = None
    start: LatLng | None = None
    end: LatLng | None = None


class Mission(MissionCreate):
    """A persisted mission, with server-generated fields."""
    id: str
    created_at: str


# ---------------------------------------------------------------------------
# AI Analysis (GPT-5.4-mini rescue plan)
# ---------------------------------------------------------------------------

class AnalyzeRequest(BaseModel):
    """Request body for POST /analyze."""
    danger_zones: dict | None = None
    route_summary: dict | None = None
    maneuvers: list[dict] | None = None
    route_geometry: dict | None = None
    start: LatLng | None = None
    end: LatLng | None = None
    disaster_type: str | None = None
    disaster_location: str | None = None
    transport_mode: str | None = "pedestrian"


class AnalyzeResponse(BaseModel):
    """Response from POST /analyze."""
    plan: dict
    model: str = "gpt-4o-mini"
    tokens_used: int = 0

