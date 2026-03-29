# 🛰️ PathFinder

**AI-powered disaster response navigation.** Upload satellite imagery → detect building damage → generate safe evacuation routes.

PathFinder analyzes post-disaster satellite images using a custom-trained YOLO segmentation model, converts damage detections into geo-referenced danger zones, and computes safe pedestrian/vehicle routes that avoid destroyed areas.

Built for [YHacks 2026](https://yhacks.org) by **GraphoLogiCode**.

---

## How It Works

```
Satellite Image → YOLO Detection → Geo-Referencing → Safe Routing → Rescue Plan
```

1. **Upload** a satellite image or select a map region
2. **AI Detection** — YOLO26m-seg identifies damaged buildings (no-damage, minor, major, destroyed)
3. **Geo-Reference** — pixel masks → lat/lng GeoJSON danger zones
4. **Safe Routing** — Valhalla calculates routes avoiding danger zones
5. **Rescue Plan** — GPT-4o generates severity-specific rescue recommendations

---

## Quick Start

```bash
# Clone
git clone https://github.com/GraphoLogiCode/PathFinder.git
cd PathFinder

# Backend (Python/FastAPI)
cd backend
pip install -r requirements.txt
cp .env.example .env  # fill in your keys
uvicorn app.main:app --host 0.0.0.0 --port 8000 --reload

# Frontend (Next.js) — in a new terminal
cd frontend
npm install
npm run dev
```

Open `http://localhost:3000` in your browser.

---

## Tech Stack

| Layer | Technology |
|-------|-----------|
| **AI Model** | YOLO26m-seg trained on xBD dataset (10 disaster types, 4 damage classes) |
| **Backend** | Python, FastAPI, Shapely, OpenCV |
| **Frontend** | Next.js, React, Mapbox GL JS |
| **Routing** | Valhalla (self-hosted) |
| **Database** | Supabase (PostgreSQL) |
| **AI Analysis** | OpenAI GPT-4o-mini |

---

## API Endpoints

| Method | Path | Description |
|--------|------|-------------|
| `POST` | `/detect` | Upload satellite image → damage polygon masks |
| `POST` | `/georef` | Convert pixel masks → GeoJSON danger zones |
| `POST` | `/route` | Calculate safe route between two points |
| `POST` | `/analyze/rescue-plan` | Generate AI rescue plan for a severity level |
| `POST` | `/missions/` | Save a mission |
| `GET`  | `/missions/` | List all missions |

---

## Model Performance

Trained on the **xBD (xView2) dataset** — 10 real-world disasters across 5 countries:

| Disaster | Location | Type |
|----------|----------|------|
| Tubbs Fire | Santa Rosa, CA | Wildfire |
| Hurricane Harvey | Houston, TX | Category 4 Hurricane |
| Hurricane Florence | Wilmington, NC | Category 1 Hurricane |
| Hurricane Michael | Panama City, FL | Category 5 Hurricane |
| Hurricane Matthew | Les Cayes, Haiti | Category 4 Hurricane |
| Puebla Earthquake | Mexico City, Mexico | 7.1 Mw Earthquake |
| Palu Tsunami | Palu, Indonesia | 7.5 Mw + Tsunami |
| Volcán de Fuego | Guatemala | Volcanic Eruption |
| Missouri River Flooding | Nebraska/Iowa, USA | River Flooding |
| Thomas/Woolsey Fire | Ventura, CA | Wildfire |

**4 damage classes:** no-damage, minor-damage, major-damage, destroyed

---

## Demo Images

Pre-selected satellite images with confirmed damage are in `demo/images/`:

| File | Location | GPS | Damage |
|------|----------|-----|--------|
| `01_tubbs-fire_66-destroyed.png` | Santa Rosa, CA | 38.4404, -122.7141 | 🔴 66 destroyed |
| `04_hurricane-harvey_39-major.png` | Houston, TX | 29.7604, -95.3698 | 🟠 39 major |
| `07_hurricane-florence_48-major.png` | Wilmington, NC | 34.2257, -78.0447 | 🟠 48 major |
| `09_hurricane-michael_20-minor.png` | Panama City, FL | 30.1588, -85.6602 | 🟡 20 minor |

Upload any of these to test damage detection in the app.

---

## Project Structure

```
PathFinder/
├── backend/              # FastAPI server
│   ├── app/
│   │   ├── main.py       # App entry point
│   │   ├── config.py     # Environment config
│   │   ├── models.py     # Pydantic schemas
│   │   └── routes/       # API endpoints
│   └── requirements.txt
├── frontend/             # Next.js app
│   └── src/
│       ├── app/          # Pages (mission, etc.)
│       ├── components/   # Map, Sidebar, DangerLayer
│       └── lib/          # API client
├── saferoute/
│   ├── ai/runs/          # Trained model weights & metrics
│   └── data/             # xBD dataset (not committed)
├── demo/
│   ├── images/           # Best-damaged satellite samples
│   ├── satellite_collection.py  # Image catalog & gallery
│   └── test_model.py     # Model validation script
└── demo.py               # Full pipeline demo
```

---

## Configuration

Create `backend/.env`:

```env
MODEL_PATH=../saferoute/ai/runs/pathfinder-damage/weights/best.pt
VALHALLA_URL=http://localhost:8002
SUPABASE_URL=https://your-project.supabase.co
SUPABASE_KEY=your-key
OPENAI_API_KEY=sk-your-key
```

---

## Team

**GraphoLogiCode** — YHacks 2026

---

## License

MIT
