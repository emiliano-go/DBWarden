---
seo:
  title: Concepts - DBWarden Documentation
  canonical: https://dbwarden.emiliano-go.com/fastapi/concepts
  robots: index,follow
  og:
    type: website
    title: Concepts - DBWarden Documentation
    description: High-level explanations of how DBWarden's FastAPI integration works.
    url: https://dbwarden.emiliano-go.com/fastapi/concepts
    image: https://dbwarden.emiliano-go.com/assets/images/og-image.png
    image:width: 1376
    image:height: 768
    image:alt: DBWarden documentation
    site_name: DBWarden Documentation
    locale: en_US
  twitter:
    card: summary_large_image
    title: Concepts - DBWarden Documentation
    description: High-level explanations of how DBWarden's FastAPI integration works.
    image: https://dbwarden.emiliano-go.com/assets/images/og-image.png
    image:alt: DBWarden documentation
    site: '@emiliano_go_'
  description: High-level explanations of how DBWarden's FastAPI integration works.
  schema_jsonld:
  - '@context': https://schema.org
    '@type': WebPage
    name: Concepts - DBWarden Documentation
    url: https://dbwarden.emiliano-go.com/fastapi/concepts
    description: High-level explanations of how DBWarden's FastAPI integration works.
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
      name: FastAPI Integration
      item: https://dbwarden.emiliano-go.com/fastapi
    - '@type': ListItem
      position: 2
      name: Concepts
      item: https://dbwarden.emiliano-go.com/fastapi/concepts
seo_html: "<title>Concepts - DBWarden Documentation</title>\n<meta name=\"description\"\
  \ content=\"High-level explanations of how DBWarden&#x27;s FastAPI integration works.\"\
  >\n<link rel=\"canonical\" href=\"https://dbwarden.emiliano-go.com/fastapi/concepts\"\
  >\n<meta name=\"robots\" content=\"index,follow\">\n<meta property=\"og:type\" content=\"\
  website\">\n<meta property=\"og:title\" content=\"Concepts - DBWarden Documentation\"\
  >\n<meta property=\"og:description\" content=\"High-level explanations of how DBWarden&#x27;s\
  \ FastAPI integration works.\">\n<meta property=\"og:url\" content=\"https://dbwarden.emiliano-go.com/fastapi/concepts\"\
  >\n<meta property=\"og:image\" content=\"https://dbwarden.emiliano-go.com/assets/images/og-image.png\"\
  >\n<meta property=\"og:image:width\" content=\"1376\">\n<meta property=\"og:image:height\"\
  \ content=\"768\">\n<meta property=\"og:image:alt\" content=\"DBWarden documentation\"\
  >\n<meta property=\"og:site_name\" content=\"DBWarden Documentation\">\n<meta property=\"\
  og:locale\" content=\"en_US\">\n<meta name=\"twitter:card\" content=\"summary_large_image\"\
  >\n<meta name=\"twitter:title\" content=\"Concepts - DBWarden Documentation\">\n\
  <meta name=\"twitter:description\" content=\"High-level explanations of how DBWarden&#x27;s\
  \ FastAPI integration works.\">\n<meta name=\"twitter:image\" content=\"https://dbwarden.emiliano-go.com/assets/images/og-image.png\"\
  >\n<meta name=\"twitter:image:alt\" content=\"DBWarden documentation\">\n<meta name=\"\
  twitter:site\" content=\"@emiliano_go_\">\n<script type=\"application/ld+json\"\
  >\n[\n  {\n    \"@context\": \"https://schema.org\",\n    \"@type\": \"WebPage\"\
  ,\n    \"name\": \"Concepts - DBWarden Documentation\",\n    \"url\": \"https://dbwarden.emiliano-go.com/fastapi/concepts\"\
  ,\n    \"description\": \"High-level explanations of how DBWarden's FastAPI integration\
  \ works.\",\n    \"image\": \"https://dbwarden.emiliano-go.com/assets/images/og-image.png\"\
  ,\n    \"publisher\": {\n      \"@type\": \"Organization\",\n      \"name\": \"\
  Emiliano Gandini Outeda\",\n      \"logo\": \"https://dbwarden.emiliano-go.com/assets/images/og-image.png\"\
  \n    }\n  },\n  {\n    \"@context\": \"https://schema.org\",\n    \"@type\": \"\
  BreadcrumbList\",\n    \"itemListElement\": [\n      {\n        \"@type\": \"ListItem\"\
  ,\n        \"position\": 1,\n        \"name\": \"FastAPI Integration\",\n      \
  \  \"item\": \"https://dbwarden.emiliano-go.com/fastapi\"\n      },\n      {\n \
  \       \"@type\": \"ListItem\",\n        \"position\": 2,\n        \"name\": \"\
  Concepts\",\n        \"item\": \"https://dbwarden.emiliano-go.com/fastapi/concepts\"\
  \n      }\n    ]\n  }\n]\n</script>\n"
---

# Concepts

High-level explanations of how DBWarden's FastAPI integration works.

## What Problem Does It Solve?

Without DBWarden, FastAPI apps typically have **split configuration**:

```python
# migrations/env.py - Alembic config
SQLALCHEMY_DATABASE_URL = "postgresql://..."

# app/database.py - App config
SQLALCHEMY_DATABASE_URL = "postgresql://..."  # Duplicate!

# app/main.py - Manual engine creation
engine = create_async_engine(SQLALCHEMY_DATABASE_URL)
SessionLocal = sessionmaker(engine)

# Manual dependency
async def get_db():
    async with SessionLocal() as session:
        yield session
```

With DBWarden, you have **one source of truth**:

```python
# dbwarden.py - Single config returns a DatabaseHandle
primary = database_config(
    database_url_sync="postgresql://...",
    model_paths=["app.models"],
)

# app/main.py - Use .async_session directly as a parameter annotation
@app.get("/users")
async def list_users(session: primary.async_session):
    ...
```

DBWarden handles:
-  Engine creation
-  Session factories
-  Connection pooling
-  Startup checks
-  Health endpoints

## Dependency Injection

FastAPI uses **dependency injection** to provide resources to routes.

### Without DBWarden

```python
# Manual dependency
async def get_db():
    async with SessionLocal() as session:
        try:
            yield session
        except:
            await session.rollback()
            raise

# Every route
@app.get("/users")
async def list_users(db: AsyncSession = Depends(get_db)):
    ...
```

### With DBWarden

```python
# One-time setup: database_config() returns a DatabaseHandle
primary = database_config(database_name="primary", ...)

# Every route: use .async_session directly
@app.get("/users")
async def list_users(session: primary.async_session):
    ...
```

The `DatabaseHandle` `.async_session` property is a FastAPI dependency annotation, ready to use in route parameters without `Annotated`, `Depends`, or type aliases.

## Engine Caching

### Why Cache Engines?

Creating database engines is expensive:

```python
#  Bad: New engine per request
@app.get("/users")
async def list_users():
    engine = create_async_engine(...)  # Expensive!
    async with engine.connect() as conn:
        ...
```

Engines should be **created once and reused**:

```python
#  Good: One engine for app lifetime
primary = database_config(database_name="primary", ...)  # Engine cached

@app.get("/users")
async def list_users(session: primary.async_session):
    # Reuses cached engine
    ...
```

DBWarden caches engines automatically:

```
First request:
1. primary.async_session resolves
2. Engine created
3. Engine cached
4. Session created from engine
5. Session yielded to route

Subsequent requests:
1. primary.async_session resolves
2. Engine retrieved from cache   Fast!
3. Session created from engine
4. Session yielded to route
```

## Session Scope

### Request-Scoped Sessions

Each request gets its own session:

```
Request 1: Session A
Request 2: Session B
Request 3: Session C
```

Sessions are **never shared** between requests, ensuring:
-  Transaction isolation
-  No race conditions
-  Predictable behavior

### Session Lifecycle

```
Request arrives
    
FastAPI calls get_session dependency
    
New session created
    
Session yielded to route
    
Route executes with session
    
Session automatically closed
    
Response returned
```

If an error occurs, the session is rolled back before closing.

## Health vs Liveness

Kubernetes has two types of probes:

### Liveness Probe

**Question:** Is the app alive?

**Answer:** If no, restart the pod.

**Use:** Basic health check

```yaml
livenessProbe:
  httpGet:
    path: /ping  # Simple endpoint, no DB
  failureThreshold: 3
```

### Readiness Probe

**Question:** Is the app ready to serve traffic?

**Answer:** If no, stop routing traffic (but don't restart).

**Use:** Database health, migration state

```yaml
readinessProbe:
  httpGet:
    path: /health/  # Full health check with DB
  failureThreshold: 2
```

DBWarden's health endpoints are perfect for readiness probes because they check:
- Database connectivity
- Migration state
- Lock status

## Async vs Sync

DBWarden's FastAPI integration is **async-native**.

### Why Async?

**Sync (blocking):**
```python
result = session.execute(select(User))  # Blocks thread
users = result.scalars().all()
```

While waiting for the database, the thread can't do anything else.

**Async (non-blocking):**
```python
result = await session.execute(select(User))  # Releases control
users = result.scalars().all()
```

While waiting for the database, the event loop can handle other requests.

**Result:** Async can handle **10-100x more concurrent requests** than sync with the same resources.

### Async Drivers

DBWarden automatically uses async drivers:

| Database | Async Driver |
|----------|-------------|
| PostgreSQL | `asyncpg` |
| SQLite | `aiosqlite` |

Your URLs are automatically upgraded:

```python
# Your config
database_url_sync="postgresql://localhost/myapp"

# DBWarden derives an async URL for its internal async engine
# (uses the configured database_url_async if provided, or upgrades from database_url_sync)
database_url_async="postgresql+asyncpg://localhost/myapp"
```

## expire_on_commit

This is a session setting that affects object behavior after commit.

### Without expire_on_commit=False

```python
user = User(email="test@example.com")
session.add(user)
await session.commit()

#  Error: Instance is not bound to a Session
return user
```

After commit, SQLAlchemy **expires** all objects, meaning they're no longer accessible without a session.

### With expire_on_commit=False

```python
user = User(email="test@example.com")
session.add(user)
await session.commit()

#  Works: Object still accessible
return user
```

Objects remain accessible after commit.

**Why does DBWarden use this?**

FastAPI serializes response objects **after** the route returns:

```
Route returns user
    
Session closes
    
FastAPI serializes user to JSON   Needs to access user.email!
    
Response sent
```

Without `expire_on_commit=False`, serialization would fail because the session is closed.

## Configuration Resolution

DBWarden resolves configuration in this order:

1. **Explicit config** - `database_config(...)` calls
2. **Runtime flags** - `dev=True` parameter
3. **Environment variables** - `ENVIRONMENT=development`
4. **Default values** - Built-in defaults

Example:

```python
primary = database_config(
    database_url_sync="postgresql://prod-db/myapp",
    dev_database_url="sqlite:///dev.db",
)

# In production: uses postgresql://prod-db/myapp
# In development (ENVIRONMENT=development): uses sqlite:///dev.db
# primary.async_session automatically picks the right URL
```

## When to Use DBWarden

**Use DBWarden when:**
-  You want migrations and runtime to share config
-  You need startup validation
-  You want built-in health endpoints
-  You're building a new FastAPI app
-  You use SQLAlchemy for models

**Don't use DBWarden when:**
-  You don't use SQLAlchemy
-  You already have working migration infrastructure
-  You use an ORM other than SQLAlchemy (e.g., Tortoise, SQLModel standalone)

## Comparison to Alternatives

### vs. Alembic + Manual Setup

| | **DBWarden** | **Alembic + Manual** |
|---|---|---|
| Configuration | One source | Split (env.py + app code) |
| Engine creation | Automatic | Manual |
| Session dependency | Built-in | Custom |
| Startup checks | Built-in | Custom |
| Health endpoints | Built-in | Custom |
| Learning curve | Lower | Higher |

### vs. SQLModel

SQLModel includes SQLAlchemy but doesn't provide:
- Migration management
- Startup checks
- Health endpoints
- Multi-database support

DBWarden can work **with** SQLModel for migrations while you use SQLModel's ORM.

### vs. Django ORM

Django's ORM is integrated with Django's migration system. DBWarden is for FastAPI + SQLAlchemy apps.

## What's Next?

- **[API Reference](reference.md)** - Complete function signatures
- **[Tutorial](tutorial/first-steps.md)** - Build your first app
