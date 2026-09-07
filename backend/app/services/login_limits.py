from __future__ import annotations

import hashlib
import hmac
import time
import uuid
from functools import lru_cache

import redis
from fastapi import HTTPException

from app.config import get_settings

# Redis is already part of the supported stack. Atomic leases cover all API
# processes, unlike a thread semaphore. No user email or password is retained.
RESERVE = """
local failures = tonumber(redis.call('GET', KEYS[1]) or '0')
if failures >= tonumber(ARGV[1]) then
  return {0, math.max(redis.call('TTL', KEYS[1]), 1)}
end
redis.call('ZREMRANGEBYSCORE', KEYS[2], '-inf', ARGV[2])
if redis.call('ZCARD', KEYS[2]) >= tonumber(ARGV[3]) then return {0, 1} end
redis.call('ZADD', KEYS[2], ARGV[4], ARGV[5])
redis.call('EXPIRE', KEYS[2], 60)
return {1, 0}
"""
FINISH = """
redis.call('ZREM', KEYS[2], ARGV[1])
if ARGV[2] == 'success' then
  redis.call('DEL', KEYS[1])
else
  local count = redis.call('INCR', KEYS[1])
  if count == 1 then redis.call('EXPIRE', KEYS[1], ARGV[3]) end
end
return 1
"""


@lru_cache
def auth_store():
    return redis.from_url(
        get_settings().redis_url,
        socket_connect_timeout=2,
        socket_timeout=2,
    )


def reserve_login(email: str) -> tuple[str, str]:
    settings = get_settings()
    digest = hmac.new(settings.secret_key.encode(), email.lower().encode(), hashlib.sha256).hexdigest()
    key = f"signalgraph:auth:failure:{digest}"
    lease = uuid.uuid4().hex
    now = time.time()
    try:
        allowed, retry = auth_store().eval(
            RESERVE,
            2,
            key,
            "signalgraph:auth:hash-leases",
            settings.login_max_failures,
            now,
            settings.login_max_concurrent,
            now + 30,
            lease,
        )
    except redis.RedisError as exc:
        raise HTTPException(503, "Authentication safety checks unavailable. Try again later.") from exc
    if not allowed:
        raise HTTPException(
            429,
            "Too many authentication attempts. Try again later.",
            headers={"Retry-After": str(retry)},
        )
    return key, lease


def finish_login(reservation: tuple[str, str], success: bool) -> None:
    key, lease = reservation
    try:
        auth_store().eval(
            FINISH,
            2,
            key,
            "signalgraph:auth:hash-leases",
            lease,
            "success" if success else "failure",
            get_settings().login_failure_window_seconds,
        )
    except redis.RedisError as exc:
        # Fail closed rather than minting a token without accounting. A crashed
        # request's hash lease expires automatically.
        raise HTTPException(503, "Authentication safety checks unavailable. Try again later.") from exc
