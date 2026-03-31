from __future__ import annotations

from typing import Any, Callable, Dict, Optional

from .action_context import ServerActionContext
from .actions import ACTION_HANDLERS

ActionHandler = Callable[[Dict[str, Any], ServerActionContext, Any], Optional[Dict[str, Any]]]


def default_action_handlers() -> Dict[str, ActionHandler]:
    return dict(ACTION_HANDLERS)


def dispatch_action(
    *,
    action: str,
    request: Dict[str, Any],
    context: ServerActionContext,
    sock: Any,
    handlers: Dict[str, ActionHandler],
) -> Optional[Dict[str, Any]]:
    handler = handlers.get(action)
    if handler is None:
        return {"status": "error", "message": f"Action '{action}' is not available"}
    return handler(request, context, sock)

