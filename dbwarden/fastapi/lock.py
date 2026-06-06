from __future__ import annotations

from contextlib import asynccontextmanager, contextmanager
from typing import Any, AsyncGenerator, Generator


@asynccontextmanager
async def migration_lock(
    redis_client: Any,
    key: str = "dbwarden_migrate",
    ttl: int = 60,
) -> AsyncGenerator[None, None]:
    """Async context manager for Redis-backed distributed migration locking.

    Ensures only one migration process can run at a time across distributed instances.

    Args:
        redis_client: An async Redis client (e.g. ``redis.asyncio.Redis``).
        key: Redis key to use for the lock (default: ``"dbwarden_migrate"``).
        ttl: Lock TTL in seconds (default: ``60``).

    Raises:
        LockError: If the lock is already held.

    Example::

        from redis.asyncio import Redis
        from dbwarden.fastapi import migration_lock

        redis = Redis.from_url("redis://localhost:6379")

        async with migration_lock(redis, key="my_lock", ttl=30):
            await run_migration()
    """
    from dbwarden.exceptions import LockError
    from dbwarden.logging import get_logger

    logger = get_logger()

    acquired = await redis_client.setnx(key, "1")
    if not acquired:
        raise LockError(
            f"Migration lock is already held (key='{key}'). "
            "Another migration process may be running."
        )

    await redis_client.expire(key, ttl)
    logger.info(f"Redis migration lock acquired (key='{key}', ttl={ttl}s)")

    try:
        yield
    finally:
        await redis_client.delete(key)
        logger.info(f"Redis migration lock released (key='{key}')")


@contextmanager
def sync_migration_lock(
    redis_client: Any,
    key: str = "dbwarden_migrate",
    ttl: int = 60,
) -> Generator[None, None, None]:
    """Sync context manager for Redis-backed distributed migration locking.

    Args:
        redis_client: A sync Redis client (e.g. ``redis.Redis``).
        key: Redis key to use for the lock (default: ``"dbwarden_migrate"``).
        ttl: Lock TTL in seconds (default: ``60``).

    Raises:
        LockError: If the lock is already held.

    Example::

        from redis import Redis
        from dbwarden.fastapi import sync_migration_lock

        redis = Redis.from_url("redis://localhost:6379")

        with sync_migration_lock(redis, key="my_lock", ttl=30):
            run_migration()
    """
    from dbwarden.exceptions import LockError
    from dbwarden.logging import get_logger

    logger = get_logger()

    acquired = redis_client.setnx(key, "1")
    if not acquired:
        raise LockError(
            f"Migration lock is already held (key='{key}'). "
            "Another migration process may be running."
        )

    redis_client.expire(key, ttl)
    logger.info(f"Redis migration lock acquired (key='{key}', ttl={ttl}s)")

    try:
        yield
    finally:
        redis_client.delete(key)
        logger.info(f"Redis migration lock released (key='{key}')")
