"""Daily fortune endpoints (public + personal)."""

from __future__ import annotations

import logging
from typing import Any

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession

from app.api._report_helpers import natal_for_user
from app.config import get_settings
from app.database import get_db
from app.deps import get_current_user
from app.models.user import User
from app.prompts.daily_fortune import (
    build_daily_personal_user_input,
    build_daily_sign_ephemeris_stub,
)
from app.services import cache_service
from app.services.astro_service import compute_ephemeris_snapshot_line, compute_transits
from app.services.daily_fortune_core import normalize_daily_payload, wrap_daily_response
from app.services.llm_service import generate_json_daily
from app.services.public_daily_fortune import ensure_public_daily_content
from app.utils.beijing_date import fortune_date_beijing
from app.utils.zodiac_calc import get_sign_meta, list_all_signs, sun_sign_from_date

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/v1", tags=["daily"])


@router.get("/daily/all")
async def daily_all(db: AsyncSession = Depends(get_db)) -> dict[str, Any]:
    today = fortune_date_beijing()
    summaries = []
    for meta in list_all_signs():
        slug = meta["sign"]
        m = get_sign_meta(slug)
        if not m:
            continue
        data = await ensure_public_daily_content(db, slug, today)
        summaries.append(
            {
                "sign": slug,
                "sign_cn": meta["sign_cn"],
                "overall_score": data.get("overall_score", 0),
                "summary": (data.get("summary") or "")[:80],
            }
        )
    return {"date": today.isoformat(), "items": summaries}


@router.get("/daily/personal")
async def get_daily_personal(
    user: User = Depends(get_current_user),
) -> dict[str, Any]:
    if not user.birth_date:
        raise HTTPException(status_code=400, detail="请先在资料页填写出生日期")
    today = fortune_date_beijing()
    cached = await cache_service.get_personal_daily_cached(user.id, today)
    if cached:
        return cached

    sign = sun_sign_from_date(user.birth_date)
    meta = get_sign_meta(sign) or {}
    sign_cn = meta.get("sign_cn", sign)

    natal = natal_for_user(user, user.birth_date, None, None, None, None, None)
    if natal:
        try:
            tr = compute_transits(natal, today)
            user_input = build_daily_personal_user_input(natal, tr)
        except Exception as e:
            logger.warning("personal transit build failed: %s", e)
            sky = compute_ephemeris_snapshot_line(today)
            user_input = build_daily_sign_ephemeris_stub(sign_cn, today.isoformat(), sky)
    else:
        sky = compute_ephemeris_snapshot_line(today)
        user_input = build_daily_sign_ephemeris_stub(sign_cn, today.isoformat(), sky)

    settings = get_settings()
    data = await generate_json_daily(settings, user_input, sign_cn, today.isoformat())
    data = normalize_daily_payload(data, sign_cn, today)
    out = wrap_daily_response(sign, sign_cn, today, data)
    out["personalized"] = True
    await cache_service.set_personal_daily_cached(user.id, today, out)
    return out


@router.get("/daily/{sign}")
async def get_daily(sign: str, db: AsyncSession = Depends(get_db)) -> dict[str, Any]:
    meta = get_sign_meta(sign)
    if not meta:
        raise HTTPException(status_code=404, detail="Unknown sign")
    today = fortune_date_beijing()
    data = await ensure_public_daily_content(db, sign, today)
    return wrap_daily_response(sign, meta["sign_cn"], today, data)
