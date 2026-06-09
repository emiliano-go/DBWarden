from __future__ import annotations

from unittest.mock import MagicMock, patch

import pytest


class TestAutoSchema:
    def test_auto_schema_raises_import_error(self):
        from dbwarden.schema._auto_schema import auto_schema

        with (
            patch("dbwarden.schema._auto_schema._schemap_auto_schema", None),
            pytest.raises(ImportError, match="schemap is required"),
        ):
            auto_schema(int)

    def test_schema_config_raises_import_error(self):
        from dbwarden.schema._auto_schema import SchemaConfig

        with (
            patch("dbwarden.schema._auto_schema._SchemaConfig", None),
            pytest.raises(ImportError, match="schemap is required"),
        ):
            SchemaConfig()

    @patch("dbwarden.schema._auto_schema._schemap_auto_schema")
    @patch("dbwarden.schema._auto_schema.apply_meta")
    @patch("dbwarden.schema._auto_schema._infer_schema_config")
    @patch("dbwarden.schema._auto_schema._merge_dbwarden_into_schemas")
    def test_auto_schema_with_cls(self, mock_merge, mock_infer, mock_meta, mock_schemap):
        mock_schemap.return_value = int

        from dbwarden.schema._auto_schema import auto_schema

        result = auto_schema(int)
        assert result is int
        mock_meta.assert_called_once_with(int)
        mock_merge.assert_called_once_with(int)

    @patch("dbwarden.schema._auto_schema._schemap_auto_schema")
    @patch("dbwarden.schema._auto_schema.apply_meta")
    @patch("dbwarden.schema._auto_schema._infer_schema_config")
    @patch("dbwarden.schema._auto_schema._merge_dbwarden_into_schemas")
    def test_auto_schema_decorator(self, mock_merge, mock_infer, mock_meta, mock_schemap):
        mock_schemap.return_value = int

        from dbwarden.schema._auto_schema import auto_schema

        decorator = auto_schema()
        result = decorator(int)
        assert result is int
        mock_meta.assert_called_once_with(int)

    @patch("dbwarden.schema._auto_schema.SchemaConfig")
    def test_infer_schema_config(self, mock_sc):
        mock_table = MagicMock()
        mock_column_public = MagicMock()
        mock_column_public.name = "name"
        mock_column_public.info = {}
        mock_column_private = MagicMock()
        mock_column_private.name = "_secret"
        mock_column_private.info = {}
        mock_column_hidden = MagicMock()
        mock_column_hidden.name = "internal"
        mock_column_hidden.info = {"dw_public": False}
        mock_table.columns = [mock_column_public, mock_column_private, mock_column_hidden]

        mock_cls = MagicMock()
        mock_cls.__table__ = mock_table

        from dbwarden.schema._auto_schema import _infer_schema_config

        _infer_schema_config(mock_cls)
        mock_sc.assert_called_once_with(
            exclude_public=["internal"],
            exclude_always=["_secret"],
        )

    def test_merge_dbwarden_into_schemas(self):
        mock_field = MagicMock()
        mock_field.description = None
        mock_field.json_schema_extra = None

        mock_schema_cls = MagicMock()
        mock_schema_cls.model_fields = {"name": mock_field}

        mock_col = MagicMock()
        mock_col.info = {"dw_comment": "The user name", "pg_index": "btree"}

        mock_table = MagicMock()
        mock_table.c.get.return_value = mock_col

        mock_cls = MagicMock()
        mock_cls.configure_mock(**{"__table__": mock_table})

        from dbwarden.schema._auto_schema import _merge_dbwarden_into_schemas

        with patch("dbwarden.schema._auto_schema.issubclass", return_value=True):
            setattr(mock_cls, "Schema", mock_schema_cls)
            _merge_dbwarden_into_schemas(mock_cls)

        assert mock_field.description == "The user name"
        assert mock_field.json_schema_extra is not None
        assert "dbwarden_backend_meta" in mock_field.json_schema_extra

    # --- Edge cases for _infer_schema_config ---

    @patch("dbwarden.schema._auto_schema.SchemaConfig")
    def test_infer_schema_config_no_columns(self, mock_sc):
        mock_table = MagicMock()
        mock_table.columns = []

        mock_cls = MagicMock()
        mock_cls.__table__ = mock_table

        from dbwarden.schema._auto_schema import _infer_schema_config

        _infer_schema_config(mock_cls)
        mock_sc.assert_called_once_with(exclude_public=[], exclude_always=[])

    @patch("dbwarden.schema._auto_schema.SchemaConfig")
    def test_infer_schema_config_only_public(self, mock_sc):
        mock_table = MagicMock()
        col = MagicMock()
        col.name = "email"
        col.info = {}
        mock_table.columns = [col]

        mock_cls = MagicMock()
        mock_cls.__table__ = mock_table

        from dbwarden.schema._auto_schema import _infer_schema_config

        _infer_schema_config(mock_cls)
        mock_sc.assert_called_once_with(exclude_public=[], exclude_always=[])

    @patch("dbwarden.schema._auto_schema.SchemaConfig")
    def test_infer_schema_config_only_private(self, mock_sc):
        mock_table = MagicMock()
        col = MagicMock()
        col.name = "_internal"
        col.info = {}
        mock_table.columns = [col]

        mock_cls = MagicMock()
        mock_cls.__table__ = mock_table

        from dbwarden.schema._auto_schema import _infer_schema_config

        _infer_schema_config(mock_cls)
        mock_sc.assert_called_once_with(exclude_public=[], exclude_always=["_internal"])

    # --- Edge cases for _merge_dbwarden_into_schemas ---

    def test_merge_schema_attr_is_none(self):
        mock_cls = MagicMock()
        mock_cls.configure_mock(**{"__table__": MagicMock()})

        from dbwarden.schema._auto_schema import _merge_dbwarden_into_schemas

        with patch("dbwarden.schema._auto_schema.issubclass", return_value=True):
            setattr(mock_cls, "Schema", None)
            # Should not raise
            _merge_dbwarden_into_schemas(mock_cls)

    def test_merge_schema_not_basemodel(self):
        from dbwarden.schema._auto_schema import _merge_dbwarden_into_schemas

        class NotBaseModel:
            model_fields = {}

        class MyModel:
            __table__ = MagicMock()
            Schema = NotBaseModel

        # Should skip since NotBaseModel is not a BaseModel subclass
        _merge_dbwarden_into_schemas(MyModel)

    def test_merge_field_not_in_table(self):
        mock_field = MagicMock()
        mock_field.description = None
        mock_field.json_schema_extra = None

        mock_schema = MagicMock()
        mock_schema.model_fields = {"ghost_field": mock_field}

        mock_table = MagicMock()
        mock_table.c.get.return_value = None

        mock_cls = MagicMock()
        mock_cls.configure_mock(**{"__table__": mock_table})

        from dbwarden.schema._auto_schema import _merge_dbwarden_into_schemas

        with patch("dbwarden.schema._auto_schema.issubclass", return_value=True):
            setattr(mock_cls, "Schema", mock_schema)
            _merge_dbwarden_into_schemas(mock_cls)
        # Should not call anything on field since sa_col is None

    def test_merge_field_no_dw_comment_no_backend_meta(self):
        mock_field = MagicMock()
        mock_field.description = None
        mock_field.json_schema_extra = None

        mock_schema = MagicMock()
        mock_schema.model_fields = {"name": mock_field}

        mock_col = MagicMock()
        mock_col.info = {}

        mock_table = MagicMock()
        mock_table.c.get.return_value = mock_col

        mock_cls = MagicMock()
        mock_cls.configure_mock(**{"__table__": mock_table})

        from dbwarden.schema._auto_schema import _merge_dbwarden_into_schemas

        with patch("dbwarden.schema._auto_schema.issubclass", return_value=True):
            setattr(mock_cls, "Schema", mock_schema)
            _merge_dbwarden_into_schemas(mock_cls)
        assert mock_field.description is None
        assert mock_field.json_schema_extra is None

    def test_merge_all_four_schema_types(self):
        from dbwarden.schema._auto_schema import _merge_dbwarden_into_schemas

        for attr in ["Schema", "CreateSchema", "UpdateSchema", "PublicSchema"]:
            mock_field = MagicMock()
            mock_field.description = None
            mock_field.json_schema_extra = None

            mock_schema = MagicMock()
            mock_schema.model_fields = {"x": mock_field}

            mock_col = MagicMock()
            mock_col.info = {"dw_comment": "desc"}

            mock_table = MagicMock()
            mock_table.c.get.return_value = mock_col

            mock_cls = MagicMock()
            mock_cls.configure_mock(**{"__table__": mock_table})

            with patch("dbwarden.schema._auto_schema.issubclass", return_value=True):
                setattr(mock_cls, attr, mock_schema)
                _merge_dbwarden_into_schemas(mock_cls)
            assert mock_field.description == "desc"

    def test_merge_preserves_existing_json_schema_extra(self):
        mock_field = MagicMock()
        mock_field.description = None
        mock_field.json_schema_extra = {"existing": True}

        mock_schema = MagicMock()
        mock_schema.model_fields = {"x": mock_field}

        mock_col = MagicMock()
        mock_col.info = {"pg_index": "btree"}

        mock_table = MagicMock()
        mock_table.c.get.return_value = mock_col

        mock_cls = MagicMock()
        mock_cls.configure_mock(**{"__table__": mock_table})

        from dbwarden.schema._auto_schema import _merge_dbwarden_into_schemas

        with patch("dbwarden.schema._auto_schema.issubclass", return_value=True):
            setattr(mock_cls, "Schema", mock_schema)
            _merge_dbwarden_into_schemas(mock_cls)
        assert mock_field.json_schema_extra["existing"] is True
        assert "dbwarden_backend_meta" in mock_field.json_schema_extra

    # --- Edge cases for auto_schema with explicit config ---

    @patch("dbwarden.schema._auto_schema._schemap_auto_schema")
    @patch("dbwarden.schema._auto_schema.apply_meta")
    @patch("dbwarden.schema._auto_schema._infer_schema_config")
    @patch("dbwarden.schema._auto_schema._merge_dbwarden_into_schemas")
    def test_auto_schema_with_explicit_config(
        self, mock_merge, mock_infer, mock_meta, mock_schemap
    ):
        mock_schemap.return_value = int
        explicit_config = MagicMock()

        from dbwarden.schema._auto_schema import auto_schema

        result = auto_schema(config=explicit_config)(int)
        assert result is int
        # _infer_schema_config should NOT be called when config is provided
        mock_infer.assert_not_called()

    # --- __all__ exports ---

    def test_all_exports(self):
        from dbwarden.schema._auto_schema import __all__

        assert "auto_schema" in __all__
        assert "SchemaConfig" in __all__
        assert len(__all__) == 2

    # --- SchemaConfig proxy with schemap installed ---

    def test_schema_config_proxy_with_schemap(self):
        from dbwarden.schema._auto_schema import _SchemaConfig

        if _SchemaConfig is not None:
            from dbwarden.schema._auto_schema import SchemaConfig

            result = SchemaConfig(exclude_public=["a"], exclude_always=["b"])
            assert result is not None
