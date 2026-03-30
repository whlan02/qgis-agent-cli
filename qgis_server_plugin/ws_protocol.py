import json
from typing import Any, Callable, Dict


def _make_error(message: str) -> Dict[str, Any]:
    return {"status": "error", "message": message}


def _make_ok(message: str, extra: Dict[str, Any] | None = None) -> Dict[str, Any]:
    payload: Dict[str, Any] = {"status": "ok", "message": message}
    if extra:
        payload.update(extra)
    return payload


def handle_request(
    request: Dict[str, Any],
    add_vector_layer_fn: Callable[[str], Dict[str, Any]],
    export_map_fn: Callable[[str], Dict[str, Any]] | None = None,
) -> Dict[str, Any]:
    """
    Handle a parsed JSON request object and return a JSON-serializable response dict.

    This module is intentionally QGIS/PyQt-free so it can be unit-tested.
    """
    action = request.get("action")
    if action == "ping":
        return {"status": "ok", "message": "QGIS is ready"}

    if action == "add_vector_layer":
        path = request.get("path")
        if not path or not isinstance(path, str):
            return _make_error("Missing or invalid 'path' for add_vector_layer")

        result: Dict[str, Any] = add_vector_layer_fn(path)
        if result.get("success") is True:
            layer_id = result.get("layer_id") or result.get("layerId") or result.get("layerID")
            extra: Dict[str, Any] = {}
            if layer_id is not None:
                extra["layerId"] = layer_id
            return _make_ok("Vector layer added", extra=extra)

        # Best-effort error message from implementation.
        err = result.get("error") or result.get("message") or "Failed to add vector layer"
        return _make_error(str(err))

    if action == "export_map":
        if export_map_fn is None:
            return _make_error("Action 'export_map' is not available")

        output_path = request.get("output_path")
        if not output_path or not isinstance(output_path, str):
            return _make_error("Missing or invalid 'output_path' for export_map")

        result = export_map_fn(output_path)
        if result.get("success") is True:
            extra: Dict[str, Any] = {"output_path": output_path}
            actual_path = result.get("output_path")
            if isinstance(actual_path, str) and actual_path:
                extra["output_path"] = actual_path
            return _make_ok("Map exported", extra=extra)

        err = result.get("error") or result.get("message") or "Failed to export map"
        return _make_error(str(err))

    return _make_error(f"Unknown action: {action}")


def handle_request_text(
    text: str,
    add_vector_layer_fn: Callable[[str], Dict[str, Any]],
    export_map_fn: Callable[[str], Dict[str, Any]] | None = None,
) -> Dict[str, Any]:
    """
    Handle a WebSocket text message that should contain JSON.
    """
    try:
        request = json.loads(text)
    except json.JSONDecodeError:
        return _make_error("Invalid JSON")

    if not isinstance(request, dict):
        return _make_error("Request JSON must be an object")

    return handle_request(
        request,
        add_vector_layer_fn=add_vector_layer_fn,
        export_map_fn=export_map_fn,
    )

