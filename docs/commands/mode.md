# mode Command

Display the current sync/async execution mode.

## Description

The `mode` command shows whether DBWarden is configured to use synchronous or asynchronous database operations.

## Usage

```bash
dbwarden mode
```

## Examples

### Synchronous Mode

```
Sync
```

### Asynchronous Mode

```
Async
```

## What It Shows

| Mode | Meaning |
|------|---------|
| **Sync** | Synchronous database operations |
| **Async** | Asynchronous database operations |

## How Mode Is Determined

1. **Configuration**: `async` setting from `warden.toml`

## Configuration

### Enable Async Mode

```toml
async = true
sqlalchemy_url = "postgresql+asyncpg://user:pass@host/db"
```

### Disable Async Mode

```toml
async = false
sqlalchemy_url = "postgresql://user:pass@host/db"
```

## Use Cases

### Debug Connection Issues

```bash
dbwarden mode
# Verify expected mode

# Check URL matches mode
dbwarden env
# Confirm DBWARDEN_SQLALCHEMY_URL has correct driver
```

### Verify CI/CD Configuration

```bash
dbwarden mode
# Expected: Async for production
```

## Async vs Sync

### Synchronous Mode

**Pros:**
- Simpler debugging
- Better for small applications
- Easier error handling

**Cons:**
- Blocking operations
- Slower for large datasets

### Asynchronous Mode

**Pros:**
- Non-blocking
- Better for high concurrency
- Faster I/O operations

**Cons:**
- More complex debugging
- Not all drivers support async

## Supported Databases

| Database | Sync | Async |
|----------|------|-------|
| PostgreSQL | Yes | Yes |
| MySQL | Yes | No |
| SQLite | Yes | Yes |

## See Also

- [env](env.md): Show full environment configuration
- [configuration](../configuration.md): Configuration guide
