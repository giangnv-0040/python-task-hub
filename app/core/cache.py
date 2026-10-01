from functools import lru_cache
from typing import Annotated

from fastapi import Depends
from redis.asyncio import Redis

from app.config import settings
from app.core.constants import REDIS_CONNECT_TIMEOUT_SECONDS, REDIS_SOCKET_TIMEOUT_SECONDS


@lru_cache
def get_redis() -> Redis:
    """Dependency tra ve Redis client dung chung (1 connection pool/process).

    Test override bang `app.dependency_overrides[get_redis]` (R35).
    """
    # redis-py mac dinh khong co timeout -> Redis treo la request treo theo (R41)
    return Redis.from_url(
        settings.redis_url,
        decode_responses=True,
        socket_connect_timeout=REDIS_CONNECT_TIMEOUT_SECONDS,
        socket_timeout=REDIS_SOCKET_TIMEOUT_SECONDS,
    )


RedisDep = Annotated[Redis, Depends(get_redis)]
