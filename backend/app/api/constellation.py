"""Constellation: signs, daily fortune, paid reports (SSE)."""

from __future__ import annotations

import json
import logging
import uuid
from datetime import date, datetime, time as dt_time
from typing import Any, AsyncGenerator, Optional

from fastapi import APIRouter, Depends, HTTPException
from fastapi.responses import StreamingResponse
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.schemas import (
    AnnualReportBody,
    AstroEventBody,
    CompatibilityReportBody,
    PersonalityDlcBody,
    PersonalityReportBody,
    QuickTestBody,
)
from app.config import get_settings
from app.database import get_db
from app.deps import get_current_user
from app.models.order import Order, OrderStatus, ProductType
from app.models.report import Report, ReportType
from app.models.user import Gender, User
from app.prompts.annual import build_annual_user_input
from app.prompts.compatibility import build_compatibility_user_input
from app.prompts.daily_fortune import (
    build_daily_personal_user_input,
    build_daily_sign_ephemeris_stub,
)
from app.prompts.astro_event import build_astro_event_user_input
from app.prompts.personality import build_personality_user_input
from app.prompts.personality_dlc import build_personality_dlc_user_input
from app.services import cache_service
from app.services.astro_service import (
    compute_ephemeris_snapshot_line,
    compute_quicktest_bundle,
    compute_synastry_data,
    compute_transits,
)
from app.services.astro_service import compute_annual_summary as astro_compute_annual_summary
from app.services.demo_order_service import get_or_create_demo_paid_order
from app.services.growth_helpers import get_or_create_growth_profile, grant_zodiac_card_if_needed
from app.services.daily_fortune_core import normalize_daily_payload, wrap_daily_response
from app.services.llm_service import (
    LLMServiceFactory,
    fallback_static_text,
    generate_json_daily,
    stream_with_fallback,
)
from app.services.public_daily_fortune import ensure_public_daily_content
from app.utils.beijing_date import fortune_date_beijing
from app.utils.stream_helper import sse_line
from app.utils.zodiac_calc import get_sign_meta, list_all_signs, parse_birth_date_http, sun_sign_from_date

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/v1", tags=["constellation"])


def _natal_for_user(
    user: Optional[User],
    bd: date,
    birth_time_override: Optional[str] = None,
    place_name: Optional[str] = None,
    lat: Optional[float] = None,
    lon: Optional[float] = None,
    tz: Optional[str] = None,
):
    """Merge profile + request fields; returns None if ephemeris fails."""
    from app.services.astro_service import (
        merge_birth_time,
        merge_chart_location,
        safe_compute_natal_chart,
    )

    pn, la, lo, tz_s = merge_chart_location(user, place_name, lat, lon, tz)
    bt = merge_birth_time(user, birth_time_override)
    return safe_compute_natal_chart(
        birth_date=bd,
        birth_time=bt,
        birth_place_name=pn,
        lat=la,
        lon=lo,
        tz_str=tz_s,
    )


@router.get("/signs")
async def list_signs() -> dict[str, Any]:
    return {"signs": list_all_signs()}


@router.get("/signs/{sign}")
async def get_sign(sign: str) -> dict[str, Any]:
    meta = get_sign_meta(sign)
    if not meta:
        raise HTTPException(status_code=404, detail="Unknown sign")
    return meta


@router.post("/quicktest")
async def quicktest(
    body: QuickTestBody,
    db: AsyncSession = Depends(get_db),
    user: User = Depends(get_current_user),
) -> dict[str, Any]:
    """免费速测：人格标签 + 五维评分 + 短摘要；并写入用户出生日期与太阳星座。"""
    bd = parse_birth_date_http(body.birth_date)
    sign = sun_sign_from_date(bd)
    meta = get_sign_meta(sign) or {}
    sign_cn = meta.get("sign_cn", sign)
    natal = _natal_for_user(
        user,
        bd,
        birth_time_override=body.birth_time,
        place_name=body.birth_place_name,
        lat=body.birth_place_lat,
        lon=body.birth_place_lon,
        tz=body.birth_tz,
    )
    data = compute_quicktest_bundle(natal, sign_cn, body.birth_date)

    user.birth_date = bd
    user.sun_sign = sign
    if body.gender in ("male", "female"):
        user.gender = Gender(body.gender)
    if body.birth_place_name:
        user.birth_place_name = body.birth_place_name.strip() or None
    if body.birth_place_lat is not None:
        user.birth_place_lat = body.birth_place_lat
    if body.birth_place_lon is not None:
        user.birth_place_lon = body.birth_place_lon
    if body.birth_tz:
        user.birth_tz = body.birth_tz.strip() or None
    if body.birth_time and str(body.birth_time).strip():
        parts = str(body.birth_time).strip().split(":")
        try:
            h = int(parts[0]) % 24
            m = int(parts[1]) % 60 if len(parts) > 1 else 0
            user.birth_time = dt_time(h, m)
        except (ValueError, IndexError):
            pass
    await db.flush()

    return {
        "persona_label": data["persona_label"],
        "dimensions": data["dimensions"],
        "summary": data["summary"],
        "sun_sign": sign,
        "sign_cn": sign_cn,
        "symbol": meta.get("symbol", ""),
    }


@router.get("/reports/{report_id}")
async def get_report_detail(
    report_id: str,
    db: AsyncSession = Depends(get_db),
    user: User = Depends(get_current_user),
) -> dict[str, Any]:
    result = await db.execute(
        select(Report).where(Report.report_id == report_id, Report.user_id == user.id)
    )
    rep = result.scalar_one_or_none()
    if not rep:
        raise HTTPException(status_code=404, detail="Report not found")
    return {
        "report_id": rep.report_id,
        "report_type": rep.report_type.value,
        "sign": rep.sign,
        "input_data": rep.input_data,
        "content": rep.content,
        "created_at": rep.created_at.isoformat() if rep.created_at else None,
        "order_id": rep.order_id,
    }


# 静态路径必须在 /daily/{sign} 之前，否则 "all"、"personal" 会被当成星座 slug。
@router.get("/daily/all")
async def daily_all(db: AsyncSession = Depends(get_db)) -> dict[str, Any]:
    today = fortune_date_beijing()
    summaries = []
    for meta in list_all_signs():
        slug = meta["sign"]
        m = get_sign_meta(slug)
        if not m:
            continue
        data = await ensure_public_daily_content(db, slug, today)
        summaries.append(
            {
                "sign": slug,
                "sign_cn": meta["sign_cn"],
                "overall_score": data.get("overall_score", 0),
                "summary": (data.get("summary") or "")[:80],
            }
        )
    return {"date": today.isoformat(), "items": summaries}


@router.get("/daily/personal")
async def get_daily_personal(
    user: User = Depends(get_current_user),
) -> dict[str, Any]:
    """今日运势（个人）：本命盘 + 当日行运，需登录且已填出生日期。"""
    if not user.birth_date:
        raise HTTPException(status_code=400, detail="请先在资料页填写出生日期")
    today = fortune_date_beijing()
    cached = await cache_service.get_personal_daily_cached(user.id, today)
    if cached:
        return cached

    sign = sun_sign_from_date(user.birth_date)
    meta = get_sign_meta(sign) or {}
    sign_cn = meta.get("sign_cn", sign)

    natal = _natal_for_user(user, user.birth_date, None, None, None, None, None)
    if natal:
        try:
            tr = compute_transits(natal, today)
            user_input = build_daily_personal_user_input(natal, tr)
        except Exception as e:
            logger.warning("personal transit build failed: %s", e)
            sky = compute_ephemeris_snapshot_line(today)
            user_input = build_daily_sign_ephemeris_stub(sign_cn, today.isoformat(), sky)
    else:
        sky = compute_ephemeris_snapshot_line(today)
        user_input = build_daily_sign_ephemeris_stub(sign_cn, today.isoformat(), sky)

    settings = get_settings()
    data = await generate_json_daily(settings, user_input, sign_cn, today.isoformat())
    data = normalize_daily_payload(data, sign_cn, today)
    out = wrap_daily_response(sign, sign_cn, today, data)
    out["personalized"] = True
    await cache_service.set_personal_daily_cached(user.id, today, out)
    return out


@router.get("/daily/{sign}")
async def get_daily(sign: str, db: AsyncSession = Depends(get_db)) -> dict[str, Any]:
    meta = get_sign_meta(sign)
    if not meta:
        raise HTTPException(status_code=404, detail="Unknown sign")
    today = fortune_date_beijing()
    data = await ensure_public_daily_content(db, sign, today)
    return wrap_daily_response(sign, meta["sign_cn"], today, data)


async def _resolve_paid_order(
    db: AsyncSession,
    user: User,
    order_id: Optional[str],
    product: ProductType,
) -> Order:
    settings = get_settings()
    if settings.demo_mode:
        return await get_or_create_demo_paid_order(db, user, product)
    if not order_id or not str(order_id).strip():
        raise HTTPException(status_code=400, detail="order_id required")
    result = await db.execute(
        select(Order).where(
            Order.order_id == order_id.strip(),
            Order.user_id == user.id,
            Order.product_type == product,
        )
    )
    order = result.scalar_one_or_none()
    if not order or order.status != OrderStatus.paid:
        raise HTTPException(status_code=402, detail="Payment required or invalid order")
    return order


def _stream_llm_params_for_annual(settings) -> dict[str, Any]:
    if settings.llm_platform.lower() != "bailian":
        return {}
    return {
        "headers": {
            "X-DashScope-DataInspection": json.dumps({"input": "disable", "output": "disable"})
        }
    }


@router.post("/report/personality")
async def report_personality(
    body: PersonalityReportBody,
    db: AsyncSession = Depends(get_db),
    user: User = Depends(get_current_user),
):
    order = await _resolve_paid_order(db, user, body.order_id, ProductType.personality)
    bd = parse_birth_date_http(body.birth_date)
    sign = sun_sign_from_date(bd)
    meta = get_sign_meta(sign) or {}
    sign_cn = meta.get("sign_cn", sign)
    natal = _natal_for_user(
        user,
        bd,
        birth_time_override=body.birth_time,
        place_name=body.birth_place_name,
        lat=body.birth_place_lat,
        lon=body.birth_place_lon,
        tz=body.birth_tz,
    )
    user_input = build_personality_user_input(
        body.birth_date,
        sign,
        sign_cn,
        birth_time=body.birth_time,
        gender=body.gender,
        natal_chart=natal,
    )
    settings = get_settings()
    primary = LLMServiceFactory.for_report(settings)
    fallback = (
        None
        if settings.llm_platform.lower() == "bailian"
        else LLMServiceFactory.bailian_for_scene(settings, "personality")
    )
    report_id = f"rpt_{uuid.uuid4().hex[:16]}"

    async def gen() -> AsyncGenerator[str, None]:
        full: list[str] = []
        try:
            async for chunk in stream_with_fallback(primary, fallback, user_input):
                full.append(chunk)
                yield sse_line({"type": "content", "text": chunk})
        except Exception:
            text = fallback_static_text()
            full.append(text)
            yield sse_line({"type": "content", "text": text})
        content = "".join(full)
        await _save_report(
            db,
            user.id,
            order.order_id,
            ReportType.personality,
            sign,
            {
                "birth_date": body.birth_date,
                "birth_time": body.birth_time,
                "gender": body.gender,
                "birth_place_name": body.birth_place_name,
                "birth_place_lat": body.birth_place_lat,
                "birth_place_lon": body.birth_place_lon,
                "birth_tz": body.birth_tz,
                "astro_natal": natal.model_dump(mode="json") if natal else None,
            },
            content,
            report_id,
        )
        yield sse_line({"type": "done", "report_id": report_id})

    return StreamingResponse(gen(), media_type="text/event-stream")


@router.post("/report/compatibility")
async def report_compatibility(
    body: CompatibilityReportBody,
    db: AsyncSession = Depends(get_db),
    user: User = Depends(get_current_user),
):
    order = await _resolve_paid_order(db, user, body.order_id, ProductType.compatibility)
    p1 = body.person1
    p2 = body.person2
    d1 = parse_birth_date_http(p1.birth_date)
    d2 = parse_birth_date_http(p2.birth_date)
    s1 = sun_sign_from_date(d1)
    s2 = sun_sign_from_date(d2)
    m1 = get_sign_meta(s1) or {}
    m2 = get_sign_meta(s2) or {}
    natal1 = natal2 = syn = None
    try:
        natal1, natal2, syn = compute_synastry_data(
            d1,
            d2,
            time1=p1.birth_time,
            time2=p2.birth_time,
            place1=p1.birth_place_name,
            place2=p2.birth_place_name,
            lat1=p1.birth_place_lat,
            lon1=p1.birth_place_lon,
            lat2=p2.birth_place_lat,
            lon2=p2.birth_place_lon,
            tz1=p1.birth_tz,
            tz2=p2.birth_tz,
        )
    except Exception as e:
        logger.warning("synastry compute failed: %s", e)
    user_input = build_compatibility_user_input(
        p1.name or "A",
        p1.birth_date,
        s1,
        m1.get("sign_cn", s1),
        p2.name or "B",
        p2.birth_date,
        s2,
        m2.get("sign_cn", s2),
        natal1=natal1,
        natal2=natal2,
        synastry=syn,
    )
    settings = get_settings()
    primary = LLMServiceFactory.for_compatibility(settings)
    fallback = (
        None
        if settings.llm_platform.lower() == "bailian"
        else LLMServiceFactory.bailian_for_scene(settings, "compatibility")
    )
    report_id = f"rpt_{uuid.uuid4().hex[:16]}"

    async def gen() -> AsyncGenerator[str, None]:
        full: list[str] = []
        try:
            async for chunk in stream_with_fallback(primary, fallback, user_input):
                full.append(chunk)
                yield sse_line({"type": "content", "text": chunk})
        except Exception:
            text = fallback_static_text()
            full.append(text)
            yield sse_line({"type": "content", "text": text})
        content = "".join(full)
        await _save_report(
            db,
            user.id,
            order.order_id,
            ReportType.compatibility,
            f"{s1}+{s2}",
            {
                "person1": p1.model_dump(mode="json"),
                "person2": p2.model_dump(mode="json"),
                "synastry_score": syn.relationship_score if syn else None,
                "natal1": natal1.model_dump(mode="json") if natal1 else None,
                "natal2": natal2.model_dump(mode="json") if natal2 else None,
            },
            content,
            report_id,
        )
        yield sse_line({"type": "done", "report_id": report_id})

    return StreamingResponse(gen(), media_type="text/event-stream")


@router.post("/report/annual")
async def report_annual(
    body: AnnualReportBody,
    db: AsyncSession = Depends(get_db),
    user: User = Depends(get_current_user),
):
    order = await _resolve_paid_order(db, user, body.order_id, ProductType.annual)
    bd = parse_birth_date_http(body.birth_date)
    sign = sun_sign_from_date(bd)
    meta = get_sign_meta(sign) or {}
    sign_cn = meta.get("sign_cn", sign)
    cy = datetime.utcnow().year
    raw_y = body.year if body.year is not None else cy
    year = min(max(int(raw_y), cy), cy + 1)
    natal = _natal_for_user(
        user,
        bd,
        birth_time_override=body.birth_time,
        place_name=body.birth_place_name,
        lat=body.birth_place_lat,
        lon=body.birth_place_lon,
        tz=body.birth_tz,
    )
    ann = astro_compute_annual_summary(natal, year) if natal else None
    user_input = build_annual_user_input(
        sign,
        sign_cn,
        year,
        natal_chart=natal,
        annual_highlights=ann.highlights if ann else None,
    )
    settings = get_settings()
    primary = LLMServiceFactory.for_annual(settings)
    fallback = (
        None
        if settings.llm_platform.lower() == "bailian"
        else LLMServiceFactory.bailian_for_scene(settings, "annual")
    )
    stream_params = _stream_llm_params_for_annual(settings)
    report_id = f"rpt_{uuid.uuid4().hex[:16]}"

    async def gen() -> AsyncGenerator[str, None]:
        full: list[str] = []
        try:
            async for chunk in stream_with_fallback(primary, fallback, user_input, stream_params):
                full.append(chunk)
                yield sse_line({"type": "content", "text": chunk})
        except Exception:
            text = fallback_static_text()
            full.append(text)
            yield sse_line({"type": "content", "text": text})
        content = "".join(full)
        await _save_report(
            db,
            user.id,
            order.order_id,
            ReportType.annual,
            sign,
            {
                "birth_date": body.birth_date,
                "year": year,
                "birth_time": body.birth_time,
                "birth_place_name": body.birth_place_name,
                "astro_natal": natal.model_dump(mode="json") if natal else None,
                "annual_highlights": ann.highlights if ann else [],
            },
            content,
            report_id,
        )
        yield sse_line({"type": "done", "report_id": report_id})

    return StreamingResponse(gen(), media_type="text/event-stream")


_PACK_TO_PRODUCT: dict[str, ProductType] = {
    "career": ProductType.personality_career,
    "love": ProductType.personality_love,
    "growth": ProductType.personality_growth,
}
_PACK_TO_REPORT: dict[str, ReportType] = {
    "career": ReportType.personality_career,
    "love": ReportType.personality_love,
    "growth": ReportType.personality_growth,
}


@router.post("/report/personality-dlc")
async def report_personality_dlc(
    body: PersonalityDlcBody,
    db: AsyncSession = Depends(get_db),
    user: User = Depends(get_current_user),
):
    pack = (body.pack or "").strip().lower()
    if pack not in _PACK_TO_PRODUCT:
        raise HTTPException(status_code=400, detail="pack must be career|love|growth")
    product = _PACK_TO_PRODUCT[pack]
    order = await _resolve_paid_order(db, user, body.order_id, product)
    bd = parse_birth_date_http(body.birth_date)
    sign = sun_sign_from_date(bd)
    meta = get_sign_meta(sign) or {}
    sign_cn = meta.get("sign_cn", sign)
    natal = _natal_for_user(
        user,
        bd,
        birth_time_override=body.birth_time,
        place_name=body.birth_place_name,
        lat=body.birth_place_lat,
        lon=body.birth_place_lon,
        tz=body.birth_tz,
    )
    user_input = build_personality_dlc_user_input(
        pack,
        body.birth_date,
        sign,
        sign_cn,
        birth_time=body.birth_time,
        gender=body.gender,
        natal_chart=natal,
    )
    settings = get_settings()
    primary = LLMServiceFactory.for_report(settings)
    fallback = (
        None
        if settings.llm_platform.lower() == "bailian"
        else LLMServiceFactory.bailian_for_scene(settings, "personality")
    )
    rtype = _PACK_TO_REPORT[pack]
    report_id = f"rpt_{uuid.uuid4().hex[:16]}"

    async def gen() -> AsyncGenerator[str, None]:
        full: list[str] = []
        try:
            async for chunk in stream_with_fallback(primary, fallback, user_input):
                full.append(chunk)
                yield sse_line({"type": "content", "text": chunk})
        except Exception:
            text = fallback_static_text()
            full.append(text)
            yield sse_line({"type": "content", "text": text})
        content = "".join(full)
        await _save_report(
            db,
            user.id,
            order.order_id,
            rtype,
            sign,
            {
                "pack": pack,
                "birth_date": body.birth_date,
                "birth_time": body.birth_time,
                "gender": body.gender,
                "birth_place_name": body.birth_place_name,
                "astro_natal": natal.model_dump(mode="json") if natal else None,
            },
            content,
            report_id,
        )
        yield sse_line({"type": "done", "report_id": report_id})

    return StreamingResponse(gen(), media_type="text/event-stream")


@router.post("/report/astro-event")
async def report_astro_event(
    body: AstroEventBody,
    db: AsyncSession = Depends(get_db),
    user: User = Depends(get_current_user),
):
    order = await _resolve_paid_order(db, user, body.order_id, ProductType.astro_event)
    bd = parse_birth_date_http(body.birth_date)
    sign = sun_sign_from_date(bd)
    meta = get_sign_meta(sign) or {}
    sign_cn = meta.get("sign_cn", sign)
    natal = _natal_for_user(
        user,
        bd,
        birth_time_override=body.birth_time,
        place_name=body.birth_place_name,
        lat=body.birth_place_lat,
        lon=body.birth_place_lon,
        tz=body.birth_tz,
    )
    user_input = build_astro_event_user_input(
        body.event_key, body.birth_date, sign, sign_cn, natal_chart=natal
    )
    settings = get_settings()
    primary = LLMServiceFactory.for_report(settings)
    fallback = (
        None
        if settings.llm_platform.lower() == "bailian"
        else LLMServiceFactory.bailian_for_scene(settings, "personality")
    )
    report_id = f"rpt_{uuid.uuid4().hex[:16]}"

    async def gen() -> AsyncGenerator[str, None]:
        full: list[str] = []
        try:
            async for chunk in stream_with_fallback(primary, fallback, user_input):
                full.append(chunk)
                yield sse_line({"type": "content", "text": chunk})
        except Exception:
            text = fallback_static_text()
            full.append(text)
            yield sse_line({"type": "content", "text": text})
        content = "".join(full)
        await _save_report(
            db,
            user.id,
            order.order_id,
            ReportType.astro_event,
            sign,
            {
                "event_key": body.event_key,
                "birth_date": body.birth_date,
                "birth_time": body.birth_time,
                "astro_natal": natal.model_dump(mode="json") if natal else None,
            },
            content,
            report_id,
        )
        yield sse_line({"type": "done", "report_id": report_id})

    return StreamingResponse(gen(), media_type="text/event-stream")


@router.get("/season/today")
async def season_today(
    db: AsyncSession = Depends(get_db),
    user: User = Depends(get_current_user),
) -> dict[str, Any]:
    gp = await get_or_create_growth_profile(db, user)
    if not gp.season_pass_until or gp.season_pass_until < datetime.utcnow():
        raise HTTPException(status_code=402, detail="需要星运月卡")
    if not user.birth_date:
        raise HTTPException(status_code=400, detail="请先在个人资料填写出生日期")
    sign = sun_sign_from_date(user.birth_date)
    meta = get_sign_meta(sign) or {}
    sign_cn = meta.get("sign_cn", sign)
    natal = _natal_for_user(user, user.birth_date, None, None, None, None, None)
    today = datetime.utcnow().date()
    prompt: str
    try:
        if natal:
            from app.prompts.chart_formatter import format_natal_chart_for_prompt, format_transit_for_prompt

            tr = compute_transits(natal, today)
            prompt = (
                "【星运月卡·今日深度参考】以下为历表计算的本命与行运事实，请据此撰写 Markdown，"
                "分「整体状态」「人际与沟通」「行动建议」；避免迷信与宿命论表述。\n\n"
                + format_natal_chart_for_prompt(natal)
                + "\n\n"
                + format_transit_for_prompt(tr)
            )
        else:
            prompt = (
                f"【星运月卡·今日深度参考】用户太阳星座：{sign_cn}（{sign}），出生日期：{user.birth_date}。"
                "请输出今日性格与节奏参考（Markdown），分「整体状态」「人际与沟通」「行动建议」；避免迷信与宿命论表述。"
            )
    except Exception as e:
        logger.warning("season today astro prompt: %s", e)
        prompt = (
            f"【星运月卡·今日深度参考】用户太阳星座：{sign_cn}（{sign}），出生日期：{user.birth_date}。"
            "请输出今日性格与节奏参考（Markdown），分「整体状态」「人际与沟通」「行动建议」；避免迷信与宿命论表述。"
        )
    settings = get_settings()
    svc = LLMServiceFactory.for_report(settings)
    try:
        text = await svc.generate(prompt)
    except Exception:
        text = f"## 今日参考\n\n{sign_cn}今日宜保持节奏平稳，适合整理计划与轻度社交。"
    return {"markdown": text, "date": datetime.utcnow().date().isoformat()}


async def _save_report(
    db: AsyncSession,
    user_id: int,
    order_id: str,
    rtype: ReportType,
    sign: str,
    input_data: dict,
    content: str,
    report_id: str,
) -> None:
    rep = Report(
        report_id=report_id,
        user_id=user_id,
        order_id=order_id,
        report_type=rtype,
        sign=sign,
        input_data=input_data,
        content=content,
    )
    db.add(rep)
    await db.flush()
    if rtype in (
        ReportType.personality,
        ReportType.personality_career,
        ReportType.personality_love,
        ReportType.personality_growth,
    ):
        await grant_zodiac_card_if_needed(db, user_id, sign)
