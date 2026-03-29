"""
PathFinder — POST /analyze

GPT-powered rescue plan generation. Sends danger zone data and route
context to GPT-4o-mini, returns a structured JSON rescue plan.
"""

from __future__ import annotations

import json

from fastapi import APIRouter, HTTPException
from openai import AsyncOpenAI

from app.config import settings
from app.models import AnalyzeRequest, AnalyzeResponse

router = APIRouter()


def build_system_prompt() -> str:
    return """You are a disaster response planning AI assistant for NGO field operations.
You analyze satellite-detected damage zones and computed safe routes to generate
actionable rescue plans.

You must respond with a JSON object containing these exact fields:
{
  "situation_summary": "2-3 sentence overview of the disaster area",
  "risk_assessment": [
    {
      "zone": "description of area",
      "risk_type": "structural_collapse | flood | fire | aftershock | chemical",
      "severity": "critical | high | moderate | low",
      "recommendation": "what to do about this zone"
    }
  ],
  "evacuation_plan": {
    "priority_zones": ["list of areas to evacuate first"],
    "assembly_points": ["suggested safe gathering locations"],
    "estimated_affected": "rough population estimate",
    "evacuation_routes": ["description of recommended evacuation corridors"]
  },
  "resource_allocation": [
    {
      "resource": "water | food | medical | shelter | search_rescue",
      "priority": "immediate | within_6h | within_24h",
      "quantity_estimate": "rough estimate",
      "deployment_location": "where to deploy"
    }
  ],
  "immediate_actions": [
    {
      "action": "what to do",
      "priority": 1,
      "responsible_team": "search_rescue | medical | logistics | comms",
      "time_window": "how soon"
    }
  ],
  "route_analysis": {
    "primary_route_reasoning": "why this route is safest",
    "alternative_considerations": "other route options and tradeoffs",
    "hazards_along_route": ["list of hazards near but not on the route"]
  }
}

Be specific, actionable, and prioritize life safety. Use the damage severity data
(no-damage, minor-damage, major-damage, destroyed) to inform your recommendations.
Always respond with valid JSON only — no markdown, no extra text."""


def build_user_prompt(request: AnalyzeRequest) -> str:
    # Summarize danger zones
    zone_summary = []
    zone_details = []
    if request.danger_zones and request.danger_zones.get("features"):
        severity_counts: dict[str, int] = {}
        for feat in request.danger_zones["features"]:
            sev = feat["properties"].get("severity", "unknown")
            severity_counts[sev] = severity_counts.get(sev, 0) + 1
            coords = feat["geometry"].get("coordinates", [[]])
            if coords and coords[0]:
                flat = coords[0]
                avg_lng = sum(c[0] for c in flat) / len(flat)
                avg_lat = sum(c[1] for c in flat) / len(flat)
                zone_details.append(
                    f"  - {sev} zone at ({avg_lat:.4f}, {avg_lng:.4f}), "
                    f"weight={feat['properties'].get('danger_weight', '?')}"
                )
        zone_summary = [
            f"{count}x {sev}" for sev, count in severity_counts.items()
        ]

    prompt = f"""Analyze this disaster area and generate a rescue plan.

DISASTER CONTEXT:
- Location: {request.disaster_location or "Unknown"}
- Disaster type: {request.disaster_type or "Unknown"}
- Total danger zones detected: {len(request.danger_zones.get('features', [])) if request.danger_zones else 0}
- Damage breakdown: {', '.join(zone_summary) if zone_summary else 'No data'}
"""

    if zone_details:
        prompt += "\nDANGER ZONE LOCATIONS (top 20):\n"
        prompt += "\n".join(zone_details[:20])
        if len(zone_details) > 20:
            prompt += f"\n  ... and {len(zone_details) - 20} more zones"
        prompt += "\n"

    if request.route_summary:
        prompt += f"""
COMPUTED SAFE ROUTE SUMMARY:
- Distance: {request.route_summary.get('distance_km', 'N/A')} km
- Travel time: {request.route_summary.get('time_minutes', 'N/A')} minutes
- Danger zones avoided: {request.route_summary.get('danger_zones_avoided', 0)}
- Transport mode: {request.transport_mode or 'pedestrian'}
"""

    if request.maneuvers:
        prompt += "\nTURN-BY-TURN ROUTE DIRECTIONS:\n"
        for i, m in enumerate(request.maneuvers[:30]):
            instruction = m.get("instruction", "Continue")
            distance = m.get("distance", 0)
            street = m.get("street_name", "")
            prompt += f"  {i+1}. {instruction}"
            if street:
                prompt += f" on {street}"
            prompt += f" ({distance} km)\n"

    if request.start and request.end:
        prompt += f"""
ROUTE ENDPOINTS:
- Start: ({request.start.lat}, {request.start.lng})
- Destination: ({request.end.lat}, {request.end.lng})
"""

    prompt += """
Generate a comprehensive rescue plan. Respond with valid JSON only."""

    return prompt


@router.post("/analyze", response_model=AnalyzeResponse)
async def analyze_area(request: AnalyzeRequest):
    """
    Send danger zone + route data to GPT-4o-mini for rescue plan generation.
    Returns a structured plan covering evacuation, resources, risk assessment.
    """
    if not settings.openai_api_key:
        raise HTTPException(503, "OpenAI API key not configured")

    client = AsyncOpenAI(api_key=settings.openai_api_key)

    try:
        response = await client.chat.completions.create(
            model="gpt-4o-mini",
            messages=[
                {"role": "system", "content": build_system_prompt()},
                {"role": "user", "content": build_user_prompt(request)},
            ],
            response_format={"type": "json_object"},
            temperature=0.3,
            max_tokens=2000,
        )

        plan = json.loads(response.choices[0].message.content)

        return AnalyzeResponse(
            plan=plan,
            model="gpt-4o-mini",
            tokens_used=response.usage.total_tokens if response.usage else 0,
        )

    except Exception as e:
        raise HTTPException(502, f"AI analysis failed: {str(e)}")
