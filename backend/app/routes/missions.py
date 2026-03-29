"""
PathFinder — /missions CRUD

Phase 1 (stub): In-memory list storage for testing.
Phase 4 (real): Supabase `missions` table with JSON columns.
"""

from __future__ import annotations

import uuid
from datetime import datetime, timezone

from fastapi import APIRouter, HTTPException

from app.models import MissionCreate, Mission
from app.database import get_supabase

router = APIRouter()

# ---------------------------------------------------------------------------
# In-memory store (Phase 1 fallback)
# ---------------------------------------------------------------------------
_memory_store: list[dict] = []


def _use_supabase() -> bool:
    """Check if Supabase is available."""
    client = get_supabase()
    return client is not None


# ---------------------------------------------------------------------------
# Endpoints
# ---------------------------------------------------------------------------

@router.post("/missions/", response_model=Mission, status_code=201)
async def create_mission(payload: MissionCreate):
    """Save a new mission (detections, danger zones, route)."""
    client = get_supabase()

    mission_id = str(uuid.uuid4())
    now = datetime.now(timezone.utc).isoformat()

    mission_data = {
        "id": mission_id,
        "name": payload.name,
        "created_at": now,
        "detections": [d.model_dump() for d in payload.detections] if payload.detections else [],
        "danger_zones": payload.danger_zones,
        "route": payload.route,
        "start_point": payload.start.model_dump() if payload.start else None,
        "end_point": payload.end.model_dump() if payload.end else None,
    }

    if client is not None:
        try:
            client.table("missions").insert(mission_data).execute()
        except Exception as e:
            raise HTTPException(status_code=503, detail=f"Supabase error: {e}")
    else:
        _memory_store.append(mission_data)

    return Mission(
        id=mission_id,
        created_at=now,
        name=payload.name,
        detections=payload.detections,
        danger_zones=payload.danger_zones,
        route=payload.route,
        start=payload.start,
        end=payload.end,
    )


@router.get("/missions/", response_model=list[dict])
async def list_missions():
    """List all missions (id, name, created_at)."""
    client = get_supabase()

    if client is not None:
        try:
            result = (
                client.table("missions")
                .select("id, name, created_at")
                .order("created_at", desc=True)
                .execute()
            )
            return result.data
        except Exception as e:
            raise HTTPException(status_code=503, detail=f"Supabase error: {e}")
    else:
        return [
            {"id": m["id"], "name": m["name"], "created_at": m["created_at"]}
            for m in sorted(_memory_store, key=lambda x: x["created_at"], reverse=True)
        ]


@router.get("/missions/{mission_id}", response_model=dict)
async def get_mission(mission_id: str):
    """Get full mission data by ID."""
    client = get_supabase()

    if client is not None:
        try:
            result = (
                client.table("missions")
                .select("*")
                .eq("id", mission_id)
                .single()
                .execute()
            )
            return result.data
        except Exception as e:
            raise HTTPException(status_code=503, detail=f"Supabase error: {e}")
    else:
        for m in _memory_store:
            if m["id"] == mission_id:
                return m
        raise HTTPException(status_code=404, detail="Mission not found")
