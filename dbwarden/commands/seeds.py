from __future__ import annotations


def seed_create_cmd(
    description: str,
    seed_type: str = "sql",
    database: str | None = None,
    verbose: bool = False,
) -> None:
    from dbwarden.plugin import HookRegistry

    if HookRegistry.is_registered("seed_create"):
        HookRegistry.execute_single(
            "seed_create",
            description,
            seed_type=seed_type,
            database=database,
            verbose=verbose,
        )
        return

    raise RuntimeError(
        "Seed creation requires dbwarden-seeds plugin. "
        "Install it: `dbwarden plugin add dbwarden-seeds`"
    )


def seed_apply_cmd(
    version: str | None = None,
    dry_run: bool = False,
    database: str | None = None,
    all_databases: bool = False,
    verbose: bool = False,
) -> None:
    from dbwarden.plugin import HookRegistry

    if HookRegistry.is_registered("seed_apply"):
        HookRegistry.execute_single(
            "seed_apply",
            version=version,
            dry_run=dry_run,
            database=database,
            all_databases=all_databases,
            verbose=verbose,
        )
        return

    raise RuntimeError(
        "Seed application requires dbwarden-seeds plugin. "
        "Install it: `dbwarden plugin add dbwarden-seeds`"
    )


def seed_list_cmd(
    database: str | None = None,
    all_databases: bool = False,
    verbose: bool = False,
    prune: bool = False,
) -> None:
    from dbwarden.plugin import HookRegistry

    if HookRegistry.is_registered("seed_list"):
        HookRegistry.execute_single(
            "seed_list",
            database=database,
            all_databases=all_databases,
            verbose=verbose,
            prune=prune,
        )
        return

    raise RuntimeError(
        "Seed listing requires dbwarden-seeds plugin. "
        "Install it: `dbwarden plugin add dbwarden-seeds`"
    )


def seed_rollback_cmd(
    count: int | None = None,
    to_version: str | None = None,
    database: str | None = None,
    all_databases: bool = False,
    verbose: bool = False,
) -> None:
    from dbwarden.plugin import HookRegistry

    if HookRegistry.is_registered("seed_rollback"):
        HookRegistry.execute_single(
            "seed_rollback",
            count=count,
            to_version=to_version,
            database=database,
            all_databases=all_databases,
            verbose=verbose,
        )
        return

    raise RuntimeError(
        "Seed rollback requires dbwarden-seeds plugin. "
        "Install it: `dbwarden plugin add dbwarden-seeds`"
    )
