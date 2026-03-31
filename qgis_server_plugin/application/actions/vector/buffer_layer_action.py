from __future__ import annotations

from typing import Any, Dict, Optional

from ...action_context import ServerActionContext
from ....domain import error, maybe_response

ACTION_NAME = "buffer_layer"


def handle(request: Dict[str, Any], context: ServerActionContext, sock: Any) -> Optional[Dict[str, Any]]:
    started, immediate_error = context.start_buffer_layer_task(sock, request)
    if started:
        return maybe_response(None)
    return immediate_error or error("Failed to start buffer task")

