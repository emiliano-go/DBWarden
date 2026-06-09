from dbwarden import database_config

primary = database_config(
    database_name="primary",
    default=True,
    database_type="postgresql",
    database_url_sync="postgresql://user:password@localhost:5432/primary",
    database_url_async="postgresql+asyncpg://user:password@localhost:5432/primary",
    model_paths=["app.models.primary"],
)

analytics = database_config(
    database_name="analytics",
    database_type="clickhouse",
    database_url_sync="http://localhost:8123/analytics",
    model_paths=["app.models.analytics"],
)
