import typer

from dbwarden.cli.validators import validate_directory
from dbwarden.config import set_dev_mode, set_strict_translation
from dbwarden.commands import (
    handle_check_db,
    handle_check,
    handle_config,
    handle_database_add,
    handle_database_list,
    handle_database_remove,
    handle_diff,
    handle_downgrade,
    handle_generate_models,
    handle_history,
    handle_init,
    handle_lock_status,
    handle_make_migrations,
    handle_make_rollback,
    handle_migrate,
    handle_new,
    handle_rollback,
    handle_seed_apply,
    handle_seed_create,
    handle_seed_list,
    handle_seed_rollback,
    handle_snapshot,
    handle_squash,
    handle_status,
    handle_unlock,
    handle_version,
    handle_settings_show_command,
    handle_settings_default_set_command,
    handle_settings_database_add_command,
    handle_settings_database_remove_command,
    handle_settings_database_rename_command,
    handle_settings_database_set_dev_command,
    handle_settings_database_clear_dev_command,
)
from dbwarden.logging import get_logger

app = typer.Typer(
    help="""DBWarden - Professional database migration system for SQLAlchemy models

All commands support the --verbose / -v flag for detailed output.""",
    add_completion=False,
)

database_app = typer.Typer(help="Manage databases in warden.toml")
app.add_typer(database_app, name="database")
settings_app = typer.Typer(help="Manage DBWarden Python settings")
app.add_typer(settings_app, name="settings")
seed_app = typer.Typer(help="Manage seed data")
app.add_typer(seed_app, name="seed")


@app.callback()
def app_callback(
    dev: bool = typer.Option(
        False,
        "--dev",
        help="Use development database settings (dev_database_url/dev_database_type)",
    ),
    strict_translation: bool = typer.Option(
        False,
        "--strict-translation",
        help="Fail when a type/default cannot be translated for target backend",
    ),
):
    """Global CLI options."""
    set_dev_mode(dev)
    set_strict_translation(strict_translation)


@app.command()
def init(
    database: str | None = typer.Option(
        None, "--database", "-d", help="Database name to create migration directory for"
    ),
):
    """Initialize the migrations directory."""
    handle_init(database=database)


@database_app.command("list")
def database_list():
    """List all configured databases."""
    handle_database_list()


@database_app.command("add")
def database_add(
    name: str = typer.Argument(..., help="Database name"),
    url: str = typer.Option(..., "--url", "-u", help="SQLAlchemy database URL"),
    database_type: str | None = typer.Option(
        None,
        "--type",
        "-t",
        help="Database type: sqlite, postgresql, mysql, mariadb, clickhouse",
    ),
    model_paths: list[str] | None = typer.Option(
        None, "--model-paths", "-m", help="Model paths"
    ),
    migrations_dir: str | None = typer.Option(
        None, "--migrations-dir", help="Migration directory"
    ),
    seed_table: str | None = typer.Option(
        None, "--seed-table", help="Seed tracking table name",
    ),
    default: bool = typer.Option(False, "--default", help="Set as default database"),
):
    """Add a new database to the configuration."""
    handle_database_add(
        name=name,
        url=url,
        database_type=database_type,
        model_paths=model_paths,
        migrations_dir=migrations_dir,
        seed_table=seed_table,
        default=default,
    )


@database_app.command("remove")
def database_remove(
    name: str = typer.Argument(..., help="Database name to remove"),
    force: bool = typer.Option(
        False, "--force", help="Force removal of default database"
    ),
):
    """Remove a database from the configuration."""
    handle_database_remove(name=name, force=force)


@settings_app.command("show")
def settings_show(
    database: str | None = typer.Argument(None, help="Database name"),
    all_databases: bool = typer.Option(False, "--all", help="Show all databases"),
):
    """Show current settings configuration."""
    handle_settings_show_command(database=database, all_databases=all_databases)


@settings_app.command("default-database")
def settings_default_database_set(
    name: str = typer.Argument(..., help="Database name to set as default"),
):
    """Set default database."""
    handle_settings_default_set_command(name)


@settings_app.command("database-add")
def settings_database_add(
    name: str = typer.Argument(..., help="Database name"),
    database_type: str = typer.Option(..., "--type", "-t", help="Database type"),
    url: str = typer.Option(..., "--url", "-u", help="Database URL"),
    migrations_dir: str | None = typer.Option(
        None, "--migrations-dir", help="Migrations directory"
    ),
    migration_table: str | None = typer.Option(
        None, "--migration-table", help="Migration tracking table name",
    ),
    seed_table: str | None = typer.Option(
        None, "--seed-table", help="Seed tracking table name",
    ),
    model_paths: list[str] | None = typer.Option(
        None, "--model-path", help="Model path (repeatable)"
    ),
    dev_type: str | None = typer.Option(None, "--dev-type", help="Dev database type"),
    dev_url: str | None = typer.Option(None, "--dev-url", help="Dev database URL"),
    overlap_models: bool = typer.Option(
        False,
        "--overlap-models",
        help="Allow model path overlap with other databases",
    ),
    default: bool = typer.Option(False, "--default", help="Set as default database"),
):
    """Add database settings entry."""
    handle_settings_database_add_command(
        name=name,
        database_type=database_type,
        url=url,
        migrations_dir=migrations_dir,
        migration_table=migration_table,
        seed_table=seed_table,
        model_paths=model_paths,
        dev_type=dev_type,
        dev_url=dev_url,
        overlap_models=overlap_models,
        default=default,
    )


@settings_app.command("database-remove")
def settings_database_remove(
    name: str = typer.Argument(..., help="Database name"),
):
    """Remove database settings entry."""
    handle_settings_database_remove_command(name)


@settings_app.command("database-rename")
def settings_database_rename(
    old: str = typer.Argument(..., help="Current database name"),
    new: str = typer.Argument(..., help="New database name"),
):
    """Rename database entry."""
    handle_settings_database_rename_command(old, new)


@settings_app.command("database-set-dev")
def settings_database_set_dev(
    name: str = typer.Argument(..., help="Database name"),
    dev_type: str = typer.Option(..., "--type", help="Dev database type"),
    dev_url: str = typer.Option(..., "--url", help="Dev database URL"),
):
    """Set development database settings."""
    handle_settings_database_set_dev_command(name, dev_type, dev_url)


@settings_app.command("database-clear-dev")
def settings_database_clear_dev(
    name: str = typer.Argument(..., help="Database name"),
):
    """Clear development database settings."""
    handle_settings_database_clear_dev_command(name)


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
        database=database,
    )


@app.command()
def make_migrations(
    description: str = typer.Argument(None, help="Description for the migration"),
    verbose: bool = typer.Option(
        False, "--verbose", "-v", help="Enable verbose logging"
    ),
    plan: bool = typer.Option(
        False,
        "--plan",
        help="Output migration plan JSON without writing files",
    ),
    database: str | None = typer.Option(
        None, "--database", "-d", help="Target database name"
    ),
    rename: list[str] = typer.Option(
        [],
        "--rename",
        help="Explicitly rename column (format: table.old_name:new_name). Can be repeated.",
    ),
    safe_type_change: bool = typer.Option(
        False,
        "--safe-type-change",
        help="Use multi-step safe type change (add temp column, backfill, swap, drop old)",
    ),
    rename_table: list[str] = typer.Option(
        [],
        "--rename-table",
        help="Declare a table rename as old_table:new_table. Repeatable.",
    ),
    concurrent: bool = typer.Option(
        True,
        "--concurrent/--no-concurrent",
        help="Use CREATE INDEX CONCURRENTLY on PostgreSQL (disable inside transactions)",
    ),
):
    """Auto-generate SQL migration from SQLAlchemy models."""
    validate_directory()
    handle_make_migrations(
        description=description,
        verbose=verbose,
        database=database,
        output_plan=plan,
        rename_flags=rename,
        safe_type_change=safe_type_change,
        rename_table_flags=rename_table,
        concurrent=concurrent,
    )


@app.command()
def new(
    description: str = typer.Argument(..., help="Description of the migration"),
    version: str | None = typer.Option(
        None, "--version", help="Version of the migration"
    ),
    database: str | None = typer.Option(
        None, "--database", "-d", help="Target database name"
    ),
):
    """Create a new manual migration file."""
    validate_directory()
    handle_new(description=description, version=version, database=database)


@app.command()
def migrate(
    count: int | None = typer.Option(
        None, "--count", "-c", help="Number of migrations to apply"
    ),
    to_version: str | None = typer.Option(
        None, "--to-version", "-t", help="Migrate to a specific version"
    ),
    verbose: bool = typer.Option(
        False, "--verbose", "-v", help="Enable verbose logging"
    ),
    database: str | None = typer.Option(
        None, "--database", "-d", help="Target database name"
    ),
    all_databases: bool = typer.Option(
        False, "--all", "-a", help="Run migrations on all databases sequentially"
    ),
    baseline: bool = typer.Option(
        False, "--baseline", help="Mark migrations as applied without executing"
    ),
    with_backup: bool = typer.Option(
        False, "--with-backup", "-b", help="Create a backup before migrating"
    ),
    backup_dir: str | None = typer.Option(
        None, "--backup-dir", help="Directory for backup files"
    ),
    dry_run: bool = typer.Option(
        False, "--dry-run", help="Show what would be applied without executing"
    ),
    sandbox: bool = typer.Option(
        False, "--sandbox", help="Apply migrations in a temporary sandbox database"
    ),
):
    """Apply pending migrations to the database."""
    validate_directory()
    handle_migrate(
        count=count,
        to_version=to_version,
        verbose=verbose,
        database=database,
        all_databases=all_databases,
        baseline=baseline,
        with_backup=with_backup,
        backup_dir=backup_dir,
        dry_run=dry_run,
        sandbox=sandbox,
    )


@app.command()
def rollback(
    count: int | None = typer.Option(
        None, "--count", "-c", help="Number of migrations to rollback"
    ),
    to_version: str | None = typer.Option(
        None, "--to-version", "-t", help="Rollback to a specific version"
    ),
    verbose: bool = typer.Option(
        False, "--verbose", "-v", help="Enable verbose logging"
    ),
    database: str | None = typer.Option(
        None, "--database", "-d", help="Target database name"
    ),
):
    """Rollback the last applied migration."""
    validate_directory()
    handle_rollback(
        count=count, to_version=to_version, verbose=verbose, database=database
    )


@app.command()
def downgrade(
    to_version: str = typer.Option(
        ..., "--to", "-t", help="Target version to downgrade to"
    ),
    verbose: bool = typer.Option(
        False, "--verbose", "-v", help="Enable verbose logging"
    ),
    database: str | None = typer.Option(
        None, "--database", "-d", help="Target database name"
    ),
):
    """Downgrade to a specific migration version by reverting applied migrations."""
    validate_directory()
    handle_downgrade(to_version=to_version, verbose=verbose, database=database)


@app.command()
def make_rollback(
    migration_file: str = typer.Argument(
        ..., help="Path to migration SQL file"
    ),
):
    """Generate a rollback SQL file for a given migration file."""
    handle_make_rollback(migration_file=migration_file)


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
def history(
    database: str | None = typer.Option(
        None, "--database", "-d", help="Target database name"
    ),
):
    """Show the full migration history."""
    validate_directory()
    handle_history(database=database)


@app.command()
def status(
    database: str | None = typer.Option(
        None, "--database", "-d", help="Target database name"
    ),
    all_databases: bool = typer.Option(
        False, "--all", "-a", help="Show status for all databases"
    ),
):
    """Show migration status (applied and pending)."""
    validate_directory()
    handle_status(database=database, all_databases=all_databases)


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
def diff(
    diff_type: str = typer.Argument(
        "all", help="Type of diff (models, migrations, all)"
    ),
    verbose: bool = typer.Option(
        False, "--verbose", "-v", help="Enable verbose logging"
    ),
    database: str | None = typer.Option(
        None, "--database", "-d", help="Target database name"
    ),
):
    """Show structural differences between models and database."""
    validate_directory()
    handle_diff(diff_type=diff_type, verbose=verbose, database=database)


@app.command()
def squash(
    verbose: bool = typer.Option(
        False, "--verbose", "-v", help="Enable verbose logging"
    ),
    database: str | None = typer.Option(
        None, "--database", "-d", help="Target database name"
    ),
):
    """Merge multiple consecutive migrations into one."""
    validate_directory()
    handle_squash(verbose=verbose, database=database)


@app.command()
def config():
    """Display current warden.toml configuration."""
    handle_config()


@app.command()
def version():
    """Display DBWarden version and compatibility information."""
    handle_version()


@app.command()
def lock_status(
    database: str | None = typer.Option(
        None, "--database", "-d", help="Target database name"
    ),
):
    """Check if migration is currently locked."""
    validate_directory()
    handle_lock_status(database=database)


@app.command()
def unlock(
    database: str | None = typer.Option(
        None, "--database", "-d", help="Target database name"
    ),
):
    """Release the migration lock."""
    validate_directory()
    handle_unlock(database=database)


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
):
    """List seed files and their applied status."""
    validate_directory()
    handle_seed_list(
        database=database,
        all_databases=all_databases,
        verbose=verbose,
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
        verbose=verbose,
    )


def main() -> None:
    """Main entry point for DBWarden CLI."""
    from dbwarden.database import reset_connection_logging

    reset_connection_logging()
    app()


if __name__ == "__main__":
    main()
