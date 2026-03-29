# PathFinder — Backend Engineer Plan (v3)

## Your Role

You are the **spine** of the system. You build the FastAPI server that connects the AI model (YOLO26m-seg on the DGX Spark) to the frontend (Next.js + MapLibre GL JS). You own the geo-referencing pipeline, Valhalla routing integration, and the database layer (Supabase).

> [!WARNING]
> This plan supersedes the old v1/v2 plan. Key changes: **Valhalla replaces A\***, a new **`/georef` endpoint** bridges pixel-space masks to real-world coordinates, and stubs use **real xView2 label data** instead of fake mock polygons.

---

## What You're Building

```
User uploads satellite image (Frontend)
        ↓
  POST /detect  ← YOLO inference → pixel-space polygon masks
        ↓
  POST /georef  ← 4 geometry algorithms → GeoJSON danger zones (lat/lng)
        ↓
  Frontend renders colored polygons on MapLibre satellite map
        ↓
  User clicks Start + Destination on map
        ↓
  POST /route   ← Valhalla routing with exclude_polygons → safe route
        ↓
  Frontend draws route line avoiding red zones
        ↓
  User clicks "Save Mission"
        ↓
  POST /missions ← Supabase persistence
```

---

## Tech Stack

| Tool | What you'll use it for |
| :-- | :-- |
| **Python 3.11+** | Language |
| **FastAPI** | REST API framework (auto-generates docs at `/docs`) |
| **Pydantic v2** | Request/response validation + settings |
| **Uvicorn** | ASGI server to run FastAPI |
| **python-multipart** | Handle file uploads |
| **Shapely 2.0** | RDP polygon simplification, union, validation |
| **httpx** | Async HTTP client for Valhalla API calls |
| **Supabase Python SDK** | Database client |
| **Ultralytics** | Load and run YOLO model (when `best.pt` is ready) |

---

## Project Structure

```
backend/
├── app/
│   ├── __init__.py
│   ├── main.py              # FastAPI app, CORS, startup
│   ├── config.py            # Environment variables
│   ├── models.py            # All Pydantic schemas
│   ├── database.py          # Supabase client initialization
│   └── routes/
│       ├── __init__.py
│       ├── detect.py        # POST /detect  (YOLO inference)
│       ├── georef.py        # POST /georef  (pixel → GeoJSON)
│       ├── route.py         # POST /route   (Valhalla routing)
│       └── missions.py      # CRUD /missions
├── tests/
│   ├── test_health.py
│   ├── test_detect.py
│   ├── test_georef.py
│   └── test_route.py
├── requirements.txt
└── .env
```

---

## Valhalla Setup on DGX Spark (GX10)

Before you write any backend code, get the routing engine running on the DGX Spark:

```bash
# On the GX10 terminal:

# 1. Create data directory
mkdir -p ~/valhalla_data && cd ~/valhalla_data

# 2. Download Florida OSM data (~1 GB — covers Hurricane Michael / Panama City)
wget https://download.geofabrik.de/north-america/us/florida-latest.osm.pbf

# 3. Start Valhalla container
docker run -dt \
  --name valhalla \
  -p 8002:8002 \
  -v ~/valhalla_data:/custom_files \
  ghcr.io/gis-ops/docker-valhalla/valhalla:latest

# 4. Watch tile building progress (takes a few minutes)
docker logs -f valhalla
```

Once tiles are built → Valhalla is live at: `http://192.168.137.117:8002`

---

## Supabase Setup

### 1. SQL — Create `missions` Table

Run this in the Supabase SQL Editor:

```sql
-- Enable UUID generation
create extension if not exists "uuid-ossp";

-- Missions table
create table if not exists missions (
  id           uuid primary key default uuid_generate_v4(),
  name         text not null,
  created_at   timestamptz not null default now(),

  -- Detection results (pixel-space polygons from YOLO)
  detections   jsonb default '[]'::jsonb,

  -- Geo-referenced danger zones (GeoJSON FeatureCollection)
  danger_zones jsonb default null,

  -- Computed safe route (GeoJSON Feature + summary)
  route        jsonb default null,

  -- Start and end coordinates
  start_point  jsonb default null,   -- {"lat": ..., "lng": ...}
  end_point    jsonb default null    -- {"lat": ..., "lng": ...}
);

-- Index for listing missions by most recent
create index if not exists idx_missions_created_at
  on missions (created_at desc);

-- Row Level Security (open for hackathon — lock down later)
alter table missions enable row level security;

create policy "Allow all access"
  on missions
  for all
  using (true)
  with check (true);
```

### 2. `.env` File

```env
SUPABASE_URL=https://ugpdqpsecgrnykudicpi.supabase.co
SUPABASE_KEY=sb_publishable_G3hvgJMIK8gvcS5fXrItEA_dTxyUW8z
MODEL_PATH=../ai/weights/best.pt
VALHALLA_URL=http://192.168.137.117:8002
```

---

## The 4 Critical Geometry Algorithms

YOLO outputs **raster masks** (pixel grids). Valhalla expects **vector coordinates** (lat/lng polygons). These algorithms bridge the gap in `POST /georef`:

### A. Mask-to-Polygon Extraction (`detect.py`)

- Ultralytics `results[0].masks.xy` extracts polygon vertices directly
- Fallback: Suzuki's Algorithm via `cv2.findContours` for raw tensors

### B. Polygon Simplification — Ramer-Douglas-Peucker (`georef.py`)

- YOLO masks have thousands of jagged vertices → Valhalla will choke
- `poly.simplify(tolerance=2.0, preserve_topology=True)` reduces by ~90%

### C. Spatial Translation — Equirectangular Approximation (`georef.py`)

```python
dx_meters = (px_x - center_x) * scale
dy_meters = (center_y - px_y) * scale  # Y is flipped in image coords
lat = anchor_lat + (dy_meters / 111_320)
lng = anchor_lng + (dx_meters / (111_320 * cos(radians(anchor_lat))))
```

### D. Polygon Union — Cascaded Boolean Union (`georef.py`)

- Overlapping danger zones cause Valhalla graph-cutting errors
- `shapely.ops.unary_union(polygons)` dissolves overlaps into clean features

---

## Phase 1 — Scaffold + Real xView2 Stubs + Database (~45 min)

Since the YOLO model isn't ready yet, the `/detect` stub returns **real xView2 label data** (pre-extracted `lng_lat` polygons from the dataset's JSON labels) instead of fake mock polygons. This means the full pipeline works with actual disaster data from day one.

### Step 1: Create `requirements.txt`

```
fastapi>=0.115
uvicorn[standard]
ultralytics>=8.3
numpy
shapely>=2.0
python-multipart
pydantic>=2.0
pydantic-settings
httpx
supabase>=2.0
python-dotenv
```

Install with:

```bash
cd backend
pip install -r requirements.txt
```

### Step 2: Create `config.py`

```python
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env")

    supabase_url: str = ""
    supabase_key: str = ""
    model_path: str = "../ai/weights/best.pt"
    valhalla_url: str = "http://192.168.137.117:8002"
    max_upload_size_mb: int = 20


settings = Settings()
```

### Step 3: Create `models.py` — All Pydantic v2 Schemas

```python
from pydantic import BaseModel


# ── Shared ──────────────────────────────────────────────────

class LatLng(BaseModel):
    lat: float
    lng: float


DAMAGE_CLASSES = {
    0: {"name": "no-damage",    "color": "#22c55e", "danger_weight": 1},
    1: {"name": "minor-damage", "color": "#eab308", "danger_weight": 3},
    2: {"name": "major-damage", "color": "#f97316", "danger_weight": 6},
    3: {"name": "destroyed",    "color": "#ef4444", "danger_weight": 10},
}


# ── Detection ──────────────────────────────────────────────

class Detection(BaseModel):
    mask: list[list[float]]       # polygon vertices [[x,y], ...]
    class_name: str               # "destroyed", "minor-damage", etc.
    class_id: int                 # 0-3
    danger_weight: float          # 1, 3, 6, or 10
    confidence: float             # 0.0 - 1.0


class DetectionResponse(BaseModel):
    detections: list[Detection]
    image_size: dict              # {"width": 1024, "height": 1024}


# ── Geo-referencing ────────────────────────────────────────

class GeoRefRequest(BaseModel):
    detections: list[Detection]
    anchor: LatLng                # known lat/lng of image center
    scale: float                  # meters per pixel (GSD)
    image_center_px: list[float]  # [cx, cy] pixel coords of anchor


# GeoRefResponse is a raw GeoJSON FeatureCollection (dict)


# ── Routing ────────────────────────────────────────────────

class RouteRequest(BaseModel):
    start: LatLng
    end: LatLng
    danger_zones: dict | None = None   # GeoJSON FeatureCollection
    mode: str = "pedestrian"           # "pedestrian", "auto", "bicycle"


class RouteResponse(BaseModel):
    route: dict                        # GeoJSON Feature (LineString)
    summary: dict                      # distance_km, time_minutes, etc.
    maneuvers: list[dict]              # turn-by-turn instructions


# ── Missions ───────────────────────────────────────────────

class MissionCreate(BaseModel):
    name: str
    detections: list[Detection] | None = None
    danger_zones: dict | None = None
    route: dict | None = None
    start: LatLng | None = None
    end: LatLng | None = None


class Mission(MissionCreate):
    id: str
    created_at: str
```

### Step 4: Create `database.py`

```python
from supabase import create_client
from app.config import settings


def get_supabase():
    """Returns Supabase client, or None if not configured."""
    if not settings.supabase_url or not settings.supabase_key:
        return None
    return create_client(settings.supabase_url, settings.supabase_key)
```

### Step 5: Create `main.py`

```python
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from app.routes import detect, georef, route, missions

app = FastAPI(title="PathFinder API", version="3.0.0")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:3000"],
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(detect.router, prefix="/detect", tags=["Detection"])
app.include_router(georef.router, prefix="/georef", tags=["Geo-referencing"])
app.include_router(route.router,  prefix="/route",  tags=["Routing"])
app.include_router(missions.router, prefix="/missions", tags=["Missions"])


@app.get("/health")
async def health():
    return {"status": "ok"}
```

### Step 6: Stub `routes/detect.py` — Returns Real xView2 Labels

> [!NOTE]
> This stub reads real xView2 label JSONs. When `best.pt` is ready, you swap in YOLO inference — the rest of the pipeline stays identical.

```python
import json
import re
from pathlib import Path
from fastapi import APIRouter, UploadFile, File

router = APIRouter()

# ── xView2 label data for demo (until real model is ready) ──
XVIEW2_LABELS_DIR = Path("../data/train_images_labels_targets/train/labels")
DAMAGE_CLASSES = {
    "no-damage": (0, 1),
    "minor-damage": (1, 3),
    "major-damage": (2, 6),
    "destroyed": (3, 10),
}


def load_xview2_detections(disaster: str = "hurricane-michael"):
    """Load real xView2 label data for demo purposes."""
    detections = []
    labels = sorted(XVIEW2_LABELS_DIR.glob(f"{disaster}*_post_disaster.json"))

    if not labels:
        return [], {"width": 1024, "height": 1024}

    # Use the first available label file
    label_file = labels[0]
    with open(label_file) as f:
        data = json.load(f)

    meta = data.get("metadata", {})
    image_size = {
        "width": meta.get("width", 1024),
        "height": meta.get("height", 1024),
    }

    for feat in data.get("features", {}).get("xy", []):
        props = feat.get("properties", {})
        subtype = props.get("subtype", "")
        if subtype not in DAMAGE_CLASSES:
            continue

        wkt = feat.get("wkt", "")
        match = re.search(r"POLYGON\s*\(\((.+?)\)\)", wkt)
        if not match:
            continue

        coords = []
        for pair in match.group(1).split(","):
            parts = pair.strip().split()
            if len(parts) == 2:
                coords.append([float(parts[0]), float(parts[1])])

        if len(coords) < 3:
            continue

        cls_id, weight = DAMAGE_CLASSES[subtype]
        detections.append({
            "mask": coords,
            "class_name": subtype,
            "class_id": cls_id,
            "danger_weight": weight,
            "confidence": 0.85,
        })

    return detections, image_size


@router.post("/")
async def detect_damage(image: UploadFile = File(...)):
    """
    Stub: returns real xView2 damage detections.
    When best.pt is ready, swap this for YOLO inference.
    """
    detections, image_size = load_xview2_detections()
    return {"detections": detections, "image_size": image_size}
```

### Step 7: Stub `routes/georef.py` — Mock GeoJSON

```python
from fastapi import APIRouter
from app.models import GeoRefRequest

router = APIRouter()


@router.post("/")
async def georef(request: GeoRefRequest):
    """
    Stub: returns mock GeoJSON near the anchor point.
    Phase 2 implements real RDP + equirectangular + union.
    """
    lat, lng = request.anchor.lat, request.anchor.lng

    # Generate mock danger zones near the anchor
    features = []
    offsets = [
        (0.001, 0.001, "destroyed", 3, 10, "#ef4444"),
        (-0.002, 0.0015, "major-damage", 2, 6, "#f97316"),
        (0.0005, -0.002, "minor-damage", 1, 3, "#eab308"),
    ]

    for dlat, dlng, severity, cls_id, weight, color in offsets:
        c_lat, c_lng = lat + dlat, lng + dlng
        size = 0.0005
        features.append({
            "type": "Feature",
            "geometry": {
                "type": "Polygon",
                "coordinates": [[
                    [c_lng - size, c_lat - size],
                    [c_lng + size, c_lat - size],
                    [c_lng + size, c_lat + size],
                    [c_lng - size, c_lat + size],
                    [c_lng - size, c_lat - size],
                ]],
            },
            "properties": {
                "severity": severity,
                "class_id": cls_id,
                "danger_weight": weight,
                "color": color,
                "confidence": 0.85,
            },
        })

    return {"type": "FeatureCollection", "features": features}
```

### Step 8: Stub `routes/route.py` — Mock Route

```python
from fastapi import APIRouter
from app.models import RouteRequest, RouteResponse

router = APIRouter()


@router.post("/")
async def calculate_route(request: RouteRequest):
    """
    Stub: returns a straight-line route between start and end.
    Phase 3 implements real Valhalla routing with exclude_polygons.
    """
    route_feature = {
        "type": "Feature",
        "geometry": {
            "type": "LineString",
            "coordinates": [
                [request.start.lng, request.start.lat],
                [request.end.lng, request.end.lat],
            ],
        },
        "properties": {},
    }

    return RouteResponse(
        route=route_feature,
        summary={
            "distance_km": 2.4,
            "time_minutes": 12.3,
            "danger_zones_avoided": 0,
        },
        maneuvers=[
            {"instruction": "Head north (stub route)", "distance": 2.4}
        ],
    )
```

### Step 9: `routes/missions.py` — Supabase CRUD

```python
from fastapi import APIRouter, HTTPException
from app.models import MissionCreate
from app.database import get_supabase

router = APIRouter()


@router.post("/")
async def save_mission(mission: MissionCreate):
    sb = get_supabase()
    if sb is None:
        raise HTTPException(503, "Supabase not configured")

    data = mission.model_dump(mode="json")
    # Rename start/end to match DB columns
    data["start_point"] = data.pop("start", None)
    data["end_point"] = data.pop("end", None)

    result = sb.table("missions").insert(data).execute()
    return {"id": result.data[0]["id"], "message": "Mission saved"}


@router.get("/")
async def list_missions():
    sb = get_supabase()
    if sb is None:
        raise HTTPException(503, "Supabase not configured")

    result = (
        sb.table("missions")
        .select("id, name, created_at")
        .order("created_at", desc=True)
        .execute()
    )
    return result.data


@router.get("/{mission_id}")
async def get_mission(mission_id: str):
    sb = get_supabase()
    if sb is None:
        raise HTTPException(503, "Supabase not configured")

    result = (
        sb.table("missions")
        .select("*")
        .eq("id", mission_id)
        .single()
        .execute()
    )
    if not result.data:
        raise HTTPException(404, "Mission not found")
    return result.data
```

---

## Phase 2 — Real Geo-referencing Pipeline (~1 hr)

Implement the 4 geometry algorithms. This works independently of the YOLO model.

### Step 10: Real `routes/georef.py`

```python
from math import cos, radians
from fastapi import APIRouter
from shapely.geometry import Polygon, mapping
from shapely.validation import make_valid
from shapely.ops import unary_union
from app.models import GeoRefRequest, DAMAGE_CLASSES

router = APIRouter()


def pixel_to_latlng(px_x, px_y, center_x, center_y, anchor_lat, anchor_lng, scale):
    """Equirectangular approximation: pixel coords → lat/lng."""
    dx_meters = (px_x - center_x) * scale
    dy_meters = (center_y - px_y) * scale  # Y is flipped
    lat = anchor_lat + (dy_meters / 111_320)
    lng = anchor_lng + (dx_meters / (111_320 * cos(radians(anchor_lat))))
    return lat, lng


@router.post("/")
async def georef(request: GeoRefRequest):
    center_x, center_y = request.image_center_px
    anchor_lat, anchor_lng = request.anchor.lat, request.anchor.lng
    scale = request.scale

    # Group features by severity class for union
    class_features: dict[int, list] = {}

    for det in request.detections:
        # 1) Create Shapely polygon from pixel mask
        if len(det.mask) < 3:
            continue
        poly = Polygon(det.mask)

        # 2) RDP Simplification — reduce vertices by ~90%
        poly = poly.simplify(tolerance=2.0, preserve_topology=True)

        # 3) Validate — fix self-intersections
        if not poly.is_valid:
            poly = make_valid(poly)

        if poly.is_empty:
            continue

        # 4) Convert pixel coords → lat/lng
        geo_coords = []
        for x, y in poly.exterior.coords:
            lat, lng = pixel_to_latlng(
                x, y, center_x, center_y, anchor_lat, anchor_lng, scale
            )
            geo_coords.append([lng, lat])  # GeoJSON is [lng, lat]

        geo_poly = Polygon(geo_coords)
        if geo_poly.is_empty:
            continue

        cls_id = det.class_id
        if cls_id not in class_features:
            class_features[cls_id] = []
        class_features[cls_id].append(geo_poly)

    # 5) Cascaded union per severity class — merge overlapping polygons
    features = []
    for cls_id, polys in class_features.items():
        merged = unary_union(polys)
        cls_info = DAMAGE_CLASSES.get(cls_id, DAMAGE_CLASSES[0])

        # unary_union may return MultiPolygon
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
```

---

## Phase 3 — Valhalla Integration (~30 min)

Wire `/route` to the Valhalla instance on the DGX Spark.

### Step 11: Real `routes/route.py`

```python
import httpx
from fastapi import APIRouter, HTTPException
from app.config import settings
from app.models import RouteRequest, RouteResponse

router = APIRouter()


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


@router.post("/")
async def calculate_route(request: RouteRequest):
    # Extract polygon coords from GeoJSON danger_zones
    exclude_polygons = []
    if request.danger_zones and request.danger_zones.get("features"):
        for feature in request.danger_zones["features"]:
            coords = feature["geometry"]["coordinates"]
            exclude_polygons.append(coords)

    valhalla_body = {
        "locations": [
            {"lat": request.start.lat, "lon": request.start.lng},
            {"lat": request.end.lat, "lon": request.end.lng},
        ],
        "costing": request.mode,
        "directions_options": {"units": "km"},
    }
    if exclude_polygons:
        valhalla_body["exclude_polygons"] = exclude_polygons

    try:
        async with httpx.AsyncClient(timeout=30.0) as client:
            resp = await client.post(
                f"{settings.valhalla_url}/route",
                json=valhalla_body,
            )
            resp.raise_for_status()
            data = resp.json()
    except httpx.HTTPError as e:
        raise HTTPException(502, f"Valhalla routing failed: {e}")

    # Parse Valhalla response
    trip = data.get("trip", {})
    legs = trip.get("legs", [{}])
    leg = legs[0] if legs else {}

    # Decode polyline6 shape → GeoJSON LineString
    shape = leg.get("shape", "")
    coordinates = decode_polyline6(shape) if shape else [
        [request.start.lng, request.start.lat],
        [request.end.lng, request.end.lat],
    ]

    route_feature = {
        "type": "Feature",
        "geometry": {"type": "LineString", "coordinates": coordinates},
        "properties": {},
    }

    summary = trip.get("summary", {})
    maneuvers = [
        {
            "instruction": m.get("instruction", ""),
            "distance": m.get("length", 0),
        }
        for m in leg.get("maneuvers", [])
    ]

    return RouteResponse(
        route=route_feature,
        summary={
            "distance_km": summary.get("length", 0),
            "time_minutes": round(summary.get("time", 0) / 60, 1),
            "danger_zones_avoided": len(exclude_polygons),
        },
        maneuvers=maneuvers,
    )
```

---

## Phase 4 — Real YOLO Model (~30 min)

When `best.pt` is trained, swap stub detection for real inference.

### Step 12: Real `routes/detect.py`

```python
from fastapi import APIRouter, UploadFile, File
from app.config import settings
from app.models import Detection, DetectionResponse, DAMAGE_CLASSES
from ultralytics import YOLO
import numpy as np
import cv2

router = APIRouter()

# Load model once at startup
model = YOLO(settings.model_path)


@router.post("/")
async def detect_damage(image: UploadFile = File(...)):
    contents = await image.read()
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
```

---

## xView2 Dataset — Geographic Analysis

The demo uses **Hurricane Michael** (Panama City, FL) — the largest high-quality disaster in the xView2 dataset:

| Disaster | Type | Images | Lat | Lng | GSD (m/px) |
| :-- | :-- | --: | --: | --: | --: |
| `guatemala-volcano` | volcano | 18 | 14.3909 | -90.8154 | 1.41 |
| `hurricane-florence` | flooding | 319 | 33.6077 | -79.0566 | 2.90 |
| `hurricane-harvey` | flooding | 319 | 29.7693 | -95.4892 | 3.02 |
| `hurricane-matthew` | wind | 238 | 18.1965 | -73.7400 | 2.77 |
| **`hurricane-michael`** | **wind** | **343** | **30.1107** | **-85.6538** | **2.07** |
| `mexico-earthquake` | earthquake | 121 | 19.3239 | -99.2275 | 2.65 |
| `midwest-flooding` | flooding | 279 | 34.7168 | -92.3676 | 1.74 |
| `palu-tsunami` | tsunami | 113 | -0.7903 | 119.7995 | 2.82 |
| `santa-rosa-wildfire` | fire | 226 | 38.4926 | -122.7696 | 1.88 |
| `socal-fire` | fire | 823 | ~34.14 | ~-118.91 | 2.57 |

**GSD** = Ground Sample Distance = meters per pixel. This is the `scale` parameter for the `/georef` endpoint.

---

## Deliverables Checklist

```
- [ ] Valhalla running on DGX Spark (Docker + Florida OSM)
- [ ] Supabase missions table created
- [ ] backend/app/main.py           (FastAPI app + CORS)
- [ ] backend/app/config.py         (env vars + Valhalla URL)
- [ ] backend/app/models.py         (Pydantic v2 schemas)
- [ ] backend/app/database.py       (Supabase client)
- [ ] backend/app/routes/detect.py  (POST /detect — xView2 stubs → YOLO)
- [ ] backend/app/routes/georef.py  (POST /georef — 4 geometry algorithms)
- [ ] backend/app/routes/route.py   (POST /route — Valhalla integration)
- [ ] backend/app/routes/missions.py (Supabase CRUD)
- [ ] backend/requirements.txt
- [ ] backend/.env
- [ ] backend/tests/
```

---

## What You Need From Your Teammates

| From | What | When |
| :-- | :-- | :-- |
| AI Lead | `ai/weights/best.pt` (trained YOLO26m-seg model) | When training finishes on GX10 |
| Person B | Frontend running at `localhost:3000` for CORS | Phase 1 |
| Person B | Confirmation they can consume the detection + GeoJSON + route schemas | Phase 1 |

---

## Quick Reference: How to Run

```bash
cd d:\School_Project\Yhacks\backend

# First time setup
pip install -r requirements.txt

# Run the server
uvicorn app.main:app --reload --port 8000

# View API docs
# Open http://localhost:8000/docs in browser

# Run tests
pytest tests/ -v
```
