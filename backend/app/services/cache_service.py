"""Redis cache: daily fortune keys and helpers."""

import json
from datetime import date
from typing import Any, Optional

import redis.asyncio as redis

from app.config import get_settings

_settings = get_settings()
_redis: Optional[redis.Redis] = None


async def get_redis() -> redis.Redis:
    global _redis
    if _redis is None:
        _redis = redis.Redis(
            host=_settings.redis_host,
            port=_settings.redis_port,
            db=_settings.redis_db,
            decode_responses=True,
        )
    return _redis


def daily_key(sign: str, d: date) -> str:
    return f"daily:{sign.lower()}:{d.isoformat()}"


def personal_daily_key(user_id: int, d: date) -> str:
    return f"daily:personal:{user_id}:{d.isoformat()}"


DAILY_TTL_SECONDS = 24 * 60 * 60


async def get_daily_cached(sign: str, fortune_date: date) -> Optional[dict[str, Any]]:
    r = await get_redis()
    raw = await r.get(daily_key(sign, fortune_date))
    if not raw:
        return None
    return json.loads(raw)


async def set_daily_cached(sign: str, fortune_date: date, payload: dict[str, Any]) -> None:
    r = await get_redis()
    await r.setex(daily_key(sign, fortune_date), DAILY_TTL_SECONDS, json.dumps(payload, ensure_ascii=False))


async def get_personal_daily_cached(user_id: int, fortune_date: date) -> Optional[dict[str, Any]]:
    r = await get_redis()
    raw = await r.get(personal_daily_key(user_id, fortune_date))
    if not raw:
        return None
    return json.loads(raw)


async def set_personal_daily_cached(user_id: int, fortune_date: date, payload: dict[str, Any]) -> None:
    r = await get_redis()
    await r.setex(personal_daily_key(user_id, fortune_date), DAILY_TTL_SECONDS, json.dumps(payload, ensure_ascii=False))


async def incr_rate(key: str, window_seconds: int, limit: int) -> tuple[bool, int]:
    """Sliding window using INCR + EXPIRE (simple fixed window per key). Returns (allowed, current_count)."""
    r = await get_redis()
    pipe = r.pipeline()
    pipe.incr(key)
    pipe.expire(key, window_seconds)
    results = await pipe.execute()
    count = int(results[0])
    return count <= limit, count
