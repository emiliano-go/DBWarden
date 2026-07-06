---
{}
---

# Transaction Management

Learn how to manage database transactions in FastAPI with DBWarden.

In these examples, `primary` is a `DatabaseHandle` created with
`database_config()`. Use `primary.async_session` as the route parameter
annotation to get a request-scoped session. See [Session Dependency](../tutorial/session-dependency.md).

## Automatic Transactions

By default, DBWarden sessions handle transactions automatically:

```python
@app.post("/users")
async def create_user(user_data: UserCreate, session: primary.async_session):
    user = User(**user_data.model_dump())
    session.add(user)
    await session.commit()  # Explicit commit
    return user
    # Session automatically closes here
```

## When to Commit

### Automatic (Session Autoflush)

For simple operations, SQLAlchemy flushes changes automatically:

```python
@app.get("/users/{user_id}")
async def get_user(user_id: int, session: primary.async_session):
    result = await session.execute(select(User).where(User.id == user_id))
    return result.scalar_one_or_none()
    # No commit needed for reads
```

### Manual Commit

For writes, explicitly commit:

```python
@app.post("/users")
async def create_user(user_data: UserCreate, session: primary.async_session):
    user = User(**user_data.model_dump())
    session.add(user)
    await session.commit()  #  Explicit commit
    await session.refresh(user)  # Get DB-generated values
    return user
```

## Error Handling and Rollback

### Automatic Rollback

If an exception occurs, the session rolls back automatically:

```python
@app.post("/users")
async def create_user(user_data: UserCreate, session: primary.async_session):
    user = User(**user_data.model_dump())
    session.add(user)
    
    if not validate_email(user.email):
        raise HTTPException(400, "Invalid email")
        # Session automatically rolls back
    
    await session.commit()
    return user
```

### Manual Rollback

For explicit control:

```python
@app.post("/users")
async def create_user(user_data: UserCreate, session: primary.async_session):
    user = User(**user_data.model_dump())
    session.add(user)
    
    try:
        await session.commit()
    except IntegrityError:
        await session.rollback()  # Explicit rollback
        raise HTTPException(400, "User already exists")
    
    return user
```

## Nested Transactions (Savepoints)

Use savepoints for partial rollbacks:

```python
from sqlalchemy.exc import IntegrityError

@app.post("/batch")
async def batch_create(users: list[UserCreate], session: primary.async_session):
    created = []
    failed = []
    
    for user_data in users:
        savepoint = await session.begin_nested()  # Create savepoint
        try:
            user = User(**user_data.model_dump())
            session.add(user)
            await session.flush()
            created.append(user)
            await savepoint.commit()
        except IntegrityError:
            await savepoint.rollback()  # Rollback to savepoint
            failed.append(user_data)
    
    await session.commit()  # Commit all successful inserts
    return {"created": created, "failed": failed}
```

## Multiple Operations in One Transaction

Group related operations:

```python
@app.post("/orders")
async def create_order(order_data: OrderCreate, session: primary.async_session):
    # All operations in one transaction
    
    # 1. Create order
    order = Order(user_id=order_data.user_id)
    session.add(order)
    await session.flush()  # Get order ID
    
    # 2. Add order items
    for item_data in order_data.items:
        item = OrderItem(order_id=order.id, **item_data.dict())
        session.add(item)
    
    # 3. Update inventory
    for item_data in order_data.items:
        await session.execute(
            update(Product)
            .where(Product.id == item_data.product_id)
            .values(stock=Product.stock - item_data.quantity)
        )
    
    # Commit everything at once
    await session.commit()
    await session.refresh(order)
    return order
```

If any step fails, everything rolls back.

## Isolation Levels

Set transaction isolation level:

```python
from sqlalchemy import create_engine

# In engine creation (advanced)
engine = create_async_engine(
    database_url,
    isolation_level="SERIALIZABLE"  # Strictest isolation
)
```

Isolation levels:
- `READ UNCOMMITTED` - Dirty reads possible
- `READ COMMITTED` - Default for PostgreSQL
- `REPEATABLE READ` - No phantom reads
- `SERIALIZABLE` - Strictest, slowest

## Two-Phase Commit (Distributed Transactions)

For multi-database transactions (advanced):

```python
@app.post("/transfer")
async def transfer_funds(
    primary_session: primary.async_session,
    analytics_session: analytics.async_session,
):
    try:
        # Phase 1: Prepare both transactions
        user = await primary_session.get(User, 1)
        user.balance -= 100
        await primary_session.flush()
        
        event = Event(type="transfer", amount=100)
        analytics_session.add(event)
        await analytics_session.flush()
        
        # Phase 2: Commit both
        await primary_session.commit()
        await analytics_session.commit()
        
    except Exception:
        # Rollback both if either fails
        await primary_session.rollback()
        await analytics_session.rollback()
        raise
```

Two-phase commit is complex and not fully supported by SQLAlchemy. Consider using saga pattern or event sourcing for distributed transactions.

## Optimistic Locking

Prevent lost updates with version columns:

```python
class User(Base):
    __tablename__ = "users"
    id: Mapped[int] = mapped_column(primary_key=True)
    email: Mapped[str]
    version: Mapped[int] = mapped_column(default=0)  # Version column

@app.patch("/users/{user_id}")
async def update_user(
    user_id: int,
    user_data: UserUpdate,
    session: primary.async_session,
):
    user = await session.get(User, user_id)
    
    # Check version matches
    if user.version != user_data.expected_version:
        raise HTTPException(409, "User was modified by someone else")
    
    user.email = user_data.email
    user.version += 1  # Increment version
    
    await session.commit()
    return user
```

## Pessimistic Locking

Lock rows explicitly:

```python
from sqlalchemy import select

@app.post("/reserve")
async def reserve_item(item_id: int, session: primary.async_session):
    # Lock the row for update
    result = await session.execute(
        select(Item)
        .where(Item.id == item_id)
        .with_for_update()  # SELECT ... FOR UPDATE
    )
    item = result.scalar_one()
    
    if item.reserved:
        raise HTTPException(400, "Already reserved")
    
    item.reserved = True
    await session.commit()
    return item
```

## Idempotency

Make operations idempotent:

```python
@app.post("/orders", status_code=201)
async def create_order(
    order_data: OrderCreate,
    idempotency_key: str,
    session: primary.async_session,
):
    # Check if order already exists
    existing = await session.execute(
        select(Order).where(Order.idempotency_key == idempotency_key)
    )
    order = existing.scalar_one_or_none()
    
    if order:
        return order  # Already created, return existing
    
    # Create new order
    order = Order(**order_data.dict(), idempotency_key=idempotency_key)
    session.add(order)
    await session.commit()
    return order
```

## What's Next?

- **[Engine Lifecycle](engine-lifecycle.md)** - Connection pooling and cleanup
- **[Production Patterns](production-patterns.md)** - Deploy with confidence
