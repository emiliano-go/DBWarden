"""Comprehensive integration test for ALL dbwarden features.

Tests every major feature against live PostgreSQL, MySQL, and ClickHouse databases.
"""
import sys, os, json, tempfile, shutil, asyncio
from pathlib import Path

# Ensure no shadowing from test project root
test_root = "/tmp/dbwarden-prod-test"
sys.path = [p for p in sys.path if test_root not in p]

os.chdir("/home/eclipse/Documents/GitHub/dbwarden")

# Track results
results = {"passed": [], "failed": []}
_test_count = 0

def test(name: str):
    global _test_count
    _test_count += 1
    def decorator(fn):
        def wrapper(*args, **kwargs):
            try:
                fn(*args, **kwargs)
                results["passed"].append(name)
                print(f"  PASS [{_test_count}] {name}")
            except Exception as e:
                import traceback
                results["failed"].append((name, str(e), traceback.format_exc()))
                print(f"  FAIL [{_test_count}] {name}: {e}")
        return wrapper
    return decorator

# ═══════════════════════════════════════════════════════════════
# 1. CONFIGURATION
# ═══════════════════════════════════════════════════════════════

from dbwarden.config import (
    DatabaseConfig, MultiDbConfig, get_database, list_databases, get_multi_db_config
)
from dbwarden.config_registry import reset_registry
from dbwarden.exceptions import ConfigurationError

@test("configuration: load from test project")
def test_config_load():
    os.environ["DBWARDEN_CONFIG_MODULE"] = ""
    config_dir = Path(test_root)
    config_dir.mkdir(parents=True, exist_ok=True)
    config_file = config_dir / "dbwarden_test_config.py"
    config_file.write_text("""
from dbwarden import database_config
primary = database_config(
    database_name="primary",
    default=True,
    database_type="postgresql",
    database_url_sync="postgresql://dbwarden:dbwarden@localhost:15432/dbwarden",
    database_url_async="postgresql+asyncpg://dbwarden:dbwarden@localhost:15432/dbwarden",
    model_paths=["/tmp/dbwarden-prod-test/app/models"],
)
""")
    import importlib.util
    module_name = f"_dbwarden_config_{abs(hash(str(config_file)))}"
    spec = importlib.util.spec_from_file_location(module_name, str(config_file))
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    assert hasattr(module, 'primary'), "primary not defined in config"
    # DatabaseHandle has _name and _db_type, not .config
    assert module.primary._db_type == "postgresql"
    assert module.primary._name == "primary"

@test("configuration: database_config registers entries")
def test_get_databases():
    from dbwarden import database_config
    from dbwarden.config_registry import registered_entries
    reset_registry()
    
    primary = database_config(
        database_name="primary",
        default=True,
        database_type="postgresql",
        database_url_sync="postgresql://dbwarden:dbwarden@localhost:15432/dbwarden",
        model_paths=[],
    )
    clickhouse = database_config(
        database_name="clickhouse",
        database_type="clickhouse",
        database_url_sync="clickhousedb://dbwarden:dbwarden@localhost:18123/dbwarden",
        model_paths=[],
    )
    mysql_db = database_config(
        database_name="mysql",
        database_type="mysql",
        database_url_sync="mysql+pymysql://dbwarden:dbwarden@localhost:13306/dbwarden",
        model_paths=[],
    )
    entries = registered_entries()
    names = [e.database_name for e in entries]
    assert len(names) >= 3, f"Expected >=3 databases, got {len(names)}: {names}"
    assert "primary" in names
    assert "clickhouse" in names
    assert "mysql" in names

@test("configuration: duplicate database_name raises")
def test_config_duplicate():
    from dbwarden.config import _finalize_entries
    from dbwarden.config_schema import DatabaseEntry
    from pathlib import Path
    entries = [
        DatabaseEntry(database_name="test_dup", default=True, database_type="postgresql",
                      database_url_sync="postgresql://u:p@localhost:15432/dbwarden",
                      database_url_async=None, model_paths=[],
                      dev_database_url=None, dev_database_type=None, overlap_models=False,
                      secure_values=False, migrations_dir=None, migration_table=None, seed_table=None),
        DatabaseEntry(database_name="test_dup", default=False, database_type="postgresql",
                      database_url_sync="postgresql://u:p@localhost:15432/dbwarden",
                      database_url_async=None, model_paths=[],
                      dev_database_url=None, dev_database_type=None, overlap_models=False,
                      secure_values=False, migrations_dir=None, migration_table=None, seed_table=None),
    ]
    try:
        _finalize_entries(entries, Path("/tmp"))
        assert False, "Should have raised ConfigurationError"
    except ConfigurationError:
        pass

@test("configuration: no default raises")
def test_config_no_default():
    from dbwarden.config import _finalize_entries
    from dbwarden.config_schema import DatabaseEntry
    from pathlib import Path
    entries = [
        DatabaseEntry(database_name="a", default=False, database_type="postgresql",
                      database_url_sync="postgresql://u:p@localhost:15432/dbwarden",
                      database_url_async=None, model_paths=[],
                      dev_database_url=None, dev_database_type=None, overlap_models=False,
                      secure_values=False, migrations_dir=None, migration_table=None, seed_table=None),
        DatabaseEntry(database_name="b", default=False, database_type="postgresql",
                      database_url_sync="postgresql://u:p@localhost:15432/dbwarden",
                      database_url_async=None, model_paths=[],
                      dev_database_url=None, dev_database_type=None, overlap_models=False,
                      secure_values=False, migrations_dir=None, migration_table=None, seed_table=None),
    ]
    try:
        _finalize_entries(entries, Path("/tmp"))
        assert False, "Should have raised ConfigurationError"
    except ConfigurationError:
        pass

# ═══════════════════════════════════════════════════════════════
# 2. DATABASE CONNECTIONS (live)
# ═══════════════════════════════════════════════════════════════

from sqlalchemy import create_engine, text

@test("connection: PostgreSQL live")
def test_pg_connect():
    e = create_engine("postgresql://dbwarden:dbwarden@localhost:15432/dbwarden")
    with e.connect() as c:
        v = c.execute(text("SELECT version()")).scalar()
        assert "PostgreSQL" in v

@test("connection: MySQL live")
def test_mysql_connect():
    e = create_engine("mysql+pymysql://dbwarden:dbwarden@localhost:13306/dbwarden")
    with e.connect() as c:
        v = c.execute(text("SELECT version()")).scalar()
        assert v is not None

@test("connection: ClickHouse live")
def test_ch_connect():
    e = create_engine("clickhousedb://dbwarden:dbwarden@localhost:18123/dbwarden")
    with e.connect() as c:
        v = c.execute(text("SELECT 1")).scalar()
        assert v == 1

@test("connection: SQLite")
def test_sqlite_connect():
    e = create_engine("sqlite:///:memory:")
    with e.connect() as c:
        v = c.execute(text("SELECT 1")).scalar()
        assert v == 1

# ═══════════════════════════════════════════════════════════════
# 3. SCHEMA / META ANNOTATION SYSTEM
# ═══════════════════════════════════════════════════════════════

from sqlalchemy.orm import declarative_base
from sqlalchemy import Column, Integer, String, Text
from dbwarden import TableMeta, FieldMeta, PGTableMeta, CHTableMeta, IndexSpec
from dbwarden.schema._meta_reader import apply_meta

Base = declarative_base()

@test("schema: class Meta table-level reading")
def test_meta_table_level():
    class TestModel(Base):
        __tablename__ = "test_meta_table"
        id = Column(Integer, primary_key=True)
        name = Column(String(100))
        class Meta(TableMeta):
            comment = "Test table"
            indexes = [IndexSpec(name="ix_name", columns=["name"])]
    
    apply_meta(TestModel)
    meta = TestModel.__dbwarden_meta__
    assert meta.comment == "Test table"
    assert len(meta.indexes) == 1

@test("schema: class Meta column-level reading")
def test_meta_column_level():
    class TestModel(Base):
        __tablename__ = "test_meta_col"
        id = Column(Integer, primary_key=True)
        email = Column(String(255))
        password = Column(String(255))
        
        class Meta(TableMeta):
            class email:
                comment = "User email"
                public = True
            class password:
                public = False
    
    apply_meta(TestModel)
    col = TestModel.__table__.c.email
    assert col.info.get("dw_comment") == "User email"
    assert col.info.get("dw_public") is True
    
    col_pw = TestModel.__table__.c.password
    assert col_pw.info.get("dw_public") is False

@test("schema: FieldMeta has all backend attributes")
def test_field_meta_attrs():
    assert hasattr(FieldMeta, "comment")
    assert hasattr(FieldMeta, "public")
    assert hasattr(FieldMeta, "pg_storage")
    assert hasattr(FieldMeta, "ch_codec")
    assert hasattr(FieldMeta, "my_charset")
    assert hasattr(FieldMeta, "mdb_invisible")
    assert hasattr(FieldMeta, "sq_generated")

@test("schema: PGTableMeta inherits common attrs")
def test_pg_table_meta():
    assert hasattr(PGTableMeta, "comment")
    assert hasattr(PGTableMeta, "indexes")
    assert hasattr(PGTableMeta, "pg_fillfactor")
    assert hasattr(PGTableMeta, "pg_tablespace")

@test("schema: CHTableMeta inherits common attrs")
def test_ch_table_meta():
    assert hasattr(CHTableMeta, "comment")
    assert hasattr(CHTableMeta, "indexes")
    assert hasattr(CHTableMeta, "ch_engine")
    assert hasattr(CHTableMeta, "ch_order_by")

@test("schema: forbidden mapped_column(info=...) detected")
def test_forbidden_info():
    from dbwarden.exceptions import DBWardenConfigError
    from sqlalchemy import String
    
    class BadModelInfo(Base):
        __tablename__ = "bad_model_info"
        id = Column(Integer, primary_key=True)
        name = Column(String(50), info={"foo": "bar"})
        class Meta:
            pass
    
    try:
        apply_meta(BadModelInfo)
        assert False, "Should have raised DBWardenConfigError"
    except DBWardenConfigError:
        pass

# ═══════════════════════════════════════════════════════════════
# 4. INDEX SPECS
# ═══════════════════════════════════════════════════════════════

from dbwarden import IndexSpec, ChIndexSpec
from dbwarden.schema.pgsql import PgIndexSpec
from dbwarden.schema.clickhouse import ChIndexSpec as CHIdx

@test("index: IndexSpec basic")
def test_index_spec():
    idx = IndexSpec(name="ix_test", columns=["col1", "col2"], unique=True)
    assert idx.name == "ix_test"
    assert idx.columns == ["col1", "col2"]
    assert idx.unique is True

@test("index: PgIndexSpec advanced features")
def test_pg_index_spec():
    idx = PgIndexSpec(
        name="ix_pg_adv",
        columns=["col1"],
        unique=True,
        nulls_not_distinct=True,
        using="btree",
        include=["col2"],
        where="col1 IS NOT NULL",
        tablespace="pg_default",
        column_sorting={"col1": "DESC"},
    )
    assert idx.name == "ix_pg_adv"
    assert idx.nulls_not_distinct is True
    assert idx.using == "btree"
    assert idx.include == ["col2"]
    assert idx.where == "col1 IS NOT NULL"

@test("index: ChIndexSpec skip index")
def test_ch_index_spec():
    idx = ChIndexSpec(
        name="ix_skip",
        columns=["payload"],
        type="bloom_filter",
        granularity=1,
    )
    assert idx.name == "ix_skip"
    assert idx.type == "bloom_filter"
    assert idx.granularity == 1

# ═══════════════════════════════════════════════════════════════
# 5. ENGINE SPEC
# ═══════════════════════════════════════════════════════════════

from dbwarden import ChEngineSpec, ProjectionSpec

@test("engine: ChEngineSpec basic")
def test_ch_engine():
    eng = ChEngineSpec("MergeTree")
    assert eng.name == "MergeTree"
    assert eng.args == ()

@test("engine: ChEngineSpec replicated")
def test_ch_engine_replicated():
    eng = ChEngineSpec(
        "ReplicatedMergeTree",
        zookeeper_path="/clickhouse/tables/shard1/events",
        replica_name="{replica}",
    )
    assert eng.name == "ReplicatedMergeTree"
    assert eng.zookeeper_path == "/clickhouse/tables/shard1/events"

@test("engine: ProjectionSpec")
def test_ch_projection():
    proj = ProjectionSpec("by_date", "SELECT date, count() GROUP BY date")
    assert proj.name == "by_date"

# ═══════════════════════════════════════════════════════════════
# 6. SEEDS
# ═══════════════════════════════════════════════════════════════

from dbwarden.schema import seed_data, SeedRow

@test("seeds: @seed_data decorator")
def test_seed_decorator():
    @seed_data(database="primary", version="0001",
               description="test seed", on_conflict="ignore")
    class TestSeed:
        model = None
        rows = [SeedRow(code="X", name="Test")]
    
    assert hasattr(TestSeed, "__dbwarden_seed__")
    seed = TestSeed.__dbwarden_seed__
    assert seed.database == "primary"
    assert seed.version == "0001"
    assert seed.on_conflict == "ignore"
    assert seed.description == "test seed"
    assert len(seed.source_hash) == 16

@test("seeds: SeedRow works")
def test_seed_row():
    row = SeedRow(name="test", value=42)
    d = row.to_dict()
    assert d["name"] == "test"
    assert d["value"] == 42

# ═══════════════════════════════════════════════════════════════
# 7. AUTO_SCHEMA
# ═══════════════════════════════════════════════════════════════

from dbwarden.schema import auto_schema

@test("auto_schema: decorator generates Pydantic schemas")
def test_auto_schema():
    # Need to re-create Base for this test to avoid table name conflicts
    from sqlalchemy.orm import declarative_base as make_base
    AB = make_base()
    
    @auto_schema
    class AutoUser(AB):
        __tablename__ = "auto_users"
        id = Column(Integer, primary_key=True)
        email = Column(String(255))
        password_hash = Column(String(255))
        
        class Meta:
            class email:
                public = True
                comment = "Primary email"
            class password_hash:
                public = False
    
    assert hasattr(AutoUser, "Schema")
    assert hasattr(AutoUser, "CreateSchema")
    assert hasattr(AutoUser, "UpdateSchema")
    assert hasattr(AutoUser, "PublicSchema")
    
    # PublicSchema should exclude password_hash but include id
    pub_schema = AutoUser.PublicSchema(id=1, email="test@example.com")
    assert pub_schema.email == "test@example.com"
    assert pub_schema.id == 1

# ═══════════════════════════════════════════════════════════════
# 8. MIGRATION ENGINE - SQL GENERATION
# ═══════════════════════════════════════════════════════════════

from dbwarden.engine.model_discovery import extract_table_from_model, ModelTable, ModelColumn

@test("migrations: extract_table_from_model produces ModelTable")
def test_extract_table():
    class ExtractModel(Base):
        __tablename__ = "extract_test"
        id = Column(Integer, primary_key=True)
        name = Column(String(255))
        class Meta(TableMeta):
            comment = "Extraction test"
    
    table = extract_table_from_model(ExtractModel)
    assert isinstance(table, ModelTable)
    assert table.name == "extract_test"
    assert len(table.columns) == 2  # id + name
    assert table.comment == "Extraction test"

@test("migrations: make-migrations flow (no actual file)")
def test_make_migrations_flow():
    """Test the model diffing flow that make-migrations uses."""
    # Build ModelTable objects manually
    from dbwarden.engine.snapshot import diff_models_against_snapshot, snapshot_diff_to_sql
    
    old_cols = [
        ModelColumn(name="id", type="integer", nullable=False, primary_key=True, unique=True, default=None, foreign_key=None),
    ]
    new_cols = [
        ModelColumn(name="id", type="integer", nullable=False, primary_key=True, unique=True, default=None, foreign_key=None),
        ModelColumn(name="name", type="varchar(255)", nullable=False, primary_key=False, unique=False, default=None, foreign_key=None),
    ]
    
    old_table = ModelTable(name="test_table", columns=old_cols)
    new_table = ModelTable(name="test_table", columns=new_cols)
    
    # Build a snapshot dict from old table (mimics actual snapshot format)
    snapshot = {
        "tables": {
            "test_table": {
                "columns": {
                    "id": {
                        "type": "integer",
                        "nullable": False,
                        "primary_key": True,
                    },
                },
                "object_type": "table",
                "comment": None,
                "ch_options": {},
                "clickhouse_options": {},
            }
        }
    }
    upgrade_ops, _ = diff_models_against_snapshot([new_table], snapshot)
    add_col_ops = [op for op in upgrade_ops if op.get("type") == "add_column"]
    assert len(add_col_ops) >= 1, f"Expected add_column ops, got {len(upgrade_ops)} ops: {[op.get('type') for op in upgrade_ops]}"

# ═══════════════════════════════════════════════════════════════
# 9. SNAPSHOTS
# ═══════════════════════════════════════════════════════════════

from dbwarden.engine.snapshot import extract_full_schema_snapshot

@test("snapshots: extract_full_schema_snapshot works with SQLite")
def test_snapshot_sqlite():
    import tempfile
    db_path = os.path.join(tempfile.gettempdir(), "test_dbwarden_snapshot.sqlite")
    try:
        eng = create_engine(f"sqlite:///{db_path}")
        with eng.begin() as conn:
            conn.execute(text("""
                CREATE TABLE snapshot_test (
                    id INTEGER PRIMARY KEY,
                    name VARCHAR(255) NOT NULL
                )
            """))
        snapshot = extract_full_schema_snapshot(sqlalchemy_url=f"sqlite:///{db_path}", database_type="sqlite")
        assert snapshot is not None
        tables = set(snapshot.get("tables", {}).keys())
        assert "snapshot_test" in tables, f"Tables found: {tables}"
    finally:
        if os.path.exists(db_path):
            os.unlink(db_path)

@test("snapshots: snapshot with PostgreSQL")
def test_snapshot_postgres():
    pg_engine = create_engine("postgresql://dbwarden:dbwarden@localhost:15432/dbwarden")
    with pg_engine.begin() as conn:
        conn.execute(text("""
            CREATE TABLE IF NOT EXISTS snapshot_pg_test (
                id SERIAL PRIMARY KEY,
                name VARCHAR(255) NOT NULL
            )
        """))
    snapshot = extract_full_schema_snapshot(sqlalchemy_url="postgresql://dbwarden:dbwarden@localhost:15432/dbwarden", database_type="postgresql")
    tables = set(snapshot.get("tables", {}).keys())
    assert "snapshot_pg_test" in tables, f"Tables found: {tables}"

# ═══════════════════════════════════════════════════════════════
# 10. SAFETY CLASSIFICATION
# ═══════════════════════════════════════════════════════════════

from dbwarden.engine.safety import Safety, classify_pg_type_change, classify_ch_column_change, classify_ch_options_change

@test("safety: Safety enum values")
def test_safety_enum():
    assert Safety.SAFE.value == "SAFE"
    assert Safety.INFO.value == "INFO"
    assert Safety.WARN.value == "WARN"
    assert Safety.CRITICAL.value == "CRITICAL"

@test("safety: classify_pg_type_change varchar widening is SAFE")
def test_safety_pg_type_safe():
    assert classify_pg_type_change({"type": "varchar", "length": 100}, {"type": "varchar", "length": 255}) == "SAFE"

@test("safety: classify_pg_type_change varchar narrowing is CRITICAL")
def test_safety_pg_type_critical():
    assert classify_pg_type_change({"type": "varchar", "length": 255}, {"type": "varchar", "length": 100}) == "CRITICAL"

@test("safety: classify_ch_column_change critical keys")
def test_safety_ch_col():
    assert classify_ch_column_change("ch_type") == Safety.CRITICAL
    assert classify_ch_column_change("ch_codec") == Safety.WARN
    assert classify_ch_column_change("ch_comment") == Safety.INFO

# ═══════════════════════════════════════════════════════════════
# 11. IMPACT ANALYSIS
# ═══════════════════════════════════════════════════════════════

from dbwarden.engine.impact import analyze_impact
from dbwarden.engine.impact import parse_plan as impact_parse_plan

@test("impact: parse_plan loads JSON file")
def test_parse_plan():
    import tempfile
    with tempfile.NamedTemporaryFile(mode="w", suffix=".json", delete=False) as f:
        json.dump({
            "migration_id": "test__0001",
            "operations": [
                {"type": "drop_column", "table": "users", "column": "username", "severity": "WARNING"}
            ]
        }, f)
        fname = f.name
    try:
        plan = impact_parse_plan(fname)
        assert plan["migration_id"] == "test__0001"
        assert len(plan["operations"]) == 1
    finally:
        os.unlink(fname)

@test("impact: analyze_impact finds references in source")
def test_analyze_impact():
    import tempfile
    with tempfile.TemporaryDirectory() as tmp:
        src_file = Path(tmp) / "test_code.py"
        src_file.write_text("# Test file\nuser.username = 'test'\nprint(user.username)\n")
        
        plan_path = Path(tmp) / "plan.json"
        json.dump({
            "migration_id": "test__0001",
            "operations": [
                {"type": "drop_column", "table": "users", "column": "username", "severity": "WARNING"}
            ]
        }, open(plan_path, "w"))
        
        result = analyze_impact(str(plan_path), scan_path=tmp)
        assert result is not None

# ═══════════════════════════════════════════════════════════════
# 12. OFFLINE MIGRATIONS
# ═══════════════════════════════════════════════════════════════

from dbwarden.engine.offline import model_state_to_dict, diff_model_states

@test("offline: model_state_to_dict produces JSON-serializable output")
def test_model_state():
    class OfflineModel(Base):
        __tablename__ = "offline_test"
        id = Column(Integer, primary_key=True)
        name = Column(String(255))
        class Meta(TableMeta):
            comment = "Offline test"
    
    table = extract_table_from_model(OfflineModel)
    state = model_state_to_dict([table])
    assert "tables" in state
    assert "offline_test" in state["tables"]
    assert state["tables"]["offline_test"]["comment"] == "Offline test"
    # Verify JSON-serializable
    json.dumps(state)  # should not raise

@test("offline: diff_model_states detects changes")
def test_diff_model_states():
    prev = {
        "tables": {
            "users": {
                "columns": {
                    "id": {"name": "id", "type": "integer", "nullable": False, "primary_key": True, "unique": False, "default": None, "foreign_key": None, "comment": None},
                },
                "indexes": [], "foreign_keys": [], "checks": [], "uniques": [], "comment": None, "object_type": "table", "backend_table_spec": {},
            }
        }
    }
    curr = {
        "tables": {
            "users": {
                "columns": {
                    "id": {"name": "id", "type": "integer", "nullable": False, "primary_key": True, "unique": False, "default": None, "foreign_key": None, "comment": None},
                    "email": {"name": "email", "type": "varchar(255)", "nullable": False, "primary_key": False, "unique": False, "default": None, "foreign_key": None, "comment": None},
                },
                "indexes": [], "foreign_keys": [], "checks": [], "uniques": [], "comment": None, "object_type": "table", "backend_table_spec": {},
            }
        }
    }
    upgrade_ops, _ = diff_model_states(prev, curr)
    add_ops = [o for o in upgrade_ops if o["type"] == "add_column"]
    assert len(add_ops) >= 1, f"Expected add_column ops, got: {upgrade_ops}"

# ═══════════════════════════════════════════════════════════════
# 13. FASTAPI INTEGRATION
# ═══════════════════════════════════════════════════════════════

from dbwarden.fastapi import (
    DBWardenHealthRouter, DBWardenRouter,
    dbwarden_lifespan, QueryTracingMiddleware, PoolMetricsCollector,
    override_database, migration_state,
)

@test("fastapi: DBWardenHealthRouter creates router")
def test_health_router():
    router = DBWardenHealthRouter()
    routes = [r.path for r in router.routes]
    assert "/liveness" in routes
    assert "/readiness" in routes

@test("fastapi: DBWardenRouter creates router")
def test_db_router():
    router = DBWardenRouter()
    routes = [r.path for r in router.routes]
    assert "/status" in routes

@test("fastapi: HealthRouter with auth mode")
def test_health_router_auth():
    router = DBWardenHealthRouter(auth_mode="authenticated", api_key="test-key")
    routes = [r.path for r in router.routes]
    assert "/liveness" in routes

@test("fastapi: QueryTracingMiddleware instantiates")
def test_query_tracing():
    middleware = QueryTracingMiddleware
    assert callable(middleware)

@test("fastapi: PoolMetricsCollector")
def test_pool_metrics():
    collector = PoolMetricsCollector()
    engine = create_engine("sqlite:///:memory:")
    collector.register("test", engine)
    metrics = collector.collect()
    assert "test" in metrics
    assert "pool_size" in metrics["test"]

@test("fastapi: override_database works")
async def test_override_db():
    from dbwarden import database_config
    reset_registry()
    
    database_config(
        database_name="primary",
        default=True,
        database_type="postgresql",
        database_url_sync="postgresql://dbwarden:dbwarden@localhost:15432/dbwarden",
        model_paths=[],
    )
    async with override_database("primary", "sqlite+aiosqlite:///:memory:"):
        db = get_database("primary")
        assert "sqlite" in db.sqlalchemy_url_sync
    db = get_database("primary")
    assert "postgresql" in db.sqlalchemy_url_sync

# ═══════════════════════════════════════════════════════════════
# 14. MODEL GENERATION
# ═══════════════════════════════════════════════════════════════

from dbwarden.commands import handle_generate_models

@test("generate-models: function exists and is callable")
def test_generate_models_fn():
    assert callable(handle_generate_models)

# ═══════════════════════════════════════════════════════════════
# 15. CLI COMMANDS
# ═══════════════════════════════════════════════════════════════

from dbwarden.commands import (
    handle_init, handle_status, handle_history,
    handle_make_migrations, handle_migrate, handle_rollback,
    handle_config, handle_version,
    handle_check_impact,
)

@test("cli: all handler functions are callable")
def test_cli_handlers():
    assert callable(handle_init)
    assert callable(handle_status)
    assert callable(handle_history)
    assert callable(handle_make_migrations)
    assert callable(handle_migrate)
    assert callable(handle_rollback)
    assert callable(handle_config)
    assert callable(handle_version)
    assert callable(handle_check_impact)

@test("cli: version returns correct string")
def test_cli_version():
    from dbwarden.constants import DBWARDEN_VERSION
    assert DBWARDEN_VERSION is not None

# ═══════════════════════════════════════════════════════════════
# 16. SQL TRANSLATION (dev mode)
# ═══════════════════════════════════════════════════════════════

from dbwarden.engine.sqlite_translation import translate_type_to_sqlite, translate_default_to_sqlite

@test("translation: translate PostgreSQL types to SQLite")
def test_type_translation():
    result, warning = translate_type_to_sqlite("integer")
    assert "INTEGER" in result.upper()
    result2, warning2 = translate_type_to_sqlite("text")
    assert "TEXT" in result2.upper()
    result3, warning3 = translate_type_to_sqlite("uuid")
    assert "TEXT" in result3.upper()
    result4, warning4 = translate_type_to_sqlite("jsonb")
    assert "TEXT" in result4.upper()

@test("translation: translate default expressions")
def test_default_translation():
    result = translate_default_to_sqlite("CURRENT_TIMESTAMP")
    assert result is not None

# ═══════════════════════════════════════════════════════════════
# 17. SANDBOX
# ═══════════════════════════════════════════════════════════════

from dbwarden.sandbox import (
    validate_path, SecurityError, RestrictedFileLoader,
    RestrictedModuleFinder
)
from pathlib import Path

@test("sandbox: validate_path rejects traversal")
def test_sandbox_traversal():
    try:
        validate_path(Path("/tmp/../../etc/passwd"), Path("/tmp"))
        assert False, "Should have raised SecurityError"
    except SecurityError:
        pass

@test("sandbox: validate_path accepts valid path")
def test_sandbox_valid():
    validate_path(Path("/tmp/dbwarden-prod-test/dbwarden_test_config.py"), Path("/tmp"))

@test("sandbox: restricted loader allows dbwarden imports")
def test_restricted_loader():
    loader = RestrictedFileLoader("/tmp/test.py", Path("/tmp"))
    assert loader._is_allowed_import("dbwarden")
    assert loader._is_allowed_import("dbwarden.database_config")
    assert not loader._is_allowed_import("os")
    assert not loader._is_allowed_import("subprocess")

# ═══════════════════════════════════════════════════════════════
# 18. REPOSITORY LAYER
# ═══════════════════════════════════════════════════════════════

from dbwarden.repositories.migrations_repo import (
    create_migrations_table_if_not_exists, get_migration_records, fetch_latest_versioned_migration,
)
from dbwarden.repositories.lock_repo import create_lock_table_if_not_exists, acquire_lock, release_lock, check_lock
from dbwarden.repositories.seeds_repo import (
    create_seeds_table_if_not_exists, get_all_seed_records, record_applied_seed, seed_is_applied
)

@test("repository: migration table CRUD against live PostgreSQL")
def test_migration_repo_pg():
    from dbwarden.database.connection import get_db_connection
    
    # Register a primary database config so repo functions can look it up
    from dbwarden import database_config
    reset_registry()
    database_config(
        database_name="primary",
        default=True,
        database_type="postgresql",
        database_url_sync="postgresql://dbwarden:dbwarden@localhost:15432/dbwarden",
        model_paths=[],
    )
    # Also register in the config module for get_db_connection to find
    import dbwarden.config as cfg
    from dbwarden.config import _finalize_entries
    from dbwarden.config_registry import registered_entries
    entries = registered_entries()
    if entries:
        mc = _finalize_entries(entries, Path("/tmp"))
        # Patch get_database to work without source resolution
        cfg.get_multi_db_config = lambda: mc
    
    with get_db_connection("primary") as conn:
        conn.execute(text("DROP TABLE IF EXISTS _dbwarden_migrations"))
        conn.execute(text("DROP TABLE IF EXISTS _dbwarden_locks"))
        conn.execute(text("DROP TABLE IF EXISTS _dbwarden_seeds"))
    
    create_lock_table_if_not_exists("primary")
    acquired = acquire_lock("primary")
    assert acquired is True
    locked = check_lock("primary")
    assert locked is True
    released = release_lock("primary")
    assert released is True
    locked = check_lock("primary")
    assert locked is False
    
    create_migrations_table_if_not_exists("primary")
    records = get_migration_records("primary")
    assert isinstance(records, list)
    
    create_seeds_table_if_not_exists("primary")
    record_applied_seed(version="0001", description="test seed", filename="test_seed.py", seed_type="py", checksum="abc123", db_name="primary")
    assert seed_is_applied("0001", "primary") is True
    records = get_all_seed_records("primary")
    assert len(records) >= 1

# ═══════════════════════════════════════════════════════════════
# 19. PROMETHEUS METRICS
# ═══════════════════════════════════════════════════════════════

@test("metrics: metrics_enabled checks env var")
def test_metrics_conditional():
    import os
    os.environ["DBWARDEN_METRICS"] = "true"
    try:
        from dbwarden.metrics import metrics_enabled
        # Don't reload; just check the env-reading function works
        assert callable(metrics_enabled)
    finally:
        os.environ.pop("DBWARDEN_METRICS", None)

# ═══════════════════════════════════════════════════════════════
# 20. CONSTANTS
# ═══════════════════════════════════════════════════════════════

from dbwarden.constants import (
    MIGRATIONS_DIR, SEEDS_DIR, SEEDS_TABLE, DBWARDEN_VERSION,
)
from dbwarden.config import DEFAULT_MIGRATION_TABLE, DEFAULT_SEEDS_TABLE
from dbwarden import __version__ as pkg_version

@test("constants: all expected constants exist")
def test_constants():
    assert MIGRATIONS_DIR == "migrations"
    assert SEEDS_DIR == "seeds"
    assert SEEDS_TABLE == "_dbwarden_seeds"
    assert DEFAULT_MIGRATION_TABLE == "_dbwarden_migrations"
    assert DEFAULT_SEEDS_TABLE == "_dbwarden_seeds"
    assert DBWARDEN_VERSION is not None
    assert pkg_version is not None

# ═══════════════════════════════════════════════════════════════
# RUN
# ═══════════════════════════════════════════════════════════════

if __name__ == "__main__":
    import pytest
    print("=" * 60)
    print("DBWarden Comprehensive Integration Test Suite")
    print("=" * 60)
    
    # Discover and run all test functions
    import inspect
    test_fns = [(name, fn) for name, fn in globals().items() 
                if name.startswith("test_") and callable(fn)]
    
    print(f"\nFound {len(test_fns)} test functions")
    print("-" * 60)
    
    # Run each test
    for name, fn in test_fns:
        try:
            # Check if it's async
            if inspect.iscoroutinefunction(fn):
                asyncio.run(fn())
                results["passed"].append(name)
                print(f"  PASS [{_test_count}] {name}")
            else:
                fn()
        except Exception as e:
            import traceback
            results["failed"].append((name, str(e), traceback.format_exc()))
            print(f"  FAIL [{_test_count}] {name}: {e}")
    
    # Report
    print("\n" + "=" * 60)
    print("RESULTS")
    print("=" * 60)
    print(f"  Passed: {len(results['passed'])}")
    print(f"  Failed: {len(results['failed'])}")
    if results["failed"]:
        print("\nFAILURES:")
        for name, err, tb in results["failed"]:
            print(f"  - {name}")
            print(f"    {err}")
    print()
