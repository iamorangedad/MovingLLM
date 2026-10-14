from fastapi.testclient import TestClient

from api_server import create_app
from src.agent import MovingLLMAgent
from src.config import get_settings
from src.models import Dimensions, FurnitureItem, FurnitureType


def _drawer():
    return FurnitureItem(
        name="抽屉",
        furniture_type=FurnitureType.DRAWER,
        dimensions=Dimensions(length=20, width=20, height=20),
        weight=2,
        quantity=1,
    )


class RecordingProvider:
    def __init__(self):
        self.payloads = []
        self.image_calls = 0

    def analyze_image(self, image_path):
        self.image_calls += 1
        with open(image_path, "rb") as handle:
            self.payloads.append(handle.read())
        return [_drawer()]

    def recommend(self, plan):
        return "先核对尺寸"


class BlockingProvider(RecordingProvider):
    def analyze_image(self, image_path):
        raise AssertionError("重算不应读取图片")


def _client(provider):
    return TestClient(create_app(MovingLLMAgent(provider=provider)))


def test_analyze_persists_upload_before_planning(monkeypatch):
    monkeypatch.setattr(get_settings().image, "max_bytes", 1024)
    provider = RecordingProvider()
    payload = b"\xff\xd8fake-jpeg"
    response = _client(provider).post(
        "/analyze",
        files=[("files", ("room.jpg", payload, "image/jpeg"))],
    )
    assert response.status_code == 200
    body = response.json()
    assert provider.payloads == [payload]
    assert body["furniture_items"][0]["name"] == "抽屉"
    assert body["dimensions_confirmed"] is False
    assert body["loading_order"]
    assert body["cargo_layout"]["placements"]
    assert body["cargo_layout"]["axis_note"]


def test_analyze_rejects_empty_non_image_and_oversize_files(monkeypatch):
    monkeypatch.setattr(get_settings().image, "max_bytes", 4)
    client = _client(RecordingProvider())
    empty = client.post("/analyze", files=[("files", ("a.jpg", b"", "image/jpeg"))])
    text = client.post("/analyze", files=[("files", ("a.txt", b"hello", "text/plain"))])
    large = client.post(
        "/analyze", files=[("files", ("a.jpg", b"12345", "image/jpeg"))]
    )
    assert empty.status_code == 400
    assert text.status_code == 400
    assert large.status_code == 413


def test_recommend_response_is_serializable():
    response = _client(RecordingProvider()).post(
        "/recommend",
        files=[("files", ("room.jpg", b"img", "image/jpeg"))],
    )
    assert response.status_code == 200
    assert response.json()["recommendations"] == "先核对尺寸"


def test_recalculate_skips_vision_and_marks_dimensions_confirmed():
    provider = BlockingProvider()
    item = _drawer().model_dump()
    response = _client(provider).post(
        "/recalculate",
        json={
            "furniture_items": [item],
            "context": {"distance_km": 12, "origin_floor": 3, "origin_has_elevator": False},
        },
    )
    assert response.status_code == 200
    body = response.json()
    assert provider.image_calls == 0
    assert body["dimensions_confirmed"] is True
    assert body["furniture_items"][0]["dimensions_confirmed"] is True
    assert body["context"]["origin_floor"] == 3
    assert body["context"]["origin_has_elevator"] is False


def test_view_page_is_served():
    response = _client(RecordingProvider()).get("/view")
    assert response.status_code == 200
    assert "三维装车" in response.text
    assert "cargo_layout" in response.text


def test_analyze_distance_changes_transport():
    client = _client(RecordingProvider())
    files = [("files", ("room.jpg", b"img", "image/jpeg"))]
    near = client.post("/analyze", files=files, data={"distance_km": "1"})
    far = client.post("/analyze", files=files, data={"distance_km": "40"})
    assert near.status_code == 200
    assert far.json()["cost_breakdown"]["transport"] > near.json()["cost_breakdown"]["transport"]
