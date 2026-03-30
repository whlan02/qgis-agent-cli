import json
import os
from typing import Any, Dict, Optional, Tuple

from . import ws_protocol


class QgisServerPlugin:
    """
    QGIS plugin that starts a local WebSocket server on plugin load.
    """

    ws_host = "127.0.0.1"
    ws_port = 8765

    def __init__(self, iface):
        self.iface = iface
        self._server = None
        self._started = False
        self._sockets = set()
        # task_id -> {"task": task, "context": context, "feedback": feedback, ...}
        # Keep strong refs for PyQGIS processing objects until task completion.
        self._buffer_tasks: Dict[str, Any] = {}

    def initGui(self):
        self._start_server()

    def unload(self):
        self._stop_server()

    def run(self):
        # No UI action needed; server is started on initGui().
        pass

    def _push_message(self, title: str, message: str, level=None, duration_ms: int = 0) -> None:
        """
        Best-effort message to QGIS message bar (only works inside QGIS).
        """
        try:
            from qgis.core import Qgis

            if level is None:
                level = Qgis.Info
            self.iface.messageBar().pushMessage(title, message, level=level, duration=duration_ms)
        except Exception:
            # Unit tests and non-QGIS runs will hit this path.
            return

    def _start_server(self) -> None:
        if self._started:
            return

        try:
            from PyQt5.QtWebSockets import QWebSocketServer
            from PyQt5.QtNetwork import QHostAddress
        except Exception as e:
            self._push_message("QGIS Agent WS", f"PyQt5 WebSockets not available: {e}", duration_ms=0)
            return

        self._server = QWebSocketServer("QGIS Agent WebSocket Server", QWebSocketServer.NonSecureMode, self.iface.mainWindow())
        ok = self._server.listen(QHostAddress(self.ws_host), self.ws_port)

        if not ok:
            self._push_message("QGIS Agent WS", f"Failed to listen on ws://{self.ws_host}:{self.ws_port}", duration_ms=0)
            self._server = None
            return

        # Qt signals are handled asynchronously in the main Qt event loop.
        self._server.newConnection.connect(self._on_new_connection)
        self._started = True

        self._push_message(
            "QGIS Agent WS",
            f"Listening on ws://{self.ws_host}:{self.ws_port}",
            duration_ms=5000,
        )

    def _stop_server(self) -> None:
        if self._server is None:
            self._started = False
            return

        try:
            try:
                for _, task_entry in list(self._buffer_tasks.items()):
                    try:
                        task = task_entry.get("task") if isinstance(task_entry, dict) else task_entry
                        cancel_fn = getattr(task, "cancel", None)
                        if callable(cancel_fn):
                            task.cancel()
                    except Exception:
                        pass
            finally:
                self._buffer_tasks.clear()

            for sock in list(self._sockets):
                try:
                    sock.close()
                except Exception:
                    pass
        finally:
            self._sockets.clear()
            try:
                self._server.close()
            except Exception:
                pass
            self._server = None
            self._started = False

    def _on_new_connection(self) -> None:
        if self._server is None:
            return

        sock = self._server.nextPendingConnection()
        if sock is None:
            return

        self._sockets.add(sock)
        sock.textMessageReceived.connect(lambda message, s=sock: self._on_text_message(s, message))
        sock.disconnected.connect(lambda s=sock: self._on_disconnected(s))

    def _on_disconnected(self, sock) -> None:
        try:
            self._sockets.discard(sock)
        except Exception:
            pass

    def _on_text_message(self, sock, message) -> None:
        message_text = ""
        try:
            if isinstance(message, bytes):
                message_text = message.decode("utf-8", errors="replace")
            else:
                message_text = str(message)

            # Special-case: buffer is potentially heavy and must not block the UI thread.
            # We start a background processing task and only send a response when it finishes.
            action, parsed = self._try_parse_action(message_text)
            if action == "buffer_layer" and isinstance(parsed, dict):
                started, immediate_error = self._start_buffer_layer_task(sock, parsed)
                if started:
                    return
                resp = immediate_error or {"status": "error", "message": "Failed to start buffer task"}
            else:
                resp = ws_protocol.handle_request_text(
                    message_text,
                    add_vector_layer_fn=self._add_vector_layer_impl,
                    export_map_fn=self._export_map_impl,
                )
        except Exception as e:
            resp = {"status": "error", "message": f"Server error: {e}"}

        self._safe_send(sock, resp)

    def _safe_send(self, sock, payload: Dict[str, Any]) -> None:
        try:
            sock.sendTextMessage(json.dumps(payload))
        except Exception:
            pass

    def _try_parse_action(self, message_text: str) -> Tuple[Optional[str], Optional[Dict[str, Any]]]:
        try:
            req = json.loads(message_text)
        except Exception:
            return None, None
        if not isinstance(req, dict):
            return None, None
        action = req.get("action")
        if isinstance(action, str):
            return action, req
        return None, req

    def _add_vector_layer_impl(self, path: str) -> Dict[str, Any]:
        """
        Called by protocol router; runs on the Qt main thread.
        """
        if not path or not isinstance(path, str):
            return {"success": False, "error": "Invalid path"}

        layer_name = os.path.splitext(os.path.basename(path))[0] or os.path.basename(path) or "vector_layer"

        try:
            layer = self.iface.addVectorLayer(path, layer_name, "ogr")
        except Exception as e:
            return {"success": False, "error": f"addVectorLayer failed: {e}"}

        if layer is None:
            return {"success": False, "error": "iface.addVectorLayer returned None"}

        # QgsMapLayer has isValid() for many layer types.
        try:
            is_valid_fn = getattr(layer, "isValid", None)
            if callable(is_valid_fn) and not layer.isValid():
                return {"success": False, "error": "Loaded layer is not valid"}
        except Exception:
            # If validity check fails, still try returning success; QGIS may handle it.
            pass

        layer_id: Optional[str] = None
        try:
            if hasattr(layer, "id"):
                layer_id = layer.id()
        except Exception:
            layer_id = None

        return {"success": True, "layer_id": layer_id, "layer_name": layer_name}

    def _export_map_impl(self, output_path: str) -> Dict[str, Any]:
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
            # Use a renderer job instead of mapCanvas().saveAsImage().
            # saveAsImage() can return false depending on canvas state/render timing.
            from PyQt5.QtGui import QColor, QImage
            from qgis.core import QgsMapRendererParallelJob

            canvas = self.iface.mapCanvas()
            settings = canvas.mapSettings()

            # Ensure the export uses the current canvas size/settings.
            size = canvas.size()
            settings.setOutputSize(size)

            job = QgsMapRendererParallelJob(settings)
            job.start()
            job.waitForFinished()

            img = job.renderedImage()
            if img is None or img.isNull():
                return {"success": False, "error": "Rendered image is null"}

            # Some renderers may leave the background transparent; default to white.
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

    def _start_buffer_layer_task(self, sock, request: Dict[str, Any]) -> Tuple[bool, Optional[Dict[str, Any]]]:
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

            # Prefer the built-in background runner task for non-blocking processing.
            from qgis.core import QgsProcessingAlgRunnerTask

            task = QgsProcessingAlgRunnerTask(alg, params, context, feedback)
        except Exception as e:
            return False, {"status": "error", "message": f"Failed to create processing task: {e}"}

        task_id = f"buffer:{id(task)}"
        # IMPORTANT: keep context/feedback alive while task runs.
        self._buffer_tasks[task_id] = {
            "task": task,
            "context": context,
            "feedback": feedback,
            "sock": sock,
            "layer_name": layer_name,
            "distance": dist_val,
        }

        def _on_executed(success: bool, results: Dict[str, Any]):  # runs on main thread
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
                    # Depending on QGIS/processing version, OUTPUT may be a layer object
                    # or a string reference that must be resolved through context.
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

                self._safe_send(
                    sock,
                    {
                        "status": "ok",
                        "message": "Buffer layer added",
                        "layerId": layer_id,
                    },
                )
            finally:
                self._buffer_tasks.pop(task_id, None)

        def _on_terminated():
            try:
                self._safe_send(sock, {"status": "error", "message": "Buffer task terminated"})
            finally:
                self._buffer_tasks.pop(task_id, None)

        try:
            task.executed.connect(_on_executed)
            # Not all QGIS versions expose a "terminated" signal on QgsProcessingAlgRunnerTask.
            term_sig = getattr(task, "terminated", None)
            if term_sig is not None:
                try:
                    term_sig.connect(_on_terminated)
                except Exception:
                    pass
            QgsApplication.taskManager().addTask(task)
        except Exception as e:
            self._buffer_tasks.pop(task_id, None)
            return False, {"status": "error", "message": f"Failed to start processing task: {e}"}

        return True, None

