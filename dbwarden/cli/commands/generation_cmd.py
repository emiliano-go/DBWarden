import typer

from dbwarden.cli.app import app
from dbwarden.cli.validators import validate_directory
from dbwarden.commands import handle_export_models, handle_generate_models


@app.command()
def generate_models(
    output: str = typer.Option(
        "models", "--output", "-o", help="Output directory for generated model files"
    ),
    tables: str | None = typer.Option(
        None, "--tables", help="Comma-separated list of tables to include"
    ),
    exclude_tables: str | None = typer.Option(
        None, "--exclude-tables", help="Comma-separated list of tables to exclude"
    ),
    clickhouse_engines: bool = typer.Option(
        False, "--clickhouse-engines", help="Include ClickHouse engine metadata"
    ),
    relationships: bool = typer.Option(
        False, "--relationships", help="Generate relationship attributes"
    ),
    dialect: str | None = typer.Option(
        None, "--dialect", help="SQL dialect for type mapping (auto-detected by default)"
    ),
    single_file: bool = typer.Option(
        False, "--single-file", help="Generate a single models.py file"
    ),
    base: str | None = typer.Option(
        None, "--base",
        help="Custom Base class import path (e.g. 'app.core.database:Base' or 'app.database:DeclarativeBase')",
    ),
    database: str | None = typer.Option(
        None, "--database", "-d", help="Target database name"
    ),
):
    """Reverse-engineer SQLAlchemy model code from a live database."""
    validate_directory()
    handle_generate_models(
        output=output,
        tables=tables,
        exclude_tables=exclude_tables,
        clickhouse_engines=clickhouse_engines,
        relationships=relationships,
        dialect=dialect,
        single_file=single_file,
        base=base,
        database=database,
    )


@app.command()
def export_models(
    output: str | None = typer.Option(
        None, "--output", "-o", help="Output path for the model state JSON file",
    ),
    database: str | None = typer.Option(
        None, "--database", "-d", help="Target database name"
    ),
):
    """Export current model definitions to a JSON state file for offline diffs."""
    validate_directory()
    handle_export_models(output=output, database=database)
