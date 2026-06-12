from __future__ import annotations

import hashlib
import importlib
from pathlib import Path
from typing import Any

from sqlalchemy import Column, MetaData, Table, create_engine, insert, text
from sqlalchemy.orm import Session as SASession

from dbwarden.config import get_database, get_multi_db_config
from dbwarden.engine.code_seeds import discover_code_seeds
from dbwarden.exceptions import SeedError
from dbwarden.logging import get_logger
from dbwarden.output import console
from dbwarden.seed import Seed, _row_to_dict

ROC_FILE_PREFIX = "ROC__"

DIALECT_MODULE_MAP: dict[str, str] = {
    "sqlite": "sqlalchemy.dialects.sqlite",
    "postgresql": "sqlalchemy.dialects.postgresql",
    "mysql": "sqlalchemy.dialects.mysql",
    "mariadb": "sqlalchemy.dialects.mysql",
    "clickhouse": "clickhouse_sqlalchemy.dialect",
}

DB_TYPE_TO_INSTALL_HINT: dict[str, str] = {
    "clickhouse": "clickhouse-sqlalchemy",
}


def export_seeds_cmd(
    database: str | None = None,
    all_databases: bool = False,
    output_dir: str = "seeds",
    render_dialect: str | None = None,
) -> None:
    """Export code seeds to ROC SQL files for stateless application.

    Discovers code seeds from ``_seed_registry``, renders ``INSERT ... ON CONFLICT``
    statements per-dialect, and writes a single ``ROC__<db>__code_seeds.sql`` file
    per database into *output_dir*.

    Logic-based seeds (those with a ``generate(session)`` method) are executed
    against a temporary in-memory SQLite database.  Row-based seeds that precede
    the logic seed in FK order are pre-loaded into that temp DB so that
    ``generate()`` can query dependency tables.

    Args:
        database: Target database handle (required unless ``--all``).
        all_databases: Export seeds for every configured database.
        output_dir: Directory to write the ROC seed files (default ``seeds/``).
        render_dialect: Override literal-rendering dialect (use with caution).
    """
    if all_databases:
        multi_config = get_multi_db_config()
        db_names = list(multi_config.databases)
    else:
        config = get_database(database)
        multi_config = get_multi_db_config()
        db_names = [database or multi_config.default]

    for db_name in db_names:
        try:
            _export_database(db_name, output_dir, render_dialect)
        except Exception as e:
            console.print(f"  Error exporting seeds for '{db_name}': {e}", style="bold red")
            continue


def _export_database(
    db_name: str,
    output_dir: str,
    render_dialect: str | None = None,
) -> None:
    console.print(f"Exporting seeds for '{db_name}'...", style="bold cyan")

    seeds = discover_code_seeds(db_name)
    if not seeds:
        console.print(f"  No code seeds found for '{db_name}'.", style="yellow")
        return

    config = get_database(db_name)
    dialect = _resolve_dialect(config.database_type, render_dialect)

    ordered = _ordered_seeds(seeds)

    statements: list[str] = []
    for seed_cls in ordered:
        meta = seed_cls.__seed_meta__
        if meta is None:
            continue
        if not hasattr(seed_cls, "model") or seed_cls.model is None:
            console.print(f"  Skipping {seed_cls.__name__}: no 'model' attribute", style="yellow")
            continue

        description = meta.description or seed_cls.__name__

        if hasattr(seed_cls, "rows") and seed_cls.rows is not None:
            stmts = _export_row_seed(seed_cls, dialect)
            statements.extend(stmts)
            console.print(f"  Exported {description}: {len(stmts)} row(s)", style="green")
        elif hasattr(seed_cls, "generate"):
            try:
                stmts = _export_logic_seed(seed_cls, ordered, dialect, db_name)
                statements.extend(stmts)
                console.print(f"  Exported {description} (logic): {len(stmts)} row(s)", style="green")
            except Exception as e:
                console.print(f"  Skipping logic seed {description}: {e}", style="yellow")
        else:
            console.print(f"  Skipping {seed_cls.__name__}: no 'rows' or 'generate()'", style="yellow")

    if not statements:
        console.print(f"  No seed data to export for '{db_name}'.", style="yellow")
        return

    header = "-- upgrade\n\n"
    if render_dialect:
        header += f"-- WARNING: rendered with {render_dialect} dialect, target is {config.database_type} -- verify literals manually\n\n"
    content = header + "\n".join(statements) + "\n"

    out_path = Path(output_dir) / f"{ROC_FILE_PREFIX}{db_name}__code_seeds.sql"
    out_path.parent.mkdir(parents=True, exist_ok=True)
    out_path.write_text(content)

    checksum = hashlib.sha256(content.encode()).hexdigest()[:16]
    console.print(f"  Wrote {out_path}  (checksum: {checksum})", style="green")
    console.print(f"  {len(statements)} statement(s) exported.", style="cyan")


def _ordered_seeds(seeds: list[type[Seed]]) -> list[type[Seed]]:
    """Topologically sort seeds by FK dependency (Kahn's algorithm).

    Seeds whose models have no FK dependencies (or whose FK targets are
    not seeded) are emitted first.  Any remaining (cycle) are appended
    at the end.
    """
    graph: dict[type[Seed], set[type[Seed]]] = {cls: set() for cls in seeds}

    for cls in seeds:
        if not hasattr(cls, "model") or cls.model is None:
            continue
        model = cls.model
        if not hasattr(model, "__table__"):
            continue
        for col in model.__table__.columns:
            for fk in col.foreign_keys:
                ref_table = fk.column.table.name
                for other in seeds:
                    if other is cls:
                        continue
                    if (
                        hasattr(other, "model")
                        and other.model is not None
                        and hasattr(other.model, "__tablename__")
                        and other.model.__tablename__ == ref_table
                    ):
                        graph[cls].add(other)

    in_degree: dict[type[Seed], int] = {cls: len(deps) for cls, deps in graph.items()}
    queue = [cls for cls, deg in in_degree.items() if deg == 0]
    result: list[type[Seed]] = []

    while queue:
        cls = queue.pop(0)
        result.append(cls)
        for other in seeds:
            if cls in graph.get(other, set()):
                in_degree[other] -= 1
                if in_degree[other] == 0:
                    if other not in result and other not in queue:
                        queue.append(other)

    remaining = [cls for cls in seeds if cls not in result]
    result.extend(remaining)
    return result


def _export_row_seed(seed_cls: type[Seed], dialect: Any) -> list[str]:
    """Export a row-based code seed as INSERT statements."""
    meta = seed_cls.__seed_meta__
    model_cls = seed_cls.model
    statements: list[str] = []

    for row in seed_cls.rows:  # type: ignore[attr-defined]
        data = _row_to_dict(row, model_cls)
        stmt = _build_insert_sql(
            table_name=model_cls.__tablename__,
            data=data,
            on_conflict=meta.on_conflict,
            conflict_columns=meta.conflict_columns,
            dialect=dialect,
            model_cls=model_cls,
        )
        statements.append(stmt)

    return statements


def _export_logic_seed(
    seed_cls: type[Seed],
    all_ordered: list[type[Seed]],
    dialect: Any,
    db_name: str,
) -> list[str]:
    """Export a logic-based code seed by running ``generate()`` in temp SQLite.

    Creates an in-memory SQLite database, creates all tables reachable via FK
    closure from the seed's model, pre-seeds with row-based seeds that precede
    this seed in FK order, runs ``generate(connection, session)``, then exports
    the resulting rows as INSERT statements rendered against the *target*
    dialect.
    """
    meta = seed_cls.__seed_meta__
    model_cls = seed_cls.model
    description = meta.description or seed_cls.__name__

    metadata = model_cls.__table__.metadata
    closure = _collect_fk_closure(model_cls.__table__, metadata)
    target_table = model_cls.__table__

    engine = create_engine("sqlite://")

    # Create only the tables in the FK closure (in sorted order)
    tables_to_create = [
        t for t in metadata.sorted_tables if t.name in closure
    ]
    if target_table not in tables_to_create:
        tables_to_create.insert(0, target_table)
    metadata.create_all(engine, tables=tables_to_create)

    def _pre_seed(conn: Any, ordered: list[type[Seed]], until: type[Seed]) -> None:
        for dep in ordered:
            if dep is until:
                break
            if not hasattr(dep, "model") or dep.model is None:
                continue
            if not hasattr(dep, "rows") or dep.rows is None:
                continue
            dep_table_name = dep.model.__tablename__
            for row in dep.rows:
                data = _row_to_dict(row, dep.model)
                cols = ", ".join(data.keys())
                ph = ", ".join(f":{k}" for k in data)
                conn.execute(
                    text(f"INSERT INTO {dep_table_name} ({cols}) VALUES ({ph})"),
                    data,
                )
        conn.commit()

    with engine.begin() as conn:
        _pre_seed(conn, all_ordered, seed_cls)
        session = SASession(bind=conn)
        generate = getattr(seed_cls, "generate")
        generate(conn, session)
        session.flush()

        rows = conn.execute(
            text(f"SELECT * FROM {model_cls.__tablename__}")
        ).mappings().all()

    if not rows:
        console.print(f"    Logic seed {description} produced no rows.", style="yellow")
        return []

    statements: list[str] = []
    for row in rows:
        data = dict(row)
        stmt = _build_insert_sql(
            table_name=model_cls.__tablename__,
            data=data,
            on_conflict=meta.on_conflict,
            conflict_columns=meta.conflict_columns,
            dialect=dialect,
            model_cls=model_cls,
        )
        statements.append(stmt)

    return statements


def _build_insert_sql(
    table_name: str,
    data: dict[str, Any],
    on_conflict: str,
    conflict_columns: list[str] | None,
    dialect: Any,
    model_cls: type | None = None,
) -> str:
    """Build a single ``INSERT`` statement with *dialect*-aware literal rendering.

    Uses ``literal_binds=True`` so that Python values (bool, datetime, None, …)
    are rendered in the target dialect's format — avoiding silent mismatches
    from generic SQL rendering.
    """
    if model_cls is not None and hasattr(model_cls, "__table__"):
        table = model_cls.__table__
    else:
        cols = [Column(k) for k in data]
        table = Table(table_name, MetaData(), *cols)

    stmt = insert(table).values(**data)
    compiled = stmt.compile(dialect=dialect, compile_kwargs={"literal_binds": True})
    sql = str(compiled).rstrip(";")

    conflict = _render_conflict_clause(
        dialect.name, on_conflict, conflict_columns or [], list(data.keys())
    )

    if conflict:
        if dialect.name == "mysql" and on_conflict == "ignore":
            sql = sql.replace("INSERT INTO", "INSERT IGNORE INTO")
        else:
            sql = f"{sql} {conflict}"

    return f"{sql};"


def _render_conflict_clause(
    dialect_name: str,
    on_conflict: str,
    conflict_columns: list[str],
    data_columns: list[str],
) -> str:
    """Return the dialect-appropriate conflict-resolution clause suffix.

    ``on_conflict`` must be one of ``"ignore"``, ``"update"``, or ``"error"``.
    Returns an empty string for ``"error"`` (intended to fail on duplicate).
    For MySQL ``"ignore"`` the caller is expected to swap the ``INSERT`` prefix
    instead (see ``_build_insert_sql``).
    """
    if on_conflict == "error":
        return ""

    conflict_pk = ", ".join(conflict_columns) if conflict_columns else ""

    if dialect_name in ("sqlite", "postgresql"):
        if on_conflict == "ignore":
            suffix = "ON CONFLICT DO NOTHING" if not conflict_pk else f"ON CONFLICT ({conflict_pk}) DO NOTHING"
            return suffix
        if on_conflict == "update":
            if not conflict_pk:
                return "ON CONFLICT DO UPDATE SET " + ", ".join(
                    f"{c} = EXCLUDED.{c}" for c in data_columns
                )
            updates = ", ".join(
                f"{c} = EXCLUDED.{c}" for c in data_columns if c not in conflict_columns
            )
            return f"ON CONFLICT ({conflict_pk}) DO UPDATE SET {updates}"

    if dialect_name == "mysql":
        if on_conflict == "ignore":
            return ""  # caller handles via INSERT IGNORE prefix
        if on_conflict == "update":
            updates = ", ".join(
                f"{c} = VALUES({c})" for c in data_columns
            )
            return f"ON DUPLICATE KEY UPDATE {updates}"

    if dialect_name == "mariadb":
        return _render_conflict_clause("mysql", on_conflict, conflict_columns, data_columns)

    return ""


def _resolve_dialect(target_type: str, override: str | None = None) -> Any:
    """Return a SQLAlchemy dialect instance for literal rendering.

    Raises ``ImportError`` with a clear install hint if the dialect package
    cannot be loaded.  The ``override`` parameter allows forcing a different
    dialect for literal rendering (loud warning emitted by caller).
    """
    dialect_name = override or target_type
    module_path = DIALECT_MODULE_MAP.get(dialect_name)
    if module_path is None:
        raise ValueError(f"Unknown or unsupported dialect: {dialect_name}")

    try:
        mod = importlib.import_module(module_path)
    except ImportError:
        hint = DB_TYPE_TO_INSTALL_HINT.get(
            dialect_name, f"pip install dbwarden[{dialect_name}]"
        )
        raise ImportError(
            f"Cannot export seeds for dialect '{dialect_name}' — missing package. "
            f"Install with: {hint}"
        )

    return mod.dialect()


def _collect_fk_closure(table: Table, metadata: MetaData) -> set[str]:
    """Collect all table names reachable via outgoing FK from *table*.

    Walks the FK graph transitively so that referenced tables' dependencies
    are also included.
    """
    visited: set[str] = set()
    queue = [table.name]

    name_to_table = {t.name: t for t in metadata.sorted_tables}

    while queue:
        name = queue.pop(0)
        if name in visited:
            continue
        visited.add(name)
        t = name_to_table.get(name)
        if t is None:
            continue
        for col in t.columns:
            for fk in col.foreign_keys:
                ref_name = fk.column.table.name
                if ref_name not in visited:
                    queue.append(ref_name)

    return visited
