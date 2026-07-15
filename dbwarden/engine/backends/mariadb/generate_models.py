from __future__ import annotations

import re
from typing import Any

from dbwarden.engine.backends.mysql.generate_models import (
    _render_mysql_meta,
    extract_mysql_meta,
    resolve_mysql_imports,
)


def resolve_mariadb_imports(columns: list[dict]) -> set[str]:
    return resolve_mysql_imports(columns)


def extract_mariadb_meta(
    connection, table_name: str,
    indexes: list[dict] | None = None,
    checks: list[dict] | None = None,
    uniques: list[dict] | None = None,
) -> tuple[dict[str, Any], dict[str, dict[str, Any]]]:
    return extract_mysql_meta(connection, table_name, indexes, checks, uniques)


_render_mariadb_meta = _render_mysql_meta
