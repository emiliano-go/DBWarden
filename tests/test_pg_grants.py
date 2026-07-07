from dbwarden.engine.model_discovery import (
    _build_grant_sql,
    _build_revoke_sql,
    _build_create_policy_sql,
    _build_alter_policy_sql,
)


class TestPGGrantsSQL:
    def test_grant_all_to_role(self):
        grant = {"role": "app_user", "privileges": "ALL", "grantable": False}
        sql = _build_grant_sql(grant, "public.users")
        assert sql == "GRANT ALL ON TABLE public.users TO app_user;"

    def test_grant_select_insert_to_public(self):
        grant = {"role": "PUBLIC", "privileges": ["SELECT", "INSERT"], "grantable": False}
        sql = _build_grant_sql(grant, "public.articles")
        assert sql == "GRANT SELECT, INSERT ON TABLE public.articles TO PUBLIC;"

    def test_grant_with_grant_option(self):
        grant = {"role": "admin", "privileges": "ALL", "grantable": True}
        sql = _build_grant_sql(grant, "accounts")
        assert sql == 'GRANT ALL ON TABLE accounts TO "admin" WITH GRANT OPTION;'

    def test_grant_schema_qualified(self):
        grant = {"role": "analyst", "privileges": ["SELECT"], "grantable": False}
        sql = _build_grant_sql(grant, '"app".orders')
        assert sql == 'GRANT SELECT ON TABLE "app".orders TO analyst;'

    def test_revoke_all_from_role(self):
        grant = {"role": "app_user", "privileges": "ALL", "grantable": False}
        sql = _build_revoke_sql(grant, "public.users")
        assert sql == "REVOKE ALL ON TABLE public.users FROM app_user;"

    def test_revoke_with_cascade(self):
        grant = {"role": "admin", "privileges": "ALL", "grantable": True}
        sql = _build_revoke_sql(grant, "accounts")
        assert sql == 'REVOKE ALL ON TABLE accounts FROM "admin" CASCADE;'

    def test_revoke_multiple_roles(self):
        grant = {"role": ["reader", "analyst"], "privileges": ["SELECT"], "grantable": False}
        sql = _build_revoke_sql(grant, "public.reports")
        assert sql == "REVOKE SELECT ON TABLE public.reports FROM reader, analyst;"

    def test_revoke_select_update_from_role(self):
        grant = {"role": "app_user", "privileges": ["SELECT", "UPDATE"], "grantable": False}
        sql = _build_revoke_sql(grant, "public.tasks")
        assert sql == "REVOKE SELECT, UPDATE ON TABLE public.tasks FROM app_user;"


class TestPGRLSPolicySQL:
    def test_create_permissive_policy(self):
        policy = {
            "name": "user_own_data",
            "command": "SELECT",
            "role": "web_user",
            "using": "user_id = current_user_id()",
            "permissive": "PERMISSIVE",
        }
        sql = _build_create_policy_sql(policy, "public.records")
        expected = (
            "CREATE POLICY user_own_data ON public.records "
            "FOR SELECT TO web_user USING (user_id = current_user_id());"
        )
        assert sql == expected

    def test_create_restrictive_policy_with_check(self):
        policy = {
            "name": "no_deletions",
            "command": "DELETE",
            "role": "app_role",
            "permissive": "RESTRICTIVE",
        }
        sql = _build_create_policy_sql(policy, "public.items")
        expected = (
            "CREATE POLICY no_deletions ON public.items "
            "AS RESTRICTIVE FOR DELETE TO app_role;"
        )
        assert sql == expected

    def test_create_policy_public_role(self):
        policy = {
            "name": "public_select",
            "command": "SELECT",
            "role": "PUBLIC",
            "using": "true",
            "permissive": "PERMISSIVE",
        }
        sql = _build_create_policy_sql(policy, "public.products")
        expected = (
            "CREATE POLICY public_select ON public.products "
            "FOR SELECT TO PUBLIC USING (true);"
        )
        assert sql == expected

    def test_create_policy_with_check_on_insert(self):
        policy = {
            "name": "insert_own",
            "command": "INSERT",
            "role": "user_role",
            "with_check": "user_id = current_user_id()",
            "permissive": "PERMISSIVE",
        }
        sql = _build_create_policy_sql(policy, "public.events")
        expected = (
            "CREATE POLICY insert_own ON public.events "
            "FOR INSERT TO user_role WITH CHECK (user_id = current_user_id());"
        )
        assert sql == expected

    def test_alter_policy_role_and_using(self):
        policy = {
            "name": "user_own_data",
            "role": "new_role",
            "using": "owner_id = current_user_id()",
            "with_check": "owner_id = current_user_id()",
        }
        sql = _build_alter_policy_sql(policy, "public.records")
        expected = (
            "ALTER POLICY user_own_data ON public.records "
            "TO new_role USING (owner_id = current_user_id()) "
            "WITH CHECK (owner_id = current_user_id());"
        )
        assert sql == expected

    def test_alter_policy_role_only(self):
        policy = {"name": "simple_policy", "role": "admin_role"}
        sql = _build_alter_policy_sql(policy, "public.records")
        expected = "ALTER POLICY simple_policy ON public.records TO admin_role;"
        assert sql == expected
