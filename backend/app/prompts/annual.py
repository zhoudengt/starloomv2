"""Annual report: user input — system prompt lives in 百炼智能体."""

from __future__ import annotations

from typing import TYPE_CHECKING, Optional

if TYPE_CHECKING:
    from app.services.astro_models import NatalChartData

from app.prompts.chart_formatter import format_annual_highlights_for_prompt, format_natal_chart_for_prompt


def build_annual_user_input(
    sun_sign: str,
    sun_sign_cn: str,
    year: int,
    natal_chart: Optional["NatalChartData"] = None,
    annual_highlights: Optional[list[str]] = None,
) -> str:
    legacy = f"{sun_sign_cn}({sun_sign}) {year}年"
    if natal_chart is not None:
        chart_block = format_natal_chart_for_prompt(natal_chart)
        hl = (
            "\n\n" + format_annual_highlights_for_prompt(year, annual_highlights or [])
            if annual_highlights
            else ""
        )
        return chart_block + hl + f"\n\n【目标年度】{legacy}"
    return legacy
