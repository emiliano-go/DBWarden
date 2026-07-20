---
seo:
  title: Architecture - DBWarden Documentation
  canonical: https://dbwarden.emiliano-go.com/architecture-deep-dive
  robots: index,follow
  og:
    type: website
    title: Architecture - DBWarden Documentation
    description: This page explains DBWarden internals for contributors and advanced
      debugging.
    url: https://dbwarden.emiliano-go.com/architecture-deep-dive
    image: https://dbwarden.emiliano-go.com/assets/images/og-image.png
    image:width: 1376
    image:height: 768
    image:alt: DBWarden documentation
    site_name: DBWarden Documentation
    locale: en_US
  twitter:
    card: summary_large_image
    title: Architecture - DBWarden Documentation
    description: This page explains DBWarden internals for contributors and advanced
      debugging.
    image: https://dbwarden.emiliano-go.com/assets/images/og-image.png
    image:alt: DBWarden documentation
    site: '@emiliano_go_'
  description: This page explains DBWarden internals for contributors and advanced
    debugging.
  schema_jsonld:
  - '@context': https://schema.org
    '@type': WebPage
    name: Architecture - DBWarden Documentation
    url: https://dbwarden.emiliano-go.com/architecture-deep-dive
    description: This page explains DBWarden internals for contributors and advanced
      debugging.
    image: https://dbwarden.emiliano-go.com/assets/images/og-image.png
    publisher:
      '@type': Organization
      name: Emiliano Gandini Outeda
      logo: https://dbwarden.emiliano-go.com/assets/images/og-image.png
  - '@context': https://schema.org
    '@type': BreadcrumbList
    itemListElement:
    - '@type': ListItem
      position: 1
      name: Architecture
      item: https://dbwarden.emiliano-go.com/architecture-deep-dive
seo_html: "<title>Architecture - DBWarden Documentation</title>\n<meta name=\"description\"\
  \ content=\"This page explains DBWarden internals for contributors and advanced\
  \ debugging.\">\n<link rel=\"canonical\" href=\"https://dbwarden.emiliano-go.com/architecture-deep-dive\"\
  >\n<meta name=\"robots\" content=\"index,follow\">\n<meta property=\"og:type\" content=\"\
  website\">\n<meta property=\"og:title\" content=\"Architecture - DBWarden Documentation\"\
  >\n<meta property=\"og:description\" content=\"This page explains DBWarden internals\
  \ for contributors and advanced debugging.\">\n<meta property=\"og:url\" content=\"\
  https://dbwarden.emiliano-go.com/architecture-deep-dive\">\n<meta property=\"og:image\"\
  \ content=\"https://dbwarden.emiliano-go.com/assets/images/og-image.png\">\n<meta\
  \ property=\"og:image:width\" content=\"1376\">\n<meta property=\"og:image:height\"\
  \ content=\"768\">\n<meta property=\"og:image:alt\" content=\"DBWarden documentation\"\
  >\n<meta property=\"og:site_name\" content=\"DBWarden Documentation\">\n<meta property=\"\
  og:locale\" content=\"en_US\">\n<meta name=\"twitter:card\" content=\"summary_large_image\"\
  >\n<meta name=\"twitter:title\" content=\"Architecture - DBWarden Documentation\"\
  >\n<meta name=\"twitter:description\" content=\"This page explains DBWarden internals\
  \ for contributors and advanced debugging.\">\n<meta name=\"twitter:image\" content=\"\
  https://dbwarden.emiliano-go.com/assets/images/og-image.png\">\n<meta name=\"twitter:image:alt\"\
  \ content=\"DBWarden documentation\">\n<meta name=\"twitter:site\" content=\"@emiliano_go_\"\
  >\n<script type=\"application/ld+json\">\n[\n  {\n    \"@context\": \"https://schema.org\"\
  ,\n    \"@type\": \"WebPage\",\n    \"name\": \"Architecture - DBWarden Documentation\"\
  ,\n    \"url\": \"https://dbwarden.emiliano-go.com/architecture-deep-dive\",\n \
  \   \"description\": \"This page explains DBWarden internals for contributors and\
  \ advanced debugging.\",\n    \"image\": \"https://dbwarden.emiliano-go.com/assets/images/og-image.png\"\
  ,\n    \"publisher\": {\n      \"@type\": \"Organization\",\n      \"name\": \"\
  Emiliano Gandini Outeda\",\n      \"logo\": \"https://dbwarden.emiliano-go.com/assets/images/og-image.png\"\
  \n    }\n  },\n  {\n    \"@context\": \"https://schema.org\",\n    \"@type\": \"\
  BreadcrumbList\",\n    \"itemListElement\": [\n      {\n        \"@type\": \"ListItem\"\
  ,\n        \"position\": 1,\n        \"name\": \"Architecture\",\n        \"item\"\
  : \"https://dbwarden.emiliano-go.com/architecture-deep-dive\"\n      }\n    ]\n\
  \  }\n]\n</script>\n"
---

# Architecture

This page explains DBWarden internals for contributors and advanced debugging.

## Layered architecture

```text
CLI (Typer)
  -> Commands layer
    -> Engine layer (planning/parsing/version/checksum/model discovery)
      -> Repository layer (migration + lock records)
        -> Database layer (SQLAlchemy connection + SQL execution)
```

## Responsibilities

- CLI: parse args, global flags (`--dev`, `--strict-translation`, `--help`)
- Commands: orchestrate workflows (`migrate`, `rollback`, `make-migrations`, `status`, `history`, `check`, `diff`, `generate-models`, `export-models`, `seed`, `lock-status`, `unlock`, `init`, `snapshot`, `settings`, `database`, `version`)
- Engine: parse files, resolve ordering, checksums, model discovery
- Repositories: read/write migration and lock metadata
- Database: execute SQL with backend-aware connections

## Configuration resolution pipeline

When runtime config is requested:

1. discover one config source (`dbwarden.py` or single callsite)
2. fallback to `DBWARDEN_CONFIG_MODULE` when configured
3. import source and execute `database_config(...)` calls
4. validate uniqueness/default/model-path rules
5. resolve selected database and apply `--dev` swap when enabled

Ambiguous sources fail fast.

## Migration execution lifecycle

For `migrate`:

1. ensure migrations metadata table exists
2. ensure lock table exists
3. acquire lock
4. build pending execution plan
5. execute SQL statements
6. record migration metadata/checksums
7. release lock

## Rollback lifecycle

Rollback uses the same lock discipline, selecting rollback SQL from applied files in reverse order.

## Model-to-SQL generation lifecycle

`make-migrations` pipeline:

1. discover model paths
2. import model modules
3. extract table/column metadata
4. load latest schema snapshot (`.dbwarden/schemas/*.schema.json`) if one exists
5. if snapshot exists: **snapshot-diff path**
   - diff model tables against snapshot tables
   - auto-detect table renames from dropped↔added table pairs (column overlap ≥ 0.6)
   - apply user `--rename-table` flags and/or interactive prompts to confirm table renames
   - emit `ALTER TABLE ... RENAME TO` (confirmed) or `DROP TABLE` + `CREATE TABLE` (not confirmed)
   - apply confirmed table renames to snapshot before column processing
   - auto-detect column renames from dropped↔added pairs of the same type
   - apply user `--rename` flags and/or interactive prompts to confirm renames
   - detect column-level changes: type, nullability, default (same-name columns)
   - emit `RENAME COLUMN` (confirmed) or `DROP` + `ADD` (not confirmed)
   - emit `ALTER COLUMN TYPE` / `SET NOT NULL` / `DROP NOT NULL` / `SET DEFAULT` / `DROP DEFAULT`
   - optionally use multi-step safe type change (`--safe-type-change`)
   - order all operations by `StatementOrder` (RENAME_TABLE first) and assemble upgrade/rollback
   - generate upgrade and rollback SQL from the ops
 6. if no snapshot: **live-DB fallback path**
    - take a full schema snapshot from the live database via `extract_full_schema_snapshot()`
    - run standard snapshot-diff pipeline against it (type, nullability, default, FK, index changes)
    - only rename detection is unavailable without a cached snapshot
7. deduplicate against existing migration statements
8. write migration file
9. write companion `.plan.json` metadata file (with `resolved_from` on rename ops)

## PostgreSQL Handler Pipeline

PostgreSQL support is implemented through `dbwarden.engine.backends.postgresql.handlers`. Each handler exposes a small contract: `extract`, `model_spec_from_tables`, `canonicalize`, `diff`, and `emit`.

The `RegistryDriver` runs that contract in order:

1. extract snapshot state into a handler specific shape
2. derive model state from `ModelTable` objects, or config for preamble handlers
3. canonicalize both sides
4. diff into `Op` objects
5. emit backend SQL from the ops

The SQL assembly layer then sorts statements by `StatementOrder` and joins upgrade and rollback SQL into migration files.

### Handler Groups

| Handler | Purpose |
|---------|---------|
| `ColumnHandler` | Column add, drop, type, nullability, default, autoincrement, comment, and backend specific column metadata |
| `ConstraintHandler` | Unique, check, and foreign key constraints |
| `IndexHandler` | PostgreSQL and ClickHouse index operations |
| `TableHandler` | Table create, drop, and table comments |
| `RenameTableHandler` | Table rename operations |
| `SchemaHandler` | Schema create and drop |
| `PgTableHandler` | PostgreSQL table options, inheritance, and exclude constraints |
| `PartitionHandler` | Native PostgreSQL partitioning and partition attachment |
| `StorageParamsHandler` | PostgreSQL storage parameter changes |
| `EnumHandler` | Enum create, drop, and add value |
| `DomainHandler` | Domain create and drop |
| `SequenceHandler` | Sequence create and drop |
| `ViewHandler` | Regular and materialized view changes |
| `PoliciesHandler` | RLS enablement and policy lifecycle |
| `GrantsHandler` | Table and schema grants |
| `RoleHandler` | Role create and alter |
| `DefaultPrivilegesHandler` | Default privilege grants and revokes |
| `FunctionHandler` | Function create, replace, and drop |
| `TriggerHandler` | Trigger create and drop |
| `EventTriggerHandler` | Event trigger lifecycle |
| `ExtendedStatisticsHandler` | `CREATE STATISTICS` and drop |
| `StatisticsHandler` | Extended statistics variants and compatibility helpers |
| `MyTableHandler` | MySQL table metadata |
| `ChTableHandler` | ClickHouse table options and engine recreate |

### Online and Offline Paths

The online path uses `diff_models_against_snapshot` and the registry driver directly.

The offline path uses `diff_model_states`, which still keeps a few raw dict comparisons for state only fields such as column diffs, PostgreSQL table scalars, MySQL table metadata, and table comments. Those raw ops still flow through the same emit layer, so the SQL output stays aligned with the handler path.

The equivalence tests in `tests/test_pg_registry.py` and `tests/engine/snapshot/test_backend.py` lock that behavior in.

### Snapshot write lifecycle (in `migrate`)

After applying versioned migrations, `migrate` calls `_write_migration_snapshot()`:

1. connect to database (respecting sandbox override)
2. extract full schema: tables, columns, types, indexes, constraints, enums
3. compute SHA-256 checksum
4. write `<migration_id>.schema.json` to `.dbwarden/schemas/`
5. on failure: log warning (non-blocking)

Snapshots are not written during `--dry-run`, `--sandbox`, or for repeatable migrations.

## Repeatable migration model

Supported classes:

- versioned (`NNNN_`): run once in ordered sequence
- runs always (`RA__`): run each migrate execution
- runs on change (`ROC__`): run only when checksum changes

## Integrity model

Checksums are recorded for migration content and used for:

- repeatable migration change detection
- migration consistency checks
- audit/debug confidence

## Concurrency model

Migration-mutating commands are serialized by lock state stored in database tables.

Recovery commands:

- `dbwarden lock-status`
- `dbwarden unlock`

## Dev translation path

With `--dev` and SQLite target:

1. extract model types/defaults
2. translate backend-specific constructs
3. fallback behavior in non-strict mode
4. fail-fast behavior with `--strict-translation`

Translation happens during SQL generation, not by mutating existing migration files.

## Error propagation strategy

- config/load validation errors fail early
- execution errors abort current run with context
- lock release is guarded in cleanup paths
