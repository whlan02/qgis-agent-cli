import unittest
from unittest.mock import patch

from qgis_client_cli.application.command_runner import CommandRunner


class TestCommandRunner(unittest.TestCase):
    @patch("qgis_client_cli.application.command_runner.call_ws_json")
    def test_execute_success(self, mocked_call):
        mocked_call.return_value = {"status": "ok", "message": "QGIS is ready"}
        runner = CommandRunner(ws_url="ws://127.0.0.1:8765", timeout_ms=5000)
        envelope = runner.execute(action="ping")

        self.assertEqual("ok", envelope["status"])
        self.assertEqual("ping", envelope["action"])
        self.assertIn("elapsed_ms", envelope)

    @patch("qgis_client_cli.application.command_runner.call_ws_json")
    def test_execute_preflight_error(self, mocked_call):
        runner = CommandRunner(ws_url="ws://127.0.0.1:8765", timeout_ms=5000)
        envelope = runner.execute(action="add_vector_layer", preflight_error="path missing")

        mocked_call.assert_not_called()
        self.assertEqual("error", envelope["status"])
        self.assertEqual("path missing", envelope["message"])


if __name__ == "__main__":
    unittest.main()

