# DBWarden Examples

Runnable example projects demonstrating DBWarden workflows.

## Getting Started

The quickest path through all core concepts:

```bash
cd core
pip install -r requirements.txt
bash scripts/01-setup.sh
bash scripts/02-models-migrations.sh
bash scripts/03-apply-inspect.sh
```

## Example Index

| Directory | Sections | What It Covers | Requires |
|-----------|----------|----------------|----------|
| `core/` | 1–7 | Full SQL workflow: setup, models, migrations, apply, rollback, inspect, offline, safety, seeds | Nothing (SQLite) |
| `multi-database/` | 8 | PostgreSQL + ClickHouse in one project | Docker |
| `fastapi-app/` | 9 | FastAPI with health, session DI, lifespan | Docker (PostgreSQL) |
| `auto-schema/` | 10 | Auto-generated Pydantic schemas from models | Nothing (SQLite) |
| `observability/` | 11 | Prometheus metrics, JSON logging, query tracing | Docker |

Detailed walkthroughs for each section are in [`docs/cookbook/`](../docs/cookbook/index.md).
