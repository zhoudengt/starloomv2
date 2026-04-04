"""Date to sun sign mapping and static sign metadata (月日查表，与热带黄道多数日期一致).

完整行星与宫位计算见 `app.services.astro_service`（kerykeion / Swiss Ephemeris）。
"""

from datetime import date, datetime
from typing import Any, Dict, List, Optional, Tuple

# (month, day) inclusive ranges for each sign (year-agnostic)
_SIGN_RANGES: List[Tuple[str, str, str, Tuple[Tuple[int, int], Tuple[int, int]]]] = [
    ("capricorn", "摩羯座", "♑", ((12, 22), (1, 19))),
    ("aquarius", "水瓶座", "♒", ((1, 20), (2, 18))),
    ("pisces", "双鱼座", "♓", ((2, 19), (3, 20))),
    ("aries", "白羊座", "♈", ((3, 21), (4, 19))),
    ("taurus", "金牛座", "♉", ((4, 20), (5, 20))),
    ("gemini", "双子座", "♊", ((5, 21), (6, 21))),
    ("cancer", "巨蟹座", "♋", ((6, 22), (7, 22))),
    ("leo", "狮子座", "♌", ((7, 23), (8, 22))),
    ("virgo", "处女座", "♍", ((8, 23), (9, 22))),
    ("libra", "天秤座", "♎", ((9, 23), (10, 23))),
    ("scorpio", "天蝎座", "♏", ((10, 24), (11, 22))),
    ("sagittarius", "射手座", "♐", ((11, 23), (12, 21))),
]


def _in_range(d: date, start: Tuple[int, int], end: Tuple[int, int]) -> bool:
    """Check if month-day falls in [start, end] crossing year boundary if needed."""
    md = (d.month, d.day)
    if start <= end:
        return start <= md <= end
    # Capricorn: Dec 22 - Jan 19
    return md >= start or md <= end


def sun_sign_from_date(birth: date) -> str:
    """Return English slug for sun sign from birth date."""
    md = (birth.month, birth.day)
    for slug, _cn, _sym, (start, end) in _SIGN_RANGES:
        if _in_range(birth, start, end):
            return slug
    return "capricorn"


def get_sign_meta(slug: str) -> Optional[Dict[str, Any]]:
    for s in _SIGN_RANGES:
        if s[0] == slug.lower():
            return {
                "sign": s[0],
                "sign_cn": s[1],
                "symbol": s[2],
                "date_range": _format_range(s[3]),
                "element": _element_for(s[0]),
            }
    return None


def _format_range(rng: Tuple[Tuple[int, int], Tuple[int, int]]) -> str:
    a, b = rng
    return f"{a[0]:02d}/{a[1]:02d} - {b[0]:02d}/{b[1]:02d}"


def _element_for(slug: str) -> str:
    fire = {"aries", "leo", "sagittarius"}
    earth = {"taurus", "virgo", "capricorn"}
    air = {"gemini", "libra", "aquarius"}
    water = {"cancer", "scorpio", "pisces"}
    if slug in fire:
        return "火象"
    if slug in earth:
        return "土象"
    if slug in air:
        return "风象"
    if slug in water:
        return "水象"
    return "未知"


def list_all_signs() -> List[Dict[str, Any]]:
    out: List[Dict[str, Any]] = []
    for slug, cn, sym, rng in _SIGN_RANGES:
        out.append(
            {
                "sign": slug,
                "sign_cn": cn,
                "symbol": sym,
                "date_range": _format_range(rng),
                "element": _element_for(slug),
            }
        )
    return out


def parse_birth_date(s: str) -> date:
    """Parse user-supplied birth date; supports common separators (API / forms)."""
    raw = (s or "").strip()
    if not raw:
        raise ValueError("empty birth date")
    for fmt in ("%Y-%m-%d", "%Y/%m/%d", "%Y.%m.%d"):
        try:
            return datetime.strptime(raw, fmt).date()
        except ValueError:
            continue
    raise ValueError(f"invalid birth date: {raw!r} (use YYYY-MM-DD)")


def parse_birth_date_http(s: str) -> date:
    """For FastAPI routes: invalid dates become 422 instead of 500."""
    try:
        return parse_birth_date(s)
    except ValueError as e:
        from fastapi import HTTPException

        raise HTTPException(status_code=422, detail=str(e)) from e
