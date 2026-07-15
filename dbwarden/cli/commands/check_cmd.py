import typer

from dbwarden.cli.app import app
from dbwarden.cli.validators import validate_directory
from dbwarden.commands import (
    handle_check,
    handle_check_db,
    handle_check_impact,
    handle_diff,
    handle_snapshot,
)


@app.command()
def snapshot(
    table_name: str = typer.Argument(..., help="Table name to snapshot"),
    database: str | None = typer.Option(
        None, "--database", "-d", help="Target database name"
    ),
):
    """Snapshot the DDL schema of a specific table."""
    validate_directory()
    handle_snapshot(table_name=table_name, database=database)


@app.command()
def check(
    output: str = typer.Option(
        "txt", "--out", "-o", help="Output format (json, txt)"
    ),
    force: bool = typer.Option(
        False,
        "--force",
        help="Allow warning-level changes to pass",
    ),
    database: str | None = typer.Option(
        None, "--database", "-d", help="Target database name"
    ),
):
    """Run the schema safety analyzer."""
    validate_directory()
    handle_check(output_format=output, database=database, force=force)


@app.command()
def check_db(
    output: str = typer.Option(
        "txt", "--out", "-o", help="Output format (json, yaml, sql, txt)"
    ),
    database: str | None = typer.Option(
        None, "--database", "-d", help="Target database name"
    ),
):
    """Inspect the live database schema."""
    validate_directory()
    handle_check_db(output_format=output, database=database)


@app.command()
def check_impact(
    migration: str = typer.Argument(
        ..., help="Migration version or plan file path"
    ),
    out: str = typer.Option(
        "text", "--out", "-o", help="Output format: text (default) or json"
    ),
    scan_path: str = typer.Option(
        ".", "--scan-path", help="Directory to scan for affected code"
    ),
    deep: bool = typer.Option(
        False, "--deep", help="Enable deep introspection (imports models live)"
    ),
    verbose: bool = typer.Option(
        False, "--verbose", "-v", help="Show INFO-level operations in scan"
    ),
    database: str | None = typer.Option(
        None, "--database", "-d", help="Target database name"
    ),
):
    """Analyze impact of a migration on your codebase."""
    validate_directory()
    handle_check_impact(
        migration=migration, out=out, scan_path=scan_path,
        deep=deep, verbose=verbose, database=database,
    )


@app.command()
def diff(
    output: str = typer.Option(
        "table", "--out", "-o", help="Output format: table (default), json, sql"
    ),
    verbose: bool = typer.Option(
        False, "--verbose", "-v", help="Enable verbose logging"
    ),
    database: str | None = typer.Option(
        None, "--database", "-d", help="Target database name"
    ),
    offline: bool = typer.Option(
        False,
        "--offline",
        help="Use model state file instead of live database snapshot",
    ),
):
    """Show structural differences between models and database (read-only, no files written)."""
    validate_directory()
    handle_diff(
        output_format=output, verbose=verbose, database=database, offline=offline
    )
