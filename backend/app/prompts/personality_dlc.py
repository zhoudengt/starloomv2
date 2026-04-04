"""Personality report DLC packs — prefix tags for 百炼 / Coze 智能体上下文."""

from __future__ import annotations

from typing import TYPE_CHECKING, Optional

if TYPE_CHECKING:
    from app.services.astro_models import NatalChartData

from app.prompts.chart_formatter import format_natal_chart_for_prompt


def build_personality_dlc_user_input(
    pack: str,
    birth_date: str,
    sun_sign: str,
    sun_sign_cn: str,
    birth_time: str | None = None,
    gender: str | None = None,
    natal_chart: Optional["NatalChartData"] = None,
) -> str:
    labels = {
        "career": "【扩展包：职场深潜】",
        "love": "【扩展包：恋爱深潜】",
        "growth": "【扩展包：成长深潜】",
    }
    head = labels.get(pack, labels["career"])
    parts = [head, f"出生日期：{birth_date}", f"星座：{sun_sign_cn}({sun_sign})"]
    if birth_time:
        parts.append(f"出生时间：{birth_time}")
    if gender:
        parts.append(f"性别：{gender}")
    legacy = "，".join(parts)
    if natal_chart is not None:
        return format_natal_chart_for_prompt(natal_chart) + "\n\n" + legacy
    return legacy
