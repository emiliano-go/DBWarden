from dbwarden import database_config

primary = database_config(
    database_name="primary",
    default=True,
    database_type="postgresql",
    database_url_sync="postgresql://user:password@localhost:5432/myapp",
    database_url_async="postgresql+asyncpg://user:password@localhost:5432/myapp",
    model_paths=["app.models"],
)
