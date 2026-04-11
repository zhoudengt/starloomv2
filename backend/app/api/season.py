"""Season pass endpoints."""

from __future__ import annotations

import logging
from datetime import datetime
from typing import Any

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession

from app.api._report_helpers import natal_for_user
from app.config import get_settings
from app.database import get_db
from app.deps import get_current_user
from app.models.user import User
from app.services.astro_service import compute_transits
from app.services.growth_helpers import get_or_create_growth_profile
from app.services.llm_service import LLMServiceFactory
from app.utils.zodiac_calc import get_sign_meta, sun_sign_from_date

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/v1", tags=["season"])


@router.get("/season/today")
async def season_today(
    db: AsyncSession = Depends(get_db),
    user: User = Depends(get_current_user),
) -> dict[str, Any]:
    gp = await get_or_create_growth_profile(db, user)
    await db.refresh(user)
    if not gp.season_pass_until or gp.season_pass_until < datetime.utcnow():
        raise HTTPException(status_code=402, detail="需要星运月卡")
    if not user.birth_date:
        raise HTTPException(status_code=400, detail="请先在个人资料填写出生日期")
    sign = sun_sign_from_date(user.birth_date)
    meta = get_sign_meta(sign) or {}
    sign_cn = meta.get("sign_cn", sign)
    natal = natal_for_user(user, user.birth_date, None, None, None, None, None)
    today = datetime.utcnow().date()
    prompt: str
    try:
        if natal:
            from app.prompts.chart_formatter import format_natal_chart_for_prompt, format_transit_for_prompt

            tr = compute_transits(natal, today)
            prompt = (
                "【星运月卡·今日深度参考】以下为历表计算的本命与行运事实，请据此撰写 Markdown，"
                "分「整体状态」「人际与沟通」「行动建议」；避免迷信与宿命论表述。\n\n"
                + format_natal_chart_for_prompt(natal)
                + "\n\n"
                + format_transit_for_prompt(tr)
            )
        else:
            prompt = (
                f"【星运月卡·今日深度参考】用户太阳星座：{sign_cn}（{sign}），出生日期：{user.birth_date}。"
                "请输出今日性格与节奏参考（Markdown），分「整体状态」「人际与沟通」「行动建议」；避免迷信与宿命论表述。"
            )
    except Exception as e:
        logger.warning("season today astro prompt: %s", e)
        prompt = (
            f"【星运月卡·今日深度参考】用户太阳星座：{sign_cn}（{sign}），出生日期：{user.birth_date}。"
            "请输出今日性格与节奏参考（Markdown），分「整体状态」「人际与沟通」「行动建议」；避免迷信与宿命论表述。"
        )
    settings = get_settings()
    svc = LLMServiceFactory.for_report(settings)
    try:
        text = await svc.generate(prompt)
    except Exception:
        text = f"## 今日参考\n\n{sign_cn}今日宜保持节奏平稳，适合整理计划与轻度社交。"
    return {"markdown": text, "date": datetime.utcnow().date().isoformat()}
