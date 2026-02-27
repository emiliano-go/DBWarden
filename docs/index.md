# DBWarden - Professional Database Migration System

**DBWarden** is a professional-grade database migration system designed specifically for Python projects using SQLAlchemy. It provides a robust, reliable, and developer-friendly approach to managing database schema changes across different environments.

## What is DBWarden?

DBWarden addresses the critical challenge of maintaining consistent database schemas across development, staging, and production environments. It combines the flexibility of SQL-based migrations with the convenience of automatic migration generation from SQLAlchemy models.

### Features

- **Automatic Migration Generation**: Automatically generate SQL migrations from your SQLAlchemy models
- **Version Control**: Track all schema changes with detailed history and timestamps
- **Rollback Support**: Safely revert migrations when needed
- **Multiple Database Support**: Works with PostgreSQL, MySQL, and SQLite
- **Model Discovery**: Automatically finds and processes your SQLAlchemy models
- **Migration Locking**: Prevents concurrent migration execution
- **Schema Inspection**: Inspect and compare database schemas

## Architecture Overview

DBWarden follows a modular architecture designed for reliability and extensibility:

```
┌─────────────────────────────────────────────────────────┐
│                     DBWarden CLI                        │
│                    (Typer-based)                        │
├─────────────────────────────────────────────────────────┤
│  Commands Layer                                         │
│  ├── init         ├── migrate      ├── rollback         │
│  ├── make-migrations ├── history    ├── status          │
│  └── ...          └── ...           └── ...             │
├─────────────────────────────────────────────────────────┤
│  Engine Layer                                           │
│  ├── Model Discovery  ├── Versioning  ├── File Parser   │
│  └── Checksum         └── Locking                       │
├─────────────────────────────────────────────────────────┤
│  Repository Layer                                       │
│  ├── Migration Records  ├── Lock Management             │
├─────────────────────────────────────────────────────────┤
│  Database Layer                                         │
│  ├── Connection Pool  ├── SQL Execution                 │
└─────────────────────────────────────────────────────────┘
```

## Quick Example

```bash
# Initialize migrations directory
dbwarden init

# Generate migration from SQLAlchemy models
dbwarden make-migrations "create users table"

# Apply migrations
dbwarden migrate --verbose

# Check migration history
dbwarden history
```

## Next Steps

- [Installation](installation.md): Get started with installing DBWarden
- [Configuration](configuration.md): Set up your environment
- [Quick Start](quickstart.md): Walk through a complete example
- [Commands](commands.md): Explore all available commands
- [SQLAlchemy Models](models.md): Learn how to define models for migrations

## License

DBWarden is released under the MIT License.
