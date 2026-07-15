import pytest

from dbwarden.engine.shared.format_utils import _format_meta_value


class TestFormatMetaValue:
    def test_string_value(self):
        result = _format_meta_value("hello")
        assert result == ["        'hello'"]

    def test_empty_list(self):
        result = _format_meta_value([])
        assert result == ["        []"]

    def test_list_of_scalars(self):
        result = _format_meta_value([1, 2, 3])
        assert result == ["        [", "            1,", "            2,", "            3,", "        ]"]

    def test_list_of_dicts(self):
        result = _format_meta_value([{"a": 1}])
        assert result == [
            "        [",
            "            {'a': 1},",
            "        ]",
        ]

    def test_list_of_strings(self):
        result = _format_meta_value(["a", "b"])
        assert result == ["        [", "            'a',", "            'b',", "        ]"]

    def test_int_value(self):
        result = _format_meta_value(42)
        assert result == ["        42"]

    def test_float_value(self):
        result = _format_meta_value(3.14)
        assert result == ["        3.14"]

    def test_none_value(self):
        result = _format_meta_value(None)
        assert result == ["        None"]

    def test_bool_value(self):
        result = _format_meta_value(True)
        assert result == ["        True"]

    def test_custom_indent(self):
        result = _format_meta_value("hello", indent="  ")
        assert result == ["  'hello'"]
