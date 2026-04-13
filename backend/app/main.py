"""StarLoom v2 FastAPI entry."""

import logging
from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.api import chat, constellation, content, daily, growth, guide, payment, reports, season, user
from app.config import get_settings
from app.database import init_db
from app.middleware.rate_limit import RateLimitMiddleware
from app.scheduler import (
    scheduler,
    setup_daily_prefetch_schedule,
    setup_guide_generation_schedule,
    setup_unified_daily_schedule,
)

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


def _log_payment_config_warnings() -> None:
    """Single global payment config — warn at startup if real pay will 503 (no behavior change)."""
    s = get_settings()
    if not (s.xunhupay_notify_url or "").strip():
        logger.warning(
            "XUNHUPAY_NOTIFY_URL is empty — POST /api/v1/payment/create will return 503 until configured"
        )
    if not (s.xunhupay_appid_wechat and s.xunhupay_appsecret_wechat):
        logger.warning(
            "XUNHUPAY wechat appid/secret incomplete — wechat payment create will return 503"
        )


@asynccontextmanager
async def lifespan(app: FastAPI):
    try:
        await init_db()
        logger.info("Database tables ensured")
    except Exception as e:
        logger.warning("init_db skipped or failed: %s", e)
    _log_payment_config_warnings()
    setup_daily_prefetch_schedule()
    setup_guide_generation_schedule()
    setup_unified_daily_schedule()
    scheduler.start()
    yield
    scheduler.shutdown(wait=False)


settings = get_settings()

app = FastAPI(
    title="StarLoom v2 API",
    version="0.1.0",
    lifespan=lifespan,
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origins_list,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)
app.add_middleware(RateLimitMiddleware)

app.include_router(constellation.router)
app.include_router(daily.router)
app.include_router(reports.router)
app.include_router(season.router)
app.include_router(content.router)
app.include_router(guide.router)
app.include_router(growth.router)
app.include_router(payment.router)
app.include_router(user.router)
app.include_router(chat.router)


@app.get("/health")
async def health() -> dict:
    return {"status": "ok", "env": settings.app_env}
