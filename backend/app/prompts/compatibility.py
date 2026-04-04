"""Compatibility: user input — system prompt lives in 百炼智能体."""

from __future__ import annotations

from typing import TYPE_CHECKING, Optional

if TYPE_CHECKING:
    from app.services.astro_models import NatalChartData, SynastryData

from app.prompts.chart_formatter import format_natal_chart_for_prompt, format_synastry_for_prompt


def build_compatibility_user_input(
    name1: str,
    birth_date1: str,
    sign1: str,
    sign1_cn: str,
    name2: str,
    birth_date2: str,
    sign2: str,
    sign2_cn: str,
    natal1: Optional["NatalChartData"] = None,
    natal2: Optional["NatalChartData"] = None,
    synastry: Optional["SynastryData"] = None,
) -> str:
    a = name1 or "A"
    b = name2 or "B"
    legacy = (
        f"用户A：{a}，出生日期 {birth_date1}，{sign1_cn}({sign1})；"
        f"用户B：{b}，出生日期 {birth_date2}，{sign2_cn}({sign2})"
    )
    blocks: list[str] = []
    if natal1 is not None:
        blocks.append("【用户A 星盘】\n" + format_natal_chart_for_prompt(natal1))
    if natal2 is not None:
        blocks.append("【用户B 星盘】\n" + format_natal_chart_for_prompt(natal2))
    if synastry is not None:
        blocks.append(format_synastry_for_prompt(synastry, a, b))
    if blocks:
        return "\n\n".join(blocks) + "\n\n【摘要】\n" + legacy
    return legacy
