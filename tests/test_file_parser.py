import pytest
import tempfile
import os
from pathlib import Path

from dbwarden.engine.file_parser import (
    parse_upgrade_statements,
    parse_rollback_statements,
    get_description_from_filename,
)


class TestFileParser:
    """Tests for SQL file parsing."""

    def test_parse_upgrade_statements(self):
        """Test parsing upgrade statements from migration file."""
        with tempfile.NamedTemporaryFile(mode="w", suffix=".sql", delete=False) as f:
            f.write("""-- upgrade

CREATE TABLE users (
    id INTEGER PRIMARY KEY,
    name VARCHAR(100) NOT NULL
);

CREATE TABLE posts (
    id INTEGER PRIMARY KEY,
    title VARCHAR(255) NOT NULL
);

-- rollback

DROP TABLE posts;
DROP TABLE users;
""")
            f.flush()

            statements = parse_upgrade_statements(f.name)

            assert len(statements) == 2
            assert "CREATE TABLE users" in statements[0]
            assert "CREATE TABLE posts" in statements[1]

            os.unlink(f.name)

    def test_parse_rollback_statements(self):
        """Test parsing rollback statements from migration file."""
        with tempfile.NamedTemporaryFile(mode="w", suffix=".sql", delete=False) as f:
            f.write("""-- upgrade

CREATE TABLE users (
    id INTEGER PRIMARY KEY,
    name VARCHAR(100) NOT NULL
);

-- rollback

DROP TABLE users;
""")
            f.flush()

            statements = parse_rollback_statements(f.name)

            assert len(statements) == 1
            assert "DROP TABLE users" in statements[0]

            os.unlink(f.name)

    def test_parse_empty_section(self):
        """Test parsing when sections are empty."""
        with tempfile.NamedTemporaryFile(mode="w", suffix=".sql", delete=False) as f:
            f.write("""-- upgrade

-- rollback
""")
            f.flush()

            upgrade = parse_upgrade_statements(f.name)
            rollback = parse_rollback_statements(f.name)

            assert len(upgrade) == 0
            assert len(rollback) == 0

            os.unlink(f.name)

    def test_get_description_from_filename(self):
        """Test extracting description from migration filename."""
        assert (
            get_description_from_filename("V1__create_users_table.sql")
            == "create users table"
        )
        assert (
            get_description_from_filename("V20240215_120000__add_user_profile.sql")
            == "add user profile"
        )
        assert (
            get_description_from_filename("V1.5__initial_schema.sql")
            == "initial schema"
        )

    def test_parse_multiline_sql(self):
        """Test parsing multiline SQL statements."""
        with tempfile.NamedTemporaryFile(mode="w", suffix=".sql", delete=False) as f:
            f.write("""-- upgrade

CREATE TABLE users (
    id INTEGER PRIMARY KEY,
    name VARCHAR(100) NOT NULL,
    email VARCHAR(255) UNIQUE NOT NULL,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- rollback

DROP TABLE users;
""")
            f.flush()

            statements = parse_upgrade_statements(f.name)

            assert len(statements) == 1
            assert "CREATE TABLE users" in statements[0]
            assert "id INTEGER PRIMARY KEY" in statements[0]
            assert "email VARCHAR(255) UNIQUE NOT NULL" in statements[0]

            os.unlink(f.name)

    def test_parse_sql_with_comments(self):
        """Test parsing SQL statements with inline comments."""
        with tempfile.NamedTemporaryFile(mode="w", suffix=".sql", delete=False) as f:
            f.write("""-- upgrade

-- This creates the users table
CREATE TABLE users (
    id INTEGER PRIMARY KEY -- primary key
);

-- rollback

DROP TABLE users;
""")
            f.flush()

            statements = parse_upgrade_statements(f.name)

            assert len(statements) == 1
            assert "CREATE TABLE users" in statements[0]

            os.unlink(f.name)
