from __future__ import annotations

from rich.table import Table

from dbwarden.engine.safety import issues_to_json, load_issues
from dbwarden.exceptions import DBDisconnectedError
from dbwarden.output import console


def check_cmd(
    output_format: str = "txt",
    database: str | None = None,
    force: bool = False,
) -> None:
    try:
        issues = load_issues(database=database)
    except DBDisconnectedError:
        console.print(
            "Database disconnected \u2014 cannot compare against live schema. "
            "Run with models only (no live compatibility checks).",
            style="yellow",
        )
        return

    if output_format == "json":
        console.print(issues_to_json(issues), markup=False, highlight=False)
    elif output_format == "txt":
        _print_issues_table(issues, database=database)
    else:
        raise ValueError(f"Unknown output format: {output_format}")

    errors = [issue for issue in issues if issue.severity.upper() == "ERROR"]
    warnings = [issue for issue in issues if issue.severity.upper() == "WARNING"]
    if errors:
        raise RuntimeError("Safety check failed: blocking changes detected.")
    if warnings and not force:
        raise RuntimeError("Safety check failed: warning-level changes require --force.")


def _print_issues_table(issues, database: str | None = None) -> None:
    db_label = database or "default"
    table = Table(
        title=f"Safety Check - {db_label}",
        show_header=True,
        header_style="bold magenta",
    )
    table.add_column("Severity", style="cyan")
    table.add_column("Change", style="white")
    table.add_column("Table", style="green")
    table.add_column("Column", style="yellow")
    table.add_column("Message", style="white")
    table.add_column("Required Flag", style="magenta")

    for issue in issues:
        table.add_row(
            issue.severity,
            issue.change_type,
            issue.table_name,
            issue.column_name or "",
            issue.message,
            issue.required_flag or "",
        )

    console.print(table)
    if not issues:
        console.print("No schema changes detected.", style="green")
