import unittest

from qgis_server_plugin import ws_protocol
from qgis_server_plugin.application.actions import ACTION_HANDLERS


class TestWsProtocol(unittest.TestCase):
    def test_action_discovery_contains_known_actions(self):
        self.assertIn("ping", ACTION_HANDLERS)
        self.assertIn("add_vector_layer", ACTION_HANDLERS)
        self.assertIn("buffer_layer", ACTION_HANDLERS)
        self.assertIn("export_map", ACTION_HANDLERS)
        self.assertIn("get_layers", ACTION_HANDLERS)

    def test_invalid_json_returns_error(self):
        resp = ws_protocol.handle_request_text(
            "not-json",
            context=object(),
            sock=object(),
            handlers={},
        )
        self.assertEqual("error", resp["status"])

    def test_missing_action_returns_error(self):
        resp = ws_protocol.handle_request(
            {},
            context=object(),
            sock=object(),
            handlers={},
        )
        self.assertEqual("error", resp["status"])
        self.assertIn("action", resp["message"])

    def test_dispatch_to_handler(self):
        def ping_handler(request, context, sock):
            _ = request, context, sock
            return {"status": "ok", "message": "pong"}

        resp = ws_protocol.handle_request(
            {"action": "ping"},
            context=object(),
            sock=object(),
            handlers={"ping": ping_handler},
        )
        self.assertEqual({"status": "ok", "message": "pong"}, resp)

    def test_get_layers_dispatch_to_handler(self):
        def get_layers_handler(request, context, sock):
            _ = context, sock
            self.assertEqual("get_layers", request.get("action"))
            return {"status": "ok", "message": "Layers listed", "layers": []}

        resp = ws_protocol.handle_request(
            {"action": "get_layers"},
            context=object(),
            sock=object(),
            handlers={"get_layers": get_layers_handler},
        )
        self.assertEqual("ok", resp["status"])
        self.assertEqual([], resp["layers"])


if __name__ == "__main__":
    unittest.main()

