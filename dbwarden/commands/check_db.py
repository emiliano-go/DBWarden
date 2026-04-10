from typing import Any

from rich.console import Console
from sqlalchemy import inspect

from dbwarden.config import get_database
from dbwarden.database.connection import get_db_connection
from dbwarden.engine.version import get_migrations_directory
from dbwarden.logging import get_logger


def check_db_cmd(output_format: str = "txt", database: str | None = None) -> None:
    """
    Inspect the live database schema.

    Args:
        output_format: Output format (json, yaml, sql, txt).
        database: Target database name.
    """
    logger = get_logger()
    config = get_database(database)
    db_name = database or "default"

    with get_db_connection(database) as connection:
        inspector = inspect(connection)
        tables = inspector.get_table_names()

        schema_info = {}
        for table in tables:
            columns = inspector.get_columns(table)
            indexes = inspector.get_indexes(table)
            foreign_keys = inspector.get_foreign_keys(table)

            schema_info[table] = {
                "columns": [
                    {
                        "name": col["name"],
                        "type": str(col["type"]),
                        "nullable": col["nullable"],
                        "default": str(col.get("default", None)),
                    }
                    for col in columns
                ],
                "indexes": [
                    {"name": idx["name"], "columns": idx["column_names"]}
                    for idx in indexes
                ],
                "foreign_keys": [
                    {
                        "name": fk["name"],
                        "columns": fk["constrained_columns"],
                        "referred_table": fk["referred_table"],
                        "referred_columns": fk["referred_columns"],
                    }
                    for fk in foreign_keys
                ],
            }

    print(f"\n=== Database Schema: {db_name} ===\n")

    if output_format == "json":
        import json

        print(json.dumps(schema_info, indent=2, default=str))
    elif output_format == "yaml":
        import yaml

        print(yaml.dump(schema_info, default_flow_style=False))
    elif output_format == "txt":
        _print_txt(schema_info)
    else:
        raise ValueError(f"Unknown output format: {output_format}")


def _print_txt(schema_info: dict[str, Any]) -> None:
    """Print schema in text format."""
    console = Console()

    for table, info in schema_info.items():
        console.print(f"\n[bold cyan]Table: {table}[/bold cyan]")
        console.print("-" * 50)

        for col in info["columns"]:
            nullable = "NULL" if col["nullable"] else "NOT NULL"
            default = (
                f" DEFAULT {col['default']}"
                if col["default"] and col["default"] != "None"
                else ""
            )
            console.print(f"  {col['name']}: {col['type']} {nullable}{default}")

        if info["indexes"]:
            console.print("\n  Indexes:")
            for idx in info["indexes"]:
                console.print(f"    - {idx['name']}: {', '.join(idx['columns'])}")

        if info["foreign_keys"]:
            console.print("\n  Foreign Keys:")
            for fk in info["foreign_keys"]:
                console.print(
                    f"    - {fk['name']}: {', '.join(fk['columns'])} -> "
                    f"{fk['referred_table']}({', '.join(fk['referred_columns'])})"
                )
