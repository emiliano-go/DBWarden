from dbwarden.commands.check import check_cmd
from dbwarden.commands.check_db import check_db_cmd
from dbwarden.commands.downgrade import downgrade_cmd
from dbwarden.commands.export_models import export_models_cmd
from dbwarden.commands.extra import diff_cmd, lock_status_cmd, squash_cmd, unlock_cmd
from dbwarden.commands.generate_models import generate_models_cmd
from dbwarden.commands.history import history_cmd
from dbwarden.commands.init import init_cmd
from dbwarden.commands.make_migrations import make_migrations_cmd, new_migration_cmd
from dbwarden.commands.make_rollback import make_rollback_cmd
from dbwarden.commands.migrate import migrate_cmd
from dbwarden.commands.rollback import rollback_cmd
from dbwarden.commands.snapshot import snapshot_cmd
from dbwarden.commands.seeds import (
    seed_apply_cmd,
    seed_create_cmd,
    seed_list_cmd,
    seed_rollback_cmd,
)
from dbwarden.commands.status import status_cmd
from dbwarden.commands.settings import (
    handle_settings_database_add,
    handle_settings_database_clear_dev,
    handle_settings_database_remove,
    handle_settings_database_rename,
    handle_settings_database_set_dev,
    handle_settings_default_set,
    handle_settings_show,
)
from dbwarden.commands.utils import config_cmd, version_cmd
from dbwarden.exceptions import ConfigurationError


def handle_database_list() -> None:
    """Legacy alias for settings list."""
    handle_settings_show(database=None, all_databases=True)


def handle_database_add(
    name: str,
    url: str,
    database_type: str | None = None,
    model_paths: list[str] | None = None,
    migrations_dir: str | None = None,
    seed_table: str | None = None,
    default: bool = False,
) -> None:
    """Legacy alias for settings database add."""
    if not database_type:
        raise ConfigurationError("--type is required for legacy database add command")
    handle_settings_database_add(
        name=name,
        database_type=database_type,
        url=url,
        migrations_dir=migrations_dir,
        seed_table=seed_table,
        model_paths=model_paths,
        default=default,
    )


def handle_database_remove(name: str, force: bool = False) -> None:
    """Legacy alias for settings database remove.

    force is ignored under settings-backed config.
    """
    _ = force
    handle_settings_database_remove(name)


def handle_init(database: str | None = None) -> None:
    """Handle init command."""
    init_cmd(database=database)


def handle_make_migrations(
    description: str | None,
    verbose: bool,
    database: str | None = None,
    output_plan: bool = False,
    rename_flags: list[str] | None = None,
    safe_type_change: bool = False,
    rename_table_flags: list[str] | None = None,
    concurrent: bool = True,
    offline: bool = False,
) -> None:
    """Handle make-migrations command."""
    make_migrations_cmd(
        description=description,
        verbose=verbose,
        database=database,
        output_plan=output_plan,
        rename_flags=rename_flags,
        safe_type_change=safe_type_change,
        rename_table_flags=rename_table_flags,
        concurrent=concurrent,
        offline=offline,
    )


def handle_new(
    description: str, version: str | None, database: str | None = None
) -> None:
    """Handle new command."""
    new_migration_cmd(description=description, version=version, database=database)


def handle_migrate(
    count: int | None,
    to_version: str | None,
    verbose: bool,
    database: str | None = None,
    all_databases: bool = False,
    baseline: bool = False,
    with_backup: bool = False,
    backup_dir: str | None = None,
    dry_run: bool = False,
    sandbox: bool = False,
) -> None:
    """Handle migrate command."""
    migrate_cmd(
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


def handle_rollback(
    count: int | None,
    to_version: str | None,
    verbose: bool,
    database: str | None = None,
) -> None:
    """Handle rollback command."""
    rollback_cmd(count=count, to_version=to_version, verbose=verbose, database=database)


def handle_history(database: str | None = None) -> None:
    """Handle history command."""
    history_cmd(database=database)


def handle_status(database: str | None = None, all_databases: bool = False) -> None:
    """Handle status command."""
    status_cmd(database=database, all_databases=all_databases)


def handle_check_db(output_format: str, database: str | None = None) -> None:
    """Handle check-db command."""
    check_db_cmd(output_format=output_format, database=database)


def handle_check(
    output_format: str,
    database: str | None = None,
    force: bool = False,
) -> None:
    """Handle safety check command."""
    check_cmd(output_format=output_format, database=database, force=force)


def handle_diff(diff_type: str, verbose: bool, database: str | None = None) -> None:
    """Handle diff command."""
    diff_cmd(diff_type=diff_type, verbose=verbose, database=database)


def handle_squash(verbose: bool, database: str | None = None) -> None:
    """Handle squash command."""
    squash_cmd(verbose=verbose, database=database)


def handle_config() -> None:
    """Handle config command."""
    config_cmd()


def handle_version() -> None:
    """Handle version command."""
    version_cmd()


def handle_lock_status(database: str | None = None) -> None:
    """Handle lock-status command."""
    lock_status_cmd(database=database)


def handle_unlock(database: str | None = None) -> None:
    """Handle unlock command."""
    unlock_cmd(database=database)


def handle_settings_show_command(
    database: str | None = None,
    all_databases: bool = False,
) -> None:
    handle_settings_show(database=database, all_databases=all_databases)


def handle_settings_default_set_command(name: str) -> None:
    handle_settings_default_set(name)


def handle_settings_database_add_command(
    name: str,
    database_type: str,
    url: str,
    migrations_dir: str | None = None,
    migration_table: str | None = None,
    seed_table: str | None = None,
    model_paths: list[str] | None = None,
    dev_type: str | None = None,
    dev_url: str | None = None,
    overlap_models: bool = False,
    default: bool = False,
) -> None:
    handle_settings_database_add(
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


def handle_settings_database_remove_command(name: str) -> None:
    handle_settings_database_remove(name)


def handle_settings_database_rename_command(old: str, new: str) -> None:
    handle_settings_database_rename(old, new)


def handle_settings_database_set_dev_command(
    name: str, dev_type: str, dev_url: str
) -> None:
    handle_settings_database_set_dev(name, dev_type, dev_url)


def handle_settings_database_clear_dev_command(name: str) -> None:
    handle_settings_database_clear_dev(name)


def handle_downgrade(
    to_version: str,
    verbose: bool = False,
    database: str | None = None,
) -> None:
    downgrade_cmd(to_version=to_version, verbose=verbose, database=database)


def handle_make_rollback(
    migration_file: str,
) -> None:
    make_rollback_cmd(migration_file=migration_file)


def handle_snapshot(
    table_name: str,
    database: str | None = None,
) -> None:
    snapshot_cmd(table_name=table_name, database=database)


def handle_generate_models(
    output: str = "models",
    tables: str | None = None,
    exclude_tables: str | None = None,
    clickhouse_engines: bool = False,
    relationships: bool = False,
    dialect: str | None = None,
    single_file: bool = False,
    database: str | None = None,
) -> None:
    if not clickhouse_engines:
        from dbwarden.config import get_database
        try:
            config = get_database(database)
            if config.database_type == "clickhouse":
                clickhouse_engines = True
        except Exception:
            pass
    generate_models_cmd(
        output=output,
        tables=tables,
        exclude_tables=exclude_tables,
        clickhouse_engines=clickhouse_engines,
        relationships=relationships,
        dialect=dialect,
        single_file=single_file,
        database=database,
    )


def handle_export_models(
    output: str = ".dbwarden/model_state.json",
    database: str | None = None,
) -> None:
    """Handle export-models command."""
    export_models_cmd(output=output, database=database)


def handle_seed_create(
    description: str,
    seed_type: str = "sql",
    database: str | None = None,
    verbose: bool = False,
) -> None:
    seed_create_cmd(
        description=description,
        seed_type=seed_type,
        database=database,
        verbose=verbose,
    )


def handle_seed_apply(
    version: str | None = None,
    dry_run: bool = False,
    database: str | None = None,
    all_databases: bool = False,
    verbose: bool = False,
) -> None:
    seed_apply_cmd(
        version=version,
        dry_run=dry_run,
        database=database,
        all_databases=all_databases,
        verbose=verbose,
    )


def handle_seed_list(
    database: str | None = None,
    all_databases: bool = False,
    verbose: bool = False,
) -> None:
    seed_list_cmd(
        database=database,
        all_databases=all_databases,
        verbose=verbose,
    )


def handle_seed_rollback(
    count: int | None = None,
    to_version: str | None = None,
    database: str | None = None,
    verbose: bool = False,
) -> None:
    seed_rollback_cmd(
        count=count,
        to_version=to_version,
        database=database,
        verbose=verbose,
    )
