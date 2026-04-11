"""Simple Redis rate limiting."""

import logging
from typing import Callable

from fastapi import Request, Response
from starlette.middleware.base import BaseHTTPMiddleware

from app.config import get_settings
from app.services.cache_service import incr_rate

logger = logging.getLogger(__name__)

FREE_PATH_PREFIX = "/api/v1/daily"
FREE_PATH_SIGNS = "/api/v1/signs"
PERSONAL_PATH = "/api/v1/daily/personal"


def _too_many(retry_after: int) -> Response:
    return Response(
        "Too Many Requests",
        status_code=429,
        headers={"Retry-After": str(retry_after)},
    )


class RateLimitMiddleware(BaseHTTPMiddleware):
    async def dispatch(self, request: Request, call_next: Callable) -> Response:
        path = request.url.path
        client_ip = request.client.host if request.client else "unknown"
        settings = get_settings()
        window = settings.rate_limit_window_seconds

        try:
            if path == PERSONAL_PATH:
                auth = request.headers.get("authorization") or ""
                user_key = auth[:80] if auth else client_ip
                key = f"rl:daily_personal:{user_key}"
                allowed, _ = await incr_rate(key, window, settings.rate_limit_daily_personal_per_minute)
                if not allowed:
                    return _too_many(window)

            if path.startswith(FREE_PATH_PREFIX) or path.startswith(FREE_PATH_SIGNS):
                key = f"rl:free:{client_ip}:{path}"
                allowed, _ = await incr_rate(key, window, settings.rate_limit_free_per_minute)
                if not allowed:
                    return _too_many(window)

            if path.startswith("/api/v1/quicktest"):
                auth = request.headers.get("authorization") or "anon"
                key = f"rl:quicktest:{auth[:80]}"
                allowed, _ = await incr_rate(key, window, settings.rate_limit_quicktest_per_minute)
                if not allowed:
                    return _too_many(window)

            if path.startswith("/api/v1/report") or path.startswith("/api/v1/chat"):
                auth = request.headers.get("authorization") or "anon"
                key = f"rl:paid:{auth[:80]}:{path}"
                allowed, _ = await incr_rate(key, window, settings.rate_limit_paid_report_chat_per_minute)
                if not allowed:
                    return _too_many(window)

            if path.startswith("/api/v1/payment/create"):
                auth = request.headers.get("authorization") or "anon"
                key = f"rl:pay:{auth[:80]}"
                allowed, _ = await incr_rate(
                    key, window, settings.rate_limit_payment_create_per_minute
                )
                if not allowed:
                    return _too_many(window)
        except Exception as e:
            logger.warning("Rate limit skipped: %s", e)

        return await call_next(request)
