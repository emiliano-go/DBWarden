from __future__ import annotations

import json
import os
from pathlib import Path

from dbwarden.config import get_database
from dbwarden.engine.model_discovery import get_all_model_tables
from dbwarden.engine.offline import model_state_to_dict


def export_models_cmd(
    output: str = ".dbwarden/model_state.json",
    database: str | None = None,
) -> None:
    """Export current model definitions to a JSON state file for offline diffs.

    Args:
        output: Path to write the model state JSON file.
        database: Target database name.
    """
    config = get_database(database)
    model_paths = config.model_paths

    if not model_paths:
        from dbwarden.commands.make_migrations import auto_discover_model_paths
        model_paths = auto_discover_model_paths()

    if not model_paths:
        msg = "No model paths found. Set model_paths in database_config(...) or ensure models/ directory exists."
        raise ValueError(msg)

    tables = get_all_model_tables(model_paths, db_name=database)
    state = model_state_to_dict(tables)

    out_path = Path(output)
    out_path.parent.mkdir(parents=True, exist_ok=True)
    out_path.write_text(json.dumps(state, indent=2, default=str) + "\n")

    from dbwarden.commands.make_migrations import console
    console.print(f"Exported {len(tables)} model(s) to {out_path}", style="green")
