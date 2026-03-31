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

    def get_layers(self) -> Dict[str, Any]:
        try:
            canvas = getattr(self._iface, "mapCanvas", None)
            if not callable(canvas):
                return {"success": False, "error": "QGIS map canvas is not available"}
            layers = canvas().layers()
        except Exception as e:
            return {"success": False, "error": f"Failed to access map layers: {e}"}

        result = []
        for layer in layers or []:
            layer_id: Optional[str] = None
            layer_name = "unknown"
            layer_type: Optional[str] = None
            provider: Optional[str] = None

            try:
                if hasattr(layer, "id"):
                    layer_id = layer.id()
            except Exception:
                layer_id = None

            try:
                if hasattr(layer, "name"):
                    layer_name = layer.name()
            except Exception:
                layer_name = "unknown"

            try:
                if hasattr(layer, "type"):
                    layer_type = str(layer.type())
            except Exception:
                layer_type = None

            try:
                if hasattr(layer, "providerType"):
                    provider = layer.providerType()
            except Exception:
                provider = None

            item: Dict[str, Any] = {"name": layer_name}
            if layer_id is not None:
                item["id"] = layer_id
            if layer_type is not None:
                item["type"] = layer_type
            if provider:
                item["provider"] = provider
            result.append(item)

        return {"success": True, "layers": result}

