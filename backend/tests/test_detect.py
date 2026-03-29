"""Tests for POST /detect stub endpoint."""

import io

from fastapi.testclient import TestClient

from app.main import app

client = TestClient(app)


def test_detect_returns_detections():
    """POST /detect with a fake image returns valid DetectionResponse."""
    # Create a minimal PNG file (1x1 pixel)
    fake_image = io.BytesIO(
        b"\x89PNG\r\n\x1a\n\x00\x00\x00\rIHDR\x00\x00\x00\x01"
        b"\x00\x00\x00\x01\x08\x02\x00\x00\x00\x90wS\xde\x00"
        b"\x00\x00\x0cIDATx\x9cc\xf8\x0f\x00\x00\x01\x01\x00"
        b"\x05\x18\xd8N\x00\x00\x00\x00IEND\xaeB`\x82"
    )
    resp = client.post(
        "/detect",
        files={"file": ("test.png", fake_image, "image/png")},
    )
    assert resp.status_code == 200

    data = resp.json()
    assert "detections" in data
    assert "image_size" in data
    assert len(data["detections"]) > 0

    # Each detection should have the expected fields
    det = data["detections"][0]
    assert "mask" in det
    assert "class_name" in det
    assert "class_id" in det
    assert "danger_weight" in det
    assert "confidence" in det
    assert isinstance(det["mask"], list)
    assert len(det["mask"]) >= 3  # at least a triangle


def test_detect_image_size():
    """Stub returns 1024x1024 image size."""
    fake_image = io.BytesIO(b"fake image data")
    resp = client.post(
        "/detect",
        files={"file": ("test.png", fake_image, "image/png")},
    )
    data = resp.json()
    assert data["image_size"]["width"] == 1024
    assert data["image_size"]["height"] == 1024


def test_detect_damage_classes():
    """Stub includes multiple damage severity classes."""
    fake_image = io.BytesIO(b"fake image data")
    resp = client.post(
        "/detect",
        files={"file": ("test.png", fake_image, "image/png")},
    )
    data = resp.json()
    class_names = {d["class_name"] for d in data["detections"]}
    # Stub should have at least 2 different damage classes
    assert len(class_names) >= 2
