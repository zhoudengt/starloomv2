"""Natal / transit / synastry computation via kerykeion (Swiss Ephemeris)."""

from __future__ import annotations

import hashlib
import logging
from datetime import date
from typing import Any, Optional

from app.services.astro_models import (
    AnnualTransitSummary,
    Aspect,
    HouseCusp,
    NatalChartData,
    PlanetPosition,
    SynastryData,
    TransitAspect,
    TransitData,
)
from app.utils.city_coordinates import (
    DEFAULT_LAT,
    DEFAULT_LON,
    DEFAULT_TZ,
    resolve_city,
)

logger = logging.getLogger(__name__)

try:
    from kerykeion import AstrologicalSubjectFactory
    from kerykeion.aspects import AspectsFactory
    from kerykeion.chart_data_factory import ChartDataFactory
except ImportError as e:  # pragma: no cover
    AstrologicalSubjectFactory = None  # type: ignore[misc, assignment]
    AspectsFactory = None  # type: ignore[misc, assignment]
    ChartDataFactory = None  # type: ignore[misc, assignment]
    _IMPORT_ERROR = e
else:
    _IMPORT_ERROR = None

# kerykeion 3-letter sign -> slug + Chinese
_KR_SIGN_TO_EN: dict[str, str] = {
    "Ari": "aries",
    "Tau": "taurus",
    "Gem": "gemini",
    "Can": "cancer",
    "Leo": "leo",
    "Vir": "virgo",
    "Lib": "libra",
    "Sco": "scorpio",
    "Sag": "sagittarius",
    "Cap": "capricorn",
    "Aqu": "aquarius",
    "Pis": "pisces",
}

_KR_SIGN_TO_CN: dict[str, str] = {
    "Ari": "白羊座",
    "Tau": "金牛座",
    "Gem": "双子座",
    "Can": "巨蟹座",
    "Leo": "狮子座",
    "Vir": "处女座",
    "Lib": "天秤座",
    "Sco": "天蝎座",
    "Sag": "射手座",
    "Cap": "摩羯座",
    "Aqu": "水瓶座",
    "Pis": "双鱼座",
}

_HOUSE_NAME_TO_INT: dict[str, int] = {
    "First_House": 1,
    "Second_House": 2,
    "Third_House": 3,
    "Fourth_House": 4,
    "Fifth_House": 5,
    "Sixth_House": 6,
    "Seventh_House": 7,
    "Eighth_House": 8,
    "Ninth_House": 9,
    "Tenth_House": 10,
    "Eleventh_House": 11,
    "Twelfth_House": 12,
}

_PLANET_LABELS: dict[str, str] = {
    "Sun": "太阳",
    "Moon": "月亮",
    "Mercury": "水星",
    "Venus": "金星",
    "Mars": "火星",
    "Jupiter": "木星",
    "Saturn": "土星",
    "Uranus": "天王星",
    "Neptune": "海王星",
    "Pluto": "冥王星",
    "Mean_Node": "北交点(平均)",
    "True_North_Lunar_Node": "北交点",
    "True_South_Lunar_Node": "南交点",
    "Chiron": "凯龙",
    "Ascendant": "上升",
    "Medium_Coeli": "中天",
}

_ASPECT_CN: dict[str, str] = {
    "conjunction": "合",
    "opposition": "冲",
    "trine": "三分",
    "square": "四分",
    "sextile": "六分",
    "quincunx": "梅花相",
    "semisextile": "半六分",
    "semisquare": "半四分",
    "sesquiquadrate": "八分三相",
    "quintile": "五分",
    "biquintile": "倍五分",
    "novile": "九分",
}

_MAJOR_ASPECTS = frozenset({"conjunction", "opposition", "trine", "square", "sextile"})

_NATAL_POINTS = [
    ("sun", "Sun"),
    ("moon", "Moon"),
    ("mercury", "Mercury"),
    ("venus", "Venus"),
    ("mars", "Mars"),
    ("jupiter", "Jupiter"),
    ("saturn", "Saturn"),
    ("uranus", "Uranus"),
    ("neptune", "Neptune"),
    ("pluto", "Pluto"),
    ("true_north_lunar_node", "True_North_Lunar_Node"),
]


def _ensure_kerykeion() -> None:
    if AstrologicalSubjectFactory is None or _IMPORT_ERROR:
        raise RuntimeError("kerykeion 未安装或不可用") from _IMPORT_ERROR


def _sign_from_kr(kr: str) -> tuple[str, str]:
    return _KR_SIGN_TO_EN.get(kr, "aries"), _KR_SIGN_TO_CN.get(kr, "白羊座")


def _house_to_int(house_raw: Any, has_houses: bool) -> Optional[int]:
    if not has_houses or house_raw is None:
        return None
    s = str(house_raw)
    return _HOUSE_NAME_TO_INT.get(s)


def _point_to_position(
    point: Any,
    label_en: str,
    has_houses: bool,
) -> Optional[PlanetPosition]:
    if point is None:
        return None
    sign_en, sign_cn = _sign_from_kr(point.sign)
    pos = float(point.position)
    abs_pos = float(point.abs_pos)
    retro = bool(point.retrograde) if point.retrograde is not None else False
    house = _house_to_int(point.house, has_houses)
    cn = _PLANET_LABELS.get(label_en, label_en)
    return PlanetPosition(
        name=cn,
        name_en=label_en,
        sign_cn=sign_cn,
        sign_en=sign_en,
        degree=pos,
        abs_degree=abs_pos,
        retrograde=retro,
        house=house,
    )


def _subject_to_natal_chart(
    subject: Any,
    birth_date: date,
    birth_time_str: Optional[str],
    has_birth_time: bool,
    location_label: str,
    lat: float,
    lon: float,
    tz_str: str,
    precision_note: Optional[str],
) -> NatalChartData:
    planets: list[PlanetPosition] = []
    for attr, label_en in _NATAL_POINTS:
        pt = getattr(subject, attr, None)
        p = _point_to_position(pt, label_en, has_houses=has_birth_time)
        if p:
            planets.append(p)

    asc = _point_to_position(getattr(subject, "ascendant", None), "Ascendant", has_houses=has_birth_time)
    mc = _point_to_position(getattr(subject, "medium_coeli", None), "Medium_Coeli", has_houses=has_birth_time)

    houses: Optional[list[HouseCusp]] = None
    if has_birth_time:
        houses = []
        _hattrs = [
            "first_house",
            "second_house",
            "third_house",
            "fourth_house",
            "fifth_house",
            "sixth_house",
            "seventh_house",
            "eighth_house",
            "ninth_house",
            "tenth_house",
            "eleventh_house",
            "twelfth_house",
        ]
        for i, attr in enumerate(_hattrs, start=1):
            hp = getattr(subject, attr, None)
            if hp is None:
                continue
            se, sc = _sign_from_kr(hp.sign)
            houses.append(HouseCusp(house=i, sign_cn=sc, sign_en=se, degree=float(hp.position)))

    natal = ChartDataFactory.create_natal_chart_data(subject)
    ed: dict[str, float] = {}
    qd: dict[str, float] = {}
    if natal.element_distribution:
        e = natal.element_distribution
        ed = {
            "火象": float(getattr(e, "fire", 0) or 0),
            "土象": float(getattr(e, "earth", 0) or 0),
            "风象": float(getattr(e, "air", 0) or 0),
            "水象": float(getattr(e, "water", 0) or 0),
        }
    if natal.quality_distribution:
        q = natal.quality_distribution
        qd = {
            "基本": float(getattr(q, "cardinal", 0) or 0),
            "固定": float(getattr(q, "fixed", 0) or 0),
            "变动": float(getattr(q, "mutable", 0) or 0),
        }

    dom_el = max(ed, key=ed.get) if ed else ""
    dom_mod = max(qd, key=qd.get) if qd else ""

    aspects: list[Aspect] = []
    ad = AspectsFactory.single_chart_aspects(subject)
    for a in ad.aspects:
        if a.aspect not in _MAJOR_ASPECTS:
            continue
        if float(a.orbit) > 8.0:
            continue
        app = None
        if getattr(a, "aspect_movement", None):
            app = a.aspect_movement == "Applying"
        aspects.append(
            Aspect(
                planet1=_PLANET_LABELS.get(a.p1_name, a.p1_name),
                planet2=_PLANET_LABELS.get(a.p2_name, a.p2_name),
                aspect_type=a.aspect,
                aspect_type_cn=_ASPECT_CN.get(a.aspect, a.aspect),
                aspect_degree=int(a.aspect_degrees or 0),
                orb=float(a.orbit),
                applying=app,
            )
        )
    aspects.sort(key=lambda x: x.orb)
    aspects = aspects[:16]

    lp_name = lp_emoji = None
    lp = getattr(subject, "lunar_phase", None)
    if lp is not None:
        lp_name = getattr(lp, "moon_phase_name", None)
        lp_emoji = getattr(lp, "moon_emoji", None)

    return NatalChartData(
        birth_date=birth_date.isoformat(),
        birth_time=birth_time_str,
        location_label=location_label,
        lat=lat,
        lon=lon,
        tz_str=tz_str,
        has_birth_time=has_birth_time,
        precision_note=precision_note,
        planets=planets,
        ascendant=asc,
        mc=mc,
        houses=houses,
        aspects=aspects,
        element_distribution=ed,
        modality_distribution=qd,
        dominant_element=dom_el,
        dominant_modality=dom_mod,
        lunar_phase_name=lp_name,
        lunar_phase_emoji=lp_emoji,
    )


def _parse_birth_time(s: Optional[str]) -> tuple[int, int, bool]:
    if not s or not str(s).strip():
        return 12, 0, False
    parts = str(s).strip().split(":")
    try:
        h = int(parts[0]) % 24
        m = int(parts[1]) % 60 if len(parts) > 1 else 0
        return h, m, True
    except (ValueError, IndexError):
        return 12, 0, False


def compute_natal_chart(
    birth_date: date,
    birth_time: Optional[str] = None,
    birth_place_name: Optional[str] = None,
    lat: Optional[float] = None,
    lon: Optional[float] = None,
    tz_str: Optional[str] = None,
) -> NatalChartData:
    """
    Full natal chart. Without birth_time: noon local, houses/ascendant omitted (unreliable).
    """
    _ensure_kerykeion()
    assert AstrologicalSubjectFactory is not None and ChartDataFactory is not None

    hour, minute, has_bt = _parse_birth_time(birth_time)
    if not has_bt:
        hour, minute = 12, 0
        precision = "未提供出生时间：宫位与上升未纳入；行星位置以当日正午近似计算（月亮位置为近似）。"
    else:
        precision = None

    la, lo, tz, label = resolve_city(birth_place_name, lat, lon, tz_str)

    subject = AstrologicalSubjectFactory.from_birth_data(
        name="User",
        year=birth_date.year,
        month=birth_date.month,
        day=birth_date.day,
        hour=hour,
        minute=minute,
        lng=lo,
        lat=la,
        tz_str=tz,
        online=False,
    )

    bt_str = f"{hour:02d}:{minute:02d}" if has_bt else None
    chart = _subject_to_natal_chart(
        subject,
        birth_date,
        bt_str,
        has_birth_time=has_bt,
        location_label=label,
        lat=la,
        lon=lo,
        tz_str=tz,
        precision_note=precision,
    )

    if not has_bt:
        # Strip unreliable house data from planets / remove houses list
        chart.houses = None
        chart.ascendant = None
        chart.mc = None
        new_planets: list[PlanetPosition] = []
        for p in chart.planets:
            new_planets.append(
                PlanetPosition(
                    name=p.name,
                    name_en=p.name_en,
                    sign_cn=p.sign_cn,
                    sign_en=p.sign_en,
                    degree=p.degree,
                    abs_degree=p.abs_degree,
                    retrograde=p.retrograde,
                    house=None,
                )
            )
        chart.planets = new_planets

    return chart


def compute_transits(
    natal: NatalChartData,
    transit_d: date,
    transit_time_h: int = 12,
    transit_time_m: int = 0,
    lat: Optional[float] = None,
    lon: Optional[float] = None,
    tz_str: Optional[str] = None,
    location_label: Optional[str] = None,
) -> TransitData:
    """Transit snapshot: transiting planets vs natal chart (same location as natal unless overridden)."""
    _ensure_kerykeion()
    assert AstrologicalSubjectFactory is not None and ChartDataFactory is not None

    la = lat if lat is not None else (natal.lat or 39.9042)
    lo = lon if lon is not None else (natal.lon or 116.4074)
    tz = tz_str or natal.tz_str or "Asia/Shanghai"
    label = location_label or natal.location_label or "默认地点"

    bd = date.fromisoformat(natal.birth_date)
    h, m, has_bt = _parse_birth_time(natal.birth_time)
    if not has_bt:
        h, m = 12, 0

    natal_sub = AstrologicalSubjectFactory.from_birth_data(
        name="N",
        year=bd.year,
        month=bd.month,
        day=bd.day,
        hour=h,
        minute=m,
        lng=lo,
        lat=la,
        tz_str=tz,
        online=False,
    )
    trans_sub = AstrologicalSubjectFactory.from_birth_data(
        name="T",
        year=transit_d.year,
        month=transit_d.month,
        day=transit_d.day,
        hour=transit_time_h,
        minute=transit_time_m,
        lng=lo,
        lat=la,
        tz_str=tz,
        online=False,
    )

    tr = ChartDataFactory.create_transit_chart_data(natal_sub, trans_sub)
    tplanets: list[PlanetPosition] = []
    for attr, label_en in _NATAL_POINTS:
        if label_en == "True_North_Lunar_Node":
            continue
        pt = getattr(trans_sub, attr, None)
        p = _point_to_position(pt, label_en, has_houses=False)
        if p:
            tplanets.append(p)

    sun_pt = getattr(natal_sub, "sun", None)
    natal_sun = ""
    if sun_pt:
        se, sc = _sign_from_kr(sun_pt.sign)
        natal_sun = f"{sc}({se}) {float(sun_pt.position):.2f}°"

    aspects_out: list[TransitAspect] = []
    for a in tr.aspects or []:
        o1 = getattr(a, "p1_owner", "")
        o2 = getattr(a, "p2_owner", "")
        if o1 == o2:
            continue
        if a.aspect not in _MAJOR_ASPECTS:
            continue
        if float(a.orbit) > 10.0:
            continue
        natal_name = a.p1_name if o1 == "N" else a.p2_name
        trans_name = a.p2_name if o1 == "N" else a.p1_name
        mov = getattr(a, "aspect_movement", None)
        aspects_out.append(
            TransitAspect(
                natal_planet=_PLANET_LABELS.get(natal_name, natal_name),
                transit_planet=_PLANET_LABELS.get(trans_name, trans_name),
                aspect_type=a.aspect,
                aspect_type_cn=_ASPECT_CN.get(a.aspect, a.aspect),
                aspect_degree=int(a.aspect_degrees or 0),
                orb=float(a.orbit),
                movement=str(mov) if mov else None,
            )
        )
    aspects_out.sort(key=lambda x: x.orb)
    aspects_out = aspects_out[:14]

    merc = getattr(trans_sub, "mercury", None)
    merc_rx = bool(merc.retrograde) if merc is not None else None

    moon_name = moon_emoji = None
    lp = getattr(trans_sub, "lunar_phase", None)
    if lp is not None:
        moon_name = getattr(lp, "moon_phase_name", None)
        moon_emoji = getattr(lp, "moon_emoji", None)

    return TransitData(
        transit_date=transit_d.isoformat(),
        transit_time=f"{transit_time_h:02d}:{transit_time_m:02d}",
        location_label=label,
        transit_planets=tplanets,
        natal_sun_summary=natal_sun,
        aspects_to_natal=aspects_out,
        moon_phase_name=moon_name,
        moon_phase_emoji=moon_emoji,
        mercury_retrograde=merc_rx,
    )


def compute_synastry_data(
    birth1: date,
    birth2: date,
    time1: Optional[str] = None,
    time2: Optional[str] = None,
    place1: Optional[str] = None,
    place2: Optional[str] = None,
    lat1: Optional[float] = None,
    lon1: Optional[float] = None,
    lat2: Optional[float] = None,
    lon2: Optional[float] = None,
    tz1: Optional[str] = None,
    tz2: Optional[str] = None,
) -> tuple[NatalChartData, NatalChartData, SynastryData]:
    _ensure_kerykeion()
    assert ChartDataFactory is not None

    c1 = compute_natal_chart(birth1, time1, place1, lat1, lon1, tz1)
    c2 = compute_natal_chart(birth2, time2, place2, lat2, lon2, tz2)

    la1, lo1, tz_a, _ = resolve_city(place1, lat1, lon1, tz1)
    la2, lo2, tz_b, _ = resolve_city(place2, lat2, lon2, tz2)

    h1, m1, ht1 = _parse_birth_time(time1)
    if not ht1:
        h1, m1 = 12, 0
    h2, m2, ht2 = _parse_birth_time(time2)
    if not ht2:
        h2, m2 = 12, 0

    s1 = AstrologicalSubjectFactory.from_birth_data(
        name="P1",
        year=birth1.year,
        month=birth1.month,
        day=birth1.day,
        hour=h1,
        minute=m1,
        lng=lo1,
        lat=la1,
        tz_str=tz_a,
        online=False,
    )
    s2 = AstrologicalSubjectFactory.from_birth_data(
        name="P2",
        year=birth2.year,
        month=birth2.month,
        day=birth2.day,
        hour=h2,
        minute=m2,
        lng=lo2,
        lat=la2,
        tz_str=tz_b,
        online=False,
    )

    syn = ChartDataFactory.create_synastry_chart_data(
        s1, s2, include_relationship_score=True, include_house_comparison=False
    )

    aspects: list[Aspect] = []
    for a in syn.aspects or []:
        if a.aspect not in _MAJOR_ASPECTS:
            continue
        if float(a.orbit) > 8.0:
            continue
        aspects.append(
            Aspect(
                planet1=_PLANET_LABELS.get(a.p1_name, a.p1_name),
                planet2=_PLANET_LABELS.get(a.p2_name, a.p2_name),
                aspect_type=a.aspect,
                aspect_type_cn=_ASPECT_CN.get(a.aspect, a.aspect),
                aspect_degree=int(a.aspect_degrees or 0),
                orb=float(a.orbit),
                applying=None,
            )
        )
    aspects.sort(key=lambda x: x.orb)
    aspects = aspects[:18]

    score_val: Optional[int] = None
    score_label: Optional[str] = None
    highlights: list[str] = []
    if syn.relationship_score:
        score_val = int(syn.relationship_score.score_value)
        score_label = syn.relationship_score.score_description
        for x in syn.relationship_score.aspects[:5]:
            highlights.append(f"{x.p1_name} {x.aspect} {x.p2_name} (orb {float(x.orbit):.2f}°)")

    syn_data = SynastryData(
        aspects=aspects,
        relationship_score=score_val,
        relationship_label=score_label,
        score_highlights=highlights,
    )
    return c1, c2, syn_data


def compute_annual_summary(
    natal: NatalChartData,
    year: int,
) -> AnnualTransitSummary:
    """Quarterly transit snapshots merged into highlight lines for annual report."""
    highlights: list[str] = []
    for month, day in ((1, 15), (4, 15), (7, 15), (10, 15)):
        try:
            td = date(year, month, day)
            tr = compute_transits(natal, td, 12, 0)
            for a in tr.aspects_to_natal[:4]:
                highlights.append(
                    f"{td.isoformat()}：行运{a.transit_planet} {a.aspect_type_cn} 本命{a.natal_planet} "
                    f"(orb {a.orb:.2f}°)"
                )
        except Exception as e:
            logger.warning("annual transit slice failed: %s", e)
    return AnnualTransitSummary(year=year, highlights=highlights[:16], natal_chart=natal)


def merge_chart_location(
    user: Any,
    place_name: Optional[str],
    lat: Optional[float],
    lon: Optional[float],
    tz: Optional[str],
) -> tuple[Optional[str], Optional[float], Optional[float], Optional[str]]:
    """Fill missing location from User profile when available."""
    pn = place_name or (getattr(user, "birth_place_name", None) if user else None)
    la = lat if lat is not None else (getattr(user, "birth_place_lat", None) if user else None)
    lo = lon if lon is not None else (getattr(user, "birth_place_lon", None) if user else None)
    tz_s = tz or (getattr(user, "birth_tz", None) if user else None)
    return pn, la, lo, tz_s


def merge_birth_time(
    user: Any,
    body_time: Optional[str],
) -> Optional[str]:
    if body_time and str(body_time).strip():
        return str(body_time).strip()
    if user and getattr(user, "birth_time", None):
        return user.birth_time.strftime("%H:%M")
    return None


def safe_compute_natal_chart(**kwargs: Any) -> Optional[NatalChartData]:
    try:
        return compute_natal_chart(**kwargs)
    except Exception as e:
        logger.exception("compute_natal_chart failed: %s", e)
        return None


# --- Quicktest: pure rule-based scores (no LLM) ---------------------------------

_WATER = frozenset({"cancer", "scorpio", "pisces"})
_FIRE = frozenset({"aries", "leo", "sagittarius"})
_AIR = frozenset({"gemini", "libra", "aquarius"})
_EARTH = frozenset({"taurus", "virgo", "capricorn"})


def _qt_planet(planets: list[PlanetPosition], name_en: str) -> Optional[PlanetPosition]:
    for p in planets:
        if p.name_en == name_en:
            return p
    return None


def _qt_clamp(x: float) -> int:
    return int(max(30, min(95, round(x))))


def _qt_el(natal: NatalChartData, key: str) -> float:
    """Share of element 0–1 (kerykeion returns weighted counts, not normalized)."""
    ed = natal.element_distribution
    keys = ("火象", "土象", "风象", "水象")
    total = sum(float(ed.get(k, 0) or 0) for k in keys)
    if total <= 0:
        return 0.25
    return float(ed.get(key, 0) or 0) / total


def _qt_mod(natal: NatalChartData, key: str) -> float:
    """Share of modality 0–1."""
    md = natal.modality_distribution
    keys = ("基本", "固定", "变动")
    total = sum(float(md.get(k, 0) or 0) for k in keys)
    if total <= 0:
        return 1.0 / 3.0
    return float(md.get(key, 0) or 0) / total


def _qt_aspect_orb_factor(orb: float) -> float:
    return max(0.0, 1.0 - float(orb) / 8.0)


def _qt_score_love(natal: NatalChartData) -> float:
    s = 52.0
    s += _qt_el(natal, "水象") * 10.0
    s += _qt_el(natal, "火象") * 5.0
    v = _qt_planet(natal.planets, "Venus")
    m = _qt_planet(natal.planets, "Moon")
    if v:
        if v.house in (5, 7):
            s += 6.0
        if v.sign_en in _WATER:
            s += 5.0
    if m and m.sign_en in _WATER:
        s += 4.0
    asp_bonus = 0.0
    for a in natal.aspects:
        if a.aspect_type not in _MAJOR_ASPECTS:
            continue
        f = _qt_aspect_orb_factor(a.orb)
        ps = {a.planet1, a.planet2}
        if not (("金星" in ps) or ("月亮" in ps)):
            continue
        if a.aspect_type in ("trine", "sextile", "conjunction"):
            asp_bonus += 2.2 * f
        elif a.aspect_type in ("square", "opposition"):
            asp_bonus -= 1.8 * f
    s += max(-8.0, min(14.0, asp_bonus))
    return s


def _qt_score_career(natal: NatalChartData) -> float:
    s = 52.0
    s += _qt_el(natal, "土象") * 9.0
    s += _qt_mod(natal, "基本") * 6.0
    sat = _qt_planet(natal.planets, "Saturn")
    mar = _qt_planet(natal.planets, "Mars")
    mc = natal.mc
    if sat:
        if sat.house in (6, 10):
            s += 6.0
        if sat.sign_en in _EARTH:
            s += 4.0
    if mar:
        if mar.house in (1, 10):
            s += 5.0
        if mar.sign_en in ("aries", "capricorn", "scorpio"):
            s += 3.0
    if mc is not None and mc.sign_en in _EARTH:
        s += 4.0
    asp_bonus = 0.0
    for a in natal.aspects:
        if a.aspect_type not in _MAJOR_ASPECTS:
            continue
        f = _qt_aspect_orb_factor(a.orb)
        ps = {a.planet1, a.planet2}
        if "土星" in ps or "火星" in ps:
            if a.aspect_type in ("trine", "sextile", "conjunction"):
                asp_bonus += 2.0 * f
            elif a.aspect_type in ("square", "opposition"):
                asp_bonus -= 1.5 * f
    s += max(-8.0, min(14.0, asp_bonus))
    return s


def _qt_score_social(natal: NatalChartData) -> float:
    s = 52.0
    s += _qt_el(natal, "风象") * 11.0
    merc = _qt_planet(natal.planets, "Mercury")
    if merc:
        if merc.house in (3, 7, 11):
            s += 6.0
        if merc.sign_en in _AIR:
            s += 5.0
    asc = natal.ascendant
    if asc and asc.sign_en in _AIR:
        s += 5.0
    if asc and asc.sign_en in _FIRE:
        s += 3.0
    asp_bonus = 0.0
    for a in natal.aspects:
        if a.aspect_type not in _MAJOR_ASPECTS:
            continue
        f = _qt_aspect_orb_factor(a.orb)
        if "水星" in {a.planet1, a.planet2} and a.aspect_type in ("trine", "sextile", "conjunction"):
            asp_bonus += 2.5 * f
    s += min(12.0, asp_bonus)
    return s


def _qt_score_creativity(natal: NatalChartData) -> float:
    s = 52.0
    s += _qt_el(natal, "水象") * 6.0
    s += _qt_mod(natal, "变动") * 7.0
    nep = _qt_planet(natal.planets, "Neptune")
    jup = _qt_planet(natal.planets, "Jupiter")
    if nep:
        if nep.house in (5, 12):
            s += 6.0
        if nep.sign_en in _WATER:
            s += 4.0
    if jup and jup.house == 5:
        s += 5.0
    ven = _qt_planet(natal.planets, "Venus")
    if ven and ven.house == 5:
        s += 4.0
    asp_bonus = 0.0
    for a in natal.aspects:
        if a.aspect_type not in _MAJOR_ASPECTS:
            continue
        f = _qt_aspect_orb_factor(a.orb)
        if "海王星" in {a.planet1, a.planet2} and a.aspect_type in ("trine", "sextile", "conjunction"):
            asp_bonus += 2.8 * f
    s += min(12.0, asp_bonus)
    return s


def _qt_score_intuition(natal: NatalChartData) -> float:
    s = 52.0
    s += _qt_el(natal, "水象") * 11.0
    moon = _qt_planet(natal.planets, "Moon")
    if moon and moon.sign_en in _WATER:
        s += 6.0
    if moon and moon.house in (8, 12):
        s += 5.0
    asp_bonus = 0.0
    for a in natal.aspects:
        if a.aspect_type not in _MAJOR_ASPECTS:
            continue
        f = _qt_aspect_orb_factor(a.orb)
        ps = {a.planet1, a.planet2}
        if ("海王星" in ps or "冥王星" in ps) and "月亮" in ps:
            if a.aspect_type in ("trine", "sextile", "conjunction"):
                asp_bonus += 3.0 * f
        elif "海王星" in ps and a.aspect_type in ("trine", "sextile"):
            asp_bonus += 2.0 * f
    s += max(-6.0, min(14.0, asp_bonus))
    if natal.lunar_phase_name and "盈" in str(natal.lunar_phase_name):
        s += 2.0
    return s


def _qt_persona_style(natal: NatalChartData) -> str:
    dom = natal.dominant_element or ""
    styles = {
        "火象": "热情行动派",
        "土象": "稳健务实派",
        "风象": "理性沟通派",
        "水象": "细腻共情派",
    }
    return styles.get(dom, "平衡探索派")


def compute_quicktest_dimensions(natal: Optional[NatalChartData]) -> dict[str, int]:
    """Rule-based 0–100-ish scores mapped to love/career/social/creativity/intuition."""
    if natal is None:
        return {
            "love": 62,
            "career": 64,
            "social": 60,
            "creativity": 66,
            "intuition": 63,
        }
    return {
        "love": _qt_clamp(_qt_score_love(natal)),
        "career": _qt_clamp(_qt_score_career(natal)),
        "social": _qt_clamp(_qt_score_social(natal)),
        "creativity": _qt_clamp(_qt_score_creativity(natal)),
        "intuition": _qt_clamp(_qt_score_intuition(natal)),
    }


def compute_quicktest_persona_label(sign_cn: str, natal: Optional[NatalChartData]) -> str:
    if natal is None:
        return f"{sign_cn} · 探索者"
    return f"{sign_cn} · {_qt_persona_style(natal)}"


def compute_quicktest_summary(sign_cn: str, natal: Optional[NatalChartData]) -> list[str]:
    """Three short lines for UI; deterministic from chart."""
    if natal is None:
        return [
            f"太阳落在{sign_cn}，你的核心气质与自我表达带有明显的星座底色。",
            "情感与社交上，保持真诚与节奏感更容易建立信任。",
            "事业与成长上，适合把目标拆细，小步快跑更容易看到正反馈。",
        ]
    moon = _qt_planet(natal.planets, "Moon")
    sun = _qt_planet(natal.planets, "Sun")
    asc = natal.ascendant
    moon_cn = moon.sign_cn if moon else "未知"
    asc_cn = asc.sign_cn if asc else "（未提供出生时间时不展示上升）"
    dom_el = natal.dominant_element or "多元素"
    sun_cn = sun.sign_cn if sun else sign_cn
    line1 = f"太阳落在{sun_cn}，月亮落在{moon_cn}，内外在气质形成有趣对照。"
    if natal.has_birth_time and asc:
        line1 = (
            f"太阳{sun_cn}、月亮{moon_cn}、上升{asc_cn}，"
            "构成你性格分析的重要三角。"
        )
    line2 = f"本命盘元素分布以「{dom_el}」相对突出，处事风格会偏向该元素的典型特质。"
    line3 = "以上仅为性格与能量倾向参考，具体仍要结合现实情境灵活看待。"
    return [line1, line2, line3]


def compute_quicktest_bundle(
    natal: Optional[NatalChartData],
    sign_cn: str,
    birth_date_str: str,
) -> dict[str, Any]:
    """
    Full quicktest payload without LLM. If natal is missing, scores vary slightly by birth_date hash.
    """
    dims = compute_quicktest_dimensions(natal)
    if natal is None:
        h = int(hashlib.sha256(birth_date_str.encode("utf-8")).hexdigest()[:8], 16)
        keys = ("love", "career", "social", "creativity", "intuition")
        for i, k in enumerate(keys):
            base = 48 + ((h >> (i * 5)) & 0x1F)
            dims[k] = max(40, min(88, base))
    label = compute_quicktest_persona_label(sign_cn, natal)
    summary = compute_quicktest_summary(sign_cn, natal)
    return {"persona_label": label, "dimensions": dims, "summary": summary}


def compute_ephemeris_snapshot_line(
    d: date,
    lat: float = DEFAULT_LAT,
    lon: float = DEFAULT_LON,
    tz: str = DEFAULT_TZ,
) -> str:
    """One-line summary of Sun/Moon positions for public daily horoscope context."""
    _ensure_kerykeion()
    assert AstrologicalSubjectFactory is not None
    try:
        sub = AstrologicalSubjectFactory.from_birth_data(
            name="Sky",
            year=d.year,
            month=d.month,
            day=d.day,
            hour=12,
            minute=0,
            lng=lon,
            lat=lat,
            tz_str=tz,
            online=False,
        )
        sun = getattr(sub, "sun", None)
        moon = getattr(sub, "moon", None)
        merc = getattr(sub, "mercury", None)
        if not sun or not moon:
            return "当日天象：黄道计算暂不可用。"
        _, sun_cn = _sign_from_kr(sun.sign)
        _, moon_cn = _sign_from_kr(moon.sign)
        merc_rx = ""
        if merc is not None and merc.retrograde:
            merc_rx = "；水星逆行"
        return (
            f"太阳约在{sun_cn} {float(sun.position):.1f}°，月亮约在{moon_cn} {float(moon.position):.1f}°{merc_rx}（历表计算，热带黄道）。"
        )
    except Exception as e:
        logger.warning("ephemeris snapshot failed: %s", e)
        return "当日天象：历表计算暂不可用。"
