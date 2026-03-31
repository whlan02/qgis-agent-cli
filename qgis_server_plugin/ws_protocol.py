import json
from typing import Any, Dict, Optional

from .application import ActionHandler, dispatch_action

def _missing_or_invalid_str(request: Dict[str, Any], key: str) -> bool:
    value = request.get(key)
    return not isinstance(value, str) or not value


def _validate_request(action: str, request: Dict[str, Any]) -> Optional[Dict[str, Any]]:
    if action == "add_vector_layer":
        if _missing_or_invalid_str(request, "path"):
            return {"status": "error", "message": "Missing or invalid 'path' for add_vector_layer"}
        return None

    if action == "export_map":
        if _missing_or_invalid_str(request, "output_path"):
            return {"status": "error", "message": "Missing or invalid 'output_path' for export_map"}
        return None

    if action == "buffer_layer":
        layer_name = request.get("layer_name")
        distance = request.get("distance")
        if not isinstance(layer_name, str) or not layer_name.strip():
            return {"status": "error", "message": "Missing or invalid 'layer_name' for buffer_layer"}
        if isinstance(distance, bool) or distance is None:
            return {"status": "error", "message": "Missing or invalid 'distance' for buffer_layer"}
        try:
            float(distance)
        except Exception:
            return {"status": "error", "message": "Missing or invalid 'distance' for buffer_layer"}
        return None

    if action == "ping":
        return None

    return {"status": "error", "message": f"Unknown action: {action}"}

def handle_request(
    request: Dict[str, Any],
    *,
    context: Any,
    sock: Any,
    handlers: Dict[str, ActionHandler],
) -> Optional[Dict[str, Any]]:
    """
    Handle a parsed JSON request object and return a JSON-serializable response dict.

    This module is intentionally QGIS/PyQt-free so it can be unit-tested.
    """
    action = request.get("action")
    if not isinstance(action, str):
        return {"status": "error", "message": "Missing or invalid 'action'"}

    validation_error = _validate_request(action, request)
    if validation_error is not None:
        return validation_error
    return dispatch_action(action=action, request=request, context=context, sock=sock, handlers=handlers)


def handle_request_text(
    text: str,
    *,
    context: Any,
    sock: Any,
    handlers: Dict[str, ActionHandler],
) -> Optional[Dict[str, Any]]:
    """
    Handle a WebSocket text message that should contain JSON.
    """
    try:
        request = json.loads(text)
    except json.JSONDecodeError:
        return {"status": "error", "message": "Invalid JSON"}

    if not isinstance(request, dict):
        return {"status": "error", "message": "Request JSON must be an object"}

    return handle_request(request, context=context, sock=sock, handlers=handlers)

