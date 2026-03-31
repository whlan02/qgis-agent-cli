from __future__ import annotations

import asyncio
import json
import time
from typing import Any, Dict, Optional

import click

from ..protocol import make_envelope, make_request
from ..ws_client import call_ws_json


class CommandRunner:
    def __init__(self, *, ws_url: str, timeout_ms: int):
        self._ws_url = ws_url
        self._timeout_ms = timeout_ms

    def execute(
        self,
        *,
        action: str,
        payload: Optional[Dict[str, Any]] = None,
        preflight_error: Optional[str] = None,
    ) -> Dict[str, Any]:
        request = make_request(action, **(payload or {}))

        start = time.perf_counter()
        response: Optional[Dict[str, Any]] = None
        error_message: Optional[str] = preflight_error

        if error_message is None:
            try:
                response = asyncio.run(
                    call_ws_json(
                        ws_url=self._ws_url,
                        request=request,
                        timeout_ms=self._timeout_ms,
                    )
                )
            except Exception as e:
                error_message = f"WebSocket call failed: {e}"

        elapsed_ms = int((time.perf_counter() - start) * 1000)
        return make_envelope(
            action=action,
            request=request,
            response=response,
            elapsed_ms=elapsed_ms,
            status="error" if error_message else None,
            message=error_message,
        )


def print_envelope(envelope: Dict[str, Any]) -> None:
    click.echo(json.dumps(envelope, ensure_ascii=False))

