import pytest

from src.errors import VisionParseError
from src.models import FurnitureType
from src.provider import parse_detection


def test_parse_fenced_json_and_drop_low_confidence():
    text = """```json
{"furniture":[
  {"name":"沙发","type":"沙发","dimensions":{"length":200,"width":90,"height":80},"weight":30,"disassemble":false,"fragile":false,"quantity":1,"description":"布艺","confidence":0.91},
  {"name":"模糊物","type":"chair","dimensions":{"length":40,"width":40,"height":40},"confidence":0.2}
]}
```"""
    items = parse_detection(text, confidence_threshold=0.7, max_detections=10)
    assert len(items) == 1
    assert items[0].furniture_type == FurnitureType.SOFA
    assert items[0].dimensions_confirmed is False


def test_unknown_type_becomes_other_and_detections_are_capped():
    text = """{"furniture":[
      {"name":"灯","type":"lamp","dimensions":{"length":20,"width":20,"height":40},"quantity":1},
      {"name":"第二件","type":"chair","dimensions":{"length":40,"width":40,"height":45},"quantity":1}
    ]}"""
    items = parse_detection(text, confidence_threshold=0.7, max_detections=1)
    assert len(items) == 1
    assert items[0].furniture_type == FurnitureType.OTHER


def test_unparseable_response_raises():
    with pytest.raises(VisionParseError):
        parse_detection("这不是清单", confidence_threshold=0.7, max_detections=10)
