from __future__ import annotations

from typing import Any, Dict

from ...action_context import ServerActionContext
from ....domain import error, ok

ACTION_NAME = "add_vector_layer"


def handle(request: Dict[str, Any], context: ServerActionContext, sock: Any) -> Dict[str, Any]:
    _ = sock
    path = request.get("path")
    result = context.add_vector_layer(path)
    if result.get("success") is True:
        layer_id = result.get("layer_id") or result.get("layerId") or result.get("layerID")
        payload: Dict[str, Any] = ok("Vector layer added")
        if layer_id is not None:
            payload["layerId"] = layer_id
        return payload

    err = result.get("error") or result.get("message") or "Failed to add vector layer"
    return error(str(err))

