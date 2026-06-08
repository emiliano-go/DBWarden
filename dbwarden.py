from dbwarden.config_registry import database_config

database_config(
    database_name="default",
    database_type="postgresql",
    database_url_sync="postgresql://postgres:test@localhost:5433/dbwarden_test",
    default=True,
    model_paths=[],
)
