import os

from dotenv import load_dotenv
from fastapi import HTTPException, Request
from redis import Redis
from redis.exceptions import RedisError

load_dotenv()

REDIS_URL = os.getenv("REDIS_URL")

if not REDIS_URL:
    raise RuntimeError("REDIS_URL is not configured")

redis_client = Redis.from_url(
    REDIS_URL,
    socket_connect_timeout=2,
    socket_timeout=2
)

RATE_LIMIT_PREFIX = "relationship-journal:rate-limit"

RATE_LIMIT_SCRIPT = """
local count = redis.call('INCR', KEYS[1])

if count == 1 then
    redis.call('EXPIRE', KEYS[1], ARGV[1])
end

local ttl = redis.call('TTL', KEYS[1])

return {count, ttl}
"""


def check_rate_limit(
    request: Request,
    action: str,
    limit: int,
    window: int
):
    ip = request.client.host if request.client else "unknown"
    key = f"{RATE_LIMIT_PREFIX}:{action}:{ip}"

    try:
        count, ttl = redis_client.eval(
            RATE_LIMIT_SCRIPT,
            1,
            key,
            window
        )

    except RedisError:
        raise HTTPException(
            status_code=503,
            detail="Authentication temporarily unavailable"
        )

    if count > limit:
        raise HTTPException(
            status_code=429,
            detail="Too many requests. Try again later.",
            headers={"Retry-After": str(max(ttl, 1))}
        )


def limit_login(request: Request):
    check_rate_limit(
        request,
        action="login",
        limit=10,
        window=60
    )


def limit_signup(request: Request):
    check_rate_limit(
        request,
        action="signup",
        limit=5,
        window=60
    )