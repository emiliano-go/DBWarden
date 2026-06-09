from __future__ import annotations

from unittest.mock import MagicMock, patch

import pytest


class TestExtraCommands:
    @patch("dbwarden.commands.extra.get_database")
    @patch("dbwarden.commands.extra.migrations_table_exists")
    @patch("dbwarden.commands.extra.console.print")
    def test_diff_no_table(self, mock_print, mock_table_exists, mock_get_db):
        mock_table_exists.return_value = False
        mock_get_db.return_value = MagicMock()
        mock_get_db.return_value.sqlalchemy_url = "sqlite:///test.db"
        mock_get_db.return_value.database_type = "sqlite"

        from dbwarden.commands.extra import diff_cmd

        diff_cmd(database="test")
        mock_print.assert_called_once()

    @patch("dbwarden.commands.extra.get_database")
    @patch("dbwarden.commands.extra.migrations_table_exists")
    @patch("dbwarden.commands.extra.console.print")
    def test_diff_with_table(self, mock_print, mock_table_exists, mock_get_db):
        mock_table_exists.return_value = True
        mock_get_db.return_value = MagicMock()
        mock_get_db.return_value.sqlalchemy_url = "sqlite:///test.db"
        mock_get_db.return_value.database_type = "sqlite"

        from dbwarden.commands.extra import diff_cmd

        diff_cmd(verbose=True, database="test")
        mock_print.assert_called()

    @patch("dbwarden.commands.extra.get_database")
    @patch("dbwarden.commands.extra.migrations_table_exists")
    @patch("dbwarden.commands.extra.console.print")
    def test_squash_no_table(self, mock_print, mock_table_exists, mock_get_db):
        mock_table_exists.return_value = False
        mock_get_db.return_value = MagicMock()
        mock_get_db.return_value.sqlalchemy_url = "sqlite:///test.db"
        mock_get_db.return_value.database_type = "sqlite"

        from dbwarden.commands.extra import squash_cmd

        squash_cmd(database="test")
        mock_print.assert_called_once()

    @patch("dbwarden.commands.extra.get_database")
    @patch("dbwarden.commands.extra.migrations_table_exists")
    @patch("dbwarden.repositories.get_migration_records")
    @patch("dbwarden.commands.extra._get_pending_count")
    @patch("dbwarden.commands.extra.console.print")
    def test_squash_dry_run(
        self, mock_print, mock_pending, mock_records, mock_exists, mock_get_db
    ):
        mock_exists.return_value = True
        mock_records.return_value = [MagicMock()]
        mock_pending.return_value = 0
        mock_get_db.return_value = MagicMock()
        mock_get_db.return_value.sqlalchemy_url = "sqlite:///test.db"
        mock_get_db.return_value.database_type = "sqlite"

        from dbwarden.commands.extra import squash_cmd

        squash_cmd(database="test", verbose=True)
        mock_print.assert_called()

    @patch("dbwarden.repositories.check_lock")
    @patch("dbwarden.commands.extra.console.print")
    def test_lock_status_locked(self, mock_print, mock_check):
        mock_check.return_value = True

        from dbwarden.commands.extra import lock_status_cmd

        lock_status_cmd("test")
        mock_print.assert_called()

    @patch("dbwarden.repositories.check_lock")
    @patch("dbwarden.commands.extra.console.print")
    def test_lock_status_unlocked(self, mock_print, mock_check):
        mock_check.return_value = False

        from dbwarden.commands.extra import lock_status_cmd

        lock_status_cmd("test")
        mock_print.assert_called()

    @patch("dbwarden.repositories.release_lock")
    @patch("dbwarden.commands.extra.console.print")
    def test_unlock_success(self, mock_print, mock_release):
        mock_release.return_value = True

        from dbwarden.commands.extra import unlock_cmd

        unlock_cmd("test")
        mock_print.assert_called_once()

    @patch("dbwarden.repositories.release_lock")
    @patch("dbwarden.commands.extra.console.print")
    def test_unlock_failure(self, mock_print, mock_release):
        mock_release.return_value = False

        from dbwarden.commands.extra import unlock_cmd

        unlock_cmd("test")
        mock_print.assert_called_once()
