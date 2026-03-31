from __future__ import annotations

from typing import Any, Dict, Optional


def ok(message: str, **extra: Any) -> Dict[str, Any]:
    payload: Dict[str, Any] = {"status": "ok", "message": message}
    payload.update(extra)
    return payload


def error(message: str, **extra: Any) -> Dict[str, Any]:
    payload: Dict[str, Any] = {"status": "error", "message": message}
    payload.update(extra)
    return payload


def maybe_response(response: Optional[Dict[str, Any]]) -> Optional[Dict[str, Any]]:
    return response

