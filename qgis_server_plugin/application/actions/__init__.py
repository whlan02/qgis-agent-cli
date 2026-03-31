from __future__ import annotations

import importlib
import pkgutil
from typing import Any, Callable, Dict, Optional

ActionHandler = Callable[[Dict[str, Any], Any, Any], Optional[Dict[str, Any]]]


def discover_action_handlers() -> Dict[str, ActionHandler]:
    handlers: Dict[str, ActionHandler] = {}
    for module_info in pkgutil.walk_packages(__path__, prefix=f"{__name__}."):  # type: ignore[name-defined]
        module_name = module_info.name
        if not module_name.endswith("_action"):
            continue
        module = importlib.import_module(module_name)
        action_name = getattr(module, "ACTION_NAME", None)
        handler = getattr(module, "handle", None)
        if isinstance(action_name, str) and callable(handler):
            handlers[action_name] = handler
    return handlers


ACTION_HANDLERS = discover_action_handlers()

__all__ = ["ACTION_HANDLERS", "discover_action_handlers"]

