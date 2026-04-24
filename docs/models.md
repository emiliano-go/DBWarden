# SQLAlchemy Models

DBWarden reads SQLAlchemy model metadata to generate migration SQL.

Use `model_paths` in your `database_config(...)` entries to control discovery.

Example:

```python
database_config(
    database_name="primary",
    default=True,
    database_type="postgresql",
    database_url="postgresql://user:pass@localhost:5432/main",
    model_paths=["app/models"],
)
```

Related docs:

- [Configuration](configuration.md)
- [Your First Migration](tutorial/your-first-migration.md)
