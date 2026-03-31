from __future__ import annotations

from typing import Any, Dict

from ...action_context import ServerActionContext
from ....domain import error, ok

ACTION_NAME = "get_layers"


def handle(request: Dict[str, Any], context: ServerActionContext, sock: Any) -> Dict[str, Any]:
    _ = request, sock
    result = context.get_layers()
    if result.get("success") is not True:
        err = result.get("error") or result.get("message") or "Failed to get layers"
        return error(str(err))

    layers = result.get("layers")
    if not isinstance(layers, list):
        layers = []
    return ok("Layers listed", layers=layers, count=len(layers))
