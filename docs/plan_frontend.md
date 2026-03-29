# SafeRoute — Person B: Frontend Engineer Plan

## Your Role

You are the **face** of the system. You build the web application that users interact with: a clean, Google/Apple Maps-style interface with satellite imagery, danger zone overlays, and safe route visualization. Everything the judges see at demo time is your work.

> **What changed from v2**: CesiumJS 3D globe is replaced with **MapLibre GL JS** — a lightweight, WebGL-accelerated 2D map with satellite tile layers. The interface now feels like Google Maps, not a globe. Routes come from **Valhalla** (real road directions), not a pixel-grid A\* path.

---

## What You're Building

A Next.js web app with two main views:

1. **Dashboard** (`/`) — Landing page with project hero + list of saved missions
2. **Mission View** (`/mission`) — The core interactive page:
   - Upload satellite image → see damage polygons on the satellite map
   - Click to set Start + Destination → see the safest route on real roads
   - Toggle between Map and Satellite view
   - **Right panel**: AI-generated rescue plan (evacuation, risk zones, resources, actions)
   - Save the mission → reload it later from the dashboard

---

## Tech Stack

| Tool | What you'll use it for |
|---|---|
| **TypeScript** | Language |
| **React 19** | UI components |
| **Next.js 15** | Framework (App Router, SSR) |
| **MapLibre GL JS** | WebGL-accelerated 2D map with satellite tiles |
| **react-map-gl** | React wrapper for MapLibre (by Uber/Visgl) |
| **Tailwind CSS 4** | Styling |
| **Supabase JS** | Client-side data fetching for missions list |

### Removed from v2

- ❌ CesiumJS / resium
- ❌ Cesium Ion access token
- ❌ copy-webpack-plugin for Cesium static assets
- ❌ 3D globe / terrain rendering

---

## Project Structure

```
frontend/
├── src/
│   ├── app/
│   │   ├── page.tsx              # Dashboard (landing + mission list)
│   │   ├── layout.tsx            # Root layout (fonts, metadata)
│   │   ├── globals.css           # Tailwind + custom styles
│   │   └── mission/
│   │       └── page.tsx          # Main mission view
│   ├── components/
│   │   ├── MapView.tsx           # MapLibre GL JS wrapper
│   │   ├── DangerLayer.tsx       # GeoJSON danger zone fill layers
│   │   ├── RouteLayer.tsx        # Route line layer
│   │   ├── ImageUpload.tsx       # Drag-and-drop upload
│   │   ├── MapControls.tsx       # Zoom, locate, layer toggle
│   │   ├── Sidebar.tsx           # Left controls panel
│   │   ├── AnalysisPanel.tsx     # Right panel — AI rescue plan display
│   │   └── MissionCard.tsx       # Dashboard mission list item
│   └── lib/
│       ├── api.ts                # Fetch wrappers for backend
│       ├── mapStyle.ts           # Satellite + street tile configs
│       └── supabase.ts           # Supabase client
├── public/
├── package.json
├── tailwind.config.ts
├── tsconfig.json
└── next.config.ts
```

---

## Phase 1 — Scaffold & Map Setup (Day 1, First Half)

### Step 1: Initialize the Next.js project

```bash
cd d:\School_Project\Yhacks
npx -y create-next-app@latest frontend --ts --tailwind --app --eslint --src-dir --import-alias "@/*" --turbopack
```

### Step 2: Install MapLibre GL JS

```bash
cd frontend
npm install maplibre-gl react-map-gl
```

> **react-map-gl** is a React wrapper by Uber/Visgl. It supports MapLibre GL JS as a backend and saves you from writing imperative map code.

### Step 3: Create `lib/mapStyle.ts` — Tile configurations

```typescript
// Satellite imagery from Esri (free, no API key required)
export const SATELLITE_STYLE: maplibregl.StyleSpecification = {
  version: 8,
  sources: {
    satellite: {
      type: "raster",
      tiles: [
        "https://server.arcgisonline.com/ArcGIS/rest/services/World_Imagery/MapServer/tile/{z}/{y}/{x}"
      ],
      tileSize: 256,
      attribution: "© Esri, Maxar, Earthstar Geographics"
    }
  },
  layers: [
    {
      id: "satellite-layer",
      type: "raster",
      source: "satellite"
    }
  ]
};

// Street map — free OpenStreetMap-based style
// Option A: Use MapTiler (better quality, requires free API key)
// export const STREET_STYLE = "https://api.maptiler.com/maps/streets-v2/style.json?key=YOUR_KEY";

// Option B: Use a free self-hosted style (no signup)
export const STREET_STYLE: maplibregl.StyleSpecification = {
  version: 8,
  sources: {
    osm: {
      type: "raster",
      tiles: ["https://tile.openstreetmap.org/{z}/{x}/{y}.png"],
      tileSize: 256,
      attribution: "© OpenStreetMap contributors"
    }
  },
  layers: [
    { id: "osm-layer", type: "raster", source: "osm" }
  ]
};
```

### Step 4: Build `MapView.tsx` — MapLibre wrapper

```typescript
"use client";
import { useRef, useCallback, useState } from "react";
import Map, { NavigationControl, GeolocateControl, MapRef } from "react-map-gl/maplibre";
import "maplibre-gl/dist/maplibre-gl.css";
import { SATELLITE_STYLE, STREET_STYLE } from "@/lib/mapStyle";

interface Props {
  onMapClick?: (lng: number, lat: number) => void;
  children?: React.ReactNode;
}

export default function MapView({ onMapClick, children }: Props) {
  const mapRef = useRef<MapRef>(null);
  const [isSatellite, setIsSatellite] = useState(true);

  const handleClick = useCallback(
    (e: maplibregl.MapMouseEvent) => {
      onMapClick?.(e.lngLat.lng, e.lngLat.lat);
    },
    [onMapClick]
  );

  return (
    <div className="relative w-full h-full">
      <Map
        ref={mapRef}
        initialViewState={{
          longitude: -90.88,
          latitude: 14.47,
          zoom: 15
        }}
        mapStyle={isSatellite ? SATELLITE_STYLE : STREET_STYLE}
        onClick={handleClick}
        style={{ width: "100%", height: "100%" }}
      >
        <NavigationControl position="top-right" />
        <GeolocateControl position="top-right" />
        {children}
      </Map>

      {/* Map / Satellite toggle (like Google Maps) */}
      <button
        className="absolute bottom-6 left-6 px-4 py-2 rounded-lg bg-zinc-900/90
                   backdrop-blur-md text-white text-sm font-medium
                   border border-zinc-700 hover:bg-zinc-800 transition-colors"
        onClick={() => setIsSatellite(!isSatellite)}
      >
        {isSatellite ? "🗺️ Map" : "🛰️ Satellite"}
      </button>
    </div>
  );
}
```

### Step 5: Create the Mission page layout

**`app/mission/page.tsx`**:

```typescript
"use client";
import { useState, useCallback } from "react";
import MapView from "@/components/MapView";
import Sidebar from "@/components/Sidebar";
import ImageUpload from "@/components/ImageUpload";
import DangerLayer from "@/components/DangerLayer";
import RouteLayer from "@/components/RouteLayer";
import { Marker } from "react-map-gl/maplibre";

export default function MissionPage() {
  const [dangerZones, setDangerZones] = useState(null);         // GeoJSON
  const [route, setRoute] = useState(null);                     // GeoJSON
  const [start, setStart] = useState<[number, number] | null>(null);
  const [end, setEnd] = useState<[number, number] | null>(null);
  const [detections, setDetections] = useState([]);

  const handleMapClick = useCallback((lng: number, lat: number) => {
    if (!start) {
      setStart([lng, lat]);
    } else if (!end) {
      setEnd([lng, lat]);
    }
  }, [start, end]);

  return (
    <div className="flex h-screen">
      {/* Sidebar: controls */}
      <aside className="w-80 bg-zinc-900 border-r border-zinc-800 p-4 flex flex-col gap-4 overflow-y-auto">
        <Sidebar
          detectionCount={detections.length}
          dangerZones={dangerZones}
          start={start}
          end={end}
          onRouteCalculated={setRoute}
          onClearMarkers={() => { setStart(null); setEnd(null); setRoute(null); }}
        />
      </aside>

      {/* Main: satellite map */}
      <main className="flex-1 relative">
        <MapView onMapClick={handleMapClick}>
          {dangerZones && <DangerLayer data={dangerZones} />}
          {route && <RouteLayer data={route} />}
          {start && (
            <Marker longitude={start[0]} latitude={start[1]} color="#22c55e" />
          )}
          {end && (
            <Marker longitude={end[0]} latitude={end[1]} color="#ef4444" />
          )}
        </MapView>

        {/* Floating upload overlay */}
        <ImageUpload
          onDetections={(dets) => {
            setDetections(dets);
            // After detection, user will also call /georef
          }}
        />
      </main>
    </div>
  );
}
```

---

## Phase 2 — Core Features (Day 1, Second Half)

### Step 6: Build `DangerLayer.tsx` — GeoJSON danger zone rendering

Render danger zones as **colored fill layers** on the map (like colored regions on Google Maps):

```typescript
"use client";
import { Source, Layer } from "react-map-gl/maplibre";

interface Props {
  data: GeoJSON.FeatureCollection;
}

export default function DangerLayer({ data }: Props) {
  return (
    <Source id="danger-zones" type="geojson" data={data}>
      {/* Filled polygons */}
      <Layer
        id="danger-fill"
        type="fill"
        paint={{
          "fill-color": [
            "match", ["get", "severity"],
            "no-damage",    "#22c55e",   // green
            "minor-damage", "#eab308",   // yellow
            "major-damage", "#f97316",   // orange
            "destroyed",    "#ef4444",   // red
            "#ffffff"
          ],
          "fill-opacity": 0.5
        }}
      />
      {/* Outline */}
      <Layer
        id="danger-outline"
        type="line"
        paint={{
          "line-color": "#ffffff",
          "line-width": 1,
          "line-opacity": 0.6
        }}
      />
    </Source>
  );
}
```

### Step 7: Build `RouteLayer.tsx` — Safe route visualization

Draw the Valhalla route as a styled line on the map:

```typescript
"use client";
import { Source, Layer } from "react-map-gl/maplibre";

interface Props {
  data: GeoJSON.Feature;
}

export default function RouteLayer({ data }: Props) {
  return (
    <Source id="safe-route" type="geojson" data={data}>
      {/* Route shadow (wider, dark) */}
      <Layer
        id="route-shadow"
        type="line"
        paint={{
          "line-color": "#000000",
          "line-width": 8,
          "line-opacity": 0.3
        }}
      />
      {/* Route line (bright green) */}
      <Layer
        id="route-line"
        type="line"
        paint={{
          "line-color": "#22c55e",
          "line-width": 4,
          "line-opacity": 0.9
        }}
      />
    </Source>
  );
}
```

### Step 8: Build `ImageUpload.tsx` — Drag-and-drop upload

Floating drag-and-drop overlay in the corner of the map:

```typescript
"use client";
import { useState, useCallback } from "react";
import { detectDamage } from "@/lib/api";

interface Props {
  onDetections: (data: any) => void;
}

export default function ImageUpload({ onDetections }: Props) {
  const [uploading, setUploading] = useState(false);
  const [dragActive, setDragActive] = useState(false);

  const handleUpload = useCallback(async (file: File) => {
    setUploading(true);
    try {
      const data = await detectDamage(file);
      onDetections(data);
    } catch (err) {
      console.error("Detection failed:", err);
    }
    setUploading(false);
  }, [onDetections]);

  return (
    <div
      className={`absolute top-4 right-4 w-72 p-4 rounded-xl backdrop-blur-md
                  border-2 border-dashed transition-colors cursor-pointer
                  ${dragActive
                    ? "border-emerald-400 bg-emerald-500/10"
                    : "border-zinc-600 bg-zinc-900/80"}`}
      onDragOver={(e) => { e.preventDefault(); setDragActive(true); }}
      onDragLeave={() => setDragActive(false)}
      onDrop={(e) => {
        e.preventDefault();
        setDragActive(false);
        if (e.dataTransfer.files[0]) handleUpload(e.dataTransfer.files[0]);
      }}
    >
      {uploading ? (
        <p className="text-emerald-400 text-sm animate-pulse">Analyzing damage...</p>
      ) : (
        <p className="text-zinc-400 text-sm text-center">
          Drop a satellite image here<br />or click to browse
        </p>
      )}
    </div>
  );
}
```

### Step 9: Build `Sidebar.tsx` — Controls panel

```typescript
"use client";
import { calculateRoute } from "@/lib/api";

interface Props {
  detectionCount: number;
  dangerZones: any;
  start: [number, number] | null;
  end: [number, number] | null;
  onRouteCalculated: (route: any) => void;
  onClearMarkers: () => void;
}

export default function Sidebar(props: Props) {
  const handleCalculateRoute = async () => {
    if (!props.start || !props.end || !props.dangerZones) return;
    const result = await calculateRoute(
      props.start, props.end, props.dangerZones, "pedestrian"
    );
    props.onRouteCalculated(result.route);
  };

  return (
    <div className="flex flex-col gap-6">
      <h2 className="text-xl font-bold text-white">SafeRoute</h2>

      {/* Danger Legend */}
      <div className="space-y-2">
        <h3 className="text-sm font-semibold text-zinc-400 uppercase tracking-wider">
          Damage Scale
        </h3>
        {[
          { label: "No Damage",    color: "bg-green-500" },
          { label: "Minor Damage", color: "bg-yellow-500" },
          { label: "Major Damage", color: "bg-orange-500" },
          { label: "Destroyed",    color: "bg-red-500" },
        ].map(({ label, color }) => (
          <div key={label} className="flex items-center gap-2">
            <div className={`w-4 h-4 rounded ${color}`} />
            <span className="text-sm text-zinc-300">{label}</span>
          </div>
        ))}
      </div>

      {/* Stats */}
      <div className="bg-zinc-800 rounded-lg p-3 space-y-1">
        <p className="text-sm text-zinc-400">
          Detections: <span className="text-white font-mono">{props.detectionCount}</span>
        </p>
        <p className="text-sm text-zinc-400">
          Start: <span className="text-emerald-400 font-mono">
            {props.start ? `${props.start[1].toFixed(4)}, ${props.start[0].toFixed(4)}` : "Click map"}
          </span>
        </p>
        <p className="text-sm text-zinc-400">
          Destination: <span className="text-red-400 font-mono">
            {props.end ? `${props.end[1].toFixed(4)}, ${props.end[0].toFixed(4)}` : "Click map"}
          </span>
        </p>
      </div>

      {/* Transport Mode */}
      <div className="flex gap-2">
        {["pedestrian", "auto", "bicycle"].map((mode) => (
          <button key={mode} className="flex-1 py-1.5 rounded-lg bg-zinc-800
                                         text-zinc-300 text-xs capitalize
                                         hover:bg-zinc-700 transition-colors">
            {mode === "pedestrian" ? "🚶 Walk" : mode === "auto" ? "🚗 Drive" : "🚴 Bike"}
          </button>
        ))}
      </div>

      {/* Actions */}
      <button
        onClick={handleCalculateRoute}
        disabled={!props.start || !props.end}
        className="w-full py-2 rounded-lg bg-emerald-600 hover:bg-emerald-500
                   disabled:bg-zinc-700 disabled:text-zinc-500
                   text-white font-medium transition-colors"
      >
        Calculate Safe Route
      </button>

      <button
        onClick={props.onClearMarkers}
        className="w-full py-2 rounded-lg border border-zinc-600
                   text-zinc-300 hover:bg-zinc-800 transition-colors"
      >
        Clear Markers
      </button>
    </div>
  );
}
```

### Step 10: Create `lib/api.ts` — Centralized fetch wrappers

```typescript
const API_BASE = process.env.NEXT_PUBLIC_API_URL || "http://localhost:8000";

export async function detectDamage(imageFile: File) {
  const formData = new FormData();
  formData.append("image", imageFile);
  const res = await fetch(`${API_BASE}/detect/`, { method: "POST", body: formData });
  if (!res.ok) throw new Error(`Detection failed: ${res.statusText}`);
  return res.json();
}

export async function geoReference(
  detections: any[],
  anchor: { lat: number; lng: number },
  scale: number,
  imageCenterPx: number[]
) {
  const res = await fetch(`${API_BASE}/georef/`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({
      detections,
      anchor,
      scale,
      image_center_px: imageCenterPx
    }),
  });
  if (!res.ok) throw new Error(`Geo-referencing failed: ${res.statusText}`);
  return res.json();
}

export async function calculateRoute(
  start: number[],
  end: number[],
  dangerZones: any,
  mode: string = "pedestrian"
) {
  const res = await fetch(`${API_BASE}/route/`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ start, end, danger_zones: dangerZones, mode }),
  });
  if (!res.ok) throw new Error(`Routing failed: ${res.statusText}`);
  return res.json();
}

export async function saveMission(data: any) {
  const res = await fetch(`${API_BASE}/missions/`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(data),
  });
  if (!res.ok) throw new Error(`Save failed: ${res.statusText}`);
  return res.json();
}

export async function getMissions() {
  const res = await fetch(`${API_BASE}/missions/`);
  return res.json();
}

export async function analyzeArea(data: {
  danger_zones: any;
  route_summary?: any;
  maneuvers?: any[];          // Valhalla turn-by-turn directions
  route_geometry?: any;       // GeoJSON geometry (LineString)
  start?: { lat: number; lng: number };
  end?: { lat: number; lng: number };
  disaster_type?: string;
  disaster_location?: string;
  transport_mode?: string;
}) {
  const res = await fetch(`${API_BASE}/analyze/`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(data),
  });
  if (!res.ok) throw new Error(`Analysis failed: ${res.statusText}`);
  return res.json();
}
```

---

## Phase 3 — Dashboard & Polish (Day 2)

### Step 11: Build the Dashboard page (`app/page.tsx`)

- Hero section with project name, tagline, and a "New Mission" button
- Grid of saved mission cards (fetched from backend)
- Each card shows: mission name, date, route summary
- Clicking a card navigates to `/mission?id=...` and reloads the data

### Step 12: Polish the UX

- **Loading states**: skeleton loaders while detecting, spinner while routing
- **Toast notifications**: "Mission saved!" confirmation
- **Responsive**: sidebar collapses on small screens
- **Dark theme**: zinc-900 background, emerald accents
- **Animations**: smooth fade-in for detection overlays, route drawing animation

---

## Phase 4 — AI Analysis Panel (Integrate When Backend Is Ready)

> [!NOTE]
> This phase is **deferred** until all backend endpoints (`/detect`, `/georef`, `/route`, `/analyze`) are working. Build the `AnalysisPanel.tsx` component, but wire it up last.

### Step 13: Build `AnalysisPanel.tsx` — Right panel for AI rescue plan

The right panel shows the GPT-5.4-mini generated rescue plan. It is a collapsible sliding panel that appears after the user clicks "Analyze Area".

**What it displays:**

| Section | Content | Visual |
|---|---|---|
| **Situation Summary** | 2-3 sentence overview | Text block with alert icon |
| **Risk Assessment** | Risk zones with severity tags | Color-coded cards (critical=red, high=orange, etc.) |
| **Evacuation Plan** | Priority zones, assembly points | Numbered list with map markers |
| **Resource Allocation** | Water, food, medical, shelter needs | Priority badges (immediate/6h/24h) |
| **Immediate Actions** | Time-critical steps | Ordered list with team assignments |
| **Route Analysis** | Why this route, alternatives, hazards | Expandable accordion |

```typescript
"use client";
import { useState } from "react";
import { analyzeArea } from "@/lib/api";

interface Props {
  dangerZones: any;
  routeSummary: any;
  start: [number, number] | null;
  end: [number, number] | null;
}

export default function AnalysisPanel({ dangerZones, routeSummary, start, end }: Props) {
  const [plan, setPlan] = useState<any>(null);
  const [loading, setLoading] = useState(false);
  const [isOpen, setIsOpen] = useState(false);

  const handleAnalyze = async () => {
    setLoading(true);
    try {
      const result = await analyzeArea({
        danger_zones: dangerZones,
        route_summary: routeSummary,
        start: start ? { lat: start[1], lng: start[0] } : undefined,
        end: end ? { lat: end[1], lng: end[0] } : undefined,
        disaster_type: "hurricane",
        disaster_location: "Panama City, FL",
      });
      setPlan(result.plan);
      setIsOpen(true);
    } catch (err) {
      console.error("Analysis failed:", err);
    }
    setLoading(false);
  };

  return (
    <>
      {/* Trigger button (in sidebar or floating) */}
      <button
        onClick={handleAnalyze}
        disabled={!dangerZones || loading}
        className="w-full py-2 rounded-lg bg-blue-600 hover:bg-blue-500
                   disabled:bg-zinc-700 disabled:text-zinc-500
                   text-white font-medium transition-colors"
      >
        {loading ? "🤖 Analyzing..." : "🤖 AI Rescue Plan"}
      </button>

      {/* Sliding right panel */}
      {isOpen && plan && (
        <aside className="fixed top-0 right-0 w-96 h-full bg-zinc-900/95
                         backdrop-blur-md border-l border-zinc-700
                         overflow-y-auto p-6 z-50 shadow-2xl">
          <div className="flex justify-between items-center mb-6">
            <h2 className="text-lg font-bold text-white">🤖 AI Rescue Plan</h2>
            <button onClick={() => setIsOpen(false)} className="text-zinc-400 hover:text-white">
              ✕
            </button>
          </div>

          {/* Situation Summary */}
          <section className="mb-6">
            <h3 className="text-sm font-semibold text-zinc-400 uppercase tracking-wider mb-2">
              Situation Overview
            </h3>
            <p className="text-sm text-zinc-300">{plan.situation_summary}</p>
          </section>

          {/* Risk Assessment */}
          <section className="mb-6 space-y-2">
            <h3 className="text-sm font-semibold text-zinc-400 uppercase tracking-wider mb-2">
              Risk Zones
            </h3>
            {plan.risk_assessment?.map((risk: any, i: number) => (
              <div key={i} className="bg-zinc-800 rounded-lg p-3">
                <div className="flex justify-between items-center mb-1">
                  <span className="text-sm font-medium text-white">{risk.zone}</span>
                  <span className={`text-xs px-2 py-0.5 rounded-full font-medium
                    ${risk.severity === 'critical' ? 'bg-red-500/20 text-red-400' :
                      risk.severity === 'high' ? 'bg-orange-500/20 text-orange-400' :
                      risk.severity === 'moderate' ? 'bg-yellow-500/20 text-yellow-400' :
                      'bg-green-500/20 text-green-400'}`}>
                    {risk.severity}
                  </span>
                </div>
                <p className="text-xs text-zinc-400">{risk.recommendation}</p>
              </div>
            ))}
          </section>

          {/* Immediate Actions */}
          <section className="mb-6 space-y-2">
            <h3 className="text-sm font-semibold text-zinc-400 uppercase tracking-wider mb-2">
              Immediate Actions
            </h3>
            {plan.immediate_actions?.map((action: any, i: number) => (
              <div key={i} className="flex gap-3 items-start">
                <span className="w-6 h-6 rounded-full bg-emerald-600 text-white
                               text-xs flex items-center justify-center flex-shrink-0">
                  {action.priority}
                </span>
                <div>
                  <p className="text-sm text-white">{action.action}</p>
                  <p className="text-xs text-zinc-500">
                    {action.responsible_team} · {action.time_window}
                  </p>
                </div>
              </div>
            ))}
          </section>

          {/* Resource Allocation */}
          <section className="mb-6 space-y-2">
            <h3 className="text-sm font-semibold text-zinc-400 uppercase tracking-wider mb-2">
              Resources Needed
            </h3>
            {plan.resource_allocation?.map((res: any, i: number) => (
              <div key={i} className="bg-zinc-800 rounded-lg p-3 flex justify-between">
                <div>
                  <p className="text-sm text-white capitalize">{res.resource}</p>
                  <p className="text-xs text-zinc-400">{res.deployment_location}</p>
                </div>
                <span className={`text-xs px-2 py-0.5 rounded-full h-fit
                  ${res.priority === 'immediate' ? 'bg-red-500/20 text-red-400' :
                    res.priority === 'within_6h' ? 'bg-orange-500/20 text-orange-400' :
                    'bg-yellow-500/20 text-yellow-400'}`}>
                  {res.priority}
                </span>
              </div>
            ))}
          </section>
        </aside>
      )}
    </>
  );
}
```

---

## Your Deliverables Checklist

```
- [ ] Next.js project scaffold with MapLibre GL JS
- [ ] MapView.tsx             (satellite map + map/satellite toggle)
- [ ] DangerLayer.tsx         (GeoJSON danger zone fills)
- [ ] RouteLayer.tsx          (safe route line layer)
- [ ] ImageUpload.tsx         (drag-and-drop → POST /detect)
- [ ] Sidebar.tsx             (controls, legend, transport mode, actions)
- [ ] AnalysisPanel.tsx       (right panel — AI rescue plan display)  ← NEW (deferred)
- [ ] lib/api.ts              (backend fetch wrappers — detect, georef, route, analyze)
- [ ] lib/mapStyle.ts         (satellite + street tile configs)
- [ ] Dashboard page          (hero + saved missions)
- [ ] Mission page            (full interactive map view)
- [ ] UX polish               (loading states, dark theme, animations)
```

---

## What You Need From Your Teammates

| From | What | When |
|---|---|---|
| Person A | Backend running at `localhost:8000` with stub `/detect` endpoint | Day 1, first half |
| Person A | Working `/detect`, `/georef`, and `/route` endpoints | Day 1, second half |
| Person A | `/missions` CRUD + `/analyze` endpoint | Day 2, first half |
| AI Lead | Agreement on the detection JSON schema | Day 1, first half |

---

## Quick Reference: How to Run

```bash
cd d:\School_Project\Yhacks\frontend

# First time setup
npm install

# Run the dev server
npm run dev

# Opens at http://localhost:3000
```

---

## Design Aesthetics Checklist

| Element | Style |
|---|---|
| Background | `zinc-950` / `zinc-900` (deep dark) |
| Accent color | `emerald-500` (safe / positive) |
| Danger colors | Green → Yellow → Orange → Red gradient |
| Font | Inter or Outfit (import from Google Fonts) |
| Glassmorphism | `backdrop-blur-md bg-zinc-900/80` on floating panels |
| Animations | Fade-in overlays, smooth route drawing, pulse on loading |
| Border radius | `rounded-xl` on cards, `rounded-lg` on buttons |
| Map toggle | Bottom-left corner, like Google Maps |
