# SQLAlchemy Models

DBWarden automatically generates migrations from SQLAlchemy models. This guide covers how to define models that work best with DBWarden.

## Model Requirements

### Basic Structure

Your models must:

1. **Inherit from `declarative_base`**: Use SQLAlchemy's declarative system
2. **Define `__tablename__`**: Each model must have a table name
3. **Use SQLAlchemy types**: Column types must be from SQLAlchemy

```python
from sqlalchemy import Column, Integer, String
from sqlalchemy.orm import declarative_base

Base = declarative_base()

class User(Base):
    __tablename__ = "users"
    
    id = Column(Integer, primary_key=True)
    username = Column(String(50))
```

## Supported Column Types

| SQLAlchemy Type | Description | Generated SQL |
|-----------------|-------------|---------------|
| `Integer` | Integer value | `INTEGER` |
| `String(n)` | Variable-length string | `VARCHAR(n)` |
| `Text` | Long text | `TEXT` |
| `Boolean` | True/False | `BOOLEAN` |
| `DateTime` | Date and time | `DATETIME` |
| `Date` | Date only | `DATE` |
| `Time` | Time only | `TIME` |
| `Float` | Floating point | `FLOAT` |
| `Numeric(p, s)` | Fixed precision | `NUMERIC(p, s)` |
| `JSON` | JSON data | `JSON` |
| `LargeBinary` | Binary data | `BLOB` |
| `Binary` | Binary data | `VARBINARY` |

## Column Options

### Primary Key

```python
class User(Base):
    __tablename__ = "users"
    
    id = Column(Integer, primary_key=True)
    # or with auto-increment
    id = Column(Integer, primary_key=True, autoincrement=True)
```

### Nullable

```python
class User(Base):
    __tablename__ = "users"
    
    email = Column(String(255), nullable=False)  # NOT NULL
    bio = Column(Text, nullable=True)           # NULL (default)
```

### Default Values

```python
from datetime import datetime

class User(Base):
    __tablename__ = "users"
    
    created_at = Column(DateTime, default=datetime.utcnow)
    is_active = Column(Boolean, default=True)
```

### Unique Constraint

```python
class User(Base):
    __tablename__ = "users"
    
    email = Column(String(255), unique=True)
```

### Primary Key + Unique

```python
class User(Base):
    __tablename__ = "users"
    
    id = Column(Integer, primary_key=True)
    username = Column(String(50), unique=True)
```

## Foreign Keys

### Basic Foreign Key

```python
class Post(Base):
    __tablename__ = "posts"
    
    id = Column(Integer, primary_key=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False)
```

### Foreign Key with ON DELETE

```python
class Post(Base):
    __tablename__ = "posts"
    
    id = Column(Integer, primary_key=True)
    user_id = Column(
        Integer, 
        ForeignKey("users.id", ondelete="CASCADE"),
        nullable=False
    )
```

### Self-Referential FK

```python
class Category(Base):
    __tablename__ = "categories"
    
    id = Column(Integer, primary_key=True)
    parent_id = Column(
        Integer, 
        ForeignKey("categories.id")
    )
```

## Indexes

### Automatic Indexes

DBWarden generates indexes for:
- Primary key columns
- Foreign key columns
- Unique columns

### Manual Indexes (Manual Migration)

For custom indexes, use manual migrations:

```sql
-- 0002_add_user_indexes.sql

-- upgrade

CREATE INDEX idx_users_username ON users(username);
CREATE INDEX idx_posts_user_id ON posts(user_id);
CREATE INDEX idx_posts_created_at ON posts(created_at DESC);

-- rollback

DROP INDEX idx_posts_created_at;
DROP INDEX idx_posts_user_id;
DROP INDEX idx_users_username;
```

## Complete Example

```python
from sqlalchemy import Column, Integer, String, Text, DateTime, ForeignKey
from sqlalchemy.orm import declarative_base
from datetime import datetime

Base = declarative_base()

class User(Base):
    __tablename__ = "users"
    
    id = Column(Integer, primary_key=True, autoincrement=True)
    username = Column(String(50), unique=True, nullable=False)
    email = Column(String(255), unique=True, nullable=False)
    bio = Column(Text)
    is_active = Column(Integer, default=1)
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)


class Post(Base):
    __tablename__ = "posts"
    
    id = Column(Integer, primary_key=True, autoincrement=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    title = Column(String(200), nullable=False)
    content = Column(Text)
    view_count = Column(Integer, default=0)
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)


class Comment(Base):
    __tablename__ = "comments"
    
    id = Column(Integer, primary_key=True, autoincrement=True)
    post_id = Column(Integer, ForeignKey("posts.id"), nullable=False)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    content = Column(Text, nullable=False)
    created_at = Column(DateTime, default=datetime.utcnow)
```

## Model Discovery

### Auto-Discovery

DBWarden automatically finds models in:
- `models/` directory
- `model/` directory

Searches up to 5 parent directories from current working directory.

### Manual Path Configuration

Set custom paths in `warden.toml`:

```toml
model_paths = ["app/models/", "core/database/models/", "shared/models/"]
```

### Import Patterns

DBWarden loads models as modules:

```python
# models/user.py
from sqlalchemy import Column, Integer, String
from sqlalchemy.orm import declarative_base

Base = declarative_base()

class User(Base):
    __tablename__ = "users"
    # ...
```

```python
# models/post.py
from sqlalchemy import Column, Integer, String
from sqlalchemy.orm import declarative_base

Base = declarative_base()

class Post(Base):
    __tablename__ = "posts"
    # ...
```

## Common Patterns

### Enum Values

```python
from sqlalchemy import Enum
import enum

class PostStatus(enum.Enum):
    DRAFT = "draft"
    PUBLISHED = "published"
    ARCHIVED = "archived"

class Post(Base):
    __tablename__ = "posts"
    
    status = Column(Enum(PostStatus), default=PostStatus.DRAFT)
```

### Composite Keys

```python
class OrderItem(Base):
    __tablename__ = "order_items"
    
    order_id = Column(Integer, ForeignKey("orders.id"), primary_key=True)
    product_id = Column(Integer, ForeignKey("products.id"), primary_key=True)
    quantity = Column(Integer, nullable=False)
```

### JSON Columns

```python
from sqlalchemy import JSON

class User(Base):
    __tablename__ = "users"
    
    id = Column(Integer, primary_key=True)
    preferences = Column(JSON, default=dict)
```

## Limitations

### Not Supported

- Column comments
- Table comments
- Partial indexes (SQLite)
- Expression indexes (some databases)
- Deferred constraints

For these features, use manual migrations.

### Workarounds

```sql
-- Add column comment (manual migration)
COMMENT ON COLUMN users.email IS 'User email address';

-- Add table comment
COMMENT ON TABLE users IS 'Registered user accounts';
```

## Best Practices

### 1. Naming Conventions

```python
# GOOD
__tablename__ = "users"          # Plural, snake_case
username = Column(String(50))    # snake_case

# AVOID
__tablename__ = "User"           # Singular
UserName = Column(String(50))   # CamelCase
```

### 2. Explicit Types

```python
# GOOD: Explicit length
email = Column(String(255))

# LESS CLEAR: Default length varies
email = Column(String)  # May be 255 or 1 depending on DB
```

### 3. Primary Keys

```python
# GOOD: Auto-incrementing integer
id = Column(Integer, primary_key=True, autoincrement=True)

# OR UUID
import uuid
id = Column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
```

### 4. Timestamps

```python
from datetime import datetime

class Model(Base):
    __tablename__ = "models"
    
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
```

## Troubleshooting

### Model Not Discovered

1. Check `model_paths` in `warden.toml`
2. Verify file is in `models/` directory
3. Ensure model inherits from `Base`
4. Check `__tablename__` is defined

### Migration Missing Columns

1. Verify column is in model
2. Check for typos in column name
3. Ensure column is defined on model class (not relationship)

### Column Type Mismatch

Migration generates different type than expected:

```python
# Model
email = Column(String(255))

# Generated SQL might be:
-- VARCHAR(255) for PostgreSQL/MySQL
-- TEXT for SQLite (no VARCHAR)
```

Use manual migrations for database-specific types.

## See Also

- [make-migrations](commands/make-migrations.md): Generate migrations from models
- [new](commands/new.md): Create manual migrations for features not in models
- [Supported Databases](databases.md): Database-specific considerations
