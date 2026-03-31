from __future__ import annotations

import os
from typing import Any, Dict, Optional


class VectorLayerService:
    def __init__(self, iface: Any):
        self._iface = iface

    def add_vector_layer(self, path: str) -> Dict[str, Any]:
        if not path or not isinstance(path, str):
            return {"success": False, "error": "Invalid path"}

        layer_name = os.path.splitext(os.path.basename(path))[0] or os.path.basename(path) or "vector_layer"

        try:
            layer = self._iface.addVectorLayer(path, layer_name, "ogr")
        except Exception as e:
            return {"success": False, "error": f"addVectorLayer failed: {e}"}

        if layer is None:
            return {"success": False, "error": "iface.addVectorLayer returned None"}

        try:
            is_valid_fn = getattr(layer, "isValid", None)
            if callable(is_valid_fn) and not layer.isValid():
                return {"success": False, "error": "Loaded layer is not valid"}
        except Exception:
            pass

        layer_id: Optional[str] = None
        try:
            if hasattr(layer, "id"):
                layer_id = layer.id()
        except Exception:
            layer_id = None

        return {"success": True, "layer_id": layer_id, "layer_name": layer_name}

