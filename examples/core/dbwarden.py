from dbwarden import database_config

primary = database_config(
    database_name="primary",
    default=True,
    database_type="sqlite",
    database_url_sync="sqlite:///./app.db",
    model_paths=["app"],
)
