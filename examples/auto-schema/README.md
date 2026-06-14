# Auto-Generated Pydantic Schemas

Demonstrates how `@auto_schema` generates CreateSchema, UpdateSchema, and PublicSchema from SQLAlchemy model annotations.

## Quick Start

```bash
uv add dbwarden sqlalchemy
python -c "
import sys; sys.path.insert(0, '.')
from app.models import User

# CreateSchema excludes server-defaulted fields (like id)
create = User.CreateSchema(
    email='alice@example.com',
    username='alice',
    password_hash='secret',
)
print('CreateSchema fields:', list(create.model_dump().keys()))

# PublicSchema excludes password_hash (public=False)
print('PublicSchema fields:', list(User.PublicSchema.model_fields.keys()))
assert 'password_hash' not in User.PublicSchema.model_fields
print('OK: password_hash correctly excluded from PublicSchema')
"
```

## What @auto_schema Generates

For each model, it creates:

| Schema | Contents |
|--------|----------|
| `Model.CreateSchema` | All fields except server-defaulted PKs |
| `Model.UpdateSchema` | All fields optional |
| `Model.PublicSchema` | Excludes fields where `public=False` |
| `Model.Schema` | All mapped columns |

Fields with names starting with `_` are implicitly `public=False`.
