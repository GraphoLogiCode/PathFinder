# SafeRoute — Person A: Backend Engineer Plan

## Your Role

You are the **spine** of the system. You build the FastAPI server that connects the AI models (provided by the AI Lead) to the frontend (built by Person B). You also own the database layer (Supabase) and are responsible for making sure data flows reliably between all three parts of the system.

---

## What You're Building

```
User uploads image (Frontend)
        ↓
  POST /detect  ← YOU build this endpoint
        ↓
  Call YOLO model (AI Lead's code) → get detections
        ↓
  Return JSON to frontend
        ↓
  User clicks Start + Goal
        ↓
  POST /route  ← YOU build this endpoint
        ↓
  Call A* pathfinder (AI Lead's code) → get safe path
        ↓
  Return JSON to frontend
        ↓
  User clicks "Save Mission"
        ↓
  POST /missions  ← YOU build this endpoint
        ↓
  Store in Supabase
```

---

## Tech Stack

| Tool | What you'll use it for |
|---|---|
| **Python 3.11+** | Language |
| **FastAPI** | REST API framework (auto-generates docs at `/docs`) |
| **Pydantic v2** | Request/response validation |
| **Uvicorn** | ASGI server to run FastAPI |
| **python-multipart** | Handle file uploads |
| **Supabase Python SDK** | Database client (PostgreSQL + PostGIS) |
| **Ultralytics** | Load and run the YOLO model (AI Lead provides weights) |

---

## Project Structure

```
backend/
├── app/
│   ├── __init__.py
│   ├── main.py              # FastAPI app, CORS, startup
│   ├── config.py             # Environment variables (Supabase URL, keys)
│   ├── models.py             # All Pydantic schemas
│   ├── database.py           # Supabase client initialization
│   └── routes/
│       ├── __init__.py
│       ├── detect.py          # POST /detect
│       ├── route.py           # POST /route
│       └── missions.py        # CRUD /missions
├── tests/
│   ├── test_detect.py
│   ├── test_route.py
│   └── test_missions.py
└── requirements.txt
```

---

## Phase 1 — Scaffold & Stubs (Day 1, First Half)

### Step 1: Initialize the project

```bash
cd d:\School_Project\Yhacks
mkdir backend\app\routes backend\tests
```

### Step 2: Create `requirements.txt`

```
fastapi>=0.115
uvicorn[standard]
ultralytics>=8.3
numpy
shapely
python-multipart
pydantic>=2.0
supabase>=2.0
python-dotenv
```

Install with:
```bash
cd backend
pip install -r requirements.txt
```

### Step 3: Create `config.py`

```python
from pydantic_settings import BaseSettings

class Settings(BaseSettings):
    supabase_url: str = ""
    supabase_key: str = ""
    model_path: str = "../ai/weights/best.pt"
    max_upload_size_mb: int = 20

    class Config:
        env_file = ".env"

settings = Settings()
```

### Step 4: Create `main.py` — FastAPI app with CORS

```python
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from app.routes import detect, route, missions

app = FastAPI(title="SafeRoute API", version="1.0.0")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:3000"],  # Frontend dev server
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(detect.router, prefix="/detect", tags=["Detection"])
app.include_router(route.router, prefix="/route", tags=["Routing"])
app.include_router(missions.router, prefix="/missions", tags=["Missions"])

@app.get("/health")
async def health():
    return {"status": "ok"}
```

Run with:
```bash
uvicorn app.main:app --reload --port 8000
```

API docs automatically available at `http://localhost:8000/docs`

### Step 5: Create stub endpoints (return mock data while AI Lead trains the model)

**`routes/detect.py`** — Stub version:
```python
from fastapi import APIRouter, UploadFile, File

router = APIRouter()

@router.post("/")
async def detect_damage(image: UploadFile = File(...)):
    # STUB: return fake detections until real model is ready
    return {
        "detections": [
            {
                "mask": [[100, 200], [150, 200], [150, 250], [100, 250]],
                "class": "destroyed",
                "class_id": 3,
                "danger_weight": 10,
                "confidence": 0.92
            },
            {
                "mask": [[400, 300], [450, 310], [440, 360], [390, 350]],
                "class": "minor-damage",
                "class_id": 1,
                "danger_weight": 3,
                "confidence": 0.78
            }
        ],
        "image_size": [1024, 1024]
    }
```

> [!IMPORTANT]
> The detection response now includes `mask` (polygon vertices) instead of `bbox` (bounding box), because the AI Lead is using **Instance Segmentation** (YOLO11s-seg). The mask is a list of `[x, y]` pixel coordinate pairs forming the building footprint.

---

## Phase 2 — Wire Real Model + Pathfinding (Day 1, Second Half)

### Step 6: Wire `/detect` to real YOLO model

Once the AI Lead delivers `best.pt`:

```python
from ultralytics import YOLO
from fastapi import APIRouter, UploadFile, File
from app.config import settings
import numpy as np
from PIL import Image
import io

router = APIRouter()

# Load model once at startup
model = YOLO(settings.model_path)

DAMAGE_CLASSES = {0: "no-damage", 1: "minor-damage", 2: "major-damage", 3: "destroyed"}
DANGER_WEIGHTS = {0: 1, 1: 3, 2: 6, 3: 10}

@router.post("/")
async def detect_damage(image: UploadFile = File(...)):
    # Read uploaded image
    contents = await image.read()
    img = Image.open(io.BytesIO(contents))
    
    # Run inference
    results = model.predict(img, conf=0.3, verbose=False)
    
    detections = []
    if results[0].masks is not None:
        for mask, box in zip(results[0].masks.xy, results[0].boxes):
            cls_id = int(box.cls[0])
            detections.append({
                "mask": mask.tolist(),        # [[x1,y1], [x2,y2], ...]
                "class": DAMAGE_CLASSES.get(cls_id, "unknown"),
                "class_id": cls_id,
                "danger_weight": DANGER_WEIGHTS.get(cls_id, 1),
                "confidence": float(box.conf[0])
            })
    
    return {
        "detections": detections,
        "image_size": [img.width, img.height]
    }
```

### Step 7: Wire `/route` to A* pathfinder

```python
from fastapi import APIRouter
from app.models import RouteRequest
# Import AI Lead's pathfinding module
import sys
sys.path.insert(0, "../ai")
from pathfinding.astar import find_safe_route

router = APIRouter()

@router.post("/")
async def calculate_route(request: RouteRequest):
    result = find_safe_route(
        detections=request.detections,
        start_px=request.start,
        end_px=request.end,
        grid_size=128,
        img_size=request.image_size[0]
    )
    return result
```

### Step 8: Define all Pydantic schemas in `models.py`

```python
from pydantic import BaseModel

class Detection(BaseModel):
    mask: list[list[float]]     # polygon vertices [[x,y], ...]
    class_name: str             # "destroyed", "minor-damage", etc.
    class_id: int               # 0-3
    danger_weight: int          # 1, 3, 6, or 10
    confidence: float           # 0.0 - 1.0

class DetectionResponse(BaseModel):
    detections: list[Detection]
    image_size: list[int]       # [width, height]

class RouteRequest(BaseModel):
    start: list[float]          # [x, y] pixel coordinates
    end: list[float]            # [x, y] pixel coordinates
    detections: list[Detection]
    image_size: list[int]

class RouteResponse(BaseModel):
    path: list[list[float]]     # [[x1,y1], [x2,y2], ...]
    total_cost: float
    danger_avoided: int

class MissionCreate(BaseModel):
    name: str
    image_url: str | None = None
    detections: list[Detection]
    path: list[list[float]]
    start_point: list[float]
    end_point: list[float]

class Mission(BaseModel):
    id: str
    name: str
    created_at: str
    image_url: str | None
    detections: list[Detection]
    path: list[list[float]]
    start_point: list[float]
    end_point: list[float]
```

---

## Phase 3 — Database & Persistence (Day 2)

### Step 9: Set up Supabase

1. Go to [supabase.com](https://supabase.com) → create a new project
2. Run this SQL in the SQL editor:

```sql
CREATE EXTENSION IF NOT EXISTS postgis;

CREATE TABLE missions (
    id UUID DEFAULT gen_random_uuid() PRIMARY KEY,
    name TEXT NOT NULL,
    created_at TIMESTAMPTZ DEFAULT now(),
    image_url TEXT,
    detections JSONB NOT NULL,
    path JSONB NOT NULL,
    start_point JSONB NOT NULL,
    end_point JSONB NOT NULL,
    metadata JSONB DEFAULT '{}'
);
```

3. Copy the **Project URL** and **anon key** into `backend/.env`:
```
SUPABASE_URL=https://xxx.supabase.co
SUPABASE_KEY=eyJ...
```

### Step 10: Create `database.py`

```python
from supabase import create_client
from app.config import settings

supabase = create_client(settings.supabase_url, settings.supabase_key)
```

### Step 11: Build `/missions` CRUD endpoints

**`routes/missions.py`**:

```python
from fastapi import APIRouter, HTTPException
from app.models import MissionCreate, Mission
from app.database import supabase

router = APIRouter()

@router.post("/", response_model=dict)
async def save_mission(mission: MissionCreate):
    data = mission.model_dump()
    result = supabase.table("missions").insert(data).execute()
    return {"id": result.data[0]["id"], "message": "Mission saved"}

@router.get("/", response_model=list[dict])
async def list_missions():
    result = supabase.table("missions") \
        .select("id, name, created_at") \
        .order("created_at", desc=True) \
        .execute()
    return result.data

@router.get("/{mission_id}", response_model=dict)
async def get_mission(mission_id: str):
    result = supabase.table("missions") \
        .select("*") \
        .eq("id", mission_id) \
        .single() \
        .execute()
    if not result.data:
        raise HTTPException(status_code=404, detail="Mission not found")
    return result.data
```

---

## Phase 4 — Error Handling & Polish (Day 2)

### Step 12: Add input validation

- Reject uploads > 20MB
- Validate image format (PNG, JPEG, TIFF only)
- Validate start/end coordinates are within image bounds
- Return clear error messages with proper HTTP status codes

### Step 13: Write tests

```python
# tests/test_detect.py
from fastapi.testclient import TestClient
from app.main import app

client = TestClient(app)

def test_health():
    response = client.get("/health")
    assert response.status_code == 200

def test_detect_no_file():
    response = client.post("/detect/")
    assert response.status_code == 422  # Missing required file
```

---

## Your Deliverables Checklist

```
- [ ] backend/app/main.py           (FastAPI app + CORS)
- [ ] backend/app/config.py         (env vars)
- [ ] backend/app/models.py         (Pydantic schemas)
- [ ] backend/app/database.py       (Supabase client)
- [ ] backend/app/routes/detect.py  (POST /detect)
- [ ] backend/app/routes/route.py   (POST /route)
- [ ] backend/app/routes/missions.py (CRUD endpoints)
- [ ] backend/requirements.txt
- [ ] backend/.env                  (Supabase credentials)
- [ ] Supabase project + missions table
- [ ] backend/tests/                (basic endpoint tests)
```

---

## What You Need From Your Teammates

| From | What | When |
|---|---|---|
| AI Lead | `ai/weights/best.pt` (trained YOLO11s-seg model) | Day 1 end |
| AI Lead | `ai/pathfinding/astar.py` with `find_safe_route()` function | Day 1, second half |
| Person B | The frontend URL/port for CORS config | Day 1, first half |
| Person B | Confirmation of the detection + route JSON schema | Day 1, first half |

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
