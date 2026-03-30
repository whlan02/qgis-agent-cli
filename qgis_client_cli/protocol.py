from __future__ import annotations

import time
from typing import Any, Dict, Optional


def make_request(action: str, **kwargs: Any) -> Dict[str, Any]:
    """
    Build a JSON request for the QGIS in-plugin WebSocket server.
    """
    payload: Dict[str, Any] = {"action": action}
    payload.update(kwargs)
    return payload


def normalize_response(response: Any) -> Dict[str, Any]:
    """
    Normalize server response into a dict (best-effort).
    """
    if isinstance(response, dict):
        return response
    return {"status": "error", "message": "Invalid response format from server"}


def make_envelope(
    *,
    action: str,
    request: Dict[str, Any],
    response: Optional[Dict[str, Any]],
    elapsed_ms: int,
    status: Optional[str] = None,
    message: Optional[str] = None,
) -> Dict[str, Any]:
    """
    Unified envelope for ALL stdout to support agent parsing.
    """
    resp = response if response is not None else {}

    resolved_status = status or resp.get("status") or "error"
    resolved_message = message or resp.get("message") or ""

    return {
        "status": resolved_status,
        "message": resolved_message,
        "action": action,
        "request": request,
        "response": response or {},
        "elapsed_ms": int(elapsed_ms),
    }


def now_ms() -> int:
    return int(time.time() * 1000)

