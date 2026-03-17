import pytest
import tempfile
import os
from pathlib import Path
from io import StringIO
import sys

from dbwarden.commands.init import init_cmd
from dbwarden.commands.utils import config_cmd, version_cmd
from dbwarden.constants import MIGRATIONS_DIR, TOML_FILE


class TestInitCommand:
    """Tests for init command."""

    def test_init_creates_migrations_directory(self):
        """Test init creates migrations directory."""
        with tempfile.TemporaryDirectory() as tmpdir:
            old_cwd = os.getcwd()
            os.chdir(tmpdir)

            try:
                init_cmd()

                migrations_path = Path(tmpdir) / MIGRATIONS_DIR
                assert migrations_path.exists()
                assert migrations_path.is_dir()
            finally:
                os.chdir(old_cwd)

    def test_init_creates_warden_toml(self):
        """Test init creates warden.toml if it doesn't exist."""
        with tempfile.TemporaryDirectory() as tmpdir:
            old_cwd = os.getcwd()
            os.chdir(tmpdir)

            try:
                init_cmd()

                toml_path = Path(tmpdir) / TOML_FILE
                assert toml_path.exists()

                content = toml_path.read_text()
                assert 'database_type = "sqlite"' in content
                assert 'sqlalchemy_url = "sqlite:///./development.db"' in content
            finally:
                os.chdir(old_cwd)

    def test_init_does_not_overwrite_existing_warden_toml(self):
        """Test init doesn't overwrite existing warden.toml."""
        with tempfile.TemporaryDirectory() as tmpdir:
            old_cwd = os.getcwd()
            os.chdir(tmpdir)

            try:
                # Create existing warden.toml
                toml_path = Path(tmpdir) / TOML_FILE
                original_content = (
                    'database_type = "sqlite"\nsqlalchemy_url = "custom.db"'
                )
                toml_path.write_text(original_content)

                init_cmd()

                # Should not have been overwritten
                content = toml_path.read_text()
                assert content == original_content
            finally:
                os.chdir(old_cwd)

    def test_init_idempotent(self):
        """Test running init multiple times is safe."""
        with tempfile.TemporaryDirectory() as tmpdir:
            old_cwd = os.getcwd()
            os.chdir(tmpdir)

            try:
                init_cmd()
                init_cmd()
                init_cmd()

                migrations_path = Path(tmpdir) / MIGRATIONS_DIR
                assert migrations_path.exists()

                toml_path = Path(tmpdir) / TOML_FILE
                assert toml_path.exists()
            finally:
                os.chdir(old_cwd)


class TestConfigCommand:
    """Tests for config command."""

    def _run_config_capture_output(self, tmpdir):
        """Helper to run config command and capture output."""
        old_cwd = os.getcwd()
        os.chdir(tmpdir)

        try:
            old_stdout = sys.stdout
            sys.stdout = StringIO()
            config_cmd()
            output = sys.stdout.getvalue()
            sys.stdout = old_stdout
            return output
        finally:
            os.chdir(old_cwd)

    def test_config_displays_sqlalchemy_url(self):
        """Test config displays sqlalchemy_url."""
        with tempfile.TemporaryDirectory() as tmpdir:
            with open(os.path.join(tmpdir, "warden.toml"), "w") as f:
                f.write('database_type = "sqlite"\n')
                f.write('sqlalchemy_url = "sqlite:///./test.db"\n')

            output = self._run_config_capture_output(tmpdir)
            assert "database_type" in output
            assert "sqlalchemy_url" in output
            assert "sqlite:///./test.db" in output

    def test_config_masks_password(self):
        """Test config masks password in URL."""
        with tempfile.TemporaryDirectory() as tmpdir:
            with open(os.path.join(tmpdir, "warden.toml"), "w") as f:
                f.write('database_type = "postgres"\n')
                f.write(
                    'sqlalchemy_url = "postgresql://user:secretpassword@localhost/db"\n'
                )

            output = self._run_config_capture_output(tmpdir)
            assert "secretpassword" not in output
            assert "user:***" in output

    def test_config_displays_model_paths(self):
        """Test config displays model_paths."""
        with tempfile.TemporaryDirectory() as tmpdir:
            with open(os.path.join(tmpdir, "warden.toml"), "w") as f:
                f.write('database_type = "sqlite"\n')
                f.write('sqlalchemy_url = "sqlite:///./test.db"\n')
                f.write('model_paths = ["./models/"]\n')

            output = self._run_config_capture_output(tmpdir)
            assert "model_paths" in output

    def test_config_displays_postgres_schema(self):
        """Test config displays postgres_schema."""
        with tempfile.TemporaryDirectory() as tmpdir:
            with open(os.path.join(tmpdir, "warden.toml"), "w") as f:
                f.write('database_type = "sqlite"\n')
                f.write('sqlalchemy_url = "sqlite:///./test.db"\n')
                f.write('postgres_schema = "custom"\n')

            output = self._run_config_capture_output(tmpdir)
            assert "postgres_schema" in output
            assert "custom" in output

    def test_config_shows_file_path(self):
        """Test config shows the config file path."""
        with tempfile.TemporaryDirectory() as tmpdir:
            with open(os.path.join(tmpdir, "warden.toml"), "w") as f:
                f.write('database_type = "sqlite"\n')
                f.write('sqlalchemy_url = "sqlite:///./test.db"\n')

            output = self._run_config_capture_output(tmpdir)
            assert "warden.toml" in output

    def test_config_no_file_found(self):
        """Test config handles missing warden.toml."""
        with tempfile.TemporaryDirectory() as tmpdir:
            output = self._run_config_capture_output(tmpdir)
            assert "No warden.toml found" in output


class TestVersionCommand:
    """Tests for version command."""

    def _run_version_capture_output(self):
        """Helper to run version command and capture output."""
        old_stdout = sys.stdout
        sys.stdout = StringIO()
        version_cmd()
        output = sys.stdout.getvalue()
        sys.stdout = old_stdout
        return output

    def test_version_displays_version(self):
        """Test version command displays version."""
        output = self._run_version_capture_output()
        assert len(output.strip()) > 0
        # Version should be a valid version string (e.g., "0.1.5")
        assert "." in output.strip()

    def test_version_is_string(self):
        """Test version outputs a string."""
        output = self._run_version_capture_output()
        assert isinstance(output.strip(), str)
