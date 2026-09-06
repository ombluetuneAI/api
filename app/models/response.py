from __future__ import annotations

from typing import Any


def ok(data: Any = None, message: str = "ok") -> dict:
    return {"code": 200, "data": data, "message": message}


def fail(code: int, message: str) -> dict:
    return {"code": code, "data": None, "message": message}
