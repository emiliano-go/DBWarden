from __future__ import annotations

from typing import Any


def diff_models_against_snapshot(
    model_tables: list[Any],
    snapshot: dict[str, Any],
    database: str | None = None,
    db_name: str | None = None,
    clickhouse_engine_recreate: bool = False,
) -> tuple[list[dict[str, Any]], list[dict[str, Any]]]:
    upgrade_ops: list[dict[str, Any]] = []
    rollback_ops: list[dict[str, Any]] = []

    snapshot_tables = snapshot.get("tables", {})
    model_by_name = {t.name: t for t in model_tables}

    _SYSTEM_TABLE_PREFIXES = ("_dbwarden_", "dbwarden_lock")

    for table in model_tables:
        if table.name.startswith(_SYSTEM_TABLE_PREFIXES):
            continue
        if table.name not in snapshot_tables:
            continue
        if table.object_type == "view":
            continue

        snap_table = snapshot_tables[table.name]
        snap_columns = snap_table.get("columns", {})
        model_columns = {c.name: c for c in table.columns}

    from dbwarden.engine.core.protocol import Op
    from dbwarden.engine.core.registry import RegistryDriver
    from dbwarden.engine.backends.postgresql.handlers import ConstraintHandler
    _con_handler = ConstraintHandler()
    _con_handler._snapshot = snapshot
    _con_handler._view_tables = {t.name for t in model_tables if getattr(t, 'object_type', None) == 'view'}
    _con_driver = RegistryDriver()
    _con_driver.register(_con_handler)
    _con_up, _con_rb = _con_driver.run(snapshot, model_tables, None)
    for op in _con_up:
        upgrade_ops.append({"type": op.object_type, **op.upgrade_attrs})
    for op in _con_rb:
        rollback_ops.append({"type": op.object_type, **op.upgrade_attrs})

    from dbwarden.engine.backends.postgresql.handlers import ColumnHandler
    _col_handler = ColumnHandler()
    _col_handler._db_name = db_name
    _col_driver = RegistryDriver()
    _col_driver.register(_col_handler)
    _col_up, _col_rb = _col_driver.run(snapshot, model_tables, None)
    for op in _col_up:
        upgrade_ops.append({"type": op.object_type, **op.upgrade_attrs})
    for op in _col_rb:
        rollback_ops.append({"type": op.object_type, **op.upgrade_attrs})

    from dbwarden.engine.backends.clickhouse.handlers import ChTableHandler
    _ch_handler = ChTableHandler()
    _ch_handler.clickhouse_engine_recreate = clickhouse_engine_recreate
    _ch_driver = RegistryDriver()
    _ch_driver.register(_ch_handler)
    _ch_up, _ch_rb = _ch_driver.run(snapshot, model_tables, None)
    for op in _ch_up:
        upgrade_ops.append({"type": op.object_type, **op.upgrade_attrs})
    for op in _ch_rb:
        rollback_ops.append({"type": op.object_type, **op.upgrade_attrs})

    from dbwarden.engine.backends.postgresql.handlers import PgTableHandler
    _pgt_driver = RegistryDriver()
    _pgt_driver.register(PgTableHandler())
    _pgt_up, _pgt_rb = _pgt_driver.run(snapshot, model_tables, None)
    for op in _pgt_up:
        upgrade_ops.append({"type": op.object_type, **op.upgrade_attrs})
    for op in _pgt_rb:
        rollback_ops.append({"type": op.object_type, **op.upgrade_attrs})

    from dbwarden.engine.backends.postgresql.handlers import IndexHandler
    _idx_driver = RegistryDriver()
    _idx_driver.register(IndexHandler())
    _idx_up, _idx_rb = _idx_driver.run(snapshot, model_tables, None)
    for op in _idx_up:
        upgrade_ops.append({"type": op.object_type, **op.upgrade_attrs})
    for op in _idx_rb:
        rollback_ops.append({"type": op.object_type, **op.upgrade_attrs})

    from dbwarden.engine.backends.postgresql.handlers import EnumHandler
    _enum_driver = RegistryDriver()
    _enum_driver.register(EnumHandler())
    _enum_up_ops, _enum_rb_ops = _enum_driver.run(snapshot, model_tables, None)
    for op in _enum_up_ops:
        upgrade_ops.append({"type": op.object_type, **op.upgrade_attrs})
    for op in _enum_rb_ops:
        rollback_ops.append({"type": op.object_type, **op.upgrade_attrs})

    from dbwarden.engine.backends.postgresql.handlers import (
        CompositeTypeHandler,
        DefaultPrivilegesHandler,
        EventTriggerHandler,
        ExtendedStatisticsHandler,
        FunctionHandler,
        PartitionHandler,
        RoleHandler,
        SequenceHandler,
        StatisticsHandler,
        TriggerHandler,
    )
    _pg_pre_driver = RegistryDriver()
    _pg_pre_driver.register(CompositeTypeHandler())
    _pg_pre_driver.register(DefaultPrivilegesHandler())
    _pg_pre_driver.register(EventTriggerHandler())
    _pg_pre_driver.register(ExtendedStatisticsHandler())
    _pg_pre_driver.register(FunctionHandler())
    _pg_pre_driver.register(PartitionHandler())
    _pg_pre_driver.register(RoleHandler())
    _pg_pre_driver.register(SequenceHandler())
    _pg_pre_driver.register(StatisticsHandler())
    _pg_pre_driver.register(TriggerHandler())
    _pg_pre_up, _pg_pre_rb = _pg_pre_driver.run(snapshot, model_tables, None)
    for op in _pg_pre_up:
        upgrade_ops.append({"type": op.object_type, **op.upgrade_attrs})
    for op in _pg_pre_rb:
        rollback_ops.append({"type": op.object_type, **op.upgrade_attrs})

    from dbwarden.engine.backends.postgresql.handlers import (
        GrantsHandler,
        PoliciesHandler,
        StorageParamsHandler,
    )
    _pg5_driver = RegistryDriver()
    _pg5_driver.register(StorageParamsHandler())
    _pg5_driver.register(PoliciesHandler())
    _pg5_driver.register(GrantsHandler())
    _pg5_up, _pg5_rb = _pg5_driver.run(snapshot, model_tables, None)
    for op in _pg5_up:
        upgrade_ops.append({"type": op.object_type, **op.upgrade_attrs})
    for op in _pg5_rb:
        rollback_ops.append({"type": op.object_type, **op.upgrade_attrs})

    from dbwarden.engine.backends.postgresql.handlers import ViewHandler
    _view_driver = RegistryDriver()
    _view_driver.register(ViewHandler())
    _view_up, _view_rb = _view_driver.run(snapshot, model_tables, None)
    for op in _view_up:
        upgrade_ops.append({"type": op.object_type, **op.upgrade_attrs})
    for op in _view_rb:
        rollback_ops.append({"type": op.object_type, **op.upgrade_attrs})

    from dbwarden.engine.backends.postgresql.handlers import TableHandler
    _table_driver = RegistryDriver()
    _table_driver.register(TableHandler())
    _table_up, _table_rb = _table_driver.run(snapshot, model_tables, None)
    for op in _table_up:
        upgrade_ops.append({"type": op.object_type, **op.upgrade_attrs})
    for op in _table_rb:
        rollback_ops.append({"type": op.object_type, **op.upgrade_attrs})

    from dbwarden.engine.backends.mysql.handlers import MyTableHandler
    _my_driver = RegistryDriver()
    _my_driver.register(MyTableHandler())
    _my_up, _my_rb = _my_driver.run(snapshot, model_tables, None)
    for op in _my_up:
        upgrade_ops.append({"type": op.object_type, **op.upgrade_attrs})
    for op in _my_rb:
        rollback_ops.append({"type": op.object_type, **op.upgrade_attrs})

    for op in upgrade_ops + rollback_ops:
        if op.get("type") == "recreate_ch_table":
            tname = op["table"]
            mvs = sorted(
                mt.name for mt in model_tables
                if mt.clickhouse_options.get("ch_to_table") == tname
                and snapshot_tables.get(mt.name, {}).get("clickhouse_options", {}).get("ch_to_table") == tname
            )
            if mvs:
                op["dependent_mvs"] = mvs

    recreate_tables = {op["table"] for op in upgrade_ops if op.get("type") == "recreate_ch_table"}
    if recreate_tables:
        allowed = {"recreate_ch_table", "drop_table", "create_table", "rename_table", "alter_enum_add_value", "create_type", "drop_type"}
        upgrade_ops = [op for op in upgrade_ops if op.get("table") not in recreate_tables or op.get("type") in allowed]
        rollback_ops = [op for op in rollback_ops if op.get("table") not in recreate_tables or op.get("type") in allowed]

    return upgrade_ops, rollback_ops
