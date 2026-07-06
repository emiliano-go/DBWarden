---
{}
---

# Production Patterns

Best practices for deploying FastAPI applications with DBWarden in production.

## Deployment Strategy

### Pattern 1: Pre-Deploy Migrations (Recommended)

Run migrations before deploying new code:

```bash
# CI/CD pipeline
1. Run tests
2. Build Docker image
3. Run migrations (on staging)
4. Deploy new code
5. Run migrations (on production)
6. Deploy to production
```

**Kubernetes example:**

```yaml
apiVersion: batch/v1
kind: Job
metadata:
  name: migrate
spec:
  template:
    spec:
      containers:
      - name: migrate
        image: myapp:v1.2.3
        command: ["dbwarden", "migrate"]
        env:
        - name: DATABASE_URL
          valueFrom:
            secretKeyRef:
              name: db-secret
              key: url
      restartPolicy: OnFailure
```

Then deploy the app:

```yaml
apiVersion: apps/v1
kind: Deployment
metadata:
  name: myapp
spec:
  replicas: 3
  template:
    spec:
      containers:
      - name: app
        image: myapp:v1.2.3
        # App uses mode="check" in lifespan
```

### Pattern 2: Init Container

Run migrations in init container before app starts:

```yaml
apiVersion: apps/v1
kind: Deployment
metadata:
  name: myapp
spec:
  template:
    spec:
      initContainers:
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
        env:
        - name: DATABASE_URL
          valueFrom:
            secretKeyRef:
              name: db-secret
              key: url
```

Multiple pods may try to migrate simultaneously. DBWarden's migration locking helps, but prefer Pattern 1 for large deployments.

### Pattern 3: Auto-Migrate on Startup (Not Recommended)

Only for simple, single-instance deployments:

```python
@asynccontextmanager
async def lifespan(app: FastAPI):
    async with migration_context(
        mode="migrate",
        allow_in_production=True,  #  Risky
    ):
        yield
```

**Risks:**
- Multiple pods race to migrate
- No rollback on failure
- Downtime during migration

## Environment Configuration

### Environment Variables

```python
# config.py
import os
from pydantic_settings import BaseSettings

class Settings(BaseSettings):
    database_url_sync: str
    environment: str = "production"
    log_level: str = "INFO"
    
    class Config:
        env_file = ".env"

settings = Settings()
```

Use in DBWarden config:

```python
# dbwarden.py
from config import settings

primary = database_config(
    database_name="primary",
    default=True,
    database_type="postgresql",
    database_url_sync=settings.database_url_sync,
    model_paths=["app.models"],
)
```

### Secrets Management

**Kubernetes Secrets:**

```yaml
apiVersion: v1
kind: Secret
metadata:
  name: db-secret
type: Opaque
stringData:
  url: postgresql://user:password@db-host:5432/myapp
```

**AWS Secrets Manager:**

```python
import boto3
import json

def get_database_url():
    client = boto3.client('secretsmanager')
    response = client.get_secret_value(SecretId='prod/database/url')
    secret = json.loads(response['SecretString'])
    return secret['DATABASE_URL']

db = database_config(
    database_url_sync=get_database_url(),
    ...
)
```

## Health Checks

### Kubernetes Probes

```yaml
apiVersion: apps/v1
kind: Deployment
metadata:
  name: myapp
spec:
  template:
    spec:
      containers:
      - name: app
        # Liveness: Is the app alive?
        livenessProbe:
          httpGet:
            path: /health/
            port: 8000
          initialDelaySeconds: 30
          periodSeconds: 30
          timeoutSeconds: 5
          failureThreshold: 3
        
        # Readiness: Is the app ready for traffic?
        readinessProbe:
          httpGet:
            path: /health/
            port: 8000
          initialDelaySeconds: 10
          periodSeconds: 10
          timeoutSeconds: 3
          failureThreshold: 2
```

### Load Balancer Health Checks

**AWS ALB:**

```yaml
TargetGroup:
  HealthCheckEnabled: true
  HealthCheckPath: /health/
  HealthCheckIntervalSeconds: 30
  HealthCheckTimeoutSeconds: 5
  HealthyThresholdCount: 2
  UnhealthyThresholdCount: 3
  Matcher:
    HttpCode: "200"
```

## Monitoring

### Prometheus Metrics

Export database metrics:

```python
from prometheus_client import Counter, Histogram, Gauge
import time

# Metrics
db_query_duration = Histogram(
    'db_query_duration_seconds',
    'Database query duration',
    ['operation']
)
db_connections_active = Gauge(
    'db_connections_active',
    'Active database connections'
)

# Middleware to track queries
@app.middleware("http")
async def track_queries(request, call_next):
    start = time.time()
    response = await call_next(request)
    duration = time.time() - start
    
    if hasattr(request.state, 'db_queries'):
        db_query_duration.labels(operation='query').observe(duration)
    
    return response
```

### Structured Logging

```python
import structlog

logger = structlog.get_logger()

@app.post("/users")
async def create_user(user_data: UserCreate, session: primary.async_session):
    logger.info(
        "creating_user",
        email=user_data.email,
        username=user_data.username
    )
    
    user = User(**user_data.model_dump())
    session.add(user)
    await session.commit()
    
    logger.info(
        "user_created",
        user_id=user.id,
        email=user.email
    )
    
    return user
```

### Distributed Tracing

```python
from opentelemetry import trace
from opentelemetry.instrumentation.fastapi import FastAPIInstrumentor
from opentelemetry.instrumentation.sqlalchemy import SQLAlchemyInstrumentor

# Initialize tracing
FastAPIInstrumentor.instrument_app(app)
SQLAlchemyInstrumentor().instrument()

# Traces will automatically include database queries
```

## Performance Optimization

### Connection Pooling

```python
# Increase pool size for high-traffic apps
create_async_engine(
    database_url,
    pool_size=20,
    max_overflow=10,
    pool_pre_ping=True,
)
```

### Query Optimization

```python
# Eager load relationships
@app.get("/users/{user_id}/posts")
async def get_user_posts(user_id: int, session: primary.async_session):
    result = await session.execute(
        select(User)
        .options(selectinload(User.posts))  # Eager load
        .where(User.id == user_id)
    )
    user = result.scalar_one()
    return user.posts
```

### Caching

```python
from functools import lru_cache

@lru_cache(maxsize=100)
def get_cached_user(user_id: int):
    # Cache expensive computations
    pass
```

## Zero-Downtime Deployments

### Blue-Green Deployment

1. Run migrations (backward compatible)
2. Deploy new version (green)
3. Shift traffic to green
4. Keep blue as backup
5. Decommission blue after validation

### Rolling Updates

```yaml
apiVersion: apps/v1
kind: Deployment
metadata:
  name: myapp
spec:
  replicas: 5
  strategy:
    type: RollingUpdate
    rollingUpdate:
      maxSurge: 1        # One extra pod during update
      maxUnavailable: 0  # All pods must be ready
```

### Backward-Compatible Migrations

**Bad:**
```python
#  Breaking change
op.drop_column('users', 'old_field')
```

**Good:**
```python
#  Backward compatible
# Step 1: Add new field
op.add_column('users', sa.Column('new_field', sa.String()))

# Step 2: Deploy code using new_field
# Step 3: Backfill data
# Step 4: Deploy code no longer using old_field
# Step 5: Drop old_field
op.drop_column('users', 'old_field')
```

## Disaster Recovery

### Backups

```bash
# Automated backups before migrations
$ dbwarden migrate --with-backup --backup-dir /backups
```

### Rollback Plan

```bash
# If deployment fails
1. Roll back code to previous version
2. Roll back migrations:
   dbwarden rollback --count 1
3. Verify health:
   curl /health/
```

## Security

### Connection String Security

```python
#  Never commit
database_url_sync="postgresql://user:password@host/db"

#  Use environment variables
database_url_sync=os.getenv("DATABASE_URL")
```

### SSL/TLS

```python
database_url_sync="postgresql://user:password@host/db?sslmode=require"
```

### Least Privilege

Create application database user with minimal permissions:

```sql
CREATE USER myapp_user WITH PASSWORD 'secret';
GRANT SELECT, INSERT, UPDATE, DELETE ON ALL TABLES IN SCHEMA public TO myapp_user;
-- Don't grant DROP, TRUNCATE, etc.
```

## CI/CD Pipeline Example

```yaml
# .github/workflows/deploy.yml
name: Deploy

on:
  push:
    branches: [main]

jobs:
  test:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v2
      - name: Run tests
        run: pytest
  
  migrate:
    needs: test
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v2
      - name: Run migrations
        run: |
          dbwarden migrate
        env:
          DATABASE_URL: ${{ secrets.DATABASE_URL }}
  
  deploy:
    needs: migrate
    runs-on: ubuntu-latest
    steps:
      - name: Deploy to Kubernetes
        run: |
          kubectl set image deployment/myapp myapp=myapp:${{ github.sha }}
```

## What's Next?

- **[Multi-Database](multi-database.md)** - Scale with multiple databases
- **[Testing](testing.md)** - Test production patterns in CI
