from __future__ import annotations

import pytest
from sqlalchemy import Integer, String
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column

import dbwarden.engine.model_discovery as model_discovery
from dbwarden.engine.model_discovery import extract_table_from_model
from dbwarden.exceptions import DBWardenConfigError
from dbwarden.schema import (
    CHColumnMeta,
    CHTableMeta,
    CheckSpec,
    PGColumnMeta,
    PGTableMeta,
    TableMeta,
    UniqueSpec,
    apply_meta,
    read_meta,
)
from dbwarden.databases import check, ch, index, pg, unique
from dbwarden.databases.clickhouse.engine import ChEngineSpec
from dbwarden.databases.clickhouse.projection import ProjectionSpec


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

        class email(PGColumnMeta):
            comment = "Primary contact email"
            public = True
            pg = pg.field(collation="en_US.UTF-8")

        class bio(CHColumnMeta):
            ch = ch.field(codec="ZSTD(3)")


class User(UserFields):
    __tablename__ = "users"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)


class ChildUser(UserFields):
    __tablename__ = "child_users"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)

    class Meta:
        comment = "Child user accounts"

        class email(PGColumnMeta):
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
        assert created_info["dw_comment"] == "Record creation timestamp"
        assert meta is not None
        assert meta.comment == "Core user accounts"
        assert meta.table_attrs["pg_fillfactor"] == 80
        assert meta.backend_table is not None
        assert meta.backend_table.fillfactor == 80

    def test_apply_meta_merges_inherited_meta(self):
        apply_meta(ChildUser)

        created_info = ChildUser.__table__.c.created_at.info
        email_info = ChildUser.__table__.c.email.info
        meta = read_meta(ChildUser)

        assert created_info["dw_comment"] == "Record creation timestamp"
        assert email_info["dw_comment"] == "Primary contact email"
        assert email_info["dw_public"] is False
        assert meta is not None
        assert meta.comment == "Child user accounts"

    def test_apply_meta_rejects_non_empty_info(self):
        class InvalidModel(Base):
            __tablename__ = "invalid_models"

            id: Mapped[int] = mapped_column(Integer, primary_key=True)
            email: Mapped[str] = mapped_column(String(255), info={"legacy": True})

            class Meta:
                class email(PGColumnMeta):
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

                class payload(CHColumnMeta):
                    ch = ch.field(codec="ZSTD(3)")

        monkeypatch.setattr(model_discovery, "_get_backend_name", lambda db_name=None: "clickhouse")

        table = extract_table_from_model(Event)

        assert table is not None
        assert table.clickhouse_options["ch_engine"] == "MergeTree"
        assert table.clickhouse_options["ch_order_by"] == ["id"]
        assert table.columns[1].codec == "ZSTD(3)"

    def test_extract_table_from_model_allows_cross_backend_keys(self, monkeypatch):
        class Report(Base):
            __tablename__ = "reports"

            id: Mapped[int] = mapped_column(Integer, primary_key=True)
            title: Mapped[str] = mapped_column(String(255))

            class Meta:
                class title(PGColumnMeta):
                    pg = pg.field(storage="extended")

        monkeypatch.setattr(model_discovery, "_get_backend_name", lambda db_name=None: "sqlite")

        table = extract_table_from_model(Report)

        assert table is not None
        assert Report.__table__.c.title.info["pg_storage"] == "extended"

    def test_flat_backend_attrs_rejected(self):
        with pytest.raises(DBWardenConfigError, match=r"Unknown attribute 'pg_collation'"):
            class BadModel(Base):
                __tablename__ = "bad_models"

                id: Mapped[int] = mapped_column(Integer, primary_key=True)
                name: Mapped[str] = mapped_column(String(255))

                class Meta:
                    class name(PGColumnMeta):
                        pg_collation = "en_US.UTF-8"


class TestIndexSpec:
    def test_index_spec_fields(self):
        from dbwarden.schema import IndexSpec

        spec = IndexSpec(columns=["a", "b"], name="ix_test", unique=True)
        assert spec.name == "ix_test"
        assert spec.columns == ["a", "b"]
        assert spec.unique is True

    def test_index_factory_returns_dict(self):
        d = index("ix_test", ["a", "b"], unique=True, using="gin", where="status = 'active'")
        assert d == {"name": "ix_test", "columns": ["a", "b"], "unique": True, "using": "gin", "where": "status = 'active'"}

    def test_index_factory_omits_defaults(self):
        d = index("ix_test", ["a"])
        assert d == {"name": "ix_test", "columns": ["a"], "unique": False}
        assert "nulls_not_distinct" not in d
        assert "using" not in d

    def test_index_factory_nulls_not_distinct(self):
        d = index("ix_test", ["a"], nulls_not_distinct=True)
        assert d["nulls_not_distinct"] is True


class TestCheckSpec:
    def test_check_spec_fields(self):
        spec = CheckSpec(expression="age >= 0", name="ck_age", no_inherit=True)
        assert spec.name == "ck_age"
        assert spec.expression == "age >= 0"
        assert spec.no_inherit is True

    def test_check_factory_returns_dict(self):
        d = check("ck_age", "age >= 0", no_inherit=True)
        assert d == {"name": "ck_age", "expression": "age >= 0", "no_inherit": True}

    def test_check_factory_omits_defaults(self):
        d = check("ck_age", "age >= 0")
        assert d == {"name": "ck_age", "expression": "age >= 0"}
        assert "no_inherit" not in d


class TestUniqueSpec:
    def test_unique_spec_fields(self):
        spec = UniqueSpec(columns=["email"], name="uq_email", nulls_not_distinct=True, deferrable=True)
        assert spec.name == "uq_email"
        assert spec.columns == ["email"]
        assert spec.nulls_not_distinct is True
        assert spec.deferrable is True

    def test_unique_factory_returns_dict(self):
        d = unique("uq_email", ["email"], nulls_not_distinct=True, deferrable=True)
        assert d == {"name": "uq_email", "columns": ["email"], "nulls_not_distinct": True, "deferrable": True}

    def test_unique_factory_omits_defaults(self):
        d = unique("uq_email", ["email"])
        assert d == {"name": "uq_email", "columns": ["email"]}
        assert "nulls_not_distinct" not in d
        assert "deferrable" not in d


class TestMetaIndexes:
    def test_meta_indexes_feed_into_model_table(self, monkeypatch):
        class Post(Base):
            __tablename__ = "posts"

            id: Mapped[int] = mapped_column(Integer, primary_key=True)
            title: Mapped[str] = mapped_column(String(255))

            class Meta:
                indexes = [
                    index("ix_posts_title", ["title"]),
                ]

        monkeypatch.setattr(model_discovery, "_get_backend_name", lambda db_name=None: "postgresql")

        table = extract_table_from_model(Post)
        assert table is not None
        assert len(table.indexes) == 1
        assert table.indexes[0].name == "ix_posts_title"
        assert table.indexes[0].columns == ["title"]

    def test_meta_indexes_empty_when_sa_indexes_exist(self, monkeypatch):
        from sqlalchemy import Index

        class BlogPost(Base):
            __tablename__ = "blog_posts"

            id: Mapped[int] = mapped_column(Integer, primary_key=True)
            title: Mapped[str] = mapped_column(String(255))

            __table_args__ = (
                Index("ix_sa_title", "title"),
            )

            class Meta:
                indexes = [
                    index("ix_meta_title", ["title"]),
                ]

        monkeypatch.setattr(model_discovery, "_get_backend_name", lambda db_name=None: "postgresql")

        table = extract_table_from_model(BlogPost)
        assert table is not None
        assert len(table.indexes) == 1
        assert table.indexes[0].name == "ix_sa_title"


class TestCHTableMeta:
    def test_ch_table_meta_all_fields_accessible(self):
        assert hasattr(CHTableMeta, "ch_engine")
        assert hasattr(CHTableMeta, "ch_order_by")
        assert hasattr(CHTableMeta, "ch_primary_key")
        assert hasattr(CHTableMeta, "ch_partition_by")
        assert hasattr(CHTableMeta, "ch_sample_by")
        assert hasattr(CHTableMeta, "ch_ttl")
        assert hasattr(CHTableMeta, "ch_settings")
        assert hasattr(CHTableMeta, "ch_object_type")
        assert hasattr(CHTableMeta, "ch_select_statement")
        assert hasattr(CHTableMeta, "ch_zookeeper_path")
        assert hasattr(CHTableMeta, "ch_replica_name")
        assert hasattr(CHTableMeta, "ch_to_table")
        assert hasattr(CHTableMeta, "ch_dict_layout")
        assert hasattr(CHTableMeta, "ch_dict_source")
        assert hasattr(CHTableMeta, "ch_dict_lifetime")
        assert hasattr(CHTableMeta, "ch_dict_primary_key")
        assert hasattr(CHTableMeta, "ch_projections")
        assert hasattr(CHTableMeta, "ch_dictionary")
        assert hasattr(CHTableMeta, "comment")

    def test_ch_column_meta_has_ch_field(self):
        assert hasattr(CHColumnMeta, "ch")

    def test_ch_engine_spec_in_meta(self, monkeypatch):
        class Event(Base):
            __tablename__ = "events2"

            id: Mapped[int] = mapped_column(Integer, primary_key=True)
            payload: Mapped[str] = mapped_column(String(255))

            class Meta:
                ch_engine = ChEngineSpec(name="ReplicatedMergeTree", args=("/clickhouse/tables/{shard}", "{replica}"))
                ch_order_by = ["id"]
                ch_partition_by = ["toYYYYMM(created_at)"]

        monkeypatch.setattr(model_discovery, "_get_backend_name", lambda db_name=None: "clickhouse")

        table = extract_table_from_model(Event)
        engine_raw = table.clickhouse_options["ch_engine_raw"]
        assert isinstance(engine_raw, ChEngineSpec)
        assert engine_raw.name == "ReplicatedMergeTree"
        assert engine_raw.args == ("/clickhouse/tables/{shard}", "{replica}")
        assert table.clickhouse_options["ch_order_by"] == ["id"]
        assert table.clickhouse_options["ch_partition_by"] == ["toYYYYMM(created_at)"]

    def test_ch_projections_meta(self, monkeypatch):
        from dbwarden.databases.clickhouse.projection import ProjectionSpec

        class Event(Base):
            __tablename__ = "events3"

            id: Mapped[int] = mapped_column(Integer, primary_key=True)
            payload: Mapped[str] = mapped_column(String(255))

            class Meta:
                ch_engine = "MergeTree"
                ch_order_by = ["id"]
                ch_projections = [
                    ProjectionSpec(name="proj_day", query="SELECT id, toDate(created_at) AS day GROUP BY day"),
                ]

        monkeypatch.setattr(model_discovery, "_get_backend_name", lambda db_name=None: "clickhouse")

        table = extract_table_from_model(Event)
        projections = table.clickhouse_options["ch_projections"]
        assert len(projections) == 1
        assert projections[0]["name"] == "proj_day"
        assert "toDate(created_at) AS day" in projections[0]["query"]

    def test_ch_meta_inheritance(self, monkeypatch):
        class BaseCH(Base):
            __abstract__ = True

            class Meta:
                ch_engine = "ReplicatedMergeTree"
                ch_order_by = ["id"]

        class DerivedCH(BaseCH):
            __tablename__ = "derived_ch"

            id: Mapped[int] = mapped_column(Integer, primary_key=True)
            payload: Mapped[str] = mapped_column(String(255))

            class Meta(BaseCH.Meta):
                ch_partition_by = ["toYYYYMM(created_at)"]

        monkeypatch.setattr(model_discovery, "_get_backend_name", lambda db_name=None: "clickhouse")

        table = extract_table_from_model(DerivedCH)
        assert table.clickhouse_options["ch_engine"] == "ReplicatedMergeTree"
        assert table.clickhouse_options["ch_order_by"] == ["id"]
        assert table.clickhouse_options["ch_partition_by"] == ["toYYYYMM(created_at)"]

    def test_no_clickhouse_backward_compat_keys_in_info(self, monkeypatch):
        class NoCompat(Base):
            __tablename__ = "no_compat_ch"

            id: Mapped[int] = mapped_column(Integer, primary_key=True)
            payload: Mapped[str] = mapped_column(String(255))

            class Meta:
                ch_engine = "MergeTree"
                ch_order_by = ["id"]

                class payload(CHColumnMeta):
                    ch = ch.field(codec="ZSTD(3)")

        monkeypatch.setattr(model_discovery, "_get_backend_name", lambda db_name=None: "clickhouse")

        table = extract_table_from_model(NoCompat)
        for col in table.columns:
            for key in col.ch_meta:
                assert not key.startswith("clickhouse_"), f"Backward compat key {key} found"
        assert "ch_engine" in table.clickhouse_options

    def test_ch_meta_apply_meta(self):
        class CHModel(Base):
            __tablename__ = "ch_models"

            id: Mapped[int] = mapped_column(Integer, primary_key=True)
            body: Mapped[str] = mapped_column(String(255))

            class Meta:
                ch_engine = "MergeTree"
                ch_order_by = ["id"]

                class body(CHColumnMeta):
                    ch = ch.field(codec="ZSTD(3)")
                    comment = "body column"

        apply_meta(CHModel)
        body_info = CHModel.__table__.c.body.info
        assert body_info["ch_codec"] == "ZSTD(3)"
        assert body_info["dw_comment"] == "body column"


class TestIndexSpecExtensions:
    def test_index_spec_to_dict_from_dict(self):
        from dbwarden.schema.index import IndexSpec

        spec = IndexSpec(columns=["a", "b"], name="ix_ab", unique=True,
                         using="gin", where="status = 'active'",
                         nulls_not_distinct=True, include=["c"],
                         tablespace="fast_ts")
        d = spec.to_dict()
        assert d["name"] == "ix_ab"
        assert d["columns"] == ["a", "b"]
        assert d["unique"] is True
        assert d["using"] == "gin"
        assert d["where"] == "status = 'active'"
        assert d["nulls_not_distinct"] is True
        assert d["include"] == ["c"]
        assert d["tablespace"] == "fast_ts"

        restored = IndexSpec.from_dict(d)
        assert restored.name == "ix_ab"
        assert restored.columns == ["a", "b"]
        assert restored.unique is True
        assert restored.include == ["c"]

    def test_index_spec_clickhouse_skip(self):
        from dbwarden.schema.index import IndexSpec

        spec = IndexSpec(columns=["a"], name="ix_sk", unique=False,
                         clickhouse_type="set(100)", clickhouse_granularity=2)
        d = spec.to_dict()
        assert d["clickhouse_type"] == "set(100)"
        assert d["clickhouse_granularity"] == 2

        restored = IndexSpec.from_dict(d)
        assert restored.clickhouse_type == "set(100)"
        assert restored.clickhouse_granularity == 2


class TestChEngineSpec:
    def test_basic_construction(self):
        from dbwarden.databases.clickhouse.engine import ChEngineSpec
        spec = ChEngineSpec("MergeTree")
        assert spec.name == "MergeTree"
        assert spec.args == ()
        assert spec.zookeeper_path is None
        assert spec.replica_name is None
        assert spec.settings is None

    def test_with_args(self):
        from dbwarden.databases.clickhouse.engine import ChEngineSpec
        spec = ChEngineSpec("ReplacingMergeTree", args=("version_col",))
        assert spec.name == "ReplacingMergeTree"
        assert spec.args == ("version_col",)

    def test_with_zk_and_replica(self):
        from dbwarden.databases.clickhouse.engine import ChEngineSpec
        spec = ChEngineSpec("ReplicatedMergeTree",
            zookeeper_path="/zk/path", replica_name="{replica}")
        assert spec.zookeeper_path == "/zk/path"
        assert spec.replica_name == "{replica}"

    def test_with_settings(self):
        from dbwarden.databases.clickhouse.engine import ChEngineSpec
        spec = ChEngineSpec("MergeTree",
            settings={"index_granularity": "8192"})
        assert spec.settings == {"index_granularity": "8192"}

    def test_to_dict_roundtrip(self):
        from dbwarden.databases.clickhouse.engine import ChEngineSpec
        spec = ChEngineSpec("ReplicatedMergeTree",
            args=("ver",), zookeeper_path="/zk", replica_name="{r}",
            settings={"s": "1"})
        d = spec.to_dict()
        restored = ChEngineSpec.from_dict(d)
        assert restored.name == spec.name
        assert restored.args == spec.args
        assert restored.zookeeper_path == spec.zookeeper_path
        assert restored.replica_name == spec.replica_name
        assert restored.settings == spec.settings

    def test_to_dict_omits_defaults(self):
        from dbwarden.databases.clickhouse.engine import ChEngineSpec
        d = ChEngineSpec("MergeTree").to_dict()
        assert "args" not in d
        assert "zookeeper_path" not in d
        assert "replica_name" not in d
        assert "settings" not in d

    def test_from_engine_string_simple(self):
        from dbwarden.databases.clickhouse.engine import ChEngineSpec
        spec = ChEngineSpec.from_engine_string("MergeTree")
        assert spec.name == "MergeTree"
        assert spec.args == ()

    def test_from_engine_string_with_args(self):
        from dbwarden.databases.clickhouse.engine import ChEngineSpec
        spec = ChEngineSpec.from_engine_string("SummingMergeTree(col1, col2)")
        assert spec.name == "SummingMergeTree"
        assert spec.args == ("col1", "col2")

    def test_from_engine_string_replicated(self):
        from dbwarden.databases.clickhouse.engine import ChEngineSpec
        spec = ChEngineSpec.from_engine_string(
            "ReplicatedMergeTree('/zk/path', '{replica}', ver)")
        assert spec.name == "ReplicatedMergeTree"
        assert spec.zookeeper_path == "/zk/path"
        assert spec.replica_name == "{replica}"
        assert spec.args == ("ver",)

    def test_post_init_coerces_string_to_tuple(self):
        from dbwarden.databases.clickhouse.engine import ChEngineSpec
        spec = ChEngineSpec("CollapsingMergeTree", args="sign")
        assert spec.args == ("sign",)


class TestProjectionSpec:
    def test_basic_construction(self):
        from dbwarden.databases.clickhouse.projection import ProjectionSpec
        p = ProjectionSpec("by_date", "SELECT date, count() GROUP BY date")
        assert p.name == "by_date"
        assert p.query == "SELECT date, count() GROUP BY date"

    def test_to_dict_roundtrip(self):
        from dbwarden.databases.clickhouse.projection import ProjectionSpec
        p = ProjectionSpec("by_date", "SELECT date, count() GROUP BY date")
        d = p.to_dict()
        restored = ProjectionSpec.from_dict(d)
        assert restored.name == p.name
        assert restored.query == p.query

    def test_from_dict_with_empty_query(self):
        from dbwarden.databases.clickhouse.projection import ProjectionSpec
        p = ProjectionSpec.from_dict({"name": "by_date"})
        assert p.name == "by_date"
        assert p.query == ""


class TestChIndexSpec:
    def test_basic_construction(self):
        from dbwarden.databases.clickhouse import ChIndexSpec
        spec = ChIndexSpec("ix_payload", ["payload"], type="bloom_filter")
        assert spec.name == "ix_payload"
        assert spec.columns == ["payload"]
        assert spec.type == "bloom_filter"
        assert spec.granularity == 1
        assert spec.expr is None

    def test_with_granularity(self):
        from dbwarden.databases.clickhouse import ChIndexSpec
        spec = ChIndexSpec("ix_url", ["url"], type="minmax", granularity=3)
        assert spec.granularity == 3

    def test_with_expr(self):
        from dbwarden.databases.clickhouse import ChIndexSpec
        spec = ChIndexSpec("ix_lower", ["url"], type="bloom_filter", expr="lower(url)")
        assert spec.expr == "lower(url)"

    def test_to_dict_roundtrip(self):
        from dbwarden.databases.clickhouse import ChIndexSpec
        spec = ChIndexSpec("ix_payload", ["payload"], type="bloom_filter", granularity=1)
        d = spec.to_dict()
        restored = ChIndexSpec.from_dict(d)
        assert restored.name == spec.name
        assert restored.columns == spec.columns
        assert restored.type == spec.type
        assert restored.granularity == spec.granularity
        assert d["clickhouse_type"] == "bloom_filter"
        assert d["clickhouse_granularity"] == 1

    def test_from_dict_with_clickhouse_keys(self):
        from dbwarden.databases.clickhouse import ChIndexSpec
        spec = ChIndexSpec.from_dict({
            "name": "ix_sk", "columns": ["a"],
            "clickhouse_type": "set(100)", "clickhouse_granularity": 2,
        })
        assert spec.type == "set(100)"
        assert spec.granularity == 2

    def test_to_dict_includes_expr(self):
        from dbwarden.databases.clickhouse import ChIndexSpec
        d = ChIndexSpec("ix_expr", ["url"], type="bloom_filter", expr="lower(url)").to_dict()
        assert d["expr"] == "lower(url)"


class TestPgIndexSpec:
    def test_basic_construction(self):
        from dbwarden.databases.pgsql import PgIndexSpec
        spec = PgIndexSpec("ix_email", ["email"])
        assert spec.name == "ix_email"
        assert spec.columns == ["email"]
        assert spec.unique is False

    def test_full_construction(self):
        from dbwarden.databases.pgsql import PgIndexSpec
        spec = PgIndexSpec("ix_ab", ["a", "b"],
            unique=True, using="gin", where="status = 'active'",
            include=["c"], tablespace="fast_ts", nulls_not_distinct=True)
        assert spec.unique is True
        assert spec.using == "gin"
        assert spec.where == "status = 'active'"
        assert spec.include == ["c"]
        assert spec.tablespace == "fast_ts"
        assert spec.nulls_not_distinct is True

    def test_to_dict_roundtrip(self):
        from dbwarden.databases.pgsql import PgIndexSpec
        spec = PgIndexSpec("ix_ab", ["a", "b"],
            unique=True, using="gin", where="status = 'active'")
        d = spec.to_dict()
        restored = PgIndexSpec.from_dict(d)
        assert restored.name == spec.name
        assert restored.columns == spec.columns
        assert restored.unique == spec.unique
        assert restored.using == spec.using
        assert restored.where == spec.where

    def test_to_dict_omits_defaults(self):
        from dbwarden.databases.pgsql import PgIndexSpec
        d = PgIndexSpec("ix_email", ["email"]).to_dict()
        assert "unique" not in d
        assert "using" not in d
        assert "where" not in d


class TestMetaValidator:
    def test_unknown_table_attr_rejected(self):
        with pytest.raises(DBWardenConfigError, match=r"Unknown attribute 'zzz_top_level"):
            class _(PGTableMeta):
                zzz_top_level = "bad"

    def test_unknown_field_attr_rejected(self):
        with pytest.raises(DBWardenConfigError, match=r"Unknown attribute 'zzz_field_attr"):
            class _(PGColumnMeta):
                zzz_field_attr = "bad"

    def test_known_table_attrs_allowed(self):
        class Okay(TableMeta):
            comment = "works"
            indexes = []
            checks = []
            uniques = []

    def test_known_field_attrs_allowed(self):
        class Okay(PGColumnMeta):
            comment = "field comment"
            public = True

    def test_nested_classes_allowed(self):
        class Parent(PGTableMeta):
            comment = "parent"
            indexes = []

            class child(PGColumnMeta):
                comment = "nested child"

    def test_pg_field_spec_accepted(self):
        class SpecTest(PGColumnMeta):
            pg = pg.field(collation="en_US.UTF-8")
            comment = "test"

        assert SpecTest.pg.collation == "en_US.UTF-8"

    def test_ch_field_spec_accepted(self):
        class SpecTest(CHColumnMeta):
            ch = ch.field(codec="ZSTD(3)")
            comment = "test"

        assert SpecTest.ch.codec == "ZSTD(3)"


class TestPgFieldSpec:
    def test_field_factory(self):
        spec = pg.field(collation="en_US.UTF-8", storage="PLAIN")
        assert spec.collation == "en_US.UTF-8"
        assert spec.storage == "PLAIN"

    def test_to_col_info(self):
        spec = pg.field(collation="en_US.UTF-8", storage="PLAIN", identity="always")
        info = spec.to_col_info()
        assert info["pg_collation"] == "en_US.UTF-8"
        assert info["pg_storage"] == "PLAIN"
        assert info["pg_identity"] == "always"

    def test_to_col_info_omits_none(self):
        spec = pg.field()
        info = spec.to_col_info()
        assert info == {}


class TestChFieldSpec:
    def test_field_factory(self):
        spec = ch.field(codec="ZSTD(3)", nullable=True, low_cardinality=True)
        assert spec.codec == "ZSTD(3)"
        assert spec.nullable is True
        assert spec.low_cardinality is True

    def test_to_col_info(self):
        spec = ch.field(codec="ZSTD(3)", nullable=True, low_cardinality=True, ttl="created_at + INTERVAL 30 DAY")
        info = spec.to_col_info()
        assert info["ch_codec"] == "ZSTD(3)"
        assert info["ch_nullable"] is True
        assert info["ch_low_cardinality"] is True
        assert info["ch_ttl"] == "created_at + INTERVAL 30 DAY"

    def test_to_col_info_omits_false(self):
        spec = ch.field()
        info = spec.to_col_info()
        assert "ch_low_cardinality" not in info
        assert "ch_nullable" not in info


class TestChEngineFactories:
    def test_merge_tree(self):
        from dbwarden.databases.clickhouse.engine import merge_tree
        spec = merge_tree()
        assert spec.name == "MergeTree"
        assert spec.args == ()

    def test_replacing_merge_tree(self):
        from dbwarden.databases.clickhouse.engine import replacing_merge_tree
        spec = replacing_merge_tree("ver")
        assert spec.name == "ReplacingMergeTree"
        assert spec.args == ("ver",)

    def test_replicated_merge_tree(self):
        from dbwarden.databases.clickhouse.engine import replicated_merge_tree
        spec = replicated_merge_tree("/zk/path", "{replica}", "ver")
        assert spec.name == "ReplicatedMergeTree"
        assert spec.args == ("ver",)
        assert spec.zookeeper_path == "/zk/path"
        assert spec.replica_name == "{replica}"

    def test_summing_merge_tree(self):
        from dbwarden.databases.clickhouse.engine import summing_merge_tree
        spec = summing_merge_tree("col1", "col2")
        assert spec.name == "SummingMergeTree"
        assert spec.args == ("col1", "col2")

    def test_aggregating_merge_tree(self):
        from dbwarden.databases.clickhouse.engine import aggregating_merge_tree
        spec = aggregating_merge_tree()
        assert spec.name == "AggregatingMergeTree"
        assert spec.args == ()
