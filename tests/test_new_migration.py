from __future__ import annotations

import os
import tempfile
from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest


class TestNewMigrationCmd:
    def _setup(self, tmpdir):
        mig_dir = Path(tmpdir) / "migrations" / "default"
        mig_dir.mkdir(parents=True)
        return str(mig_dir)

    @patch("dbwarden.commands.make_migrations.get_multi_db_config")
    @patch("dbwarden.commands.make_migrations.get_database")
    @patch("dbwarden.engine.version.get_migrations_directory")
    @patch("dbwarden.commands.make_migrations.get_migrations_directory")
    @patch("dbwarden.commands.make_migrations.Path.cwd")
    def test_new_versioned_default(
        self, mock_cwd, mock_get_mig_dir_local, mock_get_mig_dir_version,
        mock_get_db, mock_multi,
    ):
        mock_multi.return_value.default = "default"
        with tempfile.TemporaryDirectory() as tmpdir:
            mig_dir = self._setup(tmpdir)
            mock_cwd.return_value = Path(tmpdir)
            mock_get_mig_dir_local.return_value = mig_dir
            mock_get_mig_dir_version.return_value = mig_dir

            from dbwarden.commands.make_migrations import new_migration_cmd

            new_migration_cmd(description="create users", database="default")
            files = os.listdir(mig_dir)
            assert len(files) == 1
            assert "0001" in files[0]
            assert "RA__" not in files[0]
            assert "ROC__" not in files[0]

    @patch("dbwarden.commands.make_migrations.get_multi_db_config")
    @patch("dbwarden.commands.make_migrations.get_database")
    @patch("dbwarden.engine.version.get_migrations_directory")
    @patch("dbwarden.commands.make_migrations.get_migrations_directory")
    @patch("dbwarden.commands.make_migrations.Path.cwd")
    def test_new_runs_always(
        self, mock_cwd, mock_get_mig_dir_local, mock_get_mig_dir_version,
        mock_get_db, mock_multi,
    ):
        mock_multi.return_value.default = "default"
        with tempfile.TemporaryDirectory() as tmpdir:
            mig_dir = self._setup(tmpdir)
            mock_cwd.return_value = Path(tmpdir)
            mock_get_mig_dir_local.return_value = mig_dir
            mock_get_mig_dir_version.return_value = mig_dir

            from dbwarden.commands.make_migrations import new_migration_cmd

            new_migration_cmd(
                description="refresh view", database="default", migration_type="ra"
            )
            files = os.listdir(mig_dir)
            assert len(files) == 1
            assert "RA__" in files[0]

    @patch("dbwarden.commands.make_migrations.get_multi_db_config")
    @patch("dbwarden.commands.make_migrations.get_database")
    @patch("dbwarden.engine.version.get_migrations_directory")
    @patch("dbwarden.commands.make_migrations.get_migrations_directory")
    @patch("dbwarden.commands.make_migrations.Path.cwd")
    def test_new_runs_on_change(
        self, mock_cwd, mock_get_mig_dir_local, mock_get_mig_dir_version,
        mock_get_db, mock_multi,
    ):
        mock_multi.return_value.default = "default"
        with tempfile.TemporaryDirectory() as tmpdir:
            mig_dir = self._setup(tmpdir)
            mock_cwd.return_value = Path(tmpdir)
            mock_get_mig_dir_local.return_value = mig_dir
            mock_get_mig_dir_version.return_value = mig_dir

            from dbwarden.commands.make_migrations import new_migration_cmd

            new_migration_cmd(
                description="update trigger", database="default", migration_type="roc"
            )
            files = os.listdir(mig_dir)
            assert len(files) == 1
            assert "ROC__" in files[0]

    @patch("dbwarden.commands.make_migrations.get_multi_db_config")
    @patch("dbwarden.commands.make_migrations.get_database")
    @patch("dbwarden.engine.version.get_migrations_directory")
    @patch("dbwarden.commands.make_migrations.get_migrations_directory")
    @patch("dbwarden.commands.make_migrations.Path.cwd")
    def test_new_runs_always_long_alias(
        self, mock_cwd, mock_get_mig_dir_local, mock_get_mig_dir_version,
        mock_get_db, mock_multi,
    ):
        mock_multi.return_value.default = "default"
        with tempfile.TemporaryDirectory() as tmpdir:
            mig_dir = self._setup(tmpdir)
            mock_cwd.return_value = Path(tmpdir)
            mock_get_mig_dir_local.return_value = mig_dir
            mock_get_mig_dir_version.return_value = mig_dir

            from dbwarden.commands.make_migrations import new_migration_cmd

            new_migration_cmd(
                description="grants", database="default", migration_type="runs_always"
            )
            files = os.listdir(mig_dir)
            assert len(files) == 1
            assert "RA__" in files[0]

    @patch("dbwarden.commands.make_migrations.get_multi_db_config")
    @patch("dbwarden.commands.make_migrations.get_database")
    @patch("dbwarden.engine.version.get_migrations_directory")
    @patch("dbwarden.commands.make_migrations.get_migrations_directory")
    @patch("dbwarden.commands.make_migrations.Path.cwd")
    def test_new_runs_on_change_long_alias(
        self, mock_cwd, mock_get_mig_dir_local, mock_get_mig_dir_version,
        mock_get_db, mock_multi,
    ):
        mock_multi.return_value.default = "default"
        with tempfile.TemporaryDirectory() as tmpdir:
            mig_dir = self._setup(tmpdir)
            mock_cwd.return_value = Path(tmpdir)
            mock_get_mig_dir_local.return_value = mig_dir
            mock_get_mig_dir_version.return_value = mig_dir

            from dbwarden.commands.make_migrations import new_migration_cmd

            new_migration_cmd(
                description="policy", database="default", migration_type="runs_on_change"
            )
            files = os.listdir(mig_dir)
            assert len(files) == 1
            assert "ROC__" in files[0]
