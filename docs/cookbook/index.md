---
seo:
  title: Cookbook & Examples - DBWarden Documentation
  description: Cookbook & Examples Practical, runnable examples that walk through
    the entire DBWarden workflow — from project setup through advanced observability
    patterns. How to Use Each cookbook section links to...
  canonical: https://emiliano-gandini-outeda.github.io/DBWarden/cookbook/
  robots: index,follow
  og:
    type: website
    title: Cookbook & Examples - DBWarden Documentation
    description: Cookbook & Examples Practical, runnable examples that walk through
      the entire DBWarden workflow — from project setup through advanced observability
      patterns. How to Use Each cookbook section links to...
    url: https://emiliano-gandini-outeda.github.io/DBWarden/cookbook/
    image: https://emiliano-gandini-outeda.github.io/DBWarden/assets/icon.png
    site_name: DBWarden Documentation
  twitter:
    card: summary_large_image
    title: Cookbook & Examples - DBWarden Documentation
    description: Cookbook & Examples Practical, runnable examples that walk through
      the entire DBWarden workflow — from project setup through advanced observability
      patterns. How to Use Each cookbook section links to...
    image: https://emiliano-gandini-outeda.github.io/DBWarden/assets/icon.png
  schema_jsonld:
    '@context': https://schema.org
    '@type': WebPage
    name: Cookbook & Examples - DBWarden Documentation
    url: https://emiliano-gandini-outeda.github.io/DBWarden/cookbook/
    description: Cookbook & Examples Practical, runnable examples that walk through
      the entire DBWarden workflow — from project setup through advanced observability
      patterns. How to Use Each cookbook section links to...
    image: https://emiliano-gandini-outeda.github.io/DBWarden/assets/icon.png
    publisher:
      '@type': Organization
      name: Emiliano Gandini Outeda
---

# Cookbook & Examples

Practical, runnable examples that walk through the entire DBWarden workflow — from project setup through advanced observability patterns.

## How to Use

Each cookbook section links to code under the [`examples/`](https://github.com/emiliano-gandini-outeda/DBWarden/tree/main/examples) directory. The **core examples** (sections 1–7) use SQLite and require only `pip install dbwarden`. Advanced examples may need Docker for PostgreSQL, ClickHouse, or Prometheus.

```
examples/
├── core/                 # Sections 1–7: progressive SQL workflow
├── multi-database/       # Section 8
├── fastapi-app/          # Section 9
├── auto-schema/          # Section 10
└── observability/        # Section 11
```

## Sections

| # | Section | What You'll Learn | Example Dir |
|---|---------|-------------------|-------------|
| 1 | [Project Setup](01-project-setup.md) | `init`, `config`, understanding `database_config()` | `examples/core/` |
| 2 | [Models & Migrations](02-models-and-migrations.md) | Model definitions, `make-migrations`, `new`, `make-rollback` | `examples/core/` |
| 3 | [Apply & Inspect](03-apply-and-inspect.md) | `migrate`, `rollback`, `downgrade`, `history`, `status`, `check`, `check-db` | `examples/core/` |
| 4 | [Offline & CI](04-offline-ci.md) | `export-models`, `make-migrations --offline` | `examples/core/` |
| 5 | [Schema Inspection](05-schema-inspection.md) | `diff`, `snapshot`, `generate-models` | `examples/core/` |
| 6 | [Safety & Impact](06-safety-impact.md) | `check`, `check-impact`, destructive change detection | `examples/core/` |
| 7 | [Seeds](07-seeds.md) | `seed create/apply/rollback/list`, SQL seeds, `@seed_data` | `examples/core/` |
| 8 | [Multi-Database](08-multi-database.md) | Multiple `database_config()`, PG + ClickHouse, `--all` flag | `examples/multi-database/` |
| 9 | [FastAPI Integration](09-fastapi-integration.md) | Lifespan hooks, health endpoints, session DI, migration endpoints | `examples/fastapi-app/` |
| 10 | [Auto Schemas](10-auto-schemas.md) | `@auto_schema`, `CreateSchema`, `UpdateSchema`, `PublicSchema` | `examples/auto-schema/` |
| 11 | [Observability](11-observability.md) | Prometheus metrics, structured logging, query tracing | `examples/observability/` |

## Quick Start (Core)

```bash
cd examples/core
pip install -r requirements.txt
bash scripts/01-setup.sh
bash scripts/02-models-migrations.sh
bash scripts/03-apply-inspect.sh
```

Each section in the cookbook explains what these commands do, what SQL they produce, and why it matters.
