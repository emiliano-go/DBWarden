import os
import re
from typing import Optional


class MigrationMetadata:
    """Metadata parsed from a migration file header."""

    def __init__(
        self,
        depends_on: Optional[list[str]] = None,
        is_seed: bool = False,
        description: Optional[str] = None,
    ):
        self.depends_on = depends_on or []
        self.is_seed = is_seed
        self.description = description


def get_description_from_filename(filename: str) -> str:
    """
    Extract description from migration filename.

    Args:
        filename: Migration filename (e.g., "0001_create_users_table.sql")

    Returns:
        str: Description extracted from filename.
    """
    name = filename.replace(".sql", "")
    if "__" in name:
        parts = name.split("__", 1)
        return parts[1].replace("_", " ").strip()
    elif name[0:4].isdigit() and "_" in name:
        parts = name.split("_", 1)
        return parts[1].replace("_", " ").strip()
    return name.replace("_", " ").strip()


def parse_migration_header(file_path: str) -> MigrationMetadata:
    """
    Parse metadata from a migration file header.

    Supports:
    - depends_on: ["0001", "0002"]
    - -- seed
    - -- depends_on: ["0001", "0002"]

    Args:
        file_path: Path to the migration SQL file.

    Returns:
        MigrationMetadata: Parsed metadata from the header.
    """
    with open(file_path, "r") as f:
        lines = f.readlines()

    metadata = MigrationMetadata()

    for line in lines:
        stripped = line.strip()

        if stripped == "-- upgrade" or stripped == "-- rollback":
            break

        seed_match = re.match(r"^--\s*seed\s*$", stripped, re.IGNORECASE)
        if seed_match:
            metadata.is_seed = True
            continue

        depends_match = re.match(r"^--\s*depends_on:\s*(.+)$", stripped, re.IGNORECASE)
        if depends_match:
            try:
                import json

                deps = json.loads(depends_match.group(1))
                if isinstance(deps, list):
                    metadata.depends_on = [str(d) for d in deps]
            except (json.JSONDecodeError, TypeError):
                pass
            continue

        desc_match = re.match(r"^--\s*description:\s*(.+)$", stripped, re.IGNORECASE)
        if desc_match:
            metadata.description = desc_match.group(1).strip()
            continue

    return metadata


def parse_upgrade_statements(file_path: str) -> list[str]:
    """
    Parse upgrade statements from a migration file.

    Args:
        file_path: Path to the migration SQL file.

    Returns:
        list[str]: List of SQL statements for upgrade.
    """
    with open(file_path, "r") as f:
        content = f.read()

    return _extract_section_statements(content, "-- upgrade")


def parse_rollback_statements(file_path: str) -> list[str]:
    """
    Parse rollback statements from a migration file.

    Args:
        file_path: Path to the migration SQL file.

    Returns:
        list[str]: List of SQL statements for rollback.
    """
    with open(file_path, "r") as f:
        content = f.read()

    return _extract_section_statements(content, "-- rollback")


def _extract_section_statements(content: str, section_marker: str) -> list[str]:
    """
    Extract SQL statements from a section of a migration file.

    Args:
        content: Full content of the migration file.
        section_marker: Marker indicating the section start (e.g., "-- upgrade").

    Returns:
        list[str]: List of SQL statements.
    """
    lines = content.split("\n")
    statements: list[str] = []
    current_statement: list[str] = []
    in_section = False

    for line in lines:
        stripped = line.strip()

        if stripped == section_marker:
            in_section = True
            continue

        if stripped == "-- rollback" and in_section:
            if current_statement:
                statement = "\n".join(current_statement).strip()
                if statement:
                    statements.append(statement)
                current_statement = []
            in_section = False
            continue

        if in_section:
            if stripped and not stripped.startswith("--"):
                current_statement.append(line)
            elif current_statement and not stripped:
                statement = "\n".join(current_statement).strip()
                if statement:
                    statements.append(statement)
                current_statement = []

    if current_statement:
        statement = "\n".join(current_statement).strip()
        if statement:
            statements.append(statement)

    return statements
