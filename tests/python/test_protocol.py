import json
import pytest
from python.protocol import parse_message, format_result, format_progress, format_error


def test_parse_valid_message():
    line = json.dumps({"id": "abc-123", "method": "detect_gpu", "params": {}})
    msg = parse_message(line)
    assert msg["id"] == "abc-123"
    assert msg["method"] == "detect_gpu"
    assert msg["params"] == {}


def test_parse_invalid_json():
    with pytest.raises(ValueError):
        parse_message("not json")


def test_parse_missing_fields():
    with pytest.raises(ValueError):
        parse_message(json.dumps({"id": "x"}))


def test_format_result():
    out = format_result("abc-123", {"gpu": True, "vram": 16000})
    parsed = json.loads(out)
    assert parsed["id"] == "abc-123"
    assert parsed["type"] == "result"
    assert parsed["data"]["gpu"] is True


def test_format_progress():
    out = format_progress("abc-123", 50, "Embedding...")
    parsed = json.loads(out)
    assert parsed["type"] == "progress"
    assert parsed["data"]["percent"] == 50


def test_format_error():
    out = format_error("abc-123", "Something failed")
    parsed = json.loads(out)
    assert parsed["type"] == "error"
    assert parsed["data"]["message"] == "Something failed"
