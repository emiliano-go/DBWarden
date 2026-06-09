from __future__ import annotations

from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest
import tempfile


def _mock_config_with_model_paths(model_paths=None):
    mock = MagicMock()
    mock.model_paths = model_paths
    return mock


class TestExportModels:
    @patch("dbwarden.commands.export_models.get_database")
    @patch("dbwarden.commands.export_models.get_all_model_tables")
    @patch("dbwarden.commands.export_models.model_state_to_dict")
    @patch("dbwarden.commands.export_models.json.dumps")
    def test_export_models_with_model_paths(
        self, mock_json_dumps, mock_state_to_dict, mock_get_tables, mock_get_db
    ):
        mock_json_dumps.return_value = '{"models": []}'
        mock_state_to_dict.return_value = {"models": []}
        mock_get_tables.return_value = []
        mock_get_db.return_value = _mock_config_with_model_paths(["myapp.models"])

        with tempfile.TemporaryDirectory() as tmpdir:
            out = str(Path(tmpdir) / "state.json")
            from dbwarden.commands.export_models import export_models_cmd

            export_models_cmd(output=out)

            mock_get_tables.assert_called_once_with(["myapp.models"], db_name=None)

    @patch("dbwarden.commands.export_models.get_database")
    @patch("dbwarden.commands.make_migrations.auto_discover_model_paths")
    @patch("dbwarden.commands.export_models.get_all_model_tables")
    @patch("dbwarden.commands.export_models.model_state_to_dict")
    @patch("dbwarden.commands.export_models.json.dumps")
    def test_export_models_auto_discover(
        self, mock_json_dumps, mock_state_to_dict, mock_get_tables, mock_auto_discover, mock_get_db
    ):
        mock_json_dumps.return_value = '{"models": []}'
        mock_state_to_dict.return_value = {"models": []}
        mock_get_tables.return_value = []
        mock_auto_discover.return_value = ["auto.models"]
        mock_get_db.return_value = _mock_config_with_model_paths(None)

        with tempfile.TemporaryDirectory() as tmpdir:
            out = str(Path(tmpdir) / "state.json")
            from dbwarden.commands.export_models import export_models_cmd

            export_models_cmd(output=out)

            mock_get_tables.assert_called_once_with(["auto.models"], db_name=None)

    @patch("dbwarden.commands.export_models.get_database")
    @patch("dbwarden.commands.make_migrations.auto_discover_model_paths")
    def test_export_models_no_paths(self, mock_auto_discover, mock_get_db):
        mock_auto_discover.return_value = []
        mock_get_db.return_value = _mock_config_with_model_paths(None)

        from dbwarden.commands.export_models import export_models_cmd

        with pytest.raises(ValueError, match="No model paths found"):
            export_models_cmd(output="/tmp/out.json")

    @patch("dbwarden.commands.export_models.get_database")
    @patch("dbwarden.commands.export_models.get_all_model_tables")
    @patch("dbwarden.commands.export_models.model_state_to_dict")
    @patch("dbwarden.commands.export_models.json.dumps")
    def test_export_models_output_path_created(
        self, mock_json_dumps, mock_state_to_dict, mock_get_tables, mock_get_db
    ):
        mock_json_dumps.return_value = '{"models": []}'
        mock_state_to_dict.return_value = {"models": []}
        mock_get_tables.return_value = []
        mock_get_db.return_value = _mock_config_with_model_paths(["myapp.models"])

        with tempfile.TemporaryDirectory() as tmpdir:
            out = str(Path(tmpdir) / "nested" / "dir" / "state.json")
            from dbwarden.commands.export_models import export_models_cmd

            export_models_cmd(output=out)

            assert Path(out).exists()
