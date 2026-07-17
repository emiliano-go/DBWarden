from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class ChRaw:
    """A raw ClickHouse SQL fragment, deliberately opted into.

    Wrapping a string in ``ch_raw()`` marks it as an intentional bypass of the
    typed builder — exactly as SQLAlchemy's ``text()`` marks raw SQL. dbwarden
    will CANONICALIZE this text for diffing (whitespace, alias normalization) but
    will NOT PARSE it semantically. The user owns its correctness.

    Attributes:
        sql: The raw SQL fragment.
    """
    sql: str

    def __str__(self) -> str:
        return self.sql


def ch_raw(sql: str) -> ChRaw:
    """Wrap a raw ClickHouse SQL fragment.

    Use for any construct the typed builder can't express: array joins, stacked
    combinators, window frames, lambdas, CH-specific functions.

    Example::

        from dbwarden.databases.clickhouse import ch_raw, materialized_view

        events_by_tag = materialized_view(
            name="events_by_tag",
            select=ch_raw(
                "SELECT user_id, arrayJoin(tags) AS tag FROM events"
            ),
        )
    """
    return ChRaw(sql)
