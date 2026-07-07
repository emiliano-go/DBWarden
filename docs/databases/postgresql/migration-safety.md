# Migration Safety

DBWarden classifies migration changes using the `Safety` enum:

```python
from dbwarden.engine.safety import Safety

assert Safety.SAFE == "SAFE"
assert Safety.INFO == "INFO"
assert Safety.WARN == "WARN"
assert Safety.CRITICAL == "CRITICAL"
```

| Change Type | Severity | Flag Required |
|-------------|----------|---------------|
| Add column | `INFO` | None |
| Drop column | `WARNING` | `--force` |
| Change column type (safe) | `INFO` | None |
| Change column type (warn) | `WARNING` | `--force` |
| Change column type (critical) | `WARNING` | `--force` |
| Change column comment | `INFO` | None |
| Change PG column meta | `WARNING` | `--force` |
| Change fillfactor | `INFO` | None |
| Change tablespace | `WARNING` | `--force` |
| Change inheritance | `WARNING` | `--force` |
| Change exclude constraints | `WARNING` | `--force` |
| Change table comment | `INFO` | None |
| Change object type | `WARNING` | `--force` |
| Add / drop index | `INFO` / `WARNING` | `--force` |
| Add / drop FK | `INFO` / `WARNING` | `--force` |
| Refresh materialized view | `INFO` | None |
