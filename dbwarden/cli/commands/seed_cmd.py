import typer

from dbwarden.cli.app import seed_app
from dbwarden.cli.validators import validate_directory
from dbwarden.commands import (
    handle_seed_apply,
    handle_seed_create,
    handle_seed_export,
    handle_seed_list,
    handle_seed_rollback,
)


@seed_app.command("create")
def seed_create(
    description: str = typer.Argument(..., help="Description for the seed"),
    seed_type: str = typer.Option(
        "sql", "--type", "-t", help="Seed type: sql or python"
    ),
    verbose: bool = typer.Option(
        False, "--verbose", "-v", help="Enable verbose logging"
    ),
    database: str | None = typer.Option(
        None, "--database", "-d", help="Target database name"
    ),
):
    """Create a new seed file."""
    validate_directory()
    handle_seed_create(
        description=description,
        seed_type=seed_type,
        database=database,
        verbose=verbose,
    )


@seed_app.command("apply")
def seed_apply(
    version: str | None = typer.Option(
        None, "--version", "-v", help="Apply a specific seed version"
    ),
    dry_run: bool = typer.Option(
        False, "--dry-run", help="Show what would be applied without executing"
    ),
    database: str | None = typer.Option(
        None, "--database", "-d", help="Target database name"
    ),
    all_databases: bool = typer.Option(
        False, "--all", "-a", help="Apply seeds on all databases"
    ),
    verbose: bool = typer.Option(
        False, "--verbose", "-v", help="Enable verbose logging"
    ),
):
    """Apply pending seeds."""
    validate_directory()
    handle_seed_apply(
        version=version,
        dry_run=dry_run,
        database=database,
        all_databases=all_databases,
        verbose=verbose,
    )


@seed_app.command("list")
def seed_list(
    database: str | None = typer.Option(
        None, "--database", "-d", help="Target database name"
    ),
    all_databases: bool = typer.Option(
        False, "--all", "-a", help="Show seeds for all databases"
    ),
    verbose: bool = typer.Option(
        False, "--verbose", "-v", help="Enable verbose logging"
    ),
    prune: bool = typer.Option(
        False, "--prune", help="Remove tracking records for seed files that no longer exist"
    ),
):
    """List seed files and their applied status."""
    validate_directory()
    handle_seed_list(
        database=database,
        all_databases=all_databases,
        verbose=verbose,
        prune=prune,
    )


@seed_app.command("export")
def seed_export(
    database: str | None = typer.Option(
        None, "--database", "-d", help="Target database name"
    ),
    all_databases: bool = typer.Option(
        False, "--all", "-a", help="Export seeds for all configured databases"
    ),
    output_dir: str = typer.Option(
        "seeds", "--output-dir", "-o", help="Output directory for ROC seed files (default: seeds/)"
    ),
):
    """Export code seeds to ROC SQL files for stateless application."""
    handle_seed_export(
        database=database,
        all_databases=all_databases,
        output_dir=output_dir,
    )


@seed_app.command("rollback")
def seed_rollback(
    count: int | None = typer.Option(
        None, "--count", "-c", help="Number of seeds to rollback"
    ),
    to_version: str | None = typer.Option(
        None, "--to-version", "-t", help="Rollback to a specific version"
    ),
    database: str | None = typer.Option(
        None, "--database", "-d", help="Target database name"
    ),
    all_databases: bool = typer.Option(
        False, "--all", "-a", help="Rollback seeds in all databases"
    ),
    verbose: bool = typer.Option(
        False, "--verbose", "-v", help="Enable verbose logging"
    ),
):
    """Rollback seed tracking records (allows re-application)."""
    validate_directory()
    handle_seed_rollback(
        count=count,
        to_version=to_version,
        database=database,
        all_databases=all_databases,
        verbose=verbose,
    )
