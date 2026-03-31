from __future__ import annotations

import os
from typing import Any, Dict


class MapExportService:
    def __init__(self, iface: Any):
        self._iface = iface

    def export_map(self, output_path: str) -> Dict[str, Any]:
        if not output_path or not isinstance(output_path, str):
            return {"success": False, "error": "Invalid output_path"}

        if not os.path.isabs(output_path):
            return {"success": False, "error": "output_path must be an absolute path"}

        try:
            out_dir = os.path.dirname(output_path) or ""
            if out_dir and not os.path.isdir(out_dir):
                os.makedirs(out_dir, exist_ok=True)
        except Exception as e:
            return {"success": False, "error": f"Failed to create output directory: {e}"}

        try:
            from PyQt5.QtGui import QColor, QImage
            from qgis.core import QgsMapRendererParallelJob

            canvas = self._iface.mapCanvas()
            settings = canvas.mapSettings()
            settings.setOutputSize(canvas.size())

            job = QgsMapRendererParallelJob(settings)
            job.start()
            job.waitForFinished()

            img = job.renderedImage()
            if img is None or img.isNull():
                return {"success": False, "error": "Rendered image is null"}

            if img.hasAlphaChannel():
                composed = QImage(img.size(), QImage.Format_ARGB32_Premultiplied)
                composed.fill(QColor(255, 255, 255, 255))
                painter = None
                try:
                    from PyQt5.QtGui import QPainter

                    painter = QPainter(composed)
                    painter.drawImage(0, 0, img)
                finally:
                    if painter is not None:
                        painter.end()
                img = composed

            ok = bool(img.save(output_path))
        except Exception as e:
            return {"success": False, "error": f"saveAsImage failed: {e}"}

        if not ok:
            return {"success": False, "error": "Image save returned false"}

        return {"success": True, "output_path": output_path}

