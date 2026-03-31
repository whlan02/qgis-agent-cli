import json
from typing import Any, Dict, Optional, Tuple

from .application import ActionHandler, default_action_handlers
from .infrastructure.qgis import BufferLayerTaskService, MapExportService, VectorLayerService
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
        self._action_handlers: Dict[str, ActionHandler] = default_action_handlers()
        self._vector_layer_service = VectorLayerService(iface)
        self._map_export_service = MapExportService(iface)
        self._buffer_task_service = BufferLayerTaskService(safe_send=self._safe_send)

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
            self._buffer_task_service.cancel_all_tasks()

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
        try:
            message_text = ""
            if isinstance(message, bytes):
                message_text = message.decode("utf-8", errors="replace")
            else:
                message_text = str(message)

            resp = ws_protocol.handle_request_text(
                message_text,
                context=self,
                sock=sock,
                handlers=self._action_handlers,
            )
        except Exception as e:
            resp = {"status": "error", "message": f"Server error: {e}"}

        if resp is not None:
            self._safe_send(sock, resp)

    def _safe_send(self, sock, payload: Dict[str, Any]) -> None:
        try:
            sock.sendTextMessage(json.dumps(payload))
        except Exception:
            pass

    def add_vector_layer(self, path: str) -> Dict[str, Any]:
        return self._vector_layer_service.add_vector_layer(path)

    def export_map(self, output_path: str) -> Dict[str, Any]:
        return self._map_export_service.export_map(output_path)

    def start_buffer_layer_task(self, sock, request: Dict[str, Any]) -> Tuple[bool, Optional[Dict[str, Any]]]:
        return self._buffer_task_service.start_task(sock, request)

