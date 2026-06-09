from sqlalchemy import Column, Integer, String, Boolean, DateTime, Float
from sqlalchemy.orm import declarative_base
from datetime import datetime, UTC
from dbwarden import PGTableMeta, PGColumnMeta, PgIndexSpec

Base = declarative_base()


class User(Base):
    __tablename__ = "users"

    id = Column(Integer, primary_key=True)
    email = Column(String(255), unique=True, nullable=False)
    username = Column(String(100), unique=True, nullable=False)
    credit = Column(Float, nullable=True)

    class Meta(PGTableMeta):
        comment = "Transactional user accounts"

        class id(PGColumnMeta):
            pg_identity = "always"

        class email(PGColumnMeta):
            comment = "Login email, also used for notifications"

        indexes = [
            PgIndexSpec(
                name="ix_users_active_credits",
                columns=["id"],
                where="credit > 0",
            ),
        ]
