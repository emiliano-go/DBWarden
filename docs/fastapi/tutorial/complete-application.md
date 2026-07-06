---
{}
---

# Complete Application

A full, production-ready FastAPI application using all of DBWarden's features.

## Overview

This example shows:
- Database configuration
- Model definition
- Session dependencies
- CRUD operations
- Startup checks
- Health endpoints
- Transaction management
- Error handling

## Project Structure

```
my_app/
├── config.py            # Database configuration + handles
├── app/
│   ├── __init__.py
│   ├── main.py          # FastAPI app
│   ├── models.py        # SQLAlchemy models
│   └── routes/
│       ├── __init__.py
│       └── users.py     # User endpoints
└── pyproject.toml
```

## Step 1: Database Configuration

Create `config.py` in your project root:

```python
# config.py
from dbwarden import database_config

primary = database_config(
    database_name="primary",
    default=True,
    database_type="postgresql",
    database_url_sync="postgresql://user:password@localhost:5432/myapp",
    dev_database_type="sqlite",
    dev_database_url="sqlite:///./dev.db",
    model_paths=["app.models"],
    model_tables=["users", "posts"],
)
```

`primary` is a `DatabaseHandle`. Use `primary.async_session` in your route
parameters and `primary.sync_session` for synchronous routes.

In production, use environment variables for sensitive data:

```python
import os

primary = database_config(
    database_name="primary",
    default=True,
    database_type="postgresql",
    database_url_sync=os.getenv("DATABASE_URL"),
    model_paths=["app.models"],
    model_tables=["users", "posts"],
)
```

## Step 2: Define Models

Create `app/models.py`:

```python
# app/models.py
from datetime import datetime
from sqlalchemy import Boolean, DateTime, Integer, String
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column


class Base(DeclarativeBase):
    pass


class User(Base):
    __tablename__ = "users"
    
    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    email: Mapped[str] = mapped_column(String(255), unique=True, nullable=False)
    username: Mapped[str] = mapped_column(String(100), unique=True, nullable=False)
    full_name: Mapped[str | None] = mapped_column(String(200))
    is_active: Mapped[bool] = mapped_column(Boolean, default=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime, default=datetime.utcnow
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime, default=datetime.utcnow, onupdate=datetime.utcnow
    )
```

## Step 3: Shared Dependencies

The `DatabaseHandle` from `config.py` is already a shared dependency 
import `primary` wherever you need a session:

```python
# app/routes/users.py
from config import primary
```

Use `primary.async_session` directly as a route parameter annotation.
No separate `dependencies.py` module is needed.

## Step 4: Pydantic Schemas

Create `app/schemas.py` for request/response models:

```python
# app/schemas.py
from datetime import datetime
from pydantic import BaseModel, EmailStr


class UserBase(BaseModel):
    email: EmailStr
    username: str
    full_name: str | None = None


class UserCreate(UserBase):
    pass


class UserUpdate(BaseModel):
    email: EmailStr | None = None
    username: str | None = None
    full_name: str | None = None
    is_active: bool | None = None


class UserResponse(UserBase):
    id: int
    is_active: bool
    created_at: datetime
    updated_at: datetime
    
    class Config:
        from_attributes = True
```

## Step 5: User Routes

Create `app/routes/users.py`:

```python
# app/routes/users.py
from fastapi import APIRouter, HTTPException
from sqlalchemy import select
from sqlalchemy.exc import IntegrityError

from config import primary
from app.models import User
from app.schemas import UserCreate, UserResponse, UserUpdate

router = APIRouter(prefix="/users", tags=["users"])


@router.get("/", response_model=list[UserResponse])
async def list_users(
    session: primary.async_session,
    skip: int = 0,
    limit: int = 100,
    active_only: bool = False,
):
    """List all users with pagination."""
    stmt = select(User).offset(skip).limit(limit)
    
    if active_only:
        stmt = stmt.where(User.is_active == True)
    
    result = await session.execute(stmt)
    return result.scalars().all()


@router.get("/{user_id}", response_model=UserResponse)
async def get_user(user_id: int, session: primary.async_session):
    """Get a single user by ID."""
    result = await session.execute(
        select(User).where(User.id == user_id)
    )
    user = result.scalar_one_or_none()
    
    if not user:
        raise HTTPException(status_code=404, detail="User not found")
    
    return user


@router.post("/", response_model=UserResponse, status_code=201)
async def create_user(user_data: UserCreate, session: primary.async_session):
    """Create a new user."""
    user = User(**user_data.model_dump())
    session.add(user)
    
    try:
        await session.commit()
    except IntegrityError:
        await session.rollback()
        raise HTTPException(
            status_code=400,
            detail="User with this email or username already exists"
        )
    
    await session.refresh(user)
    return user


@router.patch("/{user_id}", response_model=UserResponse)
async def update_user(
    user_id: int,
    user_data: UserUpdate,
    session: primary.async_session,
):
    """Update a user."""
    result = await session.execute(
        select(User).where(User.id == user_id)
    )
    user = result.scalar_one_or_none()
    
    if not user:
        raise HTTPException(status_code=404, detail="User not found")
    
    # Update only provided fields
    update_data = user_data.model_dump(exclude_unset=True)
    for key, value in update_data.items():
        setattr(user, key, value)
    
    try:
        await session.commit()
    except IntegrityError:
        await session.rollback()
        raise HTTPException(
            status_code=400,
            detail="Email or username already taken"
        )
    
    await session.refresh(user)
    return user


@router.delete("/{user_id}", status_code=204)
async def delete_user(user_id: int, session: primary.async_session):
    """Delete a user."""
    result = await session.execute(
        select(User).where(User.id == user_id)
    )
    user = result.scalar_one_or_none()
    
    if not user:
        raise HTTPException(status_code=404, detail="User not found")
    
    await session.delete(user)
    await session.commit()
```

## Step 6: Main Application

Create `app/main.py`:

```python
# app/main.py
from contextlib import asynccontextmanager
from fastapi import FastAPI
from dbwarden.fastapi import DBWardenHealthRouter, migration_context

from app.routes import users


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Startup and shutdown logic."""
    # Startup: check database migrations
    async with migration_context(
        mode="check",
        all_databases=True,
        fail_fast=True,
        verbose=True,
    ):
        yield
    # Shutdown: cleanup happens here


# Create FastAPI app
app = FastAPI(
    title="My App",
    description="Example app with DBWarden integration",
    version="1.0.0",
    lifespan=lifespan,
)

# Include routers
app.include_router(users.router, prefix="/api/v1")
app.include_router(DBWardenHealthRouter(), prefix="/health")


@app.get("/")
async def root():
    """Root endpoint."""
    return {
        "message": "Welcome to My App",
        "docs": "/docs",
        "health": "/health/"
    }
```

## Step 7: Create Migrations

Initialize DBWarden and create your first migration:

```bash
# Initialize DBWarden (if not already done)
$ dbwarden init

# Create migration for User model
$ dbwarden make-migrations -m "create users table"
```

This generates a migration file like `0001_create_users_table.py`.

## Step 8: Apply Migrations

Apply the migration to your database:

```bash
# For development (SQLite)
export ENVIRONMENT=development
$ dbwarden migrate

# For production (PostgreSQL)
export ENVIRONMENT=production
$ dbwarden migrate
```

## Step 9: Run the Application

Start your FastAPI app:

```bash
uvicorn app.main:app --reload
```

You'll see:

```
INFO:     Started server process [12345]
INFO:     Waiting for application startup.
INFO:     DBWarden: migration_context mode=check outcome=ok duration_ms=45
INFO:     Application startup complete.
INFO:     Uvicorn running on http://127.0.0.1:8000
```

## Step 10: Test the API

### Interactive Documentation

Open <http://127.0.0.1:8000/docs> to see the Swagger UI.

### Create a User

```bash
curl -X POST http://localhost:8000/api/v1/users/ \
  -H "Content-Type: application/json" \
  -d '{
    "email": "alice@example.com",
    "username": "alice",
    "full_name": "Alice Smith"
  }'
```

Response:

```json
{
  "id": 1,
  "email": "alice@example.com",
  "username": "alice",
  "full_name": "Alice Smith",
  "is_active": true,
  "created_at": "2024-01-15T10:30:00",
  "updated_at": "2024-01-15T10:30:00"
}
```

### List Users

```bash
curl http://localhost:8000/api/v1/users/
```

### Get a User

```bash
curl http://localhost:8000/api/v1/users/1
```

### Update a User

```bash
curl -X PATCH http://localhost:8000/api/v1/users/1 \
  -H "Content-Type: application/json" \
  -d '{
    "full_name": "Alice Johnson"
  }'
```

### Delete a User

```bash
curl -X DELETE http://localhost:8000/api/v1/users/1
```

### Check Health

```bash
curl http://localhost:8000/health/
```

## Key Features Demonstrated

### 1. Session Management

```python
@router.post("/", response_model=UserResponse)
async def create_user(user_data: UserCreate, session: primary.async_session):
    # Session automatically provided
    user = User(**user_data.model_dump())
    session.add(user)
    await session.commit()
    await session.refresh(user)
    return user
    # Session automatically closed
```

### 2. Error Handling

```python
try:
    await session.commit()
except IntegrityError:
    await session.rollback()  # Explicit rollback
    raise HTTPException(400, "Duplicate entry")
```

### 3. Query Patterns

```python
# Select one
result = await session.execute(
    select(User).where(User.id == user_id)
)
user = result.scalar_one_or_none()

# Select many
result = await session.execute(
    select(User).offset(skip).limit(limit)
)
users = result.scalars().all()
```

### 4. Transaction Management

```python
# Add to session
session.add(user)

# Commit changes
await session.commit()

# Refresh to get DB-generated values
await session.refresh(user)

# Delete
await session.delete(user)
await session.commit()
```

### 5. Startup Validation

```python
@asynccontextmanager
async def lifespan(app: FastAPI):
    async with migration_context(mode="check"):
        # App only starts if database is healthy
        yield
```

### 6. Health Endpoints

```python
app.include_router(DBWardenHealthRouter(), prefix="/health")
```

Provides:
- `GET /health/` - Overall health
- `GET /health/{database_name}` - Per-database health

## Production Deployment

### Docker

Create `Dockerfile`:

```dockerfile
FROM python:3.11-slim

WORKDIR /app

COPY pyproject.toml uv.lock .
RUN uv sync

COPY . .

# Run migrations before starting app
CMD dbwarden migrate && uvicorn app.main:app --host 0.0.0.0 --port 8000
```

### Kubernetes

Create `deployment.yaml`:

```yaml
apiVersion: apps/v1
kind: Deployment
metadata:
  name: myapp
spec:
  replicas: 3
  selector:
    matchLabels:
      app: myapp
  template:
    metadata:
      labels:
        app: myapp
    spec:
      initContainers:
      # Run migrations in init container
      - name: migrate
        image: myapp:latest
        command: ["dbwarden", "migrate"]
        env:
        - name: DATABASE_URL
          valueFrom:
            secretKeyRef:
              name: db-secret
              key: url
      
      containers:
      - name: app
        image: myapp:latest
        ports:
        - containerPort: 8000
        env:
        - name: DATABASE_URL
          valueFrom:
            secretKeyRef:
              name: db-secret
              key: url
        - name: ENVIRONMENT
          value: "production"
        
        # Liveness probe
        livenessProbe:
          httpGet:
            path: /health/
            port: 8000
          initialDelaySeconds: 10
          periodSeconds: 30
        
        # Readiness probe
        readinessProbe:
          httpGet:
            path: /health/
            port: 8000
          initialDelaySeconds: 5
          periodSeconds: 10
```

## Environment Variables

Create `.env` for local development:

```bash
# .env
ENVIRONMENT=development
DATABASE_URL=sqlite:///./dev.db
```

For production, set:

```bash
ENVIRONMENT=production
DATABASE_URL=postgresql://user:password@db-host:5432/myapp
```

## Dependencies

Create `pyproject.toml`:

```toml
[project]
name = "my-app"
version = "0.1.0"
requires-python = ">=3.12"
dependencies = [
    "fastapi>=0.104.0",
    "uvicorn[standard]>=0.24.0",
    "sqlalchemy>=2.0.0",
    "asyncpg>=0.29.0",
    "aiosqlite>=0.19.0",
    "pydantic[email]>=2.4.0",
    "dbwarden>=0.1.0",
]
```

Install:

```bash
uv sync
```

## Testing

Create `tests/test_users.py`:

```python
import pytest
from httpx import AsyncClient
from app.main import app


@pytest.mark.asyncio
async def test_create_user():
    async with AsyncClient(app=app, base_url="http://test") as client:
        response = await client.post(
            "/api/v1/users/",
            json={
                "email": "test@example.com",
                "username": "testuser",
                "full_name": "Test User"
            }
        )
    assert response.status_code == 201
    data = response.json()
    assert data["email"] == "test@example.com"
    assert data["username"] == "testuser"


@pytest.mark.asyncio
async def test_list_users():
    async with AsyncClient(app=app, base_url="http://test") as client:
        response = await client.get("/api/v1/users/")
    assert response.status_code == 200
    assert isinstance(response.json(), list)


@pytest.mark.asyncio
async def test_health():
    async with AsyncClient(app=app, base_url="http://test") as client:
        response = await client.get("/health/")
    assert response.status_code == 200
    data = response.json()
    assert data["status"] in ["ok", "degraded", "error"]
```

Run tests:

```bash
pytest tests/
```

## What's Next?

Take your app further:

- **[Multi-Database](../advanced/multi-database.md)** - Add analytics or logging databases
- **[Testing](../advanced/testing.md)** - Advanced testing patterns
- **[Transaction Management](../advanced/transaction-management.md)** - Complex transactions
- **[Production Patterns](../advanced/production-patterns.md)** - CI/CD and monitoring
- **[Cookbook: FastAPI Integration](../../cookbook/09-fastapi-integration.md)** - Standalone FastAPI example
