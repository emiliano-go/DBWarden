---
description: Extensions extend DBWarden with FastAPI integration, sandbox testing, and
  pluggable runtime features for production use.
---

# Extensions

DBWarden ships with a set of optional extensions that integrate with common Python frameworks and workflows. Each extension is installed via an optional dependency group.

## Available Extensions

| Extension | Install | Purpose |
|-----------|---------|---------|
| [FastAPI](../fastapi/index.md) | `uv add "dbwarden[fastapi]"` | Async database sessions, health endpoints, migration lifecycle hooks |
| [Sandbox](sandbox.md) | built-in | Temporary database validation and config file security isolation |

## FastAPI Integration

First-class FastAPI integration for database sessions, health checks, and migration management. One configuration source for both migrations and runtime, with no more split configs.

See the [FastAPI Integration](../fastapi/index.md) guide for setup, tutorials, and reference.

## Sandbox

Two sandbox mechanisms protect your production data:

- **Migration sandbox** (`--sandbox` flag): applies pending migrations to a temporary database and reports results without modifying the real target.
- **Config security sandbox**: restricts imports when loading isolated config files, preventing path traversal and accidental code execution.

See the [Sandbox](sandbox.md) guide for usage, CI patterns, and configuration.
