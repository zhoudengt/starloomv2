"""Daily: user input — system prompt lives in 百炼智能体."""

from __future__ import annotations

from typing import TYPE_CHECKING, Optional

if TYPE_CHECKING:
    from app.services.astro_models import NatalChartData, TransitData

from app.prompts.chart_formatter import format_natal_chart_for_prompt, format_transit_for_prompt


def build_daily_user_input(sign_cn: str, fortune_date: str) -> str:
    return f"{sign_cn} {fortune_date}"


def build_daily_sign_ephemeris_stub(sign_cn: str, fortune_date: str, sky_note: str) -> str:
    """Public daily: add real-sky snapshot line (computed upstream)."""
    return f"{sign_cn} {fortune_date}\n【当日天象摘要】{sky_note}"


def build_daily_personal_user_input(
    natal_chart: "NatalChartData",
    transit: "TransitData",
) -> str:
    return (
        format_natal_chart_for_prompt(natal_chart)
        + "\n\n"
        + format_transit_for_prompt(transit)
    )
