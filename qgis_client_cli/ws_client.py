from __future__ import annotations

import asyncio
import json
from typing import Any, Dict

import websockets


async def call_ws_json(
    *,
    ws_url: str,
    request: Dict[str, Any],
    timeout_ms: int,
) -> Dict[str, Any]:
    """
    Send a JSON request via WebSocket and await a JSON response.
    """
    timeout_s = max(1e-6, timeout_ms / 1000.0)

    # websockets.connect supports open_timeout; recv/send will be covered by wait_for.
    async with websockets.connect(ws_url, open_timeout=timeout_s) as ws:
        await asyncio.wait_for(ws.send(json.dumps(request)), timeout=timeout_s)
        raw = await asyncio.wait_for(ws.recv(), timeout=timeout_s)

    if isinstance(raw, bytes):
        raw = raw.decode("utf-8", errors="replace")
    if not isinstance(raw, str):
        return {"status": "error", "message": "Non-text WebSocket response"}

    try:
        parsed = json.loads(raw)
    except json.JSONDecodeError:
        return {"status": "error", "message": "Invalid JSON in WebSocket response"}

    if not isinstance(parsed, dict):
        return {"status": "error", "message": "WebSocket response must be a JSON object"}

    return parsed

