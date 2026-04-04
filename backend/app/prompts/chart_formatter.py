"""Format computed natal / transit / synastry data for LLM prompts."""

from __future__ import annotations

from app.services.astro_models import NatalChartData, SynastryData, TransitData


def _deg_str(deg: float) -> str:
    d = int(deg)
    m = int(round((deg - d) * 60))
    if m >= 60:
        d += 1
        m = 0
    return f"{d}°{m:02d}′"


def format_natal_chart_for_prompt(chart: NatalChartData) -> str:
    lines: list[str] = ["=== 用户出生星盘（天文历表计算，热带黄道）==="]
    loc = chart.location_label or "未标注"
    lines.append(f"出生日期：{chart.birth_date}" + (f"，时间：{chart.birth_time}" if chart.birth_time else "，时间：未提供（行星以当日正午近似）"))
    lines.append(f"地点：{loc}，经纬：{chart.lon:.4f}°E {chart.lat:.4f}°N，时区：{chart.tz_str}")
    if chart.precision_note:
        lines.append(f"精度说明：{chart.precision_note}")

    lines.append("\n【行星位置】")
    for p in chart.planets:
        hx = f"，第{p.house}宫" if p.house is not None else ""
        rx = "，逆行" if p.retrograde else ""
        lines.append(
            f"- {p.name}：{p.sign_cn} {_deg_str(p.degree)}（{p.sign_en}）{hx}{rx}"
        )

    if chart.ascendant:
        lines.append(
            f"\n【上升点】{chart.ascendant.sign_cn} {_deg_str(chart.ascendant.degree)}"
        )
    if chart.mc:
        lines.append(f"【中天 MC】{chart.mc.sign_cn} {_deg_str(chart.mc.degree)}")

    if chart.houses:
        lines.append("\n【宫位头（Placidus）】")
        for h in chart.houses:
            lines.append(f"- 第{h.house}宫：{h.sign_cn} {_deg_str(h.degree)}")

    if chart.aspects:
        lines.append("\n【主要相位（容许度≤8°）】")
        for a in chart.aspects:
            app = "，入相位" if a.applying is True else ("，出相位" if a.applying is False else "")
            lines.append(
                f"- {a.planet1} {a.aspect_type_cn} {a.planet2}，容许 {a.orb:.2f}°{app}"
            )

    if chart.element_distribution:
        e = chart.element_distribution
        lines.append(
            f"\n【元素权重】火{e.get('火象',0):.1f} 土{e.get('土象',0):.1f} "
            f"风{e.get('风象',0):.1f} 水{e.get('水象',0):.1f} → 主导：{chart.dominant_element}"
        )
    if chart.modality_distribution:
        m = chart.modality_distribution
        lines.append(
            f"【模式权重】基本{m.get('基本',0):.1f} 固定{m.get('固定',0):.1f} 变动{m.get('变动',0):.1f} "
            f"→ 主导：{chart.dominant_modality}"
        )

    if chart.lunar_phase_name:
        em = chart.lunar_phase_emoji or ""
        lines.append(f"\n【出生时段月相参考】{em} {chart.lunar_phase_name}")

    return "\n".join(lines)


def format_transit_for_prompt(tr: TransitData) -> str:
    lines: list[str] = ["=== 行运分析（相对本命盘）==="]
    lines.append(f"行运日期：{tr.transit_date} {tr.transit_time}，地点：{tr.location_label or '默认'}")
    if tr.natal_sun_summary:
        lines.append(f"本命太阳：{tr.natal_sun_summary}")

    lines.append("\n【当日行运行星位置】")
    for p in tr.transit_planets:
        rx = " 逆行" if p.retrograde else ""
        lines.append(f"- {p.name}：{p.sign_cn} {_deg_str(p.degree)}{rx}")

    if tr.aspects_to_natal:
        lines.append("\n【行运与本命主要相位】")
        for a in tr.aspects_to_natal:
            mov = f"，{a.movement}" if a.movement else ""
            lines.append(
                f"- 行运{a.transit_planet} {a.aspect_type_cn} 本命{a.natal_planet}，容许 {a.orb:.2f}°{mov}"
            )

    if tr.mercury_retrograde is not None:
        lines.append(f"\n【水星状态】{'逆行' if tr.mercury_retrograde else '顺行'}")
    if tr.moon_phase_name:
        em = tr.moon_phase_emoji or ""
        lines.append(f"【月相】{em} {tr.moon_phase_name}")

    return "\n".join(lines)


def format_synastry_for_prompt(
    syn: SynastryData,
    name1: str,
    name2: str,
) -> str:
    lines: list[str] = ["=== 双人星盘互动（天文相位）==="]
    if syn.relationship_score is not None:
        lbl = syn.relationship_label or ""
        lines.append(f"关系强度指数（库内置算法）：{syn.relationship_score} / 重要度：{lbl}")
    if syn.score_highlights:
        lines.append("亮点相位：" + "；".join(syn.score_highlights[:5]))
    lines.append("\n【双方主要跨盘相位（容许度≤8°）】")
    for a in syn.aspects:
        lines.append(
            f"- {a.planet1}（{name1 or 'A'}） {a.aspect_type_cn} {a.planet2}（{name2 or 'B'}），容许 {a.orb:.2f}°"
        )
    return "\n".join(lines)


def format_annual_highlights_for_prompt(year: int, highlights: list[str]) -> str:
    lines = [
        f"=== {year} 年行运快照（季度采样，天文历表）===",
        "以下为本命盘与当年若干时点行运相位的摘要，请据此展开年度节奏参考（娱乐向）：",
    ]
    for h in highlights:
        lines.append(f"- {h}")
    return "\n".join(lines)
