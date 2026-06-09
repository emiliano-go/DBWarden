from __future__ import annotations

import json
import tempfile
from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest


class TestCheckImpact:
    @patch("dbwarden.commands.check_impact.analyze_impact")
    @patch("dbwarden.commands.check_impact._resolve_plan_path")
    def test_check_impact_json_output(self, mock_resolve, mock_analyze):
        mock_resolve.return_value = "/tmp/test.plan.json"
        mock_analyze.return_value = {
            "impact": [
                {
                    "operation_type": "alter_column",
                    "table": "users",
                    "column": "email",
                    "references": [{"file": "/tmp/app.py", "line": 42, "snippet": "user.email", "kind": "read"}],
                }
            ],
            "migration_id": "0001",
        }

        from dbwarden.commands.check_impact import check_impact_cmd

        with patch("builtins.print") as mock_print:
            check_impact_cmd(migration="0001", out="json")
            mock_print.assert_called_once()
            args, _ = mock_print.call_args
            parsed = json.loads(args[0])
            assert "impact" in parsed

    @patch("dbwarden.commands.check_impact.analyze_impact")
    @patch("dbwarden.commands.check_impact._resolve_plan_path")
    def test_check_impact_no_impact(self, mock_resolve, mock_analyze):
        mock_resolve.return_value = "/tmp/test.plan.json"
        mock_analyze.return_value = {"impact": [], "migration_id": "0001"}

        from dbwarden.commands.check_impact import check_impact_cmd

        with patch("dbwarden.commands.make_migrations.console.print") as mock_print:
            check_impact_cmd(migration="0001", out="text")
            mock_print.assert_any_call("[green]No impact detected[/green]")

    @patch("dbwarden.commands.check_impact._resolve_plan_path")
    def test_check_impact_no_plan(self, mock_resolve):
        mock_resolve.return_value = None

        from dbwarden.commands.check_impact import check_impact_cmd

        result = check_impact_cmd(migration="nonexistent")
        assert result is None

    @patch("dbwarden.commands.check_impact.analyze_impact")
    @patch("dbwarden.commands.check_impact._resolve_plan_path")
    def test_check_impact_text_output(self, mock_resolve, mock_analyze):
        mock_resolve.return_value = "/tmp/test.plan.json"
        mock_analyze.return_value = {
            "impact": [
                {
                    "operation_type": "add_column",
                    "table": "users",
                    "column": "age",
                    "references": [
                        {"file": "/tmp/app.py", "line": 10, "snippet": "user.age", "kind": "read"},
                        {"file": "/tmp/app.py", "line": 20, "snippet": "user.age = 25", "kind": "write"},
                    ],
                }
            ],
            "migration_id": "0001",
        }

        from dbwarden.commands.check_impact import check_impact_cmd

        with patch("dbwarden.commands.make_migrations.console.print") as mock_print:
            check_impact_cmd(migration="0001", out="text", deep=True, verbose=True)
            mock_print.assert_called()

    def test_resolve_plan_path_direct_file_found(self):
        from dbwarden.commands.check_impact import _resolve_plan_path

        with patch("dbwarden.commands.check_impact.os.path.isfile") as mock_isfile:
            mock_isfile.side_effect = lambda p: p == "test.sql" or p == "test.plan.json"
            result = _resolve_plan_path("test.sql")
            assert result == "test.plan.json"

    def test_resolve_plan_path_direct_file_not_found(self):
        from dbwarden.commands.check_impact import _resolve_plan_path

        with patch("dbwarden.commands.check_impact.os.path.isfile") as mock_isfile:
            mock_isfile.side_effect = lambda p: p == "test.sql"
            result = _resolve_plan_path("test.sql")
            assert result is None

    @patch("dbwarden.commands.check_impact.get_migrations_directory")
    @patch("dbwarden.commands.check_impact.get_migration_filepaths_by_version")
    def test_resolve_plan_path_by_version(self, mock_get_files, mock_get_dir):
        mock_get_dir.return_value = "/tmp/migrations"
        mock_get_files.return_value = {"0001": "/tmp/migrations/test__0001_test.sql"}

        from dbwarden.commands.check_impact import _resolve_plan_path

        def _isfile(path):
            return path.endswith(".plan.json") or path == "/tmp/migrations/test__0001_test.sql"

        with patch("dbwarden.commands.check_impact.os.path.isfile", side_effect=_isfile):
            result = _resolve_plan_path("0001")
            assert result == "/tmp/migrations/test__0001_test.plan.json"

    @patch("dbwarden.commands.check_impact.get_migrations_directory")
    def test_resolve_plan_path_migrations_dir_error(self, mock_get_dir):
        mock_get_dir.side_effect = ValueError("Config not found")

        from dbwarden.commands.check_impact import _resolve_plan_path

        with patch("dbwarden.commands.make_migrations.console.print") as mock_print:
            result = _resolve_plan_path("0001")
            assert result is None
            mock_print.assert_called()
