"""StarLoom v2 FastAPI entry."""

import logging
from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.api import chat, constellation, growth, payment, user
from app.config import get_settings
from app.database import init_db
from app.middleware.rate_limit import RateLimitMiddleware
from app.scheduler import scheduler, setup_daily_prefetch_schedule

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


@asynccontextmanager
async def lifespan(app: FastAPI):
    try:
        await init_db()
        logger.info("Database tables ensured")
    except Exception as e:
        logger.warning("init_db skipped or failed: %s", e)
    setup_daily_prefetch_schedule()
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
app.include_router(growth.router)
app.include_router(payment.router)
app.include_router(user.router)
app.include_router(chat.router)


@app.get("/health")
async def health() -> dict:
    return {"status": "ok", "env": settings.app_env}
