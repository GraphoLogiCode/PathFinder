# PathFinder

PathFinder is a satellite-based disaster navigation system. It analyzes satellite imagery to detect building damage across a disaster-affected area, converts those detections into geo-referenced danger zones, and calculates pedestrian or vehicle routes that avoid those zones using a road network routing engine.

The backend is a Python API built with FastAPI. A Next.js frontend is planned but not yet implemented. The AI component uses a YOLO segmentation model trained on the xView2 dataset to identify damaged buildings in satellite images.

---

## Features

- Upload a satellite image and receive pixel-space damage polygon masks classified by severity (no damage, minor damage, major damage, destroyed)
- Convert pixel-space masks to geo-referenced GeoJSON danger zones using an equirectangular projection with configurable ground sample distance
- Calculate safe routes around danger zones via a Valhalla routing engine, supporting pedestrian, bicycle, and auto modes
- Save and retrieve named missions (detection results, danger zones, and computed routes) via a Supabase database or an in-memory fallback
- CORS-enabled API ready to serve a Next.js frontend

---

## Requirements

- Python 3.11 or later
- A running [Valhalla](https://github.com/valhalla/valhalla) instance (optional for routing)
- A [Supabase](https://supabase.com) project (optional for mission persistence)

---

## Installation

1. Clone the repository:

   ```
   git clone https://github.com/GraphoLogiCode/PathFinder.git
   cd PathFinder
   ```

2. Create and activate a virtual environment:

   ```
   python -m venv .venv
   source .venv/bin/activate      # Linux / macOS
   .venv\Scripts\activate         # Windows
   ```

3. Install backend dependencies:

   ```
   cd backend
   pip install -r requirements.txt
   ```

---

## Configuration

The backend reads configuration from a `.env` file placed in the `backend/` directory. Create the file by copying the template below and filling in your values:

```
SUPABASE_URL=https://YOUR_PROJECT_ID.supabase.co
SUPABASE_KEY=YOUR_SUPABASE_ANON_OR_SERVICE_ROLE_KEY
MODEL_PATH=../ai/weights/best.pt
VALHALLA_URL=http://localhost:8002
MAX_UPLOAD_SIZE_MB=20
```

All settings are optional. If `SUPABASE_URL` or `SUPABASE_KEY` are left empty, the backend falls back to an in-memory store. If `MODEL_PATH` does not point to a valid YOLO weights file, the detection endpoint returns pre-baked stub data instead of running live inference.

---

## Usage

Start the development server from the `backend/` directory:

```
uvicorn app.main:app --reload --host 0.0.0.0 --port 8000
```

The interactive API documentation is available at `http://localhost:8000/docs`.

### API endpoints

| Method | Path | Description |
|--------|------|-------------|
| GET | /health | Health check |
| POST | /detect | Upload a satellite image, receive damage polygon masks |
| POST | /georef | Convert pixel masks to a GeoJSON FeatureCollection of danger zones |
| POST | /route | Calculate a safe route between two coordinates |
| POST | /missions/ | Create and persist a mission |
| GET | /missions/ | List all saved missions |
| GET | /missions/{id} | Retrieve a mission by ID |

### Example: detect damage in an image

```
curl -X POST http://localhost:8000/detect \
  -F "file=@satellite_image.png"
```

### Example: calculate a route

```
curl -X POST http://localhost:8000/route \
  -H "Content-Type: application/json" \
  -d '{
    "start": {"lat": 30.11, "lng": -85.65},
    "end":   {"lat": 30.13, "lng": -85.63},
    "mode":  "pedestrian"
  }'
```

---

## Project Structure

```
PathFinder/
├── ai/
│   ├── pathfinding/        # Reserved for future custom pathfinding logic
│   ├── scripts/            # Data processing scripts (planned)
│   ├── training/           # Model training code (planned)
│   └── weights/            # Trained YOLO model weights (.pt files, not committed)
├── backend/
│   ├── app/
│   │   ├── main.py         # FastAPI application entry point
│   │   ├── config.py       # Settings loaded from environment variables
│   │   ├── database.py     # Supabase client factory
│   │   ├── models.py       # Pydantic v2 request and response schemas
│   │   └── routes/
│   │       ├── detect.py   # POST /detect
│   │       ├── georef.py   # POST /georef
│   │       ├── route.py    # POST /route
│   │       └── missions.py # CRUD /missions
│   ├── tests/              # Pytest test suite
│   └── requirements.txt    # Python dependencies
├── docs/                   # Architecture and implementation plans
└── frontend/               # Next.js frontend (scaffolding only, not yet implemented)
```

---

## Development Notes

- The project uses phased development. Phase 1 endpoints return pre-baked stub data derived from the xView2 dataset (actual building footprint polygons with damage class labels assigned for demonstration purposes) so the full pipeline can be exercised before the YOLO model is trained. The `/detect` endpoint always returns stub data until a trained weights file is present at `MODEL_PATH`.
- Place your trained YOLO weights file at `ai/weights/best.pt` (or update `MODEL_PATH` in `.env`) to enable live inference in the detection endpoint.
- The Valhalla routing engine must be running and reachable at `VALHALLA_URL` for the `/route` endpoint to return real road-network routes.
- Damage classes and their danger weights are defined in `backend/app/models.py` under `DAMAGE_CLASSES`.

---

## Testing

Tests are located in `backend/tests/` and use [pytest](https://pytest.org) with the FastAPI test client.

Run the tests from the `backend/` directory:

```
pip install pytest
pytest tests/
```

To see verbose output:

```
pytest tests/ -v
```

The test suite covers the health check, the detection endpoint, geo-referencing, and routing.

---

## Contributing

1. Fork the repository and create a feature branch from `main`.
2. Install dependencies and confirm the test suite passes before making changes.
3. Keep commits focused and write clear commit messages.
4. Open a pull request describing what you changed and why.

---

## License

No license file has been added to this repository yet. Until a license is chosen and published, the source code is not available for use, modification, or distribution by third parties. If you are interested in contributing or using this project, contact the repository owner to request a license.
