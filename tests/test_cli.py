import unittest
from unittest.mock import patch

from click.testing import CliRunner

from qgis_client_cli.cli import main


class TestCli(unittest.TestCase):
    @patch("qgis_client_cli.cli._execute_action")
    def test_get_layers_command_dispatches_action(self, mocked_execute):
        runner = CliRunner()
        result = runner.invoke(main, ["project", "layers"])

        self.assertEqual(0, result.exit_code)
        mocked_execute.assert_called_once()
        kwargs = mocked_execute.call_args.kwargs
        self.assertEqual("get_layers", kwargs["action"])


if __name__ == "__main__":
    unittest.main()
