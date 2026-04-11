"""Daily Guide generation — call 百炼 OpenAI-compatible API with per-category system prompts."""

from __future__ import annotations

import asyncio
import logging
from datetime import date
from typing import Any

import httpx
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.config import Settings, get_settings
from app.models.daily_fortune import DailyFortune
from app.models.daily_guide import DailyGuide, GuideCategory
from app.prompts import guide_career, guide_energy, guide_relationship, guide_wealth
from app.services.astro_service import compute_ephemeris_snapshot_line
from app.services.ir_converter import markdown_to_ir
from app.utils.zodiac_calc import get_sign_meta, list_all_signs

logger = logging.getLogger(__name__)

_CATEGORY_PROMPTS = {
    GuideCategory.career: guide_career,
    GuideCategory.wealth: guide_wealth,
    GuideCategory.relationship: guide_relationship,
    GuideCategory.energy: guide_energy,
}

_FORTUNE_KEY_FOR_CATEGORY = {
    GuideCategory.career: "career",
    GuideCategory.wealth: "wealth",
    GuideCategory.relationship: "love",
    GuideCategory.energy: "health",
}

_BANNED_WORDS = ["算命", "占卜", "迷信", "神棍"]

GUIDE_CALL_TIMEOUT = 90.0


async def _call_chat_completions(
    settings: Settings,
    system_prompt: str,
    user_message: str,
) -> str:
    api_key = settings.bailian_api_key.strip()
    if not api_key:
        raise ValueError("BAILIAN_API_KEY not configured for guide generation")

    base = settings.bailian_api_base.rstrip("/")
    url = f"{base}/chat/completions"

    body = {
        "model": settings.guide_llm_model,
        "messages": [
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": user_message},
        ],
        "max_tokens": 2500,
        "temperature": 0.85,
    }
    headers = {
        "Authorization": f"Bearer {api_key}",
        "Content-Type": "application/json",
    }

    async with httpx.AsyncClient(timeout=GUIDE_CALL_TIMEOUT) as client:
        r = await client.post(url, json=body, headers=headers)
        r.raise_for_status()
        data = r.json()

    choices = data.get("choices") or []
    if not choices:
        raise ValueError("Empty choices from LLM")
    return (choices[0].get("message") or {}).get("content") or ""


def _extract_preview(content: str, max_len: int = 150) -> str:
    lines = content.strip().splitlines()
    preview_parts: list[str] = []
    chars = 0
    for line in lines:
        stripped = line.strip()
        if not stripped or stripped.startswith("#"):
            continue
        preview_parts.append(stripped)
        chars += len(stripped)
        if chars >= max_len:
            break
    text = "".join(preview_parts)
    if len(text) > max_len:
        text = text[:max_len] + "…"
    return text


def _extract_title(content: str, category: GuideCategory) -> str:
    fallback_titles = {
        GuideCategory.career: "今日职场星运",
        GuideCategory.wealth: "今日财富密码",
        GuideCategory.relationship: "今日人际沟通",
        GuideCategory.energy: "今日情绪能量",
    }
    for line in content.strip().splitlines():
        stripped = line.strip()
        if stripped.startswith("###") or stripped.startswith("##"):
            title = stripped.lstrip("#").strip()
            if title:
                return title[:200]
    return fallback_titles.get(category, "今日深析")


def _compliance_filter(text: str) -> str:
    for word in _BANNED_WORDS:
        text = text.replace(word, "星象参考")
    return text


def _extract_transit_basis(sky_context: str) -> str:
    if len(sky_context) > 300:
        return sky_context[:297] + "…"
    return sky_context


async def _generate_one_category(
    settings: Settings,
    sign_slug: str,
    fortune_date: date,
    sky_context: str,
    fortune_data: dict[str, Any],
    sign_cn: str,
    date_str: str,
    category: GuideCategory,
) -> DailyGuide | None:
    prompt_module = _CATEGORY_PROMPTS[category]
    fortune_key = _FORTUNE_KEY_FOR_CATEGORY[category]
    fortune_seed = fortune_data.get(fortune_key, "")
    if category == GuideCategory.energy:
        advice = fortune_data.get("advice", "")
        if advice:
            fortune_seed = f"{fortune_seed}\n{advice}"

    user_msg = prompt_module.build_user_message(
        sign_cn=sign_cn,
        fortune_date=date_str,
        sky_context=sky_context,
        fortune_seed=fortune_seed,
    )

    try:
        content = await _call_chat_completions(
            settings,
            prompt_module.SYSTEM_PROMPT,
            user_msg,
        )
    except Exception:
        logger.exception(
            "Guide LLM failed: sign=%s category=%s date=%s",
            sign_slug, category.value, date_str,
        )
        return None

    if not content or len(content) < 100:
        logger.warning(
            "Guide content too short: sign=%s category=%s len=%d",
            sign_slug, category.value, len(content or ""),
        )
        return None

    content = _compliance_filter(content)

    title_str = _extract_title(content, category)
    tb = _extract_transit_basis(sky_context)
    content_ir = markdown_to_ir(
        content,
        {"title": title_str, "transit_basis": tb},
    )

    return DailyGuide(
        sign=sign_slug,
        category=category,
        guide_date=fortune_date,
        title=title_str,
        preview=_extract_preview(content),
        content=content,
        content_ir=content_ir,
        transit_basis=tb,
    )


async def generate_guide_for_sign(
    settings: Settings,
    sign_slug: str,
    fortune_date: date,
    sky_context: str,
    fortune_data: dict[str, Any],
    *,
    categories: set[GuideCategory] | None = None,
) -> list[DailyGuide]:
    meta = get_sign_meta(sign_slug)
    if not meta:
        return []
    sign_cn = meta["sign_cn"]
    date_str = fortune_date.isoformat()

    cat_list = list(_CATEGORY_PROMPTS.keys())
    if categories is not None:
        cat_list = [c for c in cat_list if c in categories]

    if not cat_list:
        return []

    tasks = [
        _generate_one_category(
            settings, sign_slug, fortune_date, sky_context, fortune_data,
            sign_cn, date_str, cat,
        )
        for cat in cat_list
    ]
    results = await asyncio.gather(*tasks, return_exceptions=True)
    guides: list[DailyGuide] = []
    for cat, res in zip(cat_list, results, strict=True):
        if isinstance(res, Exception):
            logger.error(
                "Guide gather failed: sign=%s category=%s",
                sign_slug,
                cat.value,
                exc_info=res,
            )
            continue
        if res is not None:
            guides.append(res)
    return guides


async def generate_all_guides_for_date(
    db: AsyncSession,
    fortune_date: date,
    *,
    force: bool = False,
) -> int:
    settings = get_settings()
    if not force and not settings.guide_generation_enabled:
        logger.info("Guide generation disabled, skipping")
        return 0

    sky_context = compute_ephemeris_snapshot_line(fortune_date)
    total_saved = 0

    all_cats = set(_CATEGORY_PROMPTS.keys())

    for sign_meta in list_all_signs():
        slug = sign_meta["sign"]

        cat_result = await db.execute(
            select(DailyGuide.category).where(
                DailyGuide.sign == slug,
                DailyGuide.guide_date == fortune_date,
            )
        )
        have: set[GuideCategory] = set(cat_result.scalars().all())
        missing = all_cats - have
        if not missing:
            logger.debug("Guides complete for sign=%s date=%s, skipping", slug, fortune_date)
            continue

        row = await db.execute(
            select(DailyFortune).where(
                DailyFortune.sign == slug,
                DailyFortune.fortune_date == fortune_date,
            )
        )
        fortune_row = row.scalar_one_or_none()
        fortune_data: dict[str, Any] = fortune_row.content if fortune_row else {}

        try:
            guides = await generate_guide_for_sign(
                settings, slug, fortune_date, sky_context, fortune_data, categories=missing,
            )
        except Exception:
            logger.exception("Guide generation failed entirely for sign=%s", slug)
            continue

        for guide in guides:
            db.add(guide)
            total_saved += 1

        await db.flush()
        await db.commit()
        logger.info("Generated %d guides for sign=%s date=%s", len(guides), slug, fortune_date)

    return total_saved
