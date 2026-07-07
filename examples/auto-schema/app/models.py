from sqlalchemy import Boolean, Column, DateTime, Integer, String, text
from sqlalchemy.orm import declarative_base
from dbwarden import TableMeta
from dbwarden.schema._auto_schema import auto_schema

Base = declarative_base()


# ── @auto_schema ───────────────────────────────────────────────
# This decorator tells DBWarden to generate Pydantic v2 schemas
# directly from the model's column annotations.  It creates:
#
#   User.CreateSchema  : for POST requests (excludes server-defaulted fields)
#   User.UpdateSchema  : for PATCH requests (all fields optional)
#   User.PublicSchema  : for API responses (excludes fields with public=False)
#   User.Schema        : all mapped columns (including non-public)
#
# The schemas are generated at class-definition time by schemap,
# so they're available immediately: no CLI command, no migration.
# They show up as attributes on the model class itself.

@auto_schema
class User(Base):
    __tablename__ = "users"

    id = Column(Integer, primary_key=True)
    email = Column(String(255), unique=True, nullable=False)
    username = Column(String(100), unique=True, nullable=False)
    full_name = Column(String(200), nullable=True)
    password_hash = Column(String(255), nullable=False)
    is_active = Column(Boolean, default=True)
    created_at = Column(DateTime, server_default=text("CURRENT_TIMESTAMP"))

    class Meta(TableMeta):
        comment = "User accounts with auto-generated Pydantic schemas"

        # Column-level metadata inside Meta lets you annotate
        # individual columns with documentation and visibility rules.
        class email:
            comment = "Login email"

        # Setting public=False on a column excludes it from
        # PublicSchema but keeps it in Schema.  This is how you
        # prevent password_hash from leaking in API responses
        # without writing manual filtering logic in every route.
        class password_hash:
            public = False  # Excluded from PublicSchema
