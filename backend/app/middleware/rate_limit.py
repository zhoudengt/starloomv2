"""Simple Redis rate limiting."""

import logging
from typing import Callable

from fastapi import Request, Response
from starlette.middleware.base import BaseHTTPMiddleware

from app.services.cache_service import incr_rate

logger = logging.getLogger(__name__)

# limits per architecture.md
FREE_PATH_PREFIX = "/api/v1/daily"
FREE_PATH_SIGNS = "/api/v1/signs"
WINDOW = 60


class RateLimitMiddleware(BaseHTTPMiddleware):
    async def dispatch(self, request: Request, call_next: Callable) -> Response:
        path = request.url.path
        client_ip = request.client.host if request.client else "unknown"

        try:
            if path.startswith(FREE_PATH_PREFIX) or path.startswith(FREE_PATH_SIGNS):
                key = f"rl:free:{client_ip}:{path}"
                allowed, _ = await incr_rate(key, WINDOW, 60)
                if not allowed:
                    return Response("Too Many Requests", status_code=429)

            if path.startswith("/api/v1/quicktest"):
                auth = request.headers.get("authorization") or "anon"
                key = f"rl:quicktest:{auth[:80]}"
                allowed, _ = await incr_rate(key, WINDOW, 20)
                if not allowed:
                    return Response("Too Many Requests", status_code=429)

            if path.startswith("/api/v1/report") or path.startswith("/api/v1/chat"):
                auth = request.headers.get("authorization") or "anon"
                key = f"rl:paid:{auth[:80]}:{path}"
                allowed, _ = await incr_rate(key, WINDOW, 20)
                if not allowed:
                    return Response("Too Many Requests", status_code=429)

            if path.startswith("/api/v1/payment/create"):
                auth = request.headers.get("authorization") or "anon"
                key = f"rl:pay:{auth[:80]}"
                allowed, _ = await incr_rate(key, WINDOW, 5)
                if not allowed:
                    return Response("Too Many Requests", status_code=429)
        except Exception as e:
            logger.warning("Rate limit skipped: %s", e)

        return await call_next(request)
