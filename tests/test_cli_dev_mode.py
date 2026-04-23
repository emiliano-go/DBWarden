from typer.testing import CliRunner

from dbwarden.cli.main import app
from dbwarden.config import is_dev_mode, set_dev_mode


class TestCliDevMode:
    def test_dev_flag_enables_dev_mode(self):
        runner = CliRunner()
        set_dev_mode(False)

        result = runner.invoke(app, ["--dev", "version"])

        assert result.exit_code == 0
        assert is_dev_mode() is True

    def test_dev_flag_disabled_by_default(self):
        runner = CliRunner()
        set_dev_mode(True)

        result = runner.invoke(app, ["version"])

        assert result.exit_code == 0
        assert is_dev_mode() is False
