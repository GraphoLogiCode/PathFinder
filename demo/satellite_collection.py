#!/usr/bin/env python3
"""
PathFinder — Satellite Image Collection & Location Demo
=========================================================
Collects satellite images from the xBD disaster dataset, maps each
disaster event to its real-world GPS location, and generates:
  1) An annotated gallery of satellite images
  2) A JSON catalog with location metadata
  3) Optional YOLO damage detection on each image

Usage:
    python demo/satellite_collection.py                     # Collect & catalog all
    python demo/satellite_collection.py --detect            # Also run YOLO detection
    python demo/satellite_collection.py --html              # Generate HTML gallery
    python demo/satellite_collection.py --detect --html     # Full demo
"""

from __future__ import annotations

import argparse
import json
import shutil
import sys
import time
from pathlib import Path

import cv2
import numpy as np

# ─── Real-World Disaster Locations ───────────────────────────────────────────
# Each disaster in the xBD dataset corresponds to a real geo-event.
# These are the actual coordinates for each disaster.

DISASTER_CATALOG = {
    "guatemala-volcano": {
        "name": "Volcán de Fuego Eruption",
        "date": "June 3, 2018",
        "location": "San Miguel Los Lotes, Guatemala",
        "lat": 14.4734,
        "lng": -90.8810,
        "country": "Guatemala",
        "disaster_type": "Volcanic Eruption",
        "description": (
            "The Volcán de Fuego erupted violently, sending pyroclastic flows "
            "through the village of San Miguel Los Lotes.  The eruption killed "
            "over 190 people and destroyed entire communities."
        ),
        "emoji": "🌋",
    },
    "hurricane-florence": {
        "name": "Hurricane Florence",
        "date": "September 14, 2018",
        "location": "Leland / Wilmington, North Carolina, USA",
        "lat": 34.2257,
        "lng": -78.0447,
        "country": "United States",
        "disaster_type": "Hurricane (Category 1)",
        "description": (
            "Hurricane Florence made landfall near Wrightsville Beach, NC as a "
            "Category 1 hurricane.  Catastrophic freshwater flooding caused "
            "over $24 billion in damage across the Carolinas."
        ),
        "emoji": "🌀",
    },
    "hurricane-harvey": {
        "name": "Hurricane Harvey",
        "date": "August 25, 2017",
        "location": "Houston / Port Aransas, Texas, USA",
        "lat": 29.7604,
        "lng": -95.3698,
        "country": "United States",
        "disaster_type": "Hurricane (Category 4)",
        "description": (
            "Hurricane Harvey dumped over 60 inches of rain on Houston over "
            "four days — the wettest tropical cyclone on record in the US. "
            "Flooding displaced over 30,000 people and damaged 204,000 homes."
        ),
        "emoji": "🌀",
    },
    "hurricane-matthew": {
        "name": "Hurricane Matthew",
        "date": "October 4, 2016",
        "location": "Les Cayes / Jérémie, Haiti",
        "lat": 18.1942,
        "lng": -73.7508,
        "country": "Haiti",
        "disaster_type": "Hurricane (Category 4)",
        "description": (
            "Hurricane Matthew struck Haiti as a Category 4 hurricane, the "
            "strongest to hit the country since 1964. It killed over 500 "
            "people and left 1.4 million in need of humanitarian assistance."
        ),
        "emoji": "🌀",
    },
    "hurricane-michael": {
        "name": "Hurricane Michael",
        "date": "October 10, 2018",
        "location": "Mexico Beach / Panama City, Florida, USA",
        "lat": 30.1588,
        "lng": -85.6602,
        "country": "United States",
        "disaster_type": "Hurricane (Category 5)",
        "description": (
            "Hurricane Michael made landfall near Mexico Beach, FL as a "
            "Category 5 hurricane — the strongest ever to hit the Florida "
            "panhandle. Storm surge of 9–14 feet obliterated entire blocks."
        ),
        "emoji": "🌀",
    },
    "mexico-earthquake": {
        "name": "Puebla Earthquake",
        "date": "September 19, 2017",
        "location": "Mexico City / Puebla, Mexico",
        "lat": 19.4326,
        "lng": -99.1332,
        "country": "Mexico",
        "disaster_type": "Earthquake (7.1 Mw)",
        "description": (
            "A magnitude 7.1 earthquake struck central Mexico, collapsing "
            "buildings across Mexico City and Puebla. Over 370 people were "
            "killed. It occurred on the 32nd anniversary of the 1985 quake."
        ),
        "emoji": "🏚️",
    },
    "midwest-flooding": {
        "name": "Missouri River Flooding",
        "date": "March 2019",
        "location": "Nebraska / Iowa / Missouri, USA",
        "lat": 41.2565,
        "lng": -95.9345,
        "country": "United States",
        "disaster_type": "River Flooding",
        "description": (
            "A 'bomb cyclone' triggered catastrophic flooding along the "
            "Missouri and Platte Rivers, breaching levees and inundating "
            "farmland. Over $3 billion in damage across 14 million acres."
        ),
        "emoji": "🌊",
    },
    "palu-tsunami": {
        "name": "Sulawesi Earthquake & Tsunami",
        "date": "September 28, 2018",
        "location": "Palu, Central Sulawesi, Indonesia",
        "lat": -0.8917,
        "lng": 119.8707,
        "country": "Indonesia",
        "disaster_type": "Earthquake (7.5 Mw) + Tsunami",
        "description": (
            "A 7.5-magnitude earthquake generated a devastating tsunami up to "
            "11 meters high that struck the coastal city of Palu. Soil "
            "liquefaction swallowed entire neighborhoods. Over 4,340 killed."
        ),
        "emoji": "🌊",
    },
    "santa-rosa-wildfire": {
        "name": "Tubbs Fire",
        "date": "October 8, 2017",
        "location": "Santa Rosa / Napa Valley, California, USA",
        "lat": 38.4404,
        "lng": -122.7141,
        "country": "United States",
        "disaster_type": "Wildfire",
        "description": (
            "The Tubbs Fire burned through Santa Rosa's Coffey Park and "
            "Fountaingrove neighborhoods, destroying 5,636 structures. It was "
            "the most destructive wildfire in California history at the time."
        ),
        "emoji": "🔥",
    },
    "socal-fire": {
        "name": "Thomas Fire / Woolsey Fire",
        "date": "December 2017 – November 2018",
        "location": "Ventura / Malibu, California, USA",
        "lat": 34.2746,
        "lng": -119.2290,
        "country": "United States",
        "disaster_type": "Wildfire",
        "description": (
            "The Thomas Fire burned 281,893 acres in Ventura and Santa Barbara "
            "counties, making it one of the largest wildfires in California "
            "history. The later Woolsey Fire devastated Malibu communities."
        ),
        "emoji": "🔥",
    },
}


# ─── Helpers ─────────────────────────────────────────────────────────────────

def get_image_dir() -> Path:
    return Path(__file__).resolve().parent.parent / "saferoute" / "data" / "yolo_dataset" / "val" / "images"


# ── Pre-scanned best-damaged images (avoids re-scanning every run) ──────────
# These were found by scanning the val set with YOLO at conf=0.3.
# Sorted by damage severity: destroyed first, then major, then minor.
BEST_DAMAGED_IMAGES = {
    "santa-rosa-wildfire": "santa-rosa-wildfire_00000007_post_disaster.png",   # 66 destroyed
    "socal-fire":          "socal-fire_00000003_post_disaster.png",             # 17 minor
    "hurricane-harvey":    "hurricane-harvey_00000001_post_disaster.png",       # 39 major-damage
    "hurricane-florence":  "hurricane-florence_00000048_post_disaster.png",     # 16 major-damage
    "hurricane-michael":   "hurricane-michael_00000000_post_disaster.png",      # 20 minor-damage
    "hurricane-matthew":   "hurricane-matthew_00000044_post_disaster.png",      # 1 minor-damage
    "mexico-earthquake":   "mexico-earthquake_00000001_post_disaster.png",      # detected
    "palu-tsunami":        "palu-tsunami_00000000_post_disaster.png",            # detected
    "midwest-flooding":    "midwest-flooding_00000005_post_disaster.png",       # detected
    "guatemala-volcano":   "guatemala-volcano_00000000_post_disaster.png",      # detected
}


def collect_samples(img_dir: Path, max_per_disaster: int = 1,
                    damage_only: bool = False) -> dict[str, list[Path]]:
    """Pick representative post-disaster images for each event.

    Args:
        img_dir:          Directory containing all satellite images.
        max_per_disaster: How many images per disaster (default 1).
        damage_only:      If True, use the pre-scanned best-damaged images
                          instead of the first available image.
    """
    collected: dict[str, list[Path]] = {}

    if damage_only:
        print("  📡 Using pre-scanned best-damaged images per disaster …")
        for disaster_key in DISASTER_CATALOG:
            fname = BEST_DAMAGED_IMAGES.get(disaster_key)
            if fname:
                p = img_dir / fname
                if p.exists():
                    collected[disaster_key] = [p]
                    continue
            # Fallback: first available
            post_imgs = sorted(img_dir.glob(f"{disaster_key}_*_post_disaster.png"))
            if post_imgs:
                collected[disaster_key] = post_imgs[:1]
            else:
                print(f"  ⚠ No post-disaster images found for {disaster_key}")
    else:
        for disaster_key in DISASTER_CATALOG:
            post_imgs = sorted(img_dir.glob(f"{disaster_key}_*_post_disaster.png"))
            if not post_imgs:
                print(f"  ⚠ No post-disaster images found for {disaster_key}")
                continue
            collected[disaster_key] = post_imgs[:max_per_disaster]

    return collected


def annotate_image(img: np.ndarray, info: dict, filename: str) -> np.ndarray:
    """Stamp location info onto the satellite image."""
    h, w = img.shape[:2]
    result = img.copy()

    # Dark banner at the bottom
    banner_h = 110
    overlay = result.copy()
    cv2.rectangle(overlay, (0, h - banner_h), (w, h), (0, 0, 0), -1)
    result = cv2.addWeighted(overlay, 0.7, result, 0.3, 0)

    # Text
    y = h - banner_h + 25
    cv2.putText(result, f'{info["emoji"]}  {info["name"]}',
                (15, y), cv2.FONT_HERSHEY_SIMPLEX, 0.65, (0, 220, 200), 2, cv2.LINE_AA)

    y += 25
    cv2.putText(result, f'Location: {info["location"]}',
                (15, y), cv2.FONT_HERSHEY_SIMPLEX, 0.5, (200, 200, 200), 1, cv2.LINE_AA)

    y += 22
    cv2.putText(result, f'GPS: ({info["lat"]:.4f}, {info["lng"]:.4f})  |  Date: {info["date"]}',
                (15, y), cv2.FONT_HERSHEY_SIMPLEX, 0.45, (150, 150, 150), 1, cv2.LINE_AA)

    y += 22
    cv2.putText(result, f'Type: {info["disaster_type"]}  |  File: {filename}',
                (15, y), cv2.FONT_HERSHEY_SIMPLEX, 0.4, (120, 120, 120), 1, cv2.LINE_AA)

    # Top-left tag
    cv2.putText(result, "PathFinder Satellite Collection",
                (10, 25), cv2.FONT_HERSHEY_SIMPLEX, 0.55, (0, 200, 180), 1, cv2.LINE_AA)

    return result


def generate_html_gallery(catalog_data: list[dict], output_dir: Path):
    """Generate a self-contained HTML gallery with GPS search functionality."""

    # Build JSON data for the JS search engine
    items_json = json.dumps([{
        "name": item["name"],
        "emoji": item["emoji"],
        "location": item["location"],
        "date": item["date"],
        "lat": item["lat"],
        "lng": item["lng"],
        "country": item["country"],
        "disaster_type": item["disaster_type"],
        "description": item["description"],
        "source_file": item["source_file"],
        "annotated_image": item["annotated_image"],
        "disaster_key": item["disaster_key"],
        "detections": item.get("detections", 0),
        "class_breakdown": item.get("class_breakdown", {}),
    } for item in catalog_data], indent=2)

    def get_badge_class(dtype: str) -> str:
        dtype_lower = dtype.lower()
        if "hurricane" in dtype_lower:
            return "badge-hurricane"
        elif "earthquake" in dtype_lower:
            return "badge-earthquake"
        elif "wildfire" in dtype_lower or "fire" in dtype_lower:
            return "badge-wildfire"
        elif "volcano" in dtype_lower:
            return "badge-volcano"
        elif "tsunami" in dtype_lower:
            return "badge-tsunami"
        else:
            return "badge-flood"

    countries = set(item["country"] for item in catalog_data)

    html = f"""<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1.0">
<title>PathFinder — Satellite Image Collection</title>
<link href="https://fonts.googleapis.com/css2?family=Inter:wght@300;400;600;700&family=JetBrains+Mono:wght@400;500&display=swap" rel="stylesheet">
<style>
  :root {{
    --bg: #0a0e17;
    --bg2: #0f1525;
    --card-bg: #111827;
    --card-border: #1e293b;
    --card-border-active: #06d6a0;
    --accent: #06d6a0;
    --accent2: #118ab2;
    --accent-glow: rgba(6, 214, 160, 0.15);
    --text: #e2e8f0;
    --text-muted: #94a3b8;
    --danger: #ef4444;
    --warning: #f59e0b;
  }}

  * {{ margin: 0; padding: 0; box-sizing: border-box; }}

  body {{
    font-family: 'Inter', system-ui, sans-serif;
    background: var(--bg);
    color: var(--text);
    min-height: 100vh;
  }}

  /* ── Header ── */
  .header {{
    text-align: center;
    padding: 3rem 1rem 2rem;
    background: linear-gradient(135deg, #0a0e17 0%, #1a1a2e 50%, #16213e 100%);
    border-bottom: 1px solid var(--card-border);
  }}
  .header h1 {{
    font-size: 2.5rem;
    font-weight: 700;
    background: linear-gradient(135deg, var(--accent), var(--accent2));
    -webkit-background-clip: text;
    -webkit-text-fill-color: transparent;
    margin-bottom: 0.5rem;
  }}
  .header p {{
    color: var(--text-muted);
    font-size: 1.1rem;
    max-width: 600px;
    margin: 0 auto;
  }}

  /* ── Stats Bar ── */
  .stats-bar {{
    display: flex;
    justify-content: center;
    gap: 2rem;
    padding: 1.5rem;
    background: rgba(17, 24, 39, 0.8);
    border-bottom: 1px solid var(--card-border);
    flex-wrap: wrap;
  }}
  .stat {{ text-align: center; }}
  .stat-value {{ font-size: 1.8rem; font-weight: 700; color: var(--accent); }}
  .stat-label {{ font-size: 0.75rem; color: var(--text-muted); text-transform: uppercase; letter-spacing: 0.1em; }}

  /* ── Search Section ── */
  .search-section {{
    background: var(--bg2);
    border-bottom: 1px solid var(--card-border);
    padding: 1.5rem 2rem;
  }}
  .search-container {{
    max-width: 900px;
    margin: 0 auto;
  }}
  .search-title {{
    font-size: 0.8rem;
    font-weight: 600;
    text-transform: uppercase;
    letter-spacing: 0.12em;
    color: var(--accent);
    margin-bottom: 0.75rem;
    display: flex;
    align-items: center;
    gap: 0.5rem;
  }}
  .search-row {{
    display: flex;
    gap: 0.75rem;
    align-items: stretch;
    flex-wrap: wrap;
  }}
  .search-input-group {{
    flex: 1;
    min-width: 200px;
    position: relative;
  }}
  .search-input-group label {{
    display: block;
    font-size: 0.7rem;
    color: var(--text-muted);
    margin-bottom: 0.3rem;
    text-transform: uppercase;
    letter-spacing: 0.08em;
  }}
  .search-input-group input {{
    width: 100%;
    padding: 0.7rem 1rem;
    background: var(--card-bg);
    border: 1px solid var(--card-border);
    border-radius: 10px;
    color: var(--text);
    font-family: 'JetBrains Mono', monospace;
    font-size: 0.95rem;
    outline: none;
    transition: border-color 0.2s, box-shadow 0.2s;
  }}
  .search-input-group input:focus {{
    border-color: var(--accent);
    box-shadow: 0 0 0 3px var(--accent-glow);
  }}
  .search-input-group input::placeholder {{
    color: #475569;
    font-family: 'Inter', sans-serif;
    font-size: 0.85rem;
  }}
  .search-btn {{
    padding: 0.7rem 1.5rem;
    background: linear-gradient(135deg, var(--accent), var(--accent2));
    border: none;
    border-radius: 10px;
    color: #0a0e17;
    font-weight: 600;
    font-size: 0.9rem;
    cursor: pointer;
    transition: transform 0.15s, box-shadow 0.2s;
    align-self: flex-end;
    white-space: nowrap;
  }}
  .search-btn:hover {{
    transform: translateY(-1px);
    box-shadow: 0 4px 20px var(--accent-glow);
  }}
  .search-btn:active {{ transform: translateY(0); }}

  .search-btn.reset-btn {{
    background: transparent;
    border: 1px solid var(--card-border);
    color: var(--text-muted);
  }}
  .search-btn.reset-btn:hover {{
    border-color: var(--text-muted);
    color: var(--text);
    box-shadow: none;
  }}

  .search-help {{
    margin-top: 0.75rem;
    font-size: 0.78rem;
    color: #475569;
    line-height: 1.6;
  }}
  .search-help code {{
    background: rgba(6, 214, 160, 0.08);
    color: var(--accent);
    padding: 0.1rem 0.4rem;
    border-radius: 4px;
    font-family: 'JetBrains Mono', monospace;
    font-size: 0.72rem;
  }}

  /* ── Results banner ── */
  .results-banner {{
    display: none;
    max-width: 1400px;
    margin: 1rem auto 0;
    padding: 0.75rem 2rem;
    background: linear-gradient(90deg, rgba(6,214,160,0.08), transparent);
    border-left: 3px solid var(--accent);
    border-radius: 0 8px 8px 0;
    font-size: 0.9rem;
    color: var(--text-muted);
    align-items: center;
    gap: 0.5rem;
  }}
  .results-banner.visible {{ display: flex; }}
  .results-banner strong {{ color: var(--accent); }}

  /* ── Grid ── */
  .grid {{
    display: grid;
    grid-template-columns: repeat(auto-fill, minmax(480px, 1fr));
    gap: 1.5rem;
    padding: 2rem;
    max-width: 1400px;
    margin: 0 auto;
  }}

  /* ── Card ── */
  .card {{
    background: var(--card-bg);
    border: 1px solid var(--card-border);
    border-radius: 16px;
    overflow: hidden;
    transition: transform 0.3s ease, box-shadow 0.3s ease, border-color 0.3s ease, opacity 0.3s ease;
    position: relative;
  }}
  .card:hover {{
    transform: translateY(-4px);
    box-shadow: 0 12px 40px rgba(6, 214, 160, 0.1);
  }}
  .card.closest {{
    border-color: var(--accent);
    box-shadow: 0 0 30px var(--accent-glow);
  }}
  .card.hidden {{ display: none; }}

  .card img {{
    width: 100%;
    height: 300px;
    object-fit: cover;
    display: block;
  }}
  .card-body {{ padding: 1.25rem; }}
  .card-title {{
    font-size: 1.2rem;
    font-weight: 600;
    margin-bottom: 0.25rem;
    display: flex;
    align-items: center;
    gap: 0.5rem;
    flex-wrap: wrap;
  }}

  .badge {{
    display: inline-block;
    padding: 0.2rem 0.6rem;
    border-radius: 999px;
    font-size: 0.7rem;
    font-weight: 600;
    text-transform: uppercase;
    letter-spacing: 0.05em;
  }}
  .badge-hurricane  {{ background: rgba(96, 165, 250, 0.2); color: #60a5fa; }}
  .badge-earthquake {{ background: rgba(251, 191, 36, 0.2); color: #fbbf24; }}
  .badge-wildfire   {{ background: rgba(239, 68, 68, 0.2);  color: #ef4444; }}
  .badge-volcano    {{ background: rgba(249, 115, 22, 0.2); color: #f97316; }}
  .badge-flood      {{ background: rgba(56, 189, 248, 0.2); color: #38bdf8; }}
  .badge-tsunami    {{ background: rgba(139, 92, 246, 0.2); color: #8b5cf6; }}

  .badge-distance {{
    background: rgba(6, 214, 160, 0.15);
    color: var(--accent);
    font-family: 'JetBrains Mono', monospace;
    font-size: 0.68rem;
    padding: 0.2rem 0.5rem;
    border-radius: 999px;
    display: none;
  }}
  .badge-distance.visible {{ display: inline-block; }}

  .badge-closest {{
    background: var(--accent);
    color: #0a0e17;
    font-weight: 700;
    animation: pulse-glow 2s ease-in-out infinite;
  }}

  @keyframes pulse-glow {{
    0%, 100% {{ box-shadow: 0 0 0 0 var(--accent-glow); }}
    50% {{ box-shadow: 0 0 12px 4px var(--accent-glow); }}
  }}

  .card-location {{
    color: var(--text-muted);
    font-size: 0.9rem;
    margin: 0.25rem 0 0.5rem;
  }}
  .card-desc {{
    font-size: 0.85rem;
    color: var(--text-muted);
    line-height: 1.5;
    margin-bottom: 1rem;
  }}
  .card-meta {{
    display: flex;
    justify-content: space-between;
    font-size: 0.78rem;
    color: var(--text-muted);
    border-top: 1px solid var(--card-border);
    padding-top: 0.75rem;
    flex-wrap: wrap;
    gap: 0.5rem;
  }}
  .card-meta span {{
    display: flex;
    align-items: center;
    gap: 0.3rem;
  }}
  .gps {{
    font-family: 'JetBrains Mono', monospace;
    font-size: 0.75rem;
    color: var(--accent);
    background: rgba(6, 214, 160, 0.1);
    padding: 0.15rem 0.5rem;
    border-radius: 6px;
    cursor: pointer;
    transition: background 0.2s;
  }}
  .gps:hover {{
    background: rgba(6, 214, 160, 0.25);
  }}

  .footer {{
    text-align: center;
    padding: 2rem;
    color: var(--text-muted);
    font-size: 0.8rem;
    border-top: 1px solid var(--card-border);
  }}

  /* ── No results ── */
  .no-results {{
    display: none;
    text-align: center;
    padding: 4rem 2rem;
    color: var(--text-muted);
    grid-column: 1 / -1;
  }}
  .no-results.visible {{ display: block; }}
  .no-results .icon {{ font-size: 3rem; margin-bottom: 1rem; }}
  .no-results h3 {{ font-size: 1.3rem; color: var(--text); margin-bottom: 0.5rem; }}
</style>
</head>
<body>

<div class="header">
  <h1>🛰️ PathFinder Satellite Collection</h1>
  <p>Real-world satellite imagery from 10 major disaster events, geo-located and cataloged for AI-driven damage assessment.</p>
</div>

<div class="stats-bar">
  <div class="stat"><div class="stat-value">{len(catalog_data)}</div><div class="stat-label">Disaster Events</div></div>
  <div class="stat"><div class="stat-value">{len(countries)}</div><div class="stat-label">Countries</div></div>
  <div class="stat"><div class="stat-value">678</div><div class="stat-label">Satellite Images</div></div>
  <div class="stat"><div class="stat-value">5</div><div class="stat-label">Disaster Types</div></div>
</div>

<div class="search-section">
  <div class="search-container">
    <div class="search-title">🔍 Search by GPS Coordinates or Location</div>
    <div class="search-row">
      <div class="search-input-group" style="flex: 2;">
        <label for="search-input">GPS Coordinates or Location Name</label>
        <input type="text" id="search-input" placeholder="e.g.  30.15, -85.66   or   Houston   or   wildfire" autocomplete="off">
      </div>
      <div class="search-input-group" style="flex: 0.8; min-width: 120px;">
        <label for="search-radius">Max Radius (km)</label>
        <input type="number" id="search-radius" placeholder="∞" min="0" step="100" value="">
      </div>
      <button class="search-btn" onclick="doSearch()" id="search-btn">🛰️ Search</button>
      <button class="search-btn reset-btn" onclick="resetSearch()" id="reset-btn">✕ Reset</button>
    </div>
    <div class="search-help">
      <strong>GPS search:</strong> <code>30.15, -85.66</code> or <code>14.47 -90.88</code> &nbsp;·&nbsp;
      <strong>Text search:</strong> <code>Houston</code> <code>wildfire</code> <code>Haiti</code> <code>tsunami</code> &nbsp;·&nbsp;
      <strong>Tip:</strong> Click any GPS badge on a card to search from that location
    </div>
  </div>
</div>

<div class="results-banner" id="results-banner"></div>

<div class="grid" id="card-grid">
  <div class="no-results" id="no-results">
    <div class="icon">🛰️</div>
    <h3>No disasters found in this area</h3>
    <p>Try a wider search radius or different coordinates.</p>
  </div>
</div>

<div class="footer">
  PathFinder — AI-Powered Disaster Response Platform &nbsp;|&nbsp; Satellite data from xBD (xView2) Dataset
</div>

<script>
// ─── Disaster Data ────────────────────────────────────────────────
const DISASTERS = {items_json};

// ─── Badge class mapping ──────────────────────────────────────────
function getBadgeClass(dtype) {{
  const d = dtype.toLowerCase();
  if (d.includes('hurricane')) return 'badge-hurricane';
  if (d.includes('earthquake')) return 'badge-earthquake';
  if (d.includes('wildfire') || d.includes('fire')) return 'badge-wildfire';
  if (d.includes('volcano')) return 'badge-volcano';
  if (d.includes('tsunami')) return 'badge-tsunami';
  return 'badge-flood';
}}

// ─── Haversine distance (km) ──────────────────────────────────────
function haversine(lat1, lon1, lat2, lon2) {{
  const R = 6371;
  const dLat = (lat2 - lat1) * Math.PI / 180;
  const dLon = (lon2 - lon1) * Math.PI / 180;
  const a = Math.sin(dLat/2) * Math.sin(dLat/2) +
            Math.cos(lat1 * Math.PI / 180) * Math.cos(lat2 * Math.PI / 180) *
            Math.sin(dLon/2) * Math.sin(dLon/2);
  return R * 2 * Math.atan2(Math.sqrt(a), Math.sqrt(1 - a));
}}

// ─── Format distance ─────────────────────────────────────────────
function formatDist(km) {{
  if (km < 1) return Math.round(km * 1000) + ' m';
  if (km < 100) return km.toFixed(1) + ' km';
  return Math.round(km).toLocaleString() + ' km';
}}

// ─── Parse GPS from text ─────────────────────────────────────────
function parseGPS(text) {{
  // Matches: "30.15, -85.66" or "30.15 -85.66" or "(30.15, -85.66)"
  const cleaned = text.replace(/[()]/g, '').trim();
  const patterns = [
    /^\\s*(-?\\d+\\.?\\d*)\\s*[,\\s]\\s*(-?\\d+\\.?\\d*)\\s*$/,
  ];
  for (const re of patterns) {{
    const m = cleaned.match(re);
    if (m) {{
      const lat = parseFloat(m[1]);
      const lng = parseFloat(m[2]);
      if (lat >= -90 && lat <= 90 && lng >= -180 && lng <= 180) {{
        return {{ lat, lng }};
      }}
    }}
  }}
  return null;
}}

// ─── Build a card HTML ───────────────────────────────────────────
function buildCard(item, distance, isClosest) {{
  const badgeCls = getBadgeClass(item.disaster_type);
  const distBadge = distance !== null
    ? `<span class="badge badge-distance visible ${{isClosest ? 'badge-closest' : ''}}">${{isClosest ? '📍 CLOSEST · ' : ''}}${{formatDist(distance)}}</span>`
    : `<span class="badge badge-distance"></span>`;

  return `
  <div class="card ${{isClosest ? 'closest' : ''}}" data-key="${{item.disaster_key}}" data-lat="${{item.lat}}" data-lng="${{item.lng}}">
    <img src="${{item.annotated_image}}" alt="${{item.name}}" loading="lazy">
    <div class="card-body">
      <div class="card-title">
        <span>${{item.emoji}}</span>
        <span>${{item.name}}</span>
        <span class="badge ${{badgeCls}}">${{item.disaster_type}}</span>
        ${{distBadge}}
      </div>
      <div class="card-location">📍 ${{item.location}} &nbsp;|&nbsp; 📅 ${{item.date}}</div>
      <div class="card-desc">${{item.description}}</div>
      <div class="card-meta">
        <span class="gps" onclick="searchFromGPS(${{item.lat}}, ${{item.lng}})" title="Click to search from this location">(${{item.lat.toFixed(4)}}, ${{item.lng.toFixed(4)}})</span>
        <span>🌍 ${{item.country}}</span>
        <span>📸 ${{item.source_file}}</span>
      </div>
    </div>
  </div>`;
}}

// ─── Render all cards ────────────────────────────────────────────
function renderCards(items, distances, closestIdx) {{
  const grid = document.getElementById('card-grid');
  const noResults = document.getElementById('no-results');

  // Keep the no-results element reference
  let html = '';
  items.forEach((item, i) => {{
    const dist = distances ? distances[i] : null;
    const isClosest = (closestIdx !== null && i === 0);
    html += buildCard(item, dist, isClosest);
  }});

  if (items.length === 0) {{
    grid.innerHTML = '';
    grid.appendChild(createNoResults());
  }} else {{
    grid.innerHTML = html;
  }}
}}

function createNoResults() {{
  const div = document.createElement('div');
  div.className = 'no-results visible';
  div.innerHTML = '<div class="icon">🛰️</div><h3>No disasters found in this area</h3><p>Try a wider search radius or different coordinates.</p>';
  return div;
}}

// ─── Search logic ────────────────────────────────────────────────
function doSearch() {{
  const query = document.getElementById('search-input').value.trim();
  const radiusInput = document.getElementById('search-radius').value;
  const maxRadius = radiusInput ? parseFloat(radiusInput) : Infinity;
  const banner = document.getElementById('results-banner');

  if (!query) {{
    resetSearch();
    return;
  }}

  // Try GPS parse
  const gps = parseGPS(query);

  if (gps) {{
    // GPS-based search: sort by distance
    const withDist = DISASTERS.map(item => ({{
      item,
      dist: haversine(gps.lat, gps.lng, item.lat, item.lng)
    }}));

    withDist.sort((a, b) => a.dist - b.dist);

    const filtered = maxRadius < Infinity
      ? withDist.filter(d => d.dist <= maxRadius)
      : withDist;

    const items = filtered.map(d => d.item);
    const distances = filtered.map(d => d.dist);

    renderCards(items, distances, items.length > 0 ? 0 : null);

    // Update banner
    const closestName = items.length > 0 ? items[0].name : 'None';
    banner.innerHTML = `🛰️ Searching from <strong>(${{gps.lat.toFixed(4)}}, ${{gps.lng.toFixed(4)}})</strong> · Found <strong>${{items.length}}</strong> disaster(s)${{maxRadius < Infinity ? ` within ${{maxRadius}} km` : ''}} · Closest: <strong>${{closestName}}</strong>`;
    banner.classList.add('visible');

  }} else {{
    // Text-based search
    const q = query.toLowerCase();
    const matches = DISASTERS.filter(item =>
      item.name.toLowerCase().includes(q) ||
      item.location.toLowerCase().includes(q) ||
      item.country.toLowerCase().includes(q) ||
      item.disaster_type.toLowerCase().includes(q) ||
      item.description.toLowerCase().includes(q) ||
      item.disaster_key.toLowerCase().includes(q)
    );

    renderCards(matches, null, null);

    banner.innerHTML = `🔍 Text search: "<strong>${{query}}</strong>" · Found <strong>${{matches.length}}</strong> disaster(s)`;
    banner.classList.add('visible');
  }}
}}

function resetSearch() {{
  document.getElementById('search-input').value = '';
  document.getElementById('search-radius').value = '';
  document.getElementById('results-banner').classList.remove('visible');
  renderCards(DISASTERS, null, null);
}}

function searchFromGPS(lat, lng) {{
  document.getElementById('search-input').value = `${{lat}}, ${{lng}}`;
  doSearch();
  window.scrollTo({{ top: 0, behavior: 'smooth' }});
}}

// ─── Keyboard shortcut ──────────────────────────────────────────
document.getElementById('search-input').addEventListener('keydown', (e) => {{
  if (e.key === 'Enter') doSearch();
  if (e.key === 'Escape') resetSearch();
}});

// ─── Initial render ─────────────────────────────────────────────
renderCards(DISASTERS, null, null);
</script>

</body>
</html>"""

    gallery_path = output_dir / "gallery.html"
    gallery_path.write_text(html)
    return gallery_path


# ─── Main ────────────────────────────────────────────────────────────────────

def main():
    parser = argparse.ArgumentParser(description="PathFinder — Satellite Collection Demo")
    parser.add_argument("--detect", action="store_true", help="Run YOLO damage detection on each image")
    parser.add_argument("--html", action="store_true", help="Generate HTML gallery")
    parser.add_argument("--samples", type=int, default=1, help="Number of samples per disaster")
    parser.add_argument("--conf", type=float, default=0.3, help="YOLO confidence threshold")
    parser.add_argument("--damage-only", action="store_true",
                        help="Use pre-scanned best-damaged images (most destroyed/major first)")
    args = parser.parse_args()

    print(f"""
╔════════════════════════════════════════════════════════════════╗
║    🛰️  PathFinder — Satellite Image Collection & Locator  🛰️    ║
╚════════════════════════════════════════════════════════════════╝
""")

    img_dir = get_image_dir()
    output_dir = Path(__file__).resolve().parent / "output"
    output_dir.mkdir(exist_ok=True)

    if not img_dir.exists():
        print(f"  ✗ Image directory not found: {img_dir}")
        sys.exit(1)

    # ── Step 1: Collect Samples ──────────────────────────────────────────
    print("━" * 64)
    print("  STEP 1 │ Collecting Satellite Images")
    print("━" * 64)

    samples = collect_samples(img_dir, max_per_disaster=args.samples,
                              damage_only=args.damage_only)
    total = sum(len(v) for v in samples.values())
    mode_tag = "(damage-priority mode)" if args.damage_only else ""
    print(f"  ✓ Found {total} sample images across {len(samples)} disasters {mode_tag}\n")

    # ── Step 2: Catalog & Annotate ───────────────────────────────────────
    print("━" * 64)
    print("  STEP 2 │ Cataloging Locations & Annotating Images")
    print("━" * 64)

    catalog_data = []

    for disaster_key, images in sorted(samples.items()):
        info = DISASTER_CATALOG[disaster_key]

        print(f"\n  {info['emoji']}  {info['name']}")
        print(f"     📍 {info['location']}")
        print(f"     🌐 GPS: ({info['lat']:.4f}, {info['lng']:.4f})")
        print(f"     🗓  {info['date']}")
        print(f"     💥 {info['disaster_type']}")

        for img_path in images:
            img = cv2.imread(str(img_path))
            if img is None:
                print(f"     ⚠ Could not read {img_path.name}")
                continue

            h, w = img.shape[:2]
            print(f"     📸 {img_path.name} ({w}×{h})")

            # Annotate with location info
            annotated = annotate_image(img, info, img_path.name)
            ann_filename = f"{disaster_key}_annotated.png"
            ann_path = output_dir / ann_filename
            cv2.imwrite(str(ann_path), annotated)

            entry = {
                **info,
                "source_file": img_path.name,
                "annotated_image": ann_filename,
                "image_size": f"{w}x{h}",
                "disaster_key": disaster_key,
            }

            catalog_data.append(entry)

    print(f"\n  ✓ Annotated {len(catalog_data)} images → demo/output/\n")

    # ── Step 3: Optional YOLO Detection ──────────────────────────────────
    if args.detect:
        print("━" * 64)
        print("  STEP 3 │ Running YOLO Damage Detection")
        print("━" * 64)

        model_path = Path(__file__).resolve().parent.parent / "saferoute" / "ai" / "runs" / "pathfinder-damage" / "weights" / "best.pt"
        if not model_path.exists():
            print(f"  ✗ Model not found: {model_path}")
        else:
            from ultralytics import YOLO

            DAMAGE_CLASSES = {
                0: {"name": "no-damage",    "color": (34, 197, 94),   "hex": "#22c55e"},
                1: {"name": "minor-damage", "color": (234, 179, 8),   "hex": "#eab308"},
                2: {"name": "major-damage", "color": (249, 115, 22),  "hex": "#f97316"},
                3: {"name": "destroyed",    "color": (239, 68, 68),   "hex": "#ef4444"},
            }

            model = YOLO(str(model_path))
            print(f"  ✓ Model loaded: {model_path.name}\n")

            for entry in catalog_data:
                src_path = img_dir / entry["source_file"]
                img = cv2.imread(str(src_path))
                if img is None:
                    continue

                results = model.predict(img, conf=args.conf, verbose=False)
                n_detections = 0
                class_counts = {}

                if results[0].masks is not None:
                    n_detections = len(results[0].masks.xy)
                    for i in range(n_detections):
                        cls_id = int(results[0].boxes.cls[i])
                        cls_name = DAMAGE_CLASSES.get(cls_id, DAMAGE_CLASSES[0])["name"]
                        class_counts[cls_name] = class_counts.get(cls_name, 0) + 1

                        # Draw mask on image
                        pts = results[0].masks.xy[i].astype(np.int32)
                        color_bgr = DAMAGE_CLASSES.get(cls_id, DAMAGE_CLASSES[0])["color"]
                        color_bgr = (color_bgr[2], color_bgr[1], color_bgr[0])
                        cv2.fillPoly(img, [pts], color_bgr)

                    blended = cv2.addWeighted(img, 0.35, cv2.imread(str(src_path)), 0.65, 0)
                    det_filename = f"{entry['disaster_key']}_detected.png"
                    cv2.imwrite(str(output_dir / det_filename), blended)
                    entry["detected_image"] = det_filename

                entry["detections"] = n_detections
                entry["class_breakdown"] = class_counts

                status = "🔴" if class_counts.get("destroyed", 0) > 0 else "🟠" if class_counts.get("major-damage", 0) > 0 else "🟡" if n_detections > 0 else "🟢"
                print(f"  {status} {entry['name']}: {n_detections} detections {dict(class_counts)}")

            print()

            # ── Damage Summary Table ─────────────────────────────────────
            detected = [e for e in catalog_data if e.get("detections", 0) > 0]
            detected.sort(key=lambda e: (
                e.get("class_breakdown", {}).get("destroyed", 0),
                e.get("class_breakdown", {}).get("major-damage", 0),
                e.get("class_breakdown", {}).get("minor-damage", 0),
            ), reverse=True)

            print(f"  ┌{'─' * 72}┐")
            print(f"  │{'🔥  DAMAGE SUMMARY — Ranked by Severity':^72}│")
            print(f"  ├{'─' * 14}┬{'─' * 8}┬{'─' * 8}┬{'─' * 8}┬{'─' * 8}┬{'─' * 22}┤")
            print(f"  │{'Disaster':<14}│{'Destr':>8}│{'Major':>8}│{'Minor':>8}│{'NoDmg':>8}│{'Location':<22}│")
            print(f"  ├{'─' * 14}┼{'─' * 8}┼{'─' * 8}┼{'─' * 8}┼{'─' * 8}┼{'─' * 22}┤")
            for e in detected:
                cb = e.get("class_breakdown", {})
                dest  = cb.get("destroyed",   0)
                major = cb.get("major-damage", 0)
                minor = cb.get("minor-damage", 0)
                nodmg = cb.get("no-damage",    0)
                key   = e["disaster_key"][:14]
                loc   = e["location"][:22]
                sev   = "🔴" if dest > 0 else "🟠" if major > 0 else "🟡"
                print(f"  │{sev} {key:<12}│{dest:>8}│{major:>8}│{minor:>8}│{nodmg:>8}│{loc:<22}│")
            print(f"  └{'─' * 14}┴{'─' * 8}┴{'─' * 8}┴{'─' * 8}┴{'─' * 8}┴{'─' * 22}┘")
            print()

    # ── Step 4: Save Catalog JSON ────────────────────────────────────────
    print("━" * 64)
    print("  STEP 4 │ Saving Location Catalog")
    print("━" * 64)

    catalog_path = output_dir / "satellite_catalog.json"
    with open(catalog_path, "w") as f:
        json.dump(catalog_data, f, indent=2)
    print(f"  ✓ Catalog: {catalog_path}")

    # ── Step 5: HTML Gallery ─────────────────────────────────────────────
    if args.html:
        print()
        print("━" * 64)
        print("  STEP 5 │ Generating HTML Gallery")
        print("━" * 64)

        gallery_path = generate_html_gallery(catalog_data, output_dir)
        print(f"  ✓ Gallery: {gallery_path}")

    # ── Summary ──────────────────────────────────────────────────────────
    print(f"""
{'═' * 64}
  📊  SATELLITE COLLECTION SUMMARY
{'═' * 64}""")

    countries = set(e["country"] for e in catalog_data)
    types = set(e["disaster_type"] for e in catalog_data)

    print(f"  Disasters cataloged:   {len(catalog_data)}")
    print(f"  Countries:             {len(countries)} ({', '.join(sorted(countries))})")
    print(f"  Disaster types:        {len(types)}")
    print()
    print(f"  ┌{'─' * 58}┐")
    print(f"  │{'DISASTER LOCATIONS':^58}│")
    print(f"  ├{'─' * 58}┤")

    for e in catalog_data:
        name = f"{e['emoji']} {e['name']}"
        gps = f"({e['lat']:.4f}, {e['lng']:.4f})"
        cb = e.get("class_breakdown", {})
        dest  = cb.get("destroyed",   0)
        major = cb.get("major-damage", 0)
        minor = cb.get("minor-damage", 0)
        dmg_tag = f"🔴×{dest}" if dest else f"🟠×{major}" if major else f"🟡×{minor}" if minor else "🟢 clean"
        print(f"  │  {name:<32} {gps:>22}  {dmg_tag}  │")

    print(f"  └{'─' * 58}┘")
    print()
    print(f"  Output directory: {output_dir}")
    print(f"  Files generated:")
    for f in sorted(output_dir.iterdir()):
        size_kb = f.stat().st_size / 1024
        print(f"     • {f.name:<40} ({size_kb:.0f} KB)")

    print(f"""
{'═' * 64}
  ✅ Demo complete!
{'═' * 64}
""")


if __name__ == "__main__":
    main()
