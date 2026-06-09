from sqlalchemy import Boolean, Column, DateTime, Integer, String, text
from sqlalchemy.orm import declarative_base
from dbwarden import TableMeta
from dbwarden.schema import auto_schema

Base = declarative_base()


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

        class email:
            comment = "Login email"

        class password_hash:
            public = False  # Excluded from PublicSchema
