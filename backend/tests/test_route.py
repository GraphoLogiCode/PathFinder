"""Tests for POST /route stub endpoint."""

from fastapi.testclient import TestClient

from app.main import app

client = TestClient(app)


def _make_route_payload():
    """Build a valid RouteRequest payload."""
    return {
        "start": {"lat": 30.110, "lng": -85.650},
        "end": {"lat": 30.120, "lng": -85.640},
        "danger_zones": {
            "type": "FeatureCollection",
            "features": [
                {
                    "type": "Feature",
                    "geometry": {
                        "type": "Polygon",
                        "coordinates": [
                            [
                                [-85.645, 30.115],
                                [-85.645, 30.117],
                                [-85.643, 30.117],
                                [-85.643, 30.115],
                                [-85.645, 30.115],
                            ]
                        ],
                    },
                    "properties": {"severity": "destroyed"},
                }
            ],
        },
        "mode": "pedestrian",
    }


def test_route_returns_valid_response():
    """POST /route returns route, summary, and maneuvers."""
    resp = client.post("/route", json=_make_route_payload())
    assert resp.status_code == 200

    data = resp.json()
    assert "route" in data
    assert "summary" in data
    assert "maneuvers" in data


def test_route_geojson_linestring():
    """Route should be a GeoJSON Feature with LineString geometry."""
    resp = client.post("/route", json=_make_route_payload())
    data = resp.json()

    route = data["route"]
    assert route["type"] == "Feature"
    assert route["geometry"]["type"] == "LineString"
    coords = route["geometry"]["coordinates"]
    assert len(coords) >= 2  # at least start and end


def test_route_summary_fields():
    """Summary should have distance, time, mode, and danger zones count."""
    resp = client.post("/route", json=_make_route_payload())
    data = resp.json()

    summary = data["summary"]
    assert "distance_km" in summary
    assert "time_minutes" in summary
    assert "mode" in summary
    assert summary["mode"] == "pedestrian"
    assert "danger_zones_avoided" in summary
    assert summary["danger_zones_avoided"] == 1  # we sent 1 danger zone


def test_route_without_danger_zones():
    """Route should work without danger zones."""
    payload = {
        "start": {"lat": 30.110, "lng": -85.650},
        "end": {"lat": 30.120, "lng": -85.640},
    }
    resp = client.post("/route", json=payload)
    assert resp.status_code == 200

    data = resp.json()
    assert data["summary"]["danger_zones_avoided"] == 0
