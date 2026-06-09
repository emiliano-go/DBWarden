# Core DBWarden Workflow

A progressive example demonstrating the core DBWarden migration workflow.

## Prerequisites

- Python 3.12+
- `pip install dbwarden sqlalchemy`

## Quick Start

```bash
pip install -r requirements.txt
bash scripts/01-setup.sh
bash scripts/02-models-migrations.sh
bash scripts/03-apply-inspect.sh
```

## Script Index

| Script | Commands Demonstrated |
|--------|----------------------|
| `01-setup.sh` | `dbwarden init`, `dbwarden config` |
| `02-models-migrations.sh` | `make-migrations`, `new`, `make-rollback` |
| `03-apply-inspect.sh` | `migrate`, `rollback`, `downgrade`, `history`, `status`, `check`, `check-db` |
| `04-offline-ci.sh` | `export-models`, `make-migrations --offline` |
| `05-schema-inspection.sh` | `diff`, `snapshot`, `generate-models` |
| `06-safety-impact.sh` | `check`, `check-impact` |
| `07-seeds.sh` | `seed create`, `seed apply`, `seed rollback`, `seed list` |

Run scripts in order — each builds on the state left by the previous one.
