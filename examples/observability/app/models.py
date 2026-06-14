from sqlalchemy import Boolean, DateTime, Integer, String, text
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column


class Base(DeclarativeBase):
    pass


# Simple User model for the observability demo.
# The metrics and query tracing middleware are the main focus of
# this example; the model is minimal to keep attention on the
# observability tooling.
#
# When QueryTracingMiddleware is active, every SQL query executed
# through this model's session is logged with duration, database
# name, and the SQL statement (truncated).

class User(Base):
    __tablename__ = "users"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    email: Mapped[str] = mapped_column(String(255), unique=True, nullable=False)
    username: Mapped[str] = mapped_column(String(100), unique=True, nullable=False)
    full_name: Mapped[str | None] = mapped_column(String(200))
    is_active: Mapped[bool] = mapped_column(Boolean, default=True)
    created_at: Mapped[datetime] = mapped_column(  # noqa: F821
        DateTime, server_default=text("CURRENT_TIMESTAMP")
    )
