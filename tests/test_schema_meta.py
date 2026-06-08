from __future__ import annotations

import pytest
from sqlalchemy import Integer, String
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column

import dbwarden.engine.model_discovery as model_discovery
from dbwarden.engine.model_discovery import extract_table_from_model
from dbwarden.exceptions import DBWardenConfigError
from dbwarden.schema import apply_meta, read_meta


class Base(DeclarativeBase):
    pass


class Timestamped(Base):
    __abstract__ = True

    created_at: Mapped[str] = mapped_column(String(32))

    class Meta:
        class created_at:
            comment = "Record creation timestamp"
            public = True


class UserFields(Timestamped):
    __abstract__ = True

    email: Mapped[str] = mapped_column(String(255), unique=True)
    bio: Mapped[str | None] = mapped_column(String(255), nullable=True)

    class Meta:
        comment = "Core user accounts"
        pg_fillfactor = 80

        class email:
            comment = "Primary contact email"
            public = True
            pg_collation = "en_US.UTF-8"

        class bio:
            ch_codec = "ZSTD(3)"


class User(UserFields):
    __tablename__ = "users"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)


class ChildUser(UserFields):
    __tablename__ = "child_users"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)

    class Meta:
        comment = "Child user accounts"

        class email:
            public = False


class TestMetaReader:
    def test_apply_meta_writes_column_info_and_attaches_meta(self):
        apply_meta(User)

        email_info = User.__table__.c.email.info
        bio_info = User.__table__.c.bio.info
        created_info = User.__table__.c.created_at.info
        meta = read_meta(User)

        assert email_info["dw_comment"] == "Primary contact email"
        assert email_info["dw_public"] is True
        assert email_info["pg_collation"] == "en_US.UTF-8"
        assert bio_info["ch_codec"] == "ZSTD(3)"
        assert bio_info["clickhouse_codec"] == "ZSTD(3)"
        assert created_info["dw_comment"] == "Record creation timestamp"
        assert meta is not None
        assert meta.comment == "Core user accounts"
        assert meta.table_attrs["pg_fillfactor"] == 80
        assert meta.backend_table["pg_fillfactor"] == 80

    def test_apply_meta_merges_inherited_meta(self):
        apply_meta(ChildUser)

        created_info = ChildUser.__table__.c.created_at.info
        email_info = ChildUser.__table__.c.email.info
        meta = read_meta(ChildUser)

        assert created_info["dw_comment"] == "Record creation timestamp"
        assert email_info["dw_comment"] == "Primary contact email"
        assert "dw_public" not in email_info
        assert meta is not None
        assert meta.comment == "Child user accounts"

    def test_apply_meta_rejects_non_empty_info(self):
        class InvalidModel(Base):
            __tablename__ = "invalid_models"

            id: Mapped[int] = mapped_column(Integer, primary_key=True)
            email: Mapped[str] = mapped_column(String(255), info={"legacy": True})

            class Meta:
                class email:
                    comment = "Primary contact email"

        with pytest.raises(DBWardenConfigError, match=r"Do not use mapped_column\(info="):
            apply_meta(InvalidModel)

    def test_extract_table_from_model_applies_clickhouse_meta(self, monkeypatch):
        class Event(Base):
            __tablename__ = "events"

            id: Mapped[int] = mapped_column(Integer, primary_key=True)
            payload: Mapped[str] = mapped_column(String(255))

            class Meta:
                ch_engine = "MergeTree"
                ch_order_by = ["id"]

                class payload:
                    ch_codec = "ZSTD(3)"

        monkeypatch.setattr(model_discovery, "_get_backend_name", lambda db_name=None: "clickhouse")

        table = extract_table_from_model(Event)

        assert table is not None
        assert table.clickhouse_options["clickhouse_engine"] == "MergeTree"
        assert table.clickhouse_options["clickhouse_order_by"] == ["id"]
        assert table.columns[1].codec == "ZSTD(3)"

    def test_extract_table_from_model_allows_wrong_backend_keys(self, monkeypatch):
        class Report(Base):
            __tablename__ = "reports"

            id: Mapped[int] = mapped_column(Integer, primary_key=True)
            title: Mapped[str] = mapped_column(String(255))

            class Meta:
                class title:
                    pg_storage = "extended"

        monkeypatch.setattr(model_discovery, "_get_backend_name", lambda db_name=None: "sqlite")

        table = extract_table_from_model(Report)

        assert table is not None
        assert Report.__table__.c.title.info["pg_storage"] == "extended"
