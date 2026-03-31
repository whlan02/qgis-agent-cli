from __future__ import annotations

from typing import Any, Dict

from ...action_context import ServerActionContext
from ....domain import ok

ACTION_NAME = "ping"


def handle(request: Dict[str, Any], context: ServerActionContext, sock: Any) -> Dict[str, Any]:
    _ = request, context, sock
    return ok("QGIS is ready")

