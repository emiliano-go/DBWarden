from typer.testing import CliRunner

from dbwarden.cli.main import app
from dbwarden.config import (
    is_dev_mode,
    is_strict_translation,
    set_dev_mode,
    set_strict_translation,
)


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

    def test_strict_translation_flag_enables_mode(self):
        runner = CliRunner()
        set_strict_translation(False)

        result = runner.invoke(app, ["--strict-translation", "version"])

        assert result.exit_code == 0
        assert is_strict_translation() is True

    def test_strict_translation_disabled_by_default(self):
        runner = CliRunner()
        set_strict_translation(True)

        result = runner.invoke(app, ["version"])

        assert result.exit_code == 0
        assert is_strict_translation() is False
