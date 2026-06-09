from __future__ import annotations

from unittest.mock import MagicMock, patch

import pytest


class TestHistory:
    @patch("dbwarden.commands.history.migrations_table_exists")
    def test_history_no_table(self, mock_table_exists):
        mock_table_exists.return_value = False

        from dbwarden.commands.history import history_cmd

        with patch("dbwarden.commands.history.Console") as mock_console_cls:
            mock_console = MagicMock()
            mock_console_cls.return_value = mock_console
            history_cmd("test_db")
            mock_console.print.assert_called_once()

    @patch("dbwarden.commands.history.migrations_table_exists")
    @patch("dbwarden.commands.history.get_migration_records")
    def test_history_no_records(self, mock_get_records, mock_table_exists):
        mock_table_exists.return_value = True
        mock_get_records.return_value = []

        from dbwarden.commands.history import history_cmd

        with patch("dbwarden.commands.history.Console") as mock_console_cls:
            mock_console = MagicMock()
            mock_console_cls.return_value = mock_console
            history_cmd("test_db")
            mock_console.print.assert_called_once()

    @patch("dbwarden.commands.history.migrations_table_exists")
    @patch("dbwarden.commands.history.get_migration_records")
    def test_history_with_records(self, mock_get_records, mock_table_exists):
        mock_table_exists.return_value = True
        mock_record = MagicMock()
        mock_record.version = "0001"
        mock_record.order_executed = 1
        mock_record.description = "init"
        mock_record.applied_at = "2024-01-01"
        mock_record.migration_type = "migration"
        mock_get_records.return_value = [mock_record]

        from dbwarden.commands.history import history_cmd

        with patch("dbwarden.commands.history.Console") as mock_console_cls:
            mock_console = MagicMock()
            mock_console_cls.return_value = mock_console
            history_cmd("test_db")
            mock_console.print.assert_called_once()
