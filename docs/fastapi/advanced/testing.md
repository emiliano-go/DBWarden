---
seo:
  title: Testing - DBWarden Documentation
  canonical: https://dbwarden.emiliano-go.com/fastapi/advanced/testing
  robots: index,follow
  og:
    type: website
    title: Testing - DBWarden Documentation
    description: Learn how to test FastAPI applications that use DBWarden.
    url: https://dbwarden.emiliano-go.com/fastapi/advanced/testing
    image: https://dbwarden.emiliano-go.com/assets/images/og-image.png
    image:width: 1376
    image:height: 768
    image:alt: DBWarden documentation
    site_name: DBWarden Documentation
    locale: en_US
  twitter:
    card: summary_large_image
    title: Testing - DBWarden Documentation
    description: Learn how to test FastAPI applications that use DBWarden.
    image: https://dbwarden.emiliano-go.com/assets/images/og-image.png
    image:alt: DBWarden documentation
    site: '@emiliano_go_'
  description: Learn how to test FastAPI applications that use DBWarden.
  schema_jsonld:
  - '@context': https://schema.org
    '@type': WebPage
    name: Testing - DBWarden Documentation
    url: https://dbwarden.emiliano-go.com/fastapi/advanced/testing
    description: Learn how to test FastAPI applications that use DBWarden.
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
      name: Advanced
      item: https://dbwarden.emiliano-go.com/fastapi/advanced
    - '@type': ListItem
      position: 3
      name: Testing
      item: https://dbwarden.emiliano-go.com/fastapi/advanced/testing
seo_html: "<title>Testing - DBWarden Documentation</title>\n<meta name=\"description\"\
  \ content=\"Learn how to test FastAPI applications that use DBWarden.\">\n<link\
  \ rel=\"canonical\" href=\"https://dbwarden.emiliano-go.com/fastapi/advanced/testing\"\
  >\n<meta name=\"robots\" content=\"index,follow\">\n<meta property=\"og:type\" content=\"\
  website\">\n<meta property=\"og:title\" content=\"Testing - DBWarden Documentation\"\
  >\n<meta property=\"og:description\" content=\"Learn how to test FastAPI applications\
  \ that use DBWarden.\">\n<meta property=\"og:url\" content=\"https://dbwarden.emiliano-go.com/fastapi/advanced/testing\"\
  >\n<meta property=\"og:image\" content=\"https://dbwarden.emiliano-go.com/assets/images/og-image.png\"\
  >\n<meta property=\"og:image:width\" content=\"1376\">\n<meta property=\"og:image:height\"\
  \ content=\"768\">\n<meta property=\"og:image:alt\" content=\"DBWarden documentation\"\
  >\n<meta property=\"og:site_name\" content=\"DBWarden Documentation\">\n<meta property=\"\
  og:locale\" content=\"en_US\">\n<meta name=\"twitter:card\" content=\"summary_large_image\"\
  >\n<meta name=\"twitter:title\" content=\"Testing - DBWarden Documentation\">\n\
  <meta name=\"twitter:description\" content=\"Learn how to test FastAPI applications\
  \ that use DBWarden.\">\n<meta name=\"twitter:image\" content=\"https://dbwarden.emiliano-go.com/assets/images/og-image.png\"\
  >\n<meta name=\"twitter:image:alt\" content=\"DBWarden documentation\">\n<meta name=\"\
  twitter:site\" content=\"@emiliano_go_\">\n<script type=\"application/ld+json\"\
  >\n[\n  {\n    \"@context\": \"https://schema.org\",\n    \"@type\": \"WebPage\"\
  ,\n    \"name\": \"Testing - DBWarden Documentation\",\n    \"url\": \"https://dbwarden.emiliano-go.com/fastapi/advanced/testing\"\
  ,\n    \"description\": \"Learn how to test FastAPI applications that use DBWarden.\"\
  ,\n    \"image\": \"https://dbwarden.emiliano-go.com/assets/images/og-image.png\"\
  ,\n    \"publisher\": {\n      \"@type\": \"Organization\",\n      \"name\": \"\
  Emiliano Gandini Outeda\",\n      \"logo\": \"https://dbwarden.emiliano-go.com/assets/images/og-image.png\"\
  \n    }\n  },\n  {\n    \"@context\": \"https://schema.org\",\n    \"@type\": \"\
  BreadcrumbList\",\n    \"itemListElement\": [\n      {\n        \"@type\": \"ListItem\"\
  ,\n        \"position\": 1,\n        \"name\": \"FastAPI Integration\",\n      \
  \  \"item\": \"https://dbwarden.emiliano-go.com/fastapi\"\n      },\n      {\n \
  \       \"@type\": \"ListItem\",\n        \"position\": 2,\n        \"name\": \"\
  Advanced\",\n        \"item\": \"https://dbwarden.emiliano-go.com/fastapi/advanced\"\
  \n      },\n      {\n        \"@type\": \"ListItem\",\n        \"position\": 3,\n\
  \        \"name\": \"Testing\",\n        \"item\": \"https://dbwarden.emiliano-go.com/fastapi/advanced/testing\"\
  \n      }\n    ]\n  }\n]\n</script>\n"
---

# Testing

Learn how to test FastAPI applications that use DBWarden.

## Quick Example

The simplest way to test with DBWarden is to configure the test database via
environment variables. No dependency overrides needed:

```python
import os
import pytest
from fastapi.testclient import TestClient

# Point DBWarden at an in-memory SQLite database for tests
os.environ["ENVIRONMENT"] = "test"
os.environ["DEV_DATABASE_URL"] = "sqlite:///:memory:"

from app.main import app
from app.models import Base


@pytest.fixture
def client():
    from dbwarden.commands.migrate import migrate_single
    migrate_single(database="primary")
    yield TestClient(app)


def test_create_user(client):
    response = client.post(
        "/api/v1/users/",
        json={
            "email": "test@example.com",
            "username": "testuser",
        },
    )
    assert response.status_code == 201
    data = response.json()
    assert data["email"] == "test@example.com"
```

When `ENVIRONMENT=test` is set and `dev_database_url` is configured in your
`database_config()`, DBWarden automatically uses the test URL. No manual
engine creation, session factories, or dependency overrides needed.

## Test Database Setup

### Option 1: SQLite In-Memory

Fast, isolated, no cleanup needed:

```python
import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool
from app.models import Base

@pytest.fixture(scope="function")
def test_db():
    engine = create_engine(
        "sqlite:///:memory:",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
    Base.metadata.create_all(bind=engine)
    TestingSession = sessionmaker(bind=engine)
    yield TestingSession()
    Base.metadata.drop_all(bind=engine)
```

### Option 2: PostgreSQL Test Database

More realistic, slower:

```python
import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from app.models import Base

TEST_DATABASE_URL = "postgresql://user:password@localhost/test_db"

@pytest.fixture(scope="function")
def test_db():
    engine = create_engine(TEST_DATABASE_URL)
    Base.metadata.create_all(bind=engine)
    TestingSession = sessionmaker(bind=engine)
    session = TestingSession()
    yield session
    session.close()
    Base.metadata.drop_all(bind=engine)
```

### Option 3: Transaction Rollback

Fastest for repeated tests:

```python
@pytest.fixture(scope="function")
def test_db():
    connection = engine.connect()
    transaction = connection.begin()
    session = TestingSession(bind=connection)
    
    yield session
    
    session.close()
    transaction.rollback()
    connection.close()
```

## Override Session Dependency

### Method 1: Environment Variables (Recommended)

Configure a `dev_database_url` in your config, then set `ENVIRONMENT=test`:

```python
# config.py
primary = database_config(
    database_name="primary",
    default=True,
    database_type="postgresql",
    database_url_sync="postgresql://localhost/prod",
    dev_database_url="sqlite:///./test.db",
    model_paths=["app.models"],
)
```

```python
# conftest.py
import os
import pytest

os.environ["ENVIRONMENT"] = "test"

@pytest.fixture(autouse=True)
def setup_test_db():
    from dbwarden.commands.migrate import migrate_single
    migrate_single(database="primary", verbose=False)
    yield
```

This works with the `DatabaseHandle` pattern without any dependency overrides.

### Method 2: `get_session` Override

For apps that use the `Annotated[AsyncSession, Depends(get_session())]` pattern:

```python
from app.dependencies import SessionDep
from app.dependencies import get_session  # The function, not a call

def override_get_session():
    try:
        db = TestingSessionLocal()
        yield db
    finally:
        db.close()

app.dependency_overrides[get_session] = override_get_session
```

### Method 3: Fixture-Based Override

```python
import pytest

@pytest.fixture
def client(test_db):
    def override():
        try:
            yield test_db
        finally:
            test_db.rollback()
    
    app.dependency_overrides[get_session] = override
    yield TestClient(app)
    app.dependency_overrides.clear()
```

### Method 4: Async Override

For async tests using `get_session()`:

```python
import pytest
from httpx import AsyncClient
from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession

@pytest.fixture
async def async_client():
    engine = create_async_engine("sqlite+aiosqlite:///:memory:")
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    
    async def override():
        async with AsyncSession(engine) as session:
            yield session
    
    app.dependency_overrides[get_session] = override
    
    async with AsyncClient(app=app, base_url="http://test") as client:
        yield client
    
    app.dependency_overrides.clear()
```

### Method 2: Fixture-Based

```python
import pytest
from fastapi.testclient import TestClient

@pytest.fixture
def client(test_db):
    def override():
        try:
            yield test_db
        finally:
            test_db.rollback()
    
    app.dependency_overrides[get_session] = override
    yield TestClient(app)
    app.dependency_overrides.clear()
```

### Method 3: Async Override

For async tests:

```python
import pytest
from httpx import AsyncClient
from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession

@pytest.fixture
async def async_client():
    engine = create_async_engine("sqlite+aiosqlite:///:memory:")
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    
    async def override():
        async with AsyncSession(engine) as session:
            yield session
    
    app.dependency_overrides[get_session] = override
    
    async with AsyncClient(app=app, base_url="http://test") as client:
        yield client
    
    app.dependency_overrides.clear()
```

## Testing CRUD Operations

### Test Create

```python
def test_create_user(client):
    response = client.post(
        "/api/v1/users/",
        json={"email": "test@example.com", "username": "test"}
    )
    assert response.status_code == 201
    assert response.json()["email"] == "test@example.com"
```

### Test Read

```python
def test_get_user(client, test_db):
    # Setup: create user
    user = User(email="test@example.com", username="test")
    test_db.add(user)
    test_db.commit()
    
    # Test: get user
    response = client.get(f"/api/v1/users/{user.id}")
    assert response.status_code == 200
    assert response.json()["email"] == "test@example.com"
```

### Test Update

```python
def test_update_user(client, test_db):
    user = User(email="test@example.com", username="test")
    test_db.add(user)
    test_db.commit()
    
    response = client.patch(
        f"/api/v1/users/{user.id}",
        json={"email": "new@example.com"}
    )
    assert response.status_code == 200
    assert response.json()["email"] == "new@example.com"
```

### Test Delete

```python
def test_delete_user(client, test_db):
    user = User(email="test@example.com", username="test")
    test_db.add(user)
    test_db.commit()
    user_id = user.id
    
    response = client.delete(f"/api/v1/users/{user_id}")
    assert response.status_code == 204
    
    # Verify deleted
    assert test_db.get(User, user_id) is None
```

## Test Fixtures

### User Fixture

```python
@pytest.fixture
def sample_user(test_db):
    user = User(
        email="test@example.com",
        username="testuser",
        is_active=True
    )
    test_db.add(user)
    test_db.commit()
    test_db.refresh(user)
    return user
```

### Multiple Users

```python
@pytest.fixture
def sample_users(test_db):
    users = [
        User(email=f"user{i}@example.com", username=f"user{i}")
        for i in range(5)
    ]
    test_db.add_all(users)
    test_db.commit()
    return users
```

## Testing Multi-Database

Use environment variables to configure test databases per handle:

```python
import os
import pytest
from fastapi.testclient import TestClient

os.environ["PRIMARY_DB_URL"] = "sqlite:///./test_primary.db"
os.environ["ANALYTICS_DB_URL"] = "sqlite:///./test_analytics.db"
os.environ["ENVIRONMENT"] = "test"

from app.main import app  # config loads after env vars are set


@pytest.fixture
def client():
    from dbwarden.commands.migrate import migrate_single
    migrate_single(database="primary")
    migrate_single(database="analytics")
    yield TestClient(app)
```

## Testing Error Cases

### Test 404

```python
def test_user_not_found(client):
    response = client.get("/api/v1/users/9999")
    assert response.status_code == 404
    assert "not found" in response.json()["detail"].lower()
```

### Test Duplicate

```python
def test_duplicate_user(client, sample_user):
    response = client.post(
        "/api/v1/users/",
        json={
            "email": sample_user.email,  # Duplicate
            "username": "different"
        }
    )
    assert response.status_code == 400
```

### Test Validation

```python
def test_invalid_email(client):
    response = client.post(
        "/api/v1/users/",
        json={"email": "notanemail", "username": "test"}
    )
    assert response.status_code == 422
```

## Async Testing

### With pytest-asyncio

```python
import pytest
from httpx import AsyncClient

@pytest.mark.asyncio
async def test_create_user_async(async_client):
    response = await async_client.post(
        "/api/v1/users/",
        json={"email": "test@example.com", "username": "test"}
    )
    assert response.status_code == 201
```

### Async Fixtures

```python
@pytest.fixture
async def async_session():
    engine = create_async_engine("sqlite+aiosqlite:///:memory:")
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    
    async_session = AsyncSession(engine)
    yield async_session
    await async_session.close()
```

## Testing Health Endpoints

```python
def test_health_endpoint(client):
    response = client.get("/health/")
    assert response.status_code == 200
    data = response.json()
    assert "status" in data
    assert "databases" in data
```

## Mocking

### Mock External Service

```python
from unittest.mock import patch

def test_user_with_external_service(client):
    with patch('app.services.external_api.call') as mock:
        mock.return_value = {"verified": True}
        
        response = client.post(
            "/api/v1/users/",
            json={"email": "test@example.com", "username": "test"}
        )
        assert response.status_code == 201
        mock.assert_called_once()
```

## What's Next?

- **[Transaction Management](transaction-management.md)** - Complex transaction patterns
- **[Production Patterns](production-patterns.md)** - CI/CD and integration tests
