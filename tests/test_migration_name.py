import pytest

from dbwarden.engine.migration_name import (
    Change,
    autogenerate_migration_name,
    _pluralize,
    _truncate,
    _single_change,
    _single_table_multiple_changes,
    _multiple_tables,
)


class TestPluralize:
    def test_add_column(self):
        assert _pluralize("add_column") == "add_columns"

    def test_drop_column(self):
        assert _pluralize("drop_column") == "drop_columns"

    def test_rename_column(self):
        assert _pluralize("rename_column") == "rename_columns"

    def test_create_table(self):
        assert _pluralize("create_table") == "create_tables"

    def test_drop_table(self):
        assert _pluralize("drop_table") == "drop_tables"

    def test_add_index(self):
        assert _pluralize("add_index") == "add_indexes"

    def test_drop_index(self):
        assert _pluralize("drop_index") == "drop_indexes"

    def test_add_foreign_key(self):
        assert _pluralize("add_foreign_key") == "add_foreign_keys"

    def test_drop_foreign_key(self):
        assert _pluralize("drop_foreign_key") == "drop_foreign_keys"

    def test_add_constraint(self):
        assert _pluralize("add_constraint") == "add_constraints"

    def test_drop_constraint(self):
        assert _pluralize("drop_constraint") == "drop_constraints"

    def test_alter_column_type(self):
        assert _pluralize("alter_column_type") == "alter_column_types"

    def test_alter_column_nullable(self):
        assert _pluralize("alter_column_nullable") == "alter_column_nullables"

    def test_alter_column_default(self):
        assert _pluralize("alter_column_default") == "alter_column_defaults"

    def test_unknown_operation(self):
        assert _pluralize("unknown_op") == "unknown_ops"

    def test_empty_string(self):
        assert _pluralize("") == "s"


class TestTruncate:
    def test_short_name_unchanged(self):
        name = "add_column_users_email"
        assert _truncate(name) == name

    def test_near_72_chars_unchanged(self):
        name = "add_column_" + "a" * 61
        assert len(name) == 72
        assert _truncate(name) == name

    def test_truncates_long_name(self):
        name = "add_column_" + "verylongtablename_" * 10
        assert len(name) > 72
        result = _truncate(name)
        assert len(result) <= 72

    def test_truncates_preserving_operation_prefix(self):
        name = "add_columns_users_" + "a" * 100
        result = _truncate(name)
        assert result.startswith("add_columns_users_")
        assert len(result) <= 72

    def test_op_words_detected(self):
        name = "create_tables_users_posts_articles"
        result = _truncate(name)
        assert "create_tables" in result

    def test_alter_op_words_detected(self):
        name = "alter_column_type_users_bio"
        result = _truncate(name)
        assert "alter_column_type" in result


class TestSingleChange:
    def test_with_target(self):
        c = Change(operation="add_column", table="users", target="email")
        result = _single_change(c)
        assert result == "add_column_users_email"

    def test_without_target(self):
        c = Change(operation="create_table", table="users")
        result = _single_change(c)
        assert result == "create_table_users"

    def test_with_resolved_from_ignored(self):
        c = Change(operation="rename_column", table="users", target="email", resolved_from="prompt")
        result = _single_change(c)
        assert result == "rename_column_users_email"

    def test_truncation_applied(self):
        long_target = "a" * 100
        c = Change(operation="add_column", table="users", target=long_target)
        result = _single_change(c)
        assert len(result) <= 72


class TestSingleTableMultipleChanges:
    def test_single_target_pluralized(self):
        changes = [
            Change(operation="add_column", table="users", target="email"),
        ]
        result = _single_table_multiple_changes("users", changes)
        assert "add_columns" in result

    def test_two_targets(self):
        changes = [
            Change(operation="add_column", table="users", target="email"),
            Change(operation="add_column", table="users", target="phone"),
        ]
        result = _single_table_multiple_changes("users", changes)
        assert result == "add_columns_users_email_phone"

    def test_three_or_more_targets(self):
        changes = [
            Change(operation="add_column", table="users", target="email"),
            Change(operation="add_column", table="users", target="phone"),
            Change(operation="add_column", table="users", target="address"),
        ]
        result = _single_table_multiple_changes("users", changes)
        assert "add_columns_users_email_phone" in result
        assert "1_more" in result

    def test_mixed_operations_uses_alter(self):
        changes = [
            Change(operation="add_column", table="users", target="email"),
            Change(operation="drop_column", table="users", target="name"),
        ]
        result = _single_table_multiple_changes("users", changes)
        assert result.startswith("alter_")

    def test_no_targets_uses_alter(self):
        changes = [
            Change(operation="create_table", table="users"),
            Change(operation="drop_table", table="users"),
        ]
        result = _single_table_multiple_changes("users", changes)
        assert result == "alter_users"

    def test_single_mixed_op_with_targets(self):
        changes = [
            Change(operation="add_column", table="users", target="a"),
            Change(operation="drop_column", table="users", target="b"),
        ]
        result = _single_table_multiple_changes("users", changes)
        assert result == "alter_users_a_b"


class TestMultipleTables:
    def test_two_tables_same_op_no_targets(self):
        changes_by_table = {
            "users": [Change(operation="create_table", table="users")],
            "posts": [Change(operation="create_table", table="posts")],
        }
        result = _multiple_tables(changes_by_table)
        assert result == "create_tables_users_posts"

    def test_multi_table_primary_has_targets(self):
        changes_by_table = {
            "users": [Change(operation="add_column", table="users", target="email")],
            "posts": [Change(operation="create_table", table="posts")],
        }
        result = _multiple_tables(changes_by_table)
        assert "alter_" in result
        assert "users" in result
        assert "email" in result

    def test_three_tables_same_op(self):
        changes_by_table = {
            "users": [Change(operation="drop_table", table="users")],
            "posts": [Change(operation="drop_table", table="posts")],
            "comments": [Change(operation="drop_table", table="comments")],
        }
        result = _multiple_tables(changes_by_table)
        assert "drop_tables" in result
        assert "more_tables" in result

    def test_mixed_ops_across_tables(self):
        changes_by_table = {
            "users": [Change(operation="add_column", table="users", target="email")],
            "posts": [Change(operation="drop_column", table="posts", target="title")],
        }
        result = _multiple_tables(changes_by_table)
        assert result.startswith("alter_")

    def test_primary_table_chosen_by_change_count(self):
        changes_by_table = {
            "users": [
                Change(operation="add_column", table="users", target="a"),
                Change(operation="add_column", table="users", target="b"),
            ],
            "posts": [Change(operation="add_column", table="posts", target="c")],
        }
        result = _multiple_tables(changes_by_table)
        assert result.startswith("add_column_users")
        assert "a" in result
        assert "b" in result
        assert "1_more_tables" in result


class TestAutogenerateMigrationName:
    def test_empty_changes_returns_empty(self):
        assert autogenerate_migration_name([]) == ""

    def test_single_change_with_target(self):
        changes = [Change(operation="add_column", table="users", target="email")]
        result = autogenerate_migration_name(changes)
        assert result == "add_column_users_email"

    def test_single_change_no_target(self):
        changes = [Change(operation="create_table", table="users")]
        result = autogenerate_migration_name(changes)
        assert result == "create_table_users"

    def test_rename_column(self):
        changes = [Change(operation="rename_column", table="users", target="email")]
        result = autogenerate_migration_name(changes)
        assert result == "rename_column_users_email"

    def test_rename_table(self):
        changes = [Change(operation="rename_table", table="users", target="accounts")]
        result = autogenerate_migration_name(changes)
        assert result == "rename_table_users_accounts"

    def test_alter_column_type(self):
        changes = [Change(operation="alter_column_type", table="users", target="bio")]
        result = autogenerate_migration_name(changes)
        assert result == "alter_column_type_users_bio"

    def test_alter_column_nullable(self):
        changes = [Change(operation="alter_column_nullable", table="users", target="email")]
        result = autogenerate_migration_name(changes)
        assert result == "alter_column_nullable_users_email"

    def test_alter_column_default(self):
        changes = [Change(operation="alter_column_default", table="users", target="role")]
        result = autogenerate_migration_name(changes)
        assert result == "alter_column_default_users_role"

    def test_add_foreign_key(self):
        changes = [Change(operation="add_foreign_key", table="users", target="groups(id)")]
        result = autogenerate_migration_name(changes)
        assert result == "add_foreign_key_users_groups(id)"

    def test_drop_foreign_key(self):
        changes = [Change(operation="drop_foreign_key", table="users")]
        result = autogenerate_migration_name(changes)
        assert result == "drop_foreign_key_users"

    def test_add_index(self):
        changes = [Change(operation="add_index", table="users", target="email")]
        result = autogenerate_migration_name(changes)
        assert result == "add_index_users_email"

    def test_drop_index(self):
        changes = [Change(operation="drop_index", table="users")]
        result = autogenerate_migration_name(changes)
        assert result == "drop_index_users"

    def test_two_add_columns_same_table(self):
        changes = [
            Change(operation="add_column", table="users", target="email"),
            Change(operation="add_column", table="users", target="phone"),
        ]
        result = autogenerate_migration_name(changes)
        assert result == "add_columns_users_email_phone"

    def test_three_add_columns_same_table(self):
        changes = [
            Change(operation="add_column", table="users", target="email"),
            Change(operation="add_column", table="users", target="phone"),
            Change(operation="add_column", table="users", target="address"),
        ]
        result = autogenerate_migration_name(changes)
        assert "1_more" in result

    def test_add_and_drop_same_table(self):
        changes = [
            Change(operation="add_column", table="users", target="email"),
            Change(operation="drop_column", table="users", target="name"),
        ]
        result = autogenerate_migration_name(changes)
        assert result.startswith("alter_")

    def test_rename_and_type_change_same_table(self):
        changes = [
            Change(operation="rename_column", table="users", target="email"),
            Change(operation="alter_column_type", table="users", target="bio"),
        ]
        result = autogenerate_migration_name(changes)
        assert result.startswith("alter_")

    def test_same_op_two_tables(self):
        changes = [
            Change(operation="create_table", table="users"),
            Change(operation="create_table", table="posts"),
        ]
        result = autogenerate_migration_name(changes)
        assert result == "create_tables_users_posts"

    def test_three_tables_same_op(self):
        changes = [
            Change(operation="drop_table", table="users"),
            Change(operation="drop_table", table="posts"),
            Change(operation="drop_table", table="comments"),
        ]
        result = autogenerate_migration_name(changes)
        assert "drop_tables" in result
        assert "more_tables" in result

    def test_mixed_ops_multi_table(self):
        changes = [
            Change(operation="add_column", table="users", target="email"),
            Change(operation="create_table", table="posts"),
        ]
        result = autogenerate_migration_name(changes)
        assert "alter_" in result
        assert "email" in result
        assert "users" in result

    def test_truncation_of_very_long_name(self):
        changes = [
            Change(operation="add_column", table="users", target="a" * 100),
        ]
        result = autogenerate_migration_name(changes)
        assert len(result) <= 72

    def test_complex_multi_table_multi_target(self):
        changes = [
            Change(operation="add_column", table="users", target="email"),
            Change(operation="add_column", table="users", target="phone"),
            Change(operation="add_column", table="users", target="address"),
            Change(operation="add_column", table="posts", target="title"),
            Change(operation="add_column", table="comments", target="body"),
        ]
        result = autogenerate_migration_name(changes)
        assert "add_column_users" in result
        assert "more_targets" in result
        assert "more_tables" in result

    def test_drop_table_and_add_column_combined(self):
        changes = [
            Change(operation="drop_table", table="legacy"),
            Change(operation="add_column", table="users", target="new_col"),
        ]
        result = autogenerate_migration_name(changes)
        assert result

    def test_rename_table_with_column_rename(self):
        changes = [
            Change(operation="rename_table", table="users", target="accounts"),
            Change(operation="rename_column", table="accounts", target="email"),
        ]
        result = autogenerate_migration_name(changes)
        assert result.startswith("alter_")

    def test_fk_and_index_combined(self):
        changes = [
            Change(operation="add_foreign_key", table="users", target="groups(id)"),
            Change(operation="add_index", table="users", target="email"),
        ]
        result = autogenerate_migration_name(changes)
        assert result.startswith("alter_")
