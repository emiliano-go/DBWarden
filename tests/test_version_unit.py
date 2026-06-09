from __future__ import annotations

import os
import tempfile
from pathlib import Path
from unittest.mock import patch

import pytest


class TestGetNextMigrationNumber:
    def test_returns_0001_when_empty_dir(self):
        from dbwarden.engine.version import get_next_migration_number

        with tempfile.TemporaryDirectory() as tmpdir:
            result = get_next_migration_number(tmpdir)
            assert result == "0001"

    def test_increments_from_existing(self):
        from dbwarden.engine.version import get_next_migration_number

        with tempfile.TemporaryDirectory() as tmpdir:
            Path(tmpdir, "t__0001_test.sql").touch()
            Path(tmpdir, "t__0002_other.sql").touch()
            result = get_next_migration_number(tmpdir)
            assert result == "0003"

    def test_skips_non_migration_files(self):
        from dbwarden.engine.version import get_next_migration_number

        with tempfile.TemporaryDirectory() as tmpdir:
            Path(tmpdir, "README.md").touch()
            Path(tmpdir, "t__0001_test.sql").touch()
            result = get_next_migration_number(tmpdir)
            assert result == "0002"


class TestGenerateMigrationFilename:
    def test_generates_correct_filename(self):
        from dbwarden.engine.version import generate_migration_filename

        result = generate_migration_filename("primary", "create users", "0001")
        assert result == "primary__0001_create_users.sql"

    def test_sanitizes_description(self):
        from dbwarden.engine.version import generate_migration_filename

        result = generate_migration_filename("primary", "Add  USER! table?", "0002")
        assert result == "primary__0002_add_user_table.sql"

    def test_handles_special_chars(self):
        from dbwarden.engine.version import generate_migration_filename

        result = generate_migration_filename("my-db", "initial schema v1.0", "0001")
        assert result == "my-db__0001_initial_schema_v1_0.sql"


class TestGetMigrationsDirectory:
    @patch("dbwarden.config.get_database")
    @patch("dbwarden.engine.version.Path.cwd")
    def test_raises_on_missing_dir(self, mock_cwd, mock_get_db):
        mock_config = type("obj", (object,), {"migrations_dir": "migrations"})()
        mock_get_db.return_value = mock_config

        with tempfile.TemporaryDirectory() as tmpdir:
            mock_cwd.return_value = Path(tmpdir)
            from dbwarden.engine.version import get_migrations_directory

            with pytest.raises(Exception, match="Migrations directory"):
                get_migrations_directory("default")

    @patch("dbwarden.config.get_database")
    @patch("dbwarden.engine.version.Path.cwd")
    def test_returns_migrations_dir(self, mock_cwd, mock_get_db):
        mock_config = type("obj", (object,), {"migrations_dir": "migrations"})()
        mock_get_db.return_value = mock_config

        with tempfile.TemporaryDirectory() as tmpdir:
            Path(tmpdir, "migrations").mkdir()
            mock_cwd.return_value = Path(tmpdir)
            from dbwarden.engine.version import get_migrations_directory

            result = get_migrations_directory("default")
            assert result == str(Path(tmpdir) / "migrations")

    @patch("dbwarden.config.get_database")
    @patch("dbwarden.engine.version._validate_path_within_project")
    @patch("dbwarden.engine.version.Path.cwd")
    def test_path_outside_project_raises(self, mock_cwd, mock_validate, mock_get_db):
        mock_validate.side_effect = Exception("outside project")
        mock_get_db.return_value = type("obj", (object,), {"migrations_dir": "../outside"})()
        mock_cwd.return_value = Path("/tmp/project")

        from dbwarden.engine.version import get_migrations_directory

        with pytest.raises(Exception, match="outside project"):
            get_migrations_directory("default")


class TestGetMigrationFilepathsByVersion:
    def test_returns_empty_for_nonexistent_dir(self):
        from dbwarden.engine.version import get_migration_filepaths_by_version

        result = get_migration_filepaths_by_version("/nonexistent/path")
        assert result == {}

    def test_returns_migrations_in_order(self):
        from dbwarden.engine.version import get_migration_filepaths_by_version

        with tempfile.TemporaryDirectory() as tmpdir:
            Path(tmpdir, "t__0002_b.sql").touch()
            Path(tmpdir, "t__0001_a.sql").touch()
            result = get_migration_filepaths_by_version(tmpdir)
            assert list(result.keys()) == ["0001", "0002"]

    def test_filters_by_start_version(self):
        from dbwarden.engine.version import get_migration_filepaths_by_version

        with tempfile.TemporaryDirectory() as tmpdir:
            Path(tmpdir, "t__0001_a.sql").touch()
            Path(tmpdir, "t__0002_b.sql").touch()
            Path(tmpdir, "t__0003_c.sql").touch()
            result = get_migration_filepaths_by_version(tmpdir, version_to_start_from="0001")
            assert list(result.keys()) == ["0002", "0003"]

    def test_filters_by_end_version(self):
        from dbwarden.engine.version import get_migration_filepaths_by_version

        with tempfile.TemporaryDirectory() as tmpdir:
            Path(tmpdir, "t__0001_a.sql").touch()
            Path(tmpdir, "t__0002_b.sql").touch()
            Path(tmpdir, "t__0003_c.sql").touch()
            result = get_migration_filepaths_by_version(tmpdir, end_version="0002")
            assert list(result.keys()) == ["0001", "0002"]

    def test_filters_by_start_and_end(self):
        from dbwarden.engine.version import get_migration_filepaths_by_version

        with tempfile.TemporaryDirectory() as tmpdir:
            Path(tmpdir, "t__0001_a.sql").touch()
            Path(tmpdir, "t__0002_b.sql").touch()
            Path(tmpdir, "t__0003_c.sql").touch()
            result = get_migration_filepaths_by_version(
                tmpdir, version_to_start_from="0001", end_version="0002"
            )
            assert list(result.keys()) == ["0002"]

    def test_ignores_non_migration_files(self):
        from dbwarden.engine.version import get_migration_filepaths_by_version

        with tempfile.TemporaryDirectory() as tmpdir:
            Path(tmpdir, "README.md").touch()
            Path(tmpdir, "t__0001_a.sql").touch()
            result = get_migration_filepaths_by_version(tmpdir)
            assert list(result.keys()) == ["0001"]

    def test_handles_start_version_not_found(self):
        from dbwarden.engine.version import get_migration_filepaths_by_version

        with tempfile.TemporaryDirectory() as tmpdir:
            Path(tmpdir, "t__0001_a.sql").touch()
            Path(tmpdir, "t__0002_b.sql").touch()
            result = get_migration_filepaths_by_version(tmpdir, version_to_start_from="0099")
            assert list(result.keys()) == ["0001", "0002"]

    def test_handles_end_version_not_found(self):
        from dbwarden.engine.version import get_migration_filepaths_by_version

        with tempfile.TemporaryDirectory() as tmpdir:
            Path(tmpdir, "t__0001_a.sql").touch()
            result = get_migration_filepaths_by_version(tmpdir, end_version="0099")
            assert list(result.keys()) == ["0001"]


class TestParseVersionString:
    def test_parses_dotted_version(self):
        from dbwarden.engine.version import parse_version_string

        assert parse_version_string("1.2.3") == (1, 2, 3)

    def test_parses_single_number(self):
        from dbwarden.engine.version import parse_version_string

        assert parse_version_string("0001") == (1,)


class TestCompareVersions:
    def test_less_than(self):
        from dbwarden.engine.version import compare_versions

        assert compare_versions("1.0", "2.0") == -1

    def test_equal(self):
        from dbwarden.engine.version import compare_versions

        assert compare_versions("1.0", "1.0") == 0

    def test_greater_than(self):
        from dbwarden.engine.version import compare_versions

        assert compare_versions("2.0", "1.0") == 1
