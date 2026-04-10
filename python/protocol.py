import json
from typing import Any


def parse_message(line: str) -> dict:
    try:
        msg = json.loads(line.strip())
    except json.JSONDecodeError as e:
        raise ValueError(f"Invalid JSON: {e}")

    if "id" not in msg or "method" not in msg:
        raise ValueError("Message must have 'id' and 'method' fields")

    return msg


def format_result(msg_id: str, data: Any) -> str:
    return json.dumps({"id": msg_id, "type": "result", "data": data}, ensure_ascii=False)


def format_progress(msg_id: str, percent: int, message: str, stage: str | None = None, elapsed_ms: int | None = None) -> str:
    data: dict = {"percent": percent, "message": message}
    if stage is not None:
        data["stage"] = stage
    if elapsed_ms is not None:
        data["elapsed_ms"] = elapsed_ms
    return json.dumps({"id": msg_id, "type": "progress", "data": data}, ensure_ascii=False)


def format_error(msg_id: str, message: str) -> str:
    return json.dumps({"id": msg_id, "type": "error", "data": {"message": message}}, ensure_ascii=False)
