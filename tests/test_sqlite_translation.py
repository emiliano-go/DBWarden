import pytest

from dbwarden.engine.sqlite_translation import (
    translate_default_to_sqlite,
    translate_type_to_sqlite,
)


class TestSqliteTypeTranslation:
    def test_translates_postgres_uuid_to_text(self):
        translated, warning = translate_type_to_sqlite("UUID")
        assert translated == "TEXT"
        assert warning is not None

    def test_translates_clickhouse_nullable_uint64_to_integer(self):
        translated, warning = translate_type_to_sqlite("Nullable(UInt64)")
        assert translated == "INTEGER"
        assert warning is not None

    def test_falls_back_unknown_type_to_text(self):
        translated, warning = translate_type_to_sqlite("GEOGRAPHY")
        assert translated == "TEXT"
        assert "Falling back to TEXT" in (warning or "")

    def test_unknown_type_raises_in_strict_mode(self):
        with pytest.raises(ValueError, match="not supported by SQLite"):
            translate_type_to_sqlite("GEOGRAPHY", strict=True)


class TestSqliteDefaultTranslation:
    def test_removes_unsupported_default_in_non_strict_mode(self):
        translated, warning = translate_default_to_sqlite("now()")
        assert translated is None
        assert warning is not None

    def test_unsupported_default_raises_in_strict_mode(self):
        with pytest.raises(ValueError, match="not supported by SQLite"):
            translate_default_to_sqlite("gen_random_uuid()", strict=True)
