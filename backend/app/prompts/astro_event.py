"""Astronomical event themed reports — 天文事件分析参考（非占卜）."""

from __future__ import annotations

from typing import TYPE_CHECKING, Optional

if TYPE_CHECKING:
    from app.services.astro_models import NatalChartData

from app.prompts.chart_formatter import format_natal_chart_for_prompt

EVENT_LABELS: dict[str, str] = {
    "mercury_retrograde": "水星逆行期间：沟通、出行与计划复盘的天文节奏参考",
    "eclipse": "日月食周期：能量节奏与自我觉察的参考提示",
    "solstice": "至日/分日：季节转换期的生活节奏参考",
}


def build_astro_event_user_input(
    event_key: str,
    birth_date: str,
    sun_sign: str,
    sun_sign_cn: str,
    natal_chart: Optional["NatalChartData"] = None,
) -> str:
    theme = EVENT_LABELS.get(event_key, EVENT_LABELS["mercury_retrograde"])
    tail = (
        f"【天文事件主题】{theme}\n"
        f"用户出生日期：{birth_date}，太阳星座：{sun_sign_cn}({sun_sign})"
    )
    if natal_chart is not None:
        return format_natal_chart_for_prompt(natal_chart) + "\n\n" + tail
    return tail
