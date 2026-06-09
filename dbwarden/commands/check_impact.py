from __future__ import annotations

import json
import os

from dbwarden.engine.impact import analyze_impact
from dbwarden.engine.version import get_migration_filepaths_by_version, get_migrations_directory


def check_impact_cmd(
    migration: str,
    out: str = "text",
    scan_path: str = ".",
    deep: bool = False,
    verbose: bool = False,
    database: str | None = None,
) -> None:
    plan_path = _resolve_plan_path(migration, database)
    if not plan_path:
        return

    result = analyze_impact(
        plan_path=plan_path,
        scan_path=scan_path,
        deep=deep,
        verbose=verbose,
    )

    if out == "json":
        print(json.dumps(result, indent=2, default=str))
        return

    from dbwarden.commands.make_migrations import console

    impact = result.get("impact", [])
    if not impact:
        console.print("[green]No impact detected[/green]")
        console.print(f"Scanned: {scan_path}")
        return

    console.print(f"[bold]Migration:[/bold] {result.get('migration_id', plan_path)}")
    console.print(f"[bold]Impact detected:[/bold] {len(impact)} operation(s) affect code")
    console.print()

    for item in impact:
        op_type = item.get("operation_type", "?")
        table = item.get("table", "")
        column = item.get("column", "")
        refs = item.get("references", [])

        label = f"{op_type}"
        if table:
            label += f" on {table}"
        if column:
            label += f".{column}"
        console.print(f"[yellow]{label}[/yellow]")
        console.print(f"  References: {len(refs)}")

        for ref in refs[:10]:
            fpath = ref.get("file", "")
            line = ref.get("line", 0)
            snippet = ref.get("snippet", "")
            kind = ref.get("kind", "")
            short_path = os.path.relpath(fpath, scan_path) if os.path.isabs(fpath) else fpath
            console.print(f"    {short_path}:{line}  [dim]{kind}[/dim]")
            console.print(f"      [italic]{snippet}[/italic]")

        if len(refs) > 10:
            console.print(f"    ... and {len(refs) - 10} more")
        console.print()


def _resolve_plan_path(migration: str, database: str | None = None) -> str | None:
    from dbwarden.commands.make_migrations import console

    if migration.endswith(".plan.json") and os.path.isfile(migration):
        return migration

    if os.path.isfile(migration):
        base, _ext = os.path.splitext(migration)
        plan_path = base + ".plan.json"
        if os.path.isfile(plan_path):
            return plan_path
        console.print(f"[red]Plan file not found: {plan_path}[/red]")
        return None

    try:
        migrations_dir = get_migrations_directory(database)
    except Exception as exc:
        console.print(f"[red]{exc}[/red]")
        return None

    filepaths = get_migration_filepaths_by_version(migrations_dir)
    if migration in filepaths:
        sql_path = filepaths[migration]
        base, _ext = os.path.splitext(sql_path)
        plan_path = base + ".plan.json"
        if os.path.isfile(plan_path):
            return plan_path

    for ver, sql_path in sorted(filepaths.items()):
        if ver.startswith(migration):
            base, _ext = os.path.splitext(sql_path)
            plan_path = base + ".plan.json"
            if os.path.isfile(plan_path):
                return plan_path

    console.print(f"[red]No plan file found for migration: {migration}[/red]")
    console.print(f"[yellow]Migrations directory: {migrations_dir}[/yellow]")
    return None
