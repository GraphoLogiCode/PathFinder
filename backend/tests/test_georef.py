"""Tests for POST /georef stub endpoint."""

from fastapi.testclient import TestClient

from app.main import app

client = TestClient(app)


def _make_georef_payload(lat: float = 30.11, lng: float = -85.65):
    """Build a valid GeoRefRequest payload."""
    return {
        "detections": [
            {
                "mask": [[100, 100], [200, 100], [200, 200], [100, 200], [100, 100]],
                "class_name": "destroyed",
                "class_id": 3,
                "danger_weight": 10,
                "confidence": 0.9,
            }
        ],
        "anchor": {"lat": lat, "lng": lng},
        "scale": 2.07,
        "image_center_px": [512, 512],
    }


def test_georef_returns_geojson():
    """POST /georef returns a valid GeoJSON FeatureCollection."""
    resp = client.post("/georef", json=_make_georef_payload())
    assert resp.status_code == 200

    data = resp.json()
    assert data["type"] == "FeatureCollection"
    assert "features" in data
    assert len(data["features"]) > 0


def test_georef_features_have_properties():
    """Each feature should have severity, color, danger_weight."""
    resp = client.post("/georef", json=_make_georef_payload())
    data = resp.json()

    for feature in data["features"]:
        assert feature["type"] == "Feature"
        assert "geometry" in feature
        assert feature["geometry"]["type"] == "Polygon"
        props = feature["properties"]
        assert "severity" in props
        assert "color" in props
        assert "danger_weight" in props


def test_georef_coordinates_near_anchor():
    """Stub polygons should be near the provided anchor point."""
    anchor_lat, anchor_lng = 30.11, -85.65
    resp = client.post(
        "/georef",
        json=_make_georef_payload(lat=anchor_lat, lng=anchor_lng),
    )
    data = resp.json()

    for feature in data["features"]:
        coords = feature["geometry"]["coordinates"][0]
        for lng, lat in coords:
            assert abs(lat - anchor_lat) < 0.01
            assert abs(lng - anchor_lng) < 0.01
