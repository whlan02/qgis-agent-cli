from __future__ import annotations

from typing import Any, Dict, Optional, Protocol, Tuple


class ServerActionContext(Protocol):
    def add_vector_layer(self, path: str) -> Dict[str, Any]:
        ...

    def get_layers(self) -> Dict[str, Any]:
        ...

    def export_map(self, output_path: str) -> Dict[str, Any]:
        ...

    def start_buffer_layer_task(self, sock: Any, request: Dict[str, Any]) -> Tuple[bool, Optional[Dict[str, Any]]]:
        ...

