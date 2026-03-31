import unittest

from qgis_server_plugin import ws_protocol
from qgis_server_plugin.application.actions import ACTION_HANDLERS


class TestWsProtocol(unittest.TestCase):
    def test_action_discovery_contains_known_actions(self):
        self.assertIn("ping", ACTION_HANDLERS)
        self.assertIn("add_vector_layer", ACTION_HANDLERS)
        self.assertIn("buffer_layer", ACTION_HANDLERS)
        self.assertIn("export_map", ACTION_HANDLERS)

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


if __name__ == "__main__":
    unittest.main()

