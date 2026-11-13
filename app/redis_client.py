"""Redis client for caching and session management."""
import redis.asyncio as redis
from app.config import settings

# Redis connection pool
redis_client: redis.Redis = redis.from_url(
    settings.redis_url,
    encoding="utf-8",
    decode_responses=True,
)


async def get_redis() -> redis.Redis:
    """Dependency that provides Redis client."""
    return redis_client


async def close_redis():
    """Close Redis connection on shutdown."""
    await redis_client.close()
