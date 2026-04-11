"""
12 张「代表本命盘」行运切片：用于对比谁今日行运相位更密（Swiss Ephemeris / kerykeion）。
未安装 kerykeion 或计算失败时返回空列表，不抛异常。
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import date
from typing import Any, Dict, List, Optional

from app.services.astro_service import compute_natal_chart, compute_transits
from app.utils.zodiac_calc import list_all_signs


# 每个太阳星座取区间内中点日（2000 年）生成代表盘，北京默认经纬由 resolve_city 处理
_REP_BIRTH: Dict[str, date] = {
    "capricorn": date(2000, 1, 5),
    "aquarius": date(2000, 2, 5),
    "pisces": date(2000, 3, 5),
    "aries": date(2000, 4, 5),
    "taurus": date(2000, 5, 5),
    "gemini": date(2000, 6, 5),
    "cancer": date(2000, 7, 5),
    "leo": date(2000, 8, 5),
    "virgo": date(2000, 9, 5),
    "libra": date(2000, 10, 5),
    "scorpio": date(2000, 11, 5),
    "sagittarius": date(2000, 12, 5),
}


@dataclass
class TransitSlice:
    sign: str
    sign_cn: str
    aspect_count: int
    tight_score: float
    top_aspect_line: str
    mercury_retrograde: Optional[bool]
    moon_phase: Optional[str]
    engine_ref: Dict[str, Any]


def _aspect_line(a: Any) -> str:
    return (
        f"{a.natal_planet} {a.aspect_type_cn} 行运{a.transit_planet}，容许度{a.orb:.2f}°"
    )


def compute_twelve_transit_slice(transit_d: date) -> List[TransitSlice]:
    out: list[TransitSlice] = []
    for meta in list_all_signs():
        slug = meta["sign"].lower()
        cn = meta["sign_cn"]
        bd = _REP_BIRTH.get(slug)
        if not bd:
            continue
        try:
            natal = compute_natal_chart(bd, birth_place_name="北京")
            tr = compute_transits(natal, transit_d)
        except Exception:
            continue

        aspects = tr.aspects_to_natal or []
        tight = 0.0
        for a in aspects[:8]:
            tight += max(0.0, 10.0 - float(a.orb))
        top = aspects[0] if aspects else None
        top_line = _aspect_line(top) if top else "当日主要行运相位：暂无可列（历表）"

        out.append(
            TransitSlice(
                sign=slug,
                sign_cn=cn,
                aspect_count=len(aspects),
                tight_score=round(tight, 2),
                top_aspect_line=top_line,
                mercury_retrograde=tr.mercury_retrograde,
                moon_phase=tr.moon_phase_name,
                engine_ref={
                    "transit_date": tr.transit_date,
                    "transit_time": tr.transit_time,
                    "location_label": tr.location_label,
                    "aspects_sample": [
                        {
                            "natal_planet": x.natal_planet,
                            "transit_planet": x.transit_planet,
                            "aspect_type_cn": x.aspect_type_cn,
                            "orb": x.orb,
                        }
                        for x in aspects[:5]
                    ],
                },
            )
        )
    return out


def ephemeris_one_liner(d: date) -> str:
    try:
        from app.services.astro_service import compute_ephemeris_snapshot_line

        return compute_ephemeris_snapshot_line(d)
    except Exception:
        return "当日天象：历表暂不可用。"
