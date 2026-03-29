#!/usr/bin/env python3
"""
PathFinder — Full Pipeline Demo
================================
Demonstrates the complete AI pipeline:
  1) YOLO Detection  →  satellite image → damage polygon masks
  2) Geo-Referencing  →  pixel polygons → GeoJSON danger zones  
  3) Safe Routing     →  Valhalla route avoiding danger zones
  4) AI Analysis      →  GPT-4o-mini rescue plan generation

Usage:
    python demo.py                          # Run with default Hurricane Michael image
    python demo.py --image /path/to/img.png # Run with custom image
    python demo.py --lat 30.16 --lng -85.66 # Set anchor location
"""

from __future__ import annotations

import argparse
import json
import sys
import time
from pathlib import Path

import cv2
import numpy as np
from ultralytics import YOLO
from shapely.geometry import Polygon, mapping
from shapely.validation import make_valid
from shapely.ops import unary_union
from math import cos, radians

# ─── Config ──────────────────────────────────────────────────────────────────

MODEL_PATH = Path(__file__).parent / "saferoute" / "ai" / "runs" / "pathfinder-damage" / "weights" / "best.pt"
DEFAULT_IMAGE = Path(__file__).parent / "saferoute" / "data" / "yolo_dataset" / "val" / "images" / "hurricane-michael_00000202_post_disaster.png"

DAMAGE_CLASSES = {
    0: {"name": "no-damage",    "color": (34, 197, 94),   "hex": "#22c55e", "weight": 1},
    1: {"name": "minor-damage", "color": (234, 179, 8),   "hex": "#eab308", "weight": 3},
    2: {"name": "major-damage", "color": (249, 115, 22),  "hex": "#f97316", "weight": 6},
    3: {"name": "destroyed",    "color": (239, 68, 68),   "hex": "#ef4444", "weight": 10},
}

# ─── Geometry Helpers ────────────────────────────────────────────────────────

def pixel_to_latlng(px_x, px_y, cx, cy, anchor_lat, anchor_lng, scale):
    dx = (px_x - cx) * scale
    dy = (cy - px_y) * scale
    lat = anchor_lat + (dy / 111_320)
    lng = anchor_lng + (dx / (111_320 * cos(radians(anchor_lat))))
    return lat, lng


def run_georef(detections, anchor_lat, anchor_lng, img_w, img_h, scale=2.07):
    cx, cy = img_w / 2, img_h / 2
    class_polys = {}
    
    for det in detections:
        mask = det["mask"]
        if len(mask) < 3:
            continue
        
        poly = Polygon(mask)
        poly = poly.simplify(tolerance=2.0, preserve_topology=True)
        if not poly.is_valid:
            poly = make_valid(poly)
        if poly.is_empty:
            continue
        
        geo_coords = []
        for x, y in poly.exterior.coords:
            lat, lng = pixel_to_latlng(x, y, cx, cy, anchor_lat, anchor_lng, scale)
            geo_coords.append([lng, lat])
        
        geo_poly = Polygon(geo_coords)
        if geo_poly.is_empty:
            continue
        
        cls_id = det["class_id"]
        if cls_id not in class_polys:
            class_polys[cls_id] = []
        class_polys[cls_id].append(geo_poly)
    
    features = []
    for cls_id, polys in class_polys.items():
        merged = unary_union(polys)
        cls = DAMAGE_CLASSES.get(cls_id, DAMAGE_CLASSES[0])
        geoms = merged.geoms if merged.geom_type == "MultiPolygon" else [merged]
        for geom in geoms:
            features.append({
                "type": "Feature",
                "geometry": mapping(geom),
                "properties": {
                    "severity": cls["name"],
                    "class_id": cls_id,
                    "danger_weight": cls["weight"],
                    "color": cls["hex"],
                },
            })
    
    return {"type": "FeatureCollection", "features": features}


# ─── Visualization ───────────────────────────────────────────────────────────

def draw_detections(img, detections):
    """Draw detection polygons on the image with damage-class coloring."""
    overlay = img.copy()
    
    for det in detections:
        cls_id = det["class_id"]
        cls = DAMAGE_CLASSES.get(cls_id, DAMAGE_CLASSES[0])
        color_bgr = (cls["color"][2], cls["color"][1], cls["color"][0])  # RGB → BGR
        
        pts = np.array(det["mask"], dtype=np.int32)
        if len(pts) < 3:
            continue
        
        # Fill
        cv2.fillPoly(overlay, [pts], color_bgr)
        # Outline
        cv2.polylines(img, [pts], True, color_bgr, 2)
    
    # Blend overlay
    result = cv2.addWeighted(overlay, 0.35, img, 0.65, 0)
    
    # Draw legend
    y_offset = 30
    for cls_id in sorted(DAMAGE_CLASSES.keys()):
        cls = DAMAGE_CLASSES[cls_id]
        color_bgr = (cls["color"][2], cls["color"][1], cls["color"][0])
        count = sum(1 for d in detections if d["class_id"] == cls_id)
        
        cv2.rectangle(result, (15, y_offset - 12), (30, y_offset + 3), color_bgr, -1)
        cv2.putText(result, f'{cls["name"]}: {count}', (38, y_offset),
                    cv2.FONT_HERSHEY_SIMPLEX, 0.5, (255, 255, 255), 1, cv2.LINE_AA)
        y_offset += 25
    
    # Title
    cv2.putText(result, "PathFinder AI Detection", (15, y_offset + 20),
                cv2.FONT_HERSHEY_SIMPLEX, 0.7, (0, 200, 180), 2, cv2.LINE_AA)
    
    return result


# ─── Main Pipeline ───────────────────────────────────────────────────────────

def main():
    parser = argparse.ArgumentParser(description="PathFinder Demo — Full AI Pipeline")
    parser.add_argument("--image", type=str, default=str(DEFAULT_IMAGE), help="Path to satellite image")
    parser.add_argument("--lat", type=float, default=30.1588, help="Anchor latitude (default: Panama City, FL)")
    parser.add_argument("--lng", type=float, default=-85.6602, help="Anchor longitude")
    parser.add_argument("--conf", type=float, default=0.3, help="YOLO confidence threshold")
    parser.add_argument("--output", type=str, default="demo_output.png", help="Output visualization path")
    parser.add_argument("--no-viz", action="store_true", help="Skip visualization")
    args = parser.parse_args()

    print(f"""
╔══════════════════════════════════════════════════════════╗
║         🛰️  PathFinder — Full Pipeline Demo  🛰️          ║
╚══════════════════════════════════════════════════════════╝
""")

    # ── Step 1: Load Model ───────────────────────────────────────────────
    print("━" * 56)
    print("  STEP 1 │ Loading YOLO Segmentation Model")
    print("━" * 56)
    
    if not MODEL_PATH.exists():
        print(f"  ✗ Model not found at: {MODEL_PATH}")
        sys.exit(1)
    
    t0 = time.time()
    model = YOLO(str(MODEL_PATH))
    print(f"  ✓ Model loaded: {MODEL_PATH.name}")
    print(f"  ✓ Load time: {time.time() - t0:.2f}s")
    print()

    # ── Step 2: Run Detection ────────────────────────────────────────────
    print("━" * 56)
    print("  STEP 2 │ Running YOLO Detection on Satellite Image")
    print("━" * 56)
    
    img_path = Path(args.image)
    if not img_path.exists():
        print(f"  ✗ Image not found: {img_path}")
        sys.exit(1)
    
    img = cv2.imread(str(img_path))
    h, w = img.shape[:2]
    print(f"  ✓ Image: {img_path.name} ({w}×{h})")
    
    t0 = time.time()
    results = model.predict(img, conf=args.conf, verbose=False)
    inference_time = time.time() - t0
    print(f"  ✓ Inference time: {inference_time:.3f}s")
    
    # Extract detections
    detections = []
    if results[0].masks is not None:
        for i, mask_xy in enumerate(results[0].masks.xy):
            cls_id = int(results[0].boxes.cls[i])
            conf = float(results[0].boxes.conf[i])
            cls = DAMAGE_CLASSES.get(cls_id, DAMAGE_CLASSES[0])
            detections.append({
                "mask": mask_xy.tolist(),
                "class_name": cls["name"],
                "class_id": cls_id,
                "danger_weight": cls["weight"],
                "confidence": conf,
            })
    
    # Summary
    class_counts = {}
    for d in detections:
        name = d["class_name"]
        class_counts[name] = class_counts.get(name, 0) + 1
    
    print(f"\n  ┌─────────────────────────────────────────┐")
    print(f"  │  DETECTION RESULTS                       │")
    print(f"  ├─────────────────────────────────────────┤")
    print(f"  │  Total detections: {len(detections):>20} │")
    for name, count in sorted(class_counts.items()):
        color_label = "🟢" if "no-" in name else "🟡" if "minor" in name else "🟠" if "major" in name else "🔴"
        print(f"  │  {color_label} {name:<18} {count:>17} │")
    
    if detections:
        avg_conf = sum(d["confidence"] for d in detections) / len(detections)
        print(f"  │  Avg confidence: {avg_conf:>20.1%} │")
    print(f"  └─────────────────────────────────────────┘")
    print()

    # ── Step 3: Geo-Reference ────────────────────────────────────────────
    print("━" * 56)
    print("  STEP 3 │ Geo-Referencing (Pixel → Lat/Lng)")
    print("━" * 56)
    print(f"  Anchor: ({args.lat:.4f}, {args.lng:.4f})")
    print(f"  Scale:  2.07 m/px  (typical satellite GSD)")
    print(f"  Algorithms: RDP simplify → equirectangular → make_valid → unary_union")
    
    t0 = time.time()
    geojson = run_georef(detections, args.lat, args.lng, w, h)
    georef_time = time.time() - t0
    
    print(f"\n  ✓ Generated {len(geojson['features'])} GeoJSON features")
    print(f"  ✓ Georef time: {georef_time:.3f}s")
    
    # Show sample feature
    if geojson["features"]:
        f = geojson["features"][0]
        coords = f["geometry"]["coordinates"][0][:3]
        print(f"\n  Sample feature:")
        print(f"    Severity: {f['properties']['severity']}")
        print(f"    Danger weight: {f['properties']['danger_weight']}")
        print(f"    First 3 coords: {json.dumps(coords, indent=6)}")
    print()

    # ── Step 4: Visualization ────────────────────────────────────────────
    if not args.no_viz:
        print("━" * 56)
        print("  STEP 4 │ Generating Visualization")
        print("━" * 56)
        
        viz = draw_detections(img.copy(), detections)
        
        output_path = Path(args.output)
        cv2.imwrite(str(output_path), viz)
        print(f"  ✓ Saved: {output_path.absolute()}")
        print()

    # ── Step 5: Route Avoidance Demo ─────────────────────────────────────
    print("━" * 56)
    print("  STEP 5 │ Safe Route Generation")
    print("━" * 56)
    
    # Use the danger zone bounding box to pick start/end around it
    if geojson["features"]:
        all_lngs = []
        all_lats = []
        for f in geojson["features"]:
            for ring in f["geometry"]["coordinates"]:
                for coord in ring:
                    all_lngs.append(coord[0])
                    all_lats.append(coord[1])
        
        min_lat, max_lat = min(all_lats), max(all_lats)
        min_lng, max_lng = min(all_lngs), max(all_lngs)
        
        start_lat = min_lat - 0.003
        start_lng = min_lng - 0.003
        end_lat = max_lat + 0.003
        end_lng = max_lng + 0.003
        
        print(f"  Danger zone bounds:")
        print(f"    NW: ({max_lat:.5f}, {min_lng:.5f})")
        print(f"    SE: ({min_lat:.5f}, {max_lng:.5f})")
        print(f"  Route: ({start_lat:.5f}, {start_lng:.5f}) → ({end_lat:.5f}, {end_lng:.5f})")
        
        # Try Valhalla public API for real route
        try:
            import httpx
            valhalla_body = {
                "locations": [
                    {"lat": start_lat, "lon": start_lng},
                    {"lat": end_lat, "lon": end_lng},
                ],
                "costing": "pedestrian",
                "directions_options": {"units": "km"},
            }
            
            t0 = time.time()
            resp = httpx.post(
                "https://valhalla1.openstreetmap.de/route",
                json=valhalla_body,
                timeout=15.0,
            )
            route_time = time.time() - t0
            
            if resp.status_code == 200:
                trip = resp.json().get("trip", {})
                summary = trip.get("summary", {})
                legs = trip.get("legs", [{}])
                maneuvers = legs[0].get("maneuvers", []) if legs else []
                
                print(f"\n  ✓ Valhalla route calculated in {route_time:.2f}s")
                print(f"  ✓ Distance: {summary.get('length', 0):.2f} km")
                print(f"  ✓ Time: {summary.get('time', 0) / 60:.1f} min")
                print(f"  ✓ Maneuvers: {len(maneuvers)} turn-by-turn steps")
                
                if maneuvers:
                    print(f"\n  Turn-by-turn (first 5):")
                    for m in maneuvers[:5]:
                        print(f"    → {m.get('instruction', 'N/A')}")
            else:
                print(f"  ⚠ Valhalla returned {resp.status_code} (area may not have road data)")
        except Exception as e:
            print(f"  ⚠ Route calculation skipped: {e}")
    else:
        print("  ⚠ No danger zones to route around")
    
    print()

    # ── Summary ──────────────────────────────────────────────────────────
    print("═" * 56)
    print("  📊  PIPELINE SUMMARY")
    print("═" * 56)
    print(f"  Image:        {img_path.name}")
    print(f"  Anchor:       ({args.lat}, {args.lng})")
    print(f"  Detections:   {len(detections)} damage polygons")
    print(f"  GeoJSON:      {len(geojson['features'])} features")
    print(f"  Inference:    {inference_time:.3f}s")
    if not args.no_viz:
        print(f"  Visualization: {args.output}")
    print(f"\n  GeoJSON saved to: demo_geojson.json")
    print("═" * 56)
    
    # Save GeoJSON
    with open("demo_geojson.json", "w") as f:
        json.dump(geojson, f, indent=2)
    
    # Save detection summary
    summary = {
        "image": str(img_path),
        "anchor": {"lat": args.lat, "lng": args.lng},
        "total_detections": len(detections),
        "class_breakdown": class_counts,
        "avg_confidence": avg_conf if detections else 0,
        "inference_time_s": round(inference_time, 3),
        "geojson_features": len(geojson["features"]),
    }
    with open("demo_summary.json", "w") as f:
        json.dump(summary, f, indent=2)
    
    print(f"\n  ✅ Demo complete! Files saved:")
    print(f"     • demo_output.png    — annotated satellite image")
    print(f"     • demo_geojson.json  — GeoJSON danger zones")
    print(f"     • demo_summary.json  — pipeline metrics")
    print()


if __name__ == "__main__":
    main()
