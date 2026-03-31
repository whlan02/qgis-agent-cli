from __future__ import annotations

from typing import Any, Dict

from ...action_context import ServerActionContext
from ....domain import error, ok

ACTION_NAME = "export_map"


def handle(request: Dict[str, Any], context: ServerActionContext, sock: Any) -> Dict[str, Any]:
    _ = sock
    output_path = request.get("output_path")
    result = context.export_map(output_path)
    if result.get("success") is True:
        resolved_output_path = result.get("output_path")
        if not isinstance(resolved_output_path, str) or not resolved_output_path:
            resolved_output_path = output_path
        return ok("Map exported", output_path=resolved_output_path)

    err = result.get("error") or result.get("message") or "Failed to export map"
    return error(str(err))

