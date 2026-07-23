---
description: Find official, approved, and community DBWarden plugins.
---

# Finding Plugins

DBWarden plugins are standard Python packages that expose a `dbwarden.plugins` entry point. DBWarden classifies each discovered distribution into a [trust tier](consent-and-trust.md) before importing it, by matching its distribution name against the curated Official and Approved lists in core.

## Search PyPI

All plugins are distributed as:

```text
dbwarden-<name>
```

Search PyPI for `dbwarden-` to find them. The name alone does not confer trust: Official plugins are the DBWarden-owned packages listed in `dbwarden/_official.py` (for example `dbwarden-fastapi`, `dbwarden-pgsql-extensions`); every other `dbwarden-*` package is Community until it reaches the Approved list.

## Official Plugins

Official plugins are built and maintained by the DBWarden organization under the [`dbwarden` GitHub organization](https://github.com/dbwarden). They are enumerated in core (`dbwarden/_official.py`) and are eligible for provenance verification during `dbwarden plugin add`.

| Package | Repository | Purpose |
|---------|------------|---------|
| `dbwarden-fastapi` | [dbwarden/dbwarden-fastapi](https://github.com/dbwarden/dbwarden-fastapi) | FastAPI sessions, health/migration routes, lifespan. |
| `dbwarden-pgsql-extensions` | [dbwarden/dbwarden-pgsql-extensions](https://github.com/dbwarden/dbwarden-pgsql-extensions) | PostgreSQL `CREATE EXTENSION` diffing. |
| `dbwarden-pgsql-rbac` | [dbwarden/dbwarden-pgsql-rbac](https://github.com/dbwarden/dbwarden-pgsql-rbac) | PostgreSQL roles, grants, policies. |
| `dbwarden-pgsql-types` | [dbwarden/dbwarden-pgsql-types](https://github.com/dbwarden/dbwarden-pgsql-types) | PostgreSQL enum/domain/composite types. |
| `dbwarden-ch-rbac` | [dbwarden/dbwarden-ch-rbac](https://github.com/dbwarden/dbwarden-ch-rbac) | ClickHouse roles and grants. |
| `dbwarden-seeds` | [dbwarden/dbwarden-seeds](https://github.com/dbwarden/dbwarden-seeds) | Seed command implementations. |
| `dbwarden-sandbox` | [dbwarden/dbwarden-sandbox](https://github.com/dbwarden/dbwarden-sandbox) | Isolated model/config module loading. |

The authoritative list is always `OFFICIAL_PLUGINS` in `dbwarden/_official.py`.

## Approved Plugins

Approved plugins are community-maintained packages that passed DBWarden's [plugin test standard](../developing/approved-standard.md) and manual review. They load without consent once the installed version meets the approved minimum.

| Package | Minimum approved version | Description |
|---------|--------------------------|-------------|
| _None yet_ | – | Approved entries are listed in `dbwarden/_approved.py` and this table as the ecosystem grows. |

Approval is not a security audit. See [consent and trust](consent-and-trust.md).

## Community Plugins

Any other package with a `dbwarden.plugins` entry point is treated as **Community**. Community plugins require explicit consent before loading. A community-curated index may be maintained as a Markdown page in the DBWarden repository; until then, discover them via PyPI search and review the source before trusting.
