"""ClickHouse spec canonicalization — applied to both sides before comparison.

Design
------
All rules apply identically to the extract side and model side.  A helper
called on both converges them; nothing is "the truth" — canonicalization is
the truth.

The functions are granular so the audit harness can call them individually
or via the combined ``canonicalize()`` entry point.

Threading: ``defaults`` (server setting defaults) and ``database`` (MV name
qualification) are passed explicitly rather than stashed in the spec dict.
Hiding dependencies inside the data created the pg_table/backend_table_spec
mess; see that precedent.

Zero-version-variation decision
--------------------------------
Confirmed across ClickHouse 24.3.18.7, 24.8.14.39, 25.3.14.14, and 26.6.1.1193
on every measured surface: engine_full format, sorting_key, primary_key alias,
settings injection, TTL normalization, MV CTQ format.  All four versions are
indistinguishable.  No version gates, no branching, no ``if version >= X``.

Evidence path: /tmp/ch-multi-version-audit.md (field-level table proving
every case is identical across all four versions).

Rules
-----
1. Omit ch_primary_key when it equals ch_order_by (sorting-key alias).
2. Strip settings whose value matches the snapshotted server default.
3. Normalize TTL expressions to server form (INTERVAL → toInterval),
   unify null vs [] absence representation.
4. Qualify bare MV table names with the database (shared helper).
"""

from __future__ import annotations

import re
from typing import Any

_INTERVAL_UNITS = (
    "SECOND", "MINUTE", "HOUR", "DAY", "WEEK", "MONTH", "QUARTER", "YEAR",
)
_INTERVAL_RE = re.compile(
    r"\bINTERVAL\s+(\d+)\s+(" + "|".join(_INTERVAL_UNITS) + r")\b",
    re.IGNORECASE,
)


# ── helpers ─────────────────────────────────────────────────────────────────


def _normalize_order_by(val: str | list[str] | None) -> tuple[str, ...] | None:
    """Normalize ch_order_by / ch_primary_key to a tuple for comparison.

    ``"a"`` and ``["a"]`` both become ``("a",)``.
    ``"a, b"`` and ``["a", "b"]`` both become ``("a", "b")``.
    """
    if val is None or val == "":
        return None
    if isinstance(val, str):
        return tuple(part.strip() for part in val.split(",") if part.strip())
    if isinstance(val, (list, tuple)):
        return tuple(str(v).strip() for v in val if v)
    return None


def _normalize_intervals(expr: str) -> str:
    """Rewrite ``INTERVAL <n> <UNIT>`` → ``toInterval<Unit>(<n>)``."""
    def _sub(m: re.Match) -> str:
        n, unit = m.group(1), m.group(2).capitalize()
        return f"toInterval{unit}({n})"
    return _INTERVAL_RE.sub(_sub, expr)


# ── rule 1: primary-key alias ──────────────────────────────────────────────


def canonicalize_primary_key(spec: dict) -> dict:
    """Omit ``ch_primary_key`` when it matches ``ch_order_by``.

    The server always returns ``system.tables.primary_key = sorting_key``
    when no explicit PRIMARY KEY is set.  An explicit PK identical to
    ORDER BY is semantically a no-op.  Omitting on both sides is correct
    — not just a papering-over.

    Also normalises None to absent — same pattern as TTL null vs [].
    Compare AFTER normalizing shapes via ``_normalize_order_by`` so that
    ``"a"`` matches ``["a"]`` and ``"a, b"`` matches ``["a", "b"]``.
    """
    pk = spec.get("ch_primary_key")
    ob = spec.get("ch_order_by")
    if pk is None:
        spec.pop("ch_primary_key", None)
        return spec
    if ob is not None and _normalize_order_by(pk) == _normalize_order_by(ob):
        spec.pop("ch_primary_key", None)
    return spec


# ── rule 2: strip server-injected default settings ─────────────────────────


def canonicalize_settings(spec: dict, *, defaults: dict[str, str]) -> dict:
    """Strip settings whose value equals the server default.

    ``defaults`` is a ``{name: value}`` map snapshotted at extract time from
    ``system.merge_tree_settings WHERE changed = 0``.  Unknown settings are
    left alone — never guess.

    A user who explicitly declares a default value to pin it gets it stripped.
    Accepted, and identical to the PG ``MATCH SIMPLE`` precedent.

    When all settings are stripped the key is removed entirely (null-vs-absent
    convention: no settings → nothing in the dict).
    """
    settings = spec.get("ch_settings")
    if not settings:
        spec.pop("ch_settings", None)
        return spec
    kept = {
        k: v for k, v in settings.items()
        if str(v) != defaults.get(k)
    }
    if kept:
        spec["ch_settings"] = kept
    else:
        spec.pop("ch_settings", None)
    return spec


# ── rule 3: TTL normalization ──────────────────────────────────────────────


def canonicalize_ttl(spec: dict) -> dict:
    """Normalize TTL to the server's form, and absence to None.

    Two normalizations:
      - Empty/absent TTL becomes ``None`` on both sides (parser returns [],
        models leave null).  ``None`` over ``[]`` matches the
        defaults-as-absence convention used everywhere else.
      - ``INTERVAL 1 MONTH`` → ``toIntervalMonth(1)``: the server rewrites
        user interval syntax into function form in the CTQ.  Canonicalize
        to the server's form rather than trying to un-rewrite it.
    """
    ttl = spec.get("ch_ttl")
    if not ttl:
        spec["ch_ttl"] = None
        return spec
    spec["ch_ttl"] = [_normalize_intervals(t) for t in ttl]
    return spec


# ── rule 4: MV name qualification ──────────────────────────────────────────


def qualify(name: str, database: str) -> str:
    """Qualify a bare table name with the database.

    ONE shared helper for both sides.  If ``name`` already contains ``.``
    it is returned unchanged (the extract side).  If bare, it is qualified
    (the model side).  Two inline implementations would drift — same lesson
    as PG's ``pg_inherits`` schema-qualification.
    """
    return name if "." in name else f"{database}.{name}"


def _qualify_select_tables(select: str, database: str) -> str:
    """Qualify bare table names appearing after FROM in a SELECT statement."""
    def _repl(m: re.Match) -> str:
        inner = m.group(1)
        return f"FROM {database}.{inner}" if "." not in inner else m.group(0)
    return re.sub(r'\bFROM\s+(\w+(?:\.\w+)?)\b', _repl, select, count=1)


def canonicalize_mv_names(spec: dict, *, database: str) -> dict:
    """Qualify bare MV table names via the shared helper."""
    to_table = spec.get("ch_to_table")
    if to_table:
        spec["ch_to_table"] = qualify(to_table, database)
    select = spec.get("ch_select_statement")
    if select:
        spec["ch_select_statement"] = _qualify_select_tables(select, database)
    return spec


# ── ORDER BY append-only check ───────────────────────────────────────────────


def is_append_only_order_by(old: Any, new: Any) -> bool:
    """Check that an ORDER BY change is a clean append (extend-only).

    ClickHouse only allows *extending* the sorting key — appending new
    columns at the end.  Reordering, truncating, or altering existing
    columns produces invalid DDL.

    Args:
        old: The current ORDER BY value (string or list of strings).
        new: The proposed ORDER BY value.

    Returns:
        True if *old* is a prefix of *new* (same columns, same order,
        possibly extended).  False otherwise.
    """
    old_tuple = _normalize_order_by(old) or ()
    new_tuple = _normalize_order_by(new) or ()
    if len(old_tuple) > len(new_tuple):
        return False
    return new_tuple[:len(old_tuple)] == old_tuple


# ── immutable change detection ──────────────────────────────────────────────

# Only keys that produce invalid DDL when emit() tries to ALTER them.
# Keys with existing handler paths (engine, select_statement, to_table,
# zookeeper_path, replica_name, object_type, dictionary) are covered by the
# recreate-flag mechanism and are NOT listed here — they are refused (or
# allowed) by that separate gate.
_IMMUTABLE_KEYS: frozenset[str] = frozenset({
    "ch_partition_by",
    "ch_primary_key",
    "ch_sample_by",
})

_IMMUTABLE_MESSAGES: dict[str, str] = {
    "ch_partition_by": (
        "PARTITION BY is immutable after table creation. "
        "To change partitioning, create a new table with the desired "
        "PARTITION BY, migrate data via INSERT SELECT, rename the tables, "
        "and drop the old table. Use data_op() to author a controlled rebuild."
    ),
    "ch_primary_key": (
        "PRIMARY KEY is derived from ORDER BY and cannot be changed independently. "
        "Change ch_order_by instead."
    ),
    "ch_sample_by": (
        "SAMPLE BY is immutable after table creation. "
        "To change sampling, recreate the table with a rebuild+swap pattern. "
        "Use data_op() to author a controlled rebuild."
    ),
    "ch_engine": (
        "Changing the table engine requires a full rebuild. "
        "The engine is immutable in-place — create a new table with the target "
        "engine, migrate data via INSERT SELECT, rename, and drop the old table. "
        "Use data_op() to author a controlled rebuild, or re-run with "
        "--clickhouse-engine-recreate to auto-generate the swap sequence."
    ),
    "ch_object_type": (
        "Changing the object type (table <-> materialized_view <-> dictionary) "
        "is not supported in-place. Create the new object and drop the old one."
    ),
    "ch_select_statement": (
        "The MV SELECT query cannot be changed for non-refreshable MVs. "
        "For refreshable MVs (CH 24.8+), the handler may support MODIFY QUERY. "
        "Otherwise, recreate the MV."
    ),
    "ch_to_table": (
        "The MV target table cannot be changed. Recreate the MV."
    ),
    "ch_dictionary": (
        "Cannot toggle dictionary flag in place. Recreate the table/dictionary."
    ),
    "ch_zookeeper_path": (
        "ZooKeeper path is set at table creation and cannot be changed."
    ),
    "ch_replica_name": (
        "Replica name is set at table creation and cannot be changed."
    ),
}


def check_immutable(
    snap_opts: dict, model_opts: dict, table_name: str,
) -> None:
    """Raise ``ImmutableChangeError`` if any immutable key changed.

    Includes the ORDER BY append-only check: reordering, truncation, or
    in-place alteration of the sorting key is refused (same class of
    invalid DDL as MODIFY PARTITION BY before issue #1).

    Called from ``ChTableHandler.diff()`` before falling through to the
    ``alter_ch_options`` emit path.
    """
    for key in _IMMUTABLE_KEYS:
        snap_val = snap_opts.get(key)
        model_val = model_opts.get(key)
        if key == "ch_primary_key":
            snap_val = _normalize_order_by(snap_val)
            model_val = _normalize_order_by(model_val)
        if snap_val is not None and model_val is not None and snap_val != model_val:
            msg = _IMMUTABLE_MESSAGES.get(
                key,
                f"{key} is immutable after table creation for '{table_name}'",
            )
            from dbwarden.exceptions import ImmutableChangeError
            raise ImmutableChangeError(
                f"Immutable change rejected for '{table_name}': {key} changed. {msg}"
            )

    # ORDER BY append-only check (extend-only, not fully immutable)
    snap_ob = snap_opts.get("ch_order_by")
    model_ob = model_opts.get("ch_order_by")
    if snap_ob is not None and model_ob is not None and snap_ob != model_ob:
        if not is_append_only_order_by(snap_ob, model_ob):
            from dbwarden.exceptions import ImmutableChangeError
            raise ImmutableChangeError(
                f"Immutable change rejected for '{table_name}': "
                f"ORDER BY changed from {snap_ob!r} to {model_ob!r}. "
                f"ClickHouse only supports extending the sorting key "
                f"(appending new columns at the end). Reordering, truncating, "
                f"or altering existing columns is not allowed. "
                f"To make this change, create a new table with the desired "
                f"ORDER BY, migrate data, rename, and drop the old table. "
                f"Use data_op() to author a controlled rebuild."
            )


# ── combined entry point ───────────────────────────────────────────────────


def canonicalize(
    spec: dict,
    *,
    defaults: dict[str, str] | None = None,
    database: str | None = None,
) -> dict:
    """Apply all ClickHouse canonicalization rules."""
    spec = canonicalize_primary_key(spec)
    if defaults is not None:
        spec = canonicalize_settings(spec, defaults=defaults)
    spec = canonicalize_ttl(spec)
    if database is not None:
        spec = canonicalize_mv_names(spec, database=database)
    return spec
