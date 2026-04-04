"""Personality report: user input — system prompt lives in 百炼智能体."""

from __future__ import annotations

from typing import TYPE_CHECKING, Optional

if TYPE_CHECKING:
    from app.services.astro_models import NatalChartData

from app.prompts.chart_formatter import format_natal_chart_for_prompt


def build_personality_user_input(
    birth_date: str,
    sun_sign: str,
    sun_sign_cn: str,
    birth_time: str | None = None,
    gender: str | None = None,
    natal_chart: Optional["NatalChartData"] = None,
) -> str:
    parts = [f"出生日期：{birth_date}", f"星座：{sun_sign_cn}({sun_sign})"]
    if birth_time:
        parts.append(f"出生时间：{birth_time}")
    if gender:
        parts.append(f"性别：{gender}")
    legacy = "，".join(parts)
    if natal_chart is not None:
        return format_natal_chart_for_prompt(natal_chart) + "\n\n【摘要行】\n" + legacy
    return legacy
