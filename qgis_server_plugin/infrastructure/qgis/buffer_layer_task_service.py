from __future__ import annotations

from typing import Any, Callable, Dict, Optional, Tuple


class BufferLayerTaskService:
    def __init__(self, safe_send: Callable[[Any, Dict[str, Any]], None]):
        self._safe_send = safe_send
        self._tasks: Dict[str, Dict[str, Any]] = {}

    def cancel_all_tasks(self) -> None:
        try:
            for _, task_entry in list(self._tasks.items()):
                try:
                    task = task_entry.get("task") if isinstance(task_entry, dict) else task_entry
                    cancel_fn = getattr(task, "cancel", None)
                    if callable(cancel_fn):
                        task.cancel()
                except Exception:
                    pass
        finally:
            self._tasks.clear()

    def start_task(self, sock: Any, request: Dict[str, Any]) -> Tuple[bool, Optional[Dict[str, Any]]]:
        layer_name = request.get("layer_name")
        distance = request.get("distance")

        if not isinstance(layer_name, str) or not layer_name.strip():
            return False, {"status": "error", "message": "Missing or invalid 'layer_name' for buffer_layer"}

        if isinstance(distance, bool) or distance is None:
            return False, {"status": "error", "message": "Missing or invalid 'distance' for buffer_layer"}

        try:
            dist_val = float(distance)
        except Exception:
            return False, {"status": "error", "message": "Missing or invalid 'distance' for buffer_layer"}

        try:
            from qgis.core import QgsApplication, QgsProject, QgsProcessingContext, QgsProcessingFeedback
        except Exception as e:
            return False, {"status": "error", "message": f"QGIS core not available: {e}"}

        try:
            layers = QgsProject.instance().mapLayersByName(layer_name)
            if not layers:
                return False, {"status": "error", "message": f"Layer not found: {layer_name}"}
            layer = layers[0]
        except Exception as e:
            return False, {"status": "error", "message": f"Failed to resolve layer: {e}"}

        try:
            alg = QgsApplication.processingRegistry().algorithmById("native:buffer")
            if alg is None:
                return False, {"status": "error", "message": "Processing algorithm not found: native:buffer"}

            params = {
                "INPUT": layer,
                "DISTANCE": dist_val,
                "SEGMENTS": 5,
                "END_CAP_STYLE": 0,
                "JOIN_STYLE": 0,
                "MITER_LIMIT": 2.0,
                "DISSOLVE": False,
                "OUTPUT": "memory:",
            }

            context = QgsProcessingContext()
            feedback = QgsProcessingFeedback()

            from qgis.core import QgsProcessingAlgRunnerTask

            task = QgsProcessingAlgRunnerTask(alg, params, context, feedback)
        except Exception as e:
            return False, {"status": "error", "message": f"Failed to create processing task: {e}"}

        task_id = f"buffer:{id(task)}"
        self._tasks[task_id] = {
            "task": task,
            "context": context,
            "feedback": feedback,
            "sock": sock,
            "layer_name": layer_name,
            "distance": dist_val,
        }

        def _on_executed(success: bool, results: Dict[str, Any]) -> None:
            try:
                if not success:
                    detail = ""
                    try:
                        text_log_fn = getattr(feedback, "textLog", None)
                        if callable(text_log_fn):
                            detail = str(text_log_fn() or "").strip()
                    except Exception:
                        detail = ""
                    if detail:
                        self._safe_send(sock, {"status": "error", "message": f"Buffer failed: {detail}"})
                    else:
                        self._safe_send(sock, {"status": "error", "message": "Buffer failed"})
                    return

                out = results.get("OUTPUT")
                if out is None:
                    self._safe_send(sock, {"status": "error", "message": "Buffer produced no output layer"})
                    return

                try:
                    output_layer = out
                    if isinstance(out, str):
                        try:
                            from qgis.core import QgsProcessingUtils

                            output_layer = QgsProcessingUtils.mapLayerFromString(out, context)
                        except Exception:
                            output_layer = None
                    if output_layer is None:
                        self._safe_send(sock, {"status": "error", "message": "Buffer output layer could not be resolved"})
                        return

                    QgsProject.instance().addMapLayer(output_layer)
                except Exception as e:
                    self._safe_send(sock, {"status": "error", "message": f"Failed to add buffer layer: {e}"})
                    return

                layer_id = None
                try:
                    if hasattr(output_layer, "id"):
                        layer_id = output_layer.id()
                except Exception:
                    layer_id = None

                self._safe_send(sock, {"status": "ok", "message": "Buffer layer added", "layerId": layer_id})
            finally:
                self._tasks.pop(task_id, None)

        def _on_terminated() -> None:
            try:
                self._safe_send(sock, {"status": "error", "message": "Buffer task terminated"})
            finally:
                self._tasks.pop(task_id, None)

        try:
            task.executed.connect(_on_executed)
            term_sig = getattr(task, "terminated", None)
            if term_sig is not None:
                try:
                    term_sig.connect(_on_terminated)
                except Exception:
                    pass
            QgsApplication.taskManager().addTask(task)
        except Exception as e:
            self._tasks.pop(task_id, None)
            return False, {"status": "error", "message": f"Failed to start processing task: {e}"}

        return True, None

