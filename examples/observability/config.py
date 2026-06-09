import os
from dbwarden import database_config

primary = database_config(
    database_name="primary",
    default=True,
    database_type="postgresql",
    database_url_sync=os.getenv(
        "DATABASE_URL",
        "postgresql://user:password@localhost:5432/myapp",
    ),
    database_url_async=os.getenv(
        "DATABASE_URL_ASYNC",
        "postgresql+asyncpg://user:password@localhost:5432/myapp",
    ),
    model_paths=["app.models"],
)
