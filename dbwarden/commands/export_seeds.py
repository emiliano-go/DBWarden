from __future__ import annotations

from dbwarden.logging import get_logger
from dbwarden.output import error


def export_seeds_cmd(
    database: str | None = None,
    all_databases: bool = False,
    output_dir: str = "seeds",
) -> None:
    from dbwarden.plugin import HookRegistry

    if HookRegistry.is_registered("seed_export"):
        HookRegistry.execute_single(
            "seed_export",
            database=database,
            all_databases=all_databases,
            output_dir=output_dir,
        )
        return

    raise RuntimeError(
        "Seed export requires dbwarden-seeds plugin. "
        "Install it: `dbwarden plugin add dbwarden-seeds`"
    )
