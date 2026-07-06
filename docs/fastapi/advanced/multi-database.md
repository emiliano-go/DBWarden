---
{}
---

# Multi-Database

Learn how to work with multiple databases in your FastAPI application.

## When to Use Multiple Databases

Common scenarios:
- **Primary + Analytics** - Separate reporting from transactional data
- **Primary + Logging** - Dedicated audit/logging database
- **Microservices** - Each service has its own database
- **Multi-tenancy** - One database per tenant
- **Read Replicas** - Separate read and write databases

## Quick Example

Configure multiple databases:

```python
# config.py
from dbwarden import database_config

# Primary database
primary = database_config(
    database_name="primary",
    default=True,
    database_type="postgresql",
    database_url_sync="postgresql://user:password@localhost/myapp",
    model_paths=["app.models.primary"],
)

# Analytics database
analytics = database_config(
    database_name="analytics",
    database_type="postgresql",
    database_url_sync="postgresql://user:password@localhost/analytics",
    model_paths=["app.models.analytics"],
)

# Logging database
logging = database_config(
    database_name="logging",
    database_type="postgresql",
    database_url_sync="postgresql://user:password@localhost/logs",
    model_paths=["app.models.logging"],
)
```

Each handle's `.async_session` is a FastAPI dependency annotation: use it directly in routes:

```python
from config import primary, analytics, logging


@app.get("/users")
async def list_users(session: primary.async_session):
    result = await session.execute(select(User))
    return result.scalars().all()


@app.get("/analytics/events")
async def list_events(session: analytics.async_session):
    result = await session.execute(select(Event))
    return result.scalars().all()
```

## Query Multiple Databases

You can use multiple handles in the same route:

```python
@app.get("/dashboard")
async def get_dashboard(
    users_session: primary.async_session,
    events_session: analytics.async_session,
    logs_session: logging.async_session,
):
    # Query primary database
    users = await users_session.execute(select(User))
    
    # Query analytics database
    events = await events_session.execute(select(Event))
    
    # Query logging database
    logs = await logs_session.execute(select(AuditLog))
    
    return {
        "users": users.scalars().all(),
        "events": events.scalars().all(),
        "logs": logs.scalars().all(),
    }
```

Each session has its own transaction. If one fails, others are unaffected.

## Cross-Database Queries

SQLAlchemy doesn't support joining across different databases. Instead:

### Pattern 1: Query Then Combine

```python
@app.get("/dashboard")
async def get_dashboard(
    primary_session: primary.async_session,
    analytics_session: analytics.async_session,
):
    # Get user IDs from primary
    user_result = await primary_session.execute(select(User.id))
    user_ids = [row[0] for row in user_result.all()]
    
    # Get events for those users from analytics
    event_result = await analytics_session.execute(
        select(Event).where(Event.user_id.in_(user_ids))
    )
    
    return {"events": event_result.scalars().all()}
```

### Pattern 2: Denormalize

Store redundant data in each database:

```python
# Primary DB - User
class User(Base):
    __tablename__ = "users"
    id: Mapped[int] = mapped_column(primary_key=True)
    email: Mapped[str]

# Analytics DB - Event with user email
class Event(Base):
    __tablename__ = "events"
    id: Mapped[int] = mapped_column(primary_key=True)
    user_email: Mapped[str]  # Denormalized from User
    event_type: Mapped[str]
```

### Pattern 3: Application-Level Join

```python
@app.get("/enriched-events")
async def get_enriched_events(
    primary_session: primary.async_session,
    analytics_session: analytics.async_session,
):
    # Get all users
    users_result = await primary_session.execute(select(User))
    users = {u.id: u for u in users_result.scalars().all()}
    
    # Get all events
    events_result = await analytics_session.execute(select(Event))
    events = events_result.scalars().all()
    
    # Join in Python
    enriched = [
        {
            "event": event,
            "user": users.get(event.user_id)
        }
        for event in events
    ]
    
    return enriched
```

## Startup Checks for All Databases

Check all databases on startup:

```python
from contextlib import asynccontextmanager
from dbwarden.fastapi import migration_context

@asynccontextmanager
async def lifespan(app: FastAPI):
    async with migration_context(
        mode="check",
        all_databases=True,  #  Check all databases
        fail_fast=True,
    ):
        yield
```

## Health Checks for All Databases

Health endpoints automatically report all databases:

```python
from dbwarden.fastapi import DBWardenHealthRouter

app.include_router(DBWardenHealthRouter(), prefix="/health")
```

Response shows all databases:

```json
{
  "status": "ok",
  "databases": [
    {
      "database": "primary",
      "status": "ok",
      "connected": true,
      "pending_migrations": 0,
      "lock_active": false,
      "error": null
    },
    {
      "database": "analytics",
      "status": "ok",
      "connected": true,
      "pending_migrations": 0,
      "lock_active": false,
      "error": null
    },
    {
      "database": "logging",
      "status": "ok",
      "connected": true,
      "pending_migrations": 0,
      "lock_active": false,
      "error": null
    }
  ]
}
```

Check a specific database:

```bash
curl http://localhost:8000/health/analytics
```

## Migrations for Multiple Databases

Each database has its own migration history:

```bash
# Create migration for primary database
$ dbwarden make-migrations -d primary -m "add users table"

# Create migration for analytics database
$ dbwarden make-migrations -d analytics -m "add events table"

# Apply migrations to all databases
$ dbwarden migrate --all
```

## Common Patterns

### Pattern 1: Primary + Read Replica

```python
# config.py
primary = database_config(database_name="primary", ...)
replica = database_config(database_name="replica", ...)

# Routes
@app.post("/users")
async def create_user(session: primary.async_session):
    # Write to primary
    ...

@app.get("/users")
async def list_users(session: replica.async_session):
    # Read from replica
    ...
```

### Pattern 2: Tenant Per Database

```python
def get_tenant_session(tenant_id: str):
    return Annotated[AsyncSession, Depends(get_session(f"tenant_{tenant_id}"))]

@app.get("/data")
async def get_data(tenant_id: str):
    TenantSessionDep = get_tenant_session(tenant_id)
    # Use tenant-specific database
    ...
```

### Pattern 3: Audit Logging

```python
@app.post("/users")
async def create_user(
    user_data: UserCreate,
    primary_session: primary.async_session,
    logging_session: logging.async_session,
):
    # Create user in primary
    user = User(**user_data.model_dump())
    primary_session.add(user)
    await primary_session.commit()
    
    # Log action in logging database
    log = AuditLog(action="create_user", user_id=user.id)
    logging_session.add(log)
    await logging_session.commit()
    
    return user
```

## What's Next?

- **[Testing](testing.md)** - Test multi-database applications
- **[Transaction Management](transaction-management.md)** - Coordinate across databases
- **[Production Patterns](production-patterns.md)** - Deploy multi-database apps
