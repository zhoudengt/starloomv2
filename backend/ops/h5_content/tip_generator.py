"""Generate 4 daily practical tips (career / wealth / relationship / energy)
based on real transit data and optional LLM enrichment.

Each tip follows the pattern:
  [transit fact] -> [actionable advice] -> [CTA product mapping]
"""

from __future__ import annotations

import json
import logging
import re
from dataclasses import dataclass
from datetime import date
from typing import Any, Dict, List, Optional

from app.config import get_settings
from app.services.llm_service import BailianApplicationService

from ops.config import get_ops_settings
from ops.copy.compliance import strip_banned
from ops.signals.astro_slice import compute_twelve_transit_slice, ephemeris_one_liner

logger = logging.getLogger(__name__)

CATEGORY_CTA_MAP: Dict[str, str] = {
    "career": "personality_career",
    "wealth": "annual",
    "relationship": "compatibility",
    "energy": "season_pass",
}

CATEGORY_CN: Dict[str, str] = {
    "career": "职场",
    "wealth": "财务",
    "relationship": "人际沟通",
    "energy": "情绪与休息",
}


@dataclass
class GeneratedTip:
    category: str
    tip_text: str
    transit_basis: str
    cta_product: str


_SYSTEM_PROMPT = """\
你是 StarLoom 星座实用指南编辑。根据给定的当日天象数据，为四个生活领域各写一条实用建议。

要求：
1. 每条建议 40-80 字，必须包含一个具体可执行的行动建议
2. 必须引用给定天象事实（行星、相位），不得编造新数据
3. 语气：温和务实，像朋友提醒，不要命令式
4. 禁止使用「算命」「占卜」「必须」「一定会」等绝对化用语
5. 返回严格 JSON 格式

返回格式（JSON数组，4个对象）：
[
  {"category": "career", "tip": "...", "transit_basis": "引用的天象事实"},
  {"category": "wealth", "tip": "...", "transit_basis": "..."},
  {"category": "relationship", "tip": "...", "transit_basis": "..."},
  {"category": "energy", "tip": "...", "transit_basis": "..."}
]
"""


def _build_transit_context(d: date) -> str:
    parts: list[str] = []
    ep = ephemeris_one_liner(d)
    if ep:
        parts.append(f"天象概要：{ep}")

    transits = compute_twelve_transit_slice(d)
    if transits:
        tight_aspects: list[str] = []
        for slug, ts in transits.items():
            for asp in (ts.get("tight_aspects") or []):
                name = asp.get("aspect_name", "")
                p1 = asp.get("transit_planet", "")
                p2 = asp.get("natal_planet", "")
                if name and p1:
                    tight_aspects.append(f"{p1}{name}{p2}（{slug}）")
        if tight_aspects:
            parts.append("紧密相位：" + "；".join(tight_aspects[:8]))

    return "\n".join(parts) if parts else "今日无特殊紧密相位记录。"


def _extract_json_array(text: str) -> Optional[List[Dict[str, Any]]]:
    match = re.search(r'\[.*\]', text, re.DOTALL)
    if not match:
        return None
    try:
        arr = json.loads(match.group())
        if isinstance(arr, list) and len(arr) >= 4:
            return arr
        return None
    except json.JSONDecodeError:
        return None


def _fallback_tips(d: date) -> List[GeneratedTip]:
    ep = ephemeris_one_liner(d) or "行星照常运行"
    return [
        GeneratedTip(
            category="career",
            tip_text=f"今日天象：{ep}。适合先梳理优先级再行动，避免同时开启多个新项目。",
            transit_basis=ep,
            cta_product="personality_career",
        ),
        GeneratedTip(
            category="wealth",
            tip_text=f"今日天象：{ep}。大额支出前多对比，小额可适当放松——先列清单再打开购物车。",
            transit_basis=ep,
            cta_product="annual",
        ),
        GeneratedTip(
            category="relationship",
            tip_text=f"今日天象：{ep}。表达分歧时试试「我感觉…」句式，比「你总是…」更容易被接受。",
            transit_basis=ep,
            cta_product="compatibility",
        ),
        GeneratedTip(
            category="energy",
            tip_text=f"今日天象：{ep}。如果下午感到低能量，10 分钟的散步比咖啡更有效——试试看。",
            transit_basis=ep,
            cta_product="season_pass",
        ),
    ]


async def generate_daily_tips(d: date) -> List[GeneratedTip]:
    ops = get_ops_settings()
    settings = get_settings()

    if not ops.llm_enabled or not ops.bailian_app_id.strip() or not settings.bailian_api_key:
        logger.info("LLM not configured for tips, using template fallback")
        return _fallback_tips(d)

    transit_ctx = _build_transit_context(d)
    user_input = f"日期：{d.isoformat()}\n{transit_ctx}"

    try:
        svc = BailianApplicationService(settings, ops.bailian_app_id.strip())
        raw = await svc.generate(
            f"{_SYSTEM_PROMPT}\n\n{user_input}"
        )
        arr = _extract_json_array(raw)
        if not arr:
            logger.warning("LLM tips response not valid JSON array, using fallback")
            return _fallback_tips(d)

        cal_ctx = {}
        try:
            from ops.data_sources.calendar_config import calendar_for_date
            from ops.config import load_calendar_yaml_path
            cal_ctx = calendar_for_date(load_calendar_yaml_path(), d)
        except Exception:
            pass
        banned = list(cal_ctx.get("banned_words") or [])

        tips: list[GeneratedTip] = []
        for item in arr[:4]:
            cat = item.get("category", "")
            if cat not in CATEGORY_CTA_MAP:
                continue
            text = strip_banned(str(item.get("tip", "")), banned)
            tips.append(
                GeneratedTip(
                    category=cat,
                    tip_text=text,
                    transit_basis=str(item.get("transit_basis", "")),
                    cta_product=CATEGORY_CTA_MAP[cat],
                )
            )
        if len(tips) < 4:
            logger.warning("LLM returned < 4 valid tips, padding with fallback")
            fb = _fallback_tips(d)
            existing_cats = {t.category for t in tips}
            for ft in fb:
                if ft.category not in existing_cats:
                    tips.append(ft)

        return tips[:4]

    except Exception:
        logger.exception("LLM tip generation failed, using fallback")
        return _fallback_tips(d)
