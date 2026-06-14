from sqlalchemy import Column, Integer, String, Boolean, DateTime, Float
from sqlalchemy.orm import declarative_base
from datetime import datetime, UTC
from dbwarden import PGTableMeta, PGColumnMeta, PgIndexSpec

Base = declarative_base()


# ── PGTableMeta ────────────────────────────────────────────────
# PostgreSQL-specific table metadata.  Same as TableMeta but adds
# support for PG-specific features: identity columns, tablespace,
# WITH (fillfactor), etc.
#
# PGColumnMeta adds per-column PG features: identity (always/by
# default), storage, compression, collation.
#
# PgIndexSpec adds PG-specific index features:
#   where=    : partial index (WHERE clause)
#   include=  : covering index (INCLUDE columns)
#   using=    : access method (btree, hash, gin, gist, brin)
#   nulls_not_distinct=True : PG 15+ feature
#   with=     : storage parameters (fillfactor)


class User(Base):
    __tablename__ = "users"

    id = Column(Integer, primary_key=True)
    email = Column(String(255), unique=True, nullable=False)
    username = Column(String(100), unique=True, nullable=False)
    credit = Column(Float, nullable=True)

    class Meta(PGTableMeta):
        comment = "Transactional user accounts"

        # PGColumnMeta lets you annotate columns with
        # PostgreSQL-specific properties.
        class id(PGColumnMeta):
            pg_identity = "always"  # GENERATED ALWAYS AS IDENTITY

        class email(PGColumnMeta):
            comment = "Login email, also used for notifications"

        indexes = [
            # Partial index: only rows where credit > 0 are indexed.
            # Useful for filtered queries without the index overhead
            # of the full table.
            PgIndexSpec(
                name="ix_users_active_credits",
                columns=["id"],
                where="credit > 0",
            ),
        ]
