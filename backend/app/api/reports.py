"""Paid report SSE endpoints: personality, compatibility, annual, DLC, astro-event."""

from __future__ import annotations

import json
import logging
import uuid
from datetime import datetime
from typing import Any, AsyncGenerator

from fastapi import APIRouter, Depends
from fastapi.responses import StreamingResponse
from sqlalchemy.ext.asyncio import AsyncSession

from app.api._report_helpers import (
    natal_for_user,
    resolve_paid_order,
    save_report,
    schedule_profile_update,
)
from app.api.schemas import (
    AnnualReportBody,
    AstroEventBody,
    CompatibilityReportBody,
    PersonalityDlcBody,
    PersonalityReportBody,
)
from app.config import get_settings
from app.database import get_db
from app.deps import get_current_user
from app.models.order import ProductType
from app.models.report import ReportType
from app.models.user import User
from app.prompts.annual import build_annual_user_input
from app.prompts.astro_event import build_astro_event_user_input
from app.prompts.chart_formatter import format_natal_chart_for_prompt
from app.prompts.compatibility import build_compatibility_user_input
from app.prompts.personality import build_personality_user_input
from app.prompts.personality_dlc import build_personality_dlc_user_input
from app.prompts.report_plan_prompt import build_plan_user_input
from app.services.astro_service import compute_synastry_data
from app.services.astro_service import compute_annual_summary as astro_compute_annual_summary
from app.services.llm_service import (
    LLMServiceFactory,
    fallback_static_text,
    stream_with_fallback,
)
from app.services.report_planner import two_stage_report
from app.utils.stream_helper import sse_line
from app.utils.zodiac_calc import get_sign_meta, parse_birth_date_http, sun_sign_from_date

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/v1", tags=["reports"])


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
    order = await resolve_paid_order(db, user, body.order_id, ProductType.personality)
    await db.refresh(user)
    bd = parse_birth_date_http(body.birth_date)
    sign = sun_sign_from_date(bd)
    meta = get_sign_meta(sign) or {}
    sign_cn = meta.get("sign_cn", sign)
    natal = natal_for_user(
        user, bd,
        birth_time_override=body.birth_time,
        place_name=body.birth_place_name,
        lat=body.birth_place_lat, lon=body.birth_place_lon, tz=body.birth_tz,
    )
    user_input = build_personality_user_input(
        body.birth_date, sign, sign_cn,
        birth_time=body.birth_time, gender=body.gender, natal_chart=natal,
    )
    settings = get_settings()
    primary = LLMServiceFactory.for_report(settings)
    fallback = (
        None if settings.llm_platform.lower() == "bailian"
        else LLMServiceFactory.bailian_for_scene(settings, "personality")
    )
    report_id = f"rpt_{uuid.uuid4().hex[:16]}"

    async def gen() -> AsyncGenerator[str, None]:
        full: list[str] = []
        try:
            plan_input = build_plan_user_input(
                "personality",
                format_natal_chart_for_prompt(natal) if natal else user_input,
            )
            planner = LLMServiceFactory.for_planner(settings)
            async for event in two_stage_report(
                planner_llm=planner, writer_llm=primary, writer_fallback=fallback,
                plan_user_input=plan_input, report_type="personality",
                fallback_full_prompt=user_input,
            ):
                if event.get("type") == "content":
                    full.append(event.get("text", ""))
                yield sse_line(event)
        except Exception:
            text = fallback_static_text()
            full.append(text)
            yield sse_line({"type": "content", "text": text})
        content = "".join(full)
        await save_report(
            db, user.id, order.order_id, ReportType.personality, sign,
            {
                "birth_date": body.birth_date, "birth_time": body.birth_time,
                "gender": body.gender, "birth_place_name": body.birth_place_name,
                "birth_place_lat": body.birth_place_lat, "birth_place_lon": body.birth_place_lon,
                "birth_tz": body.birth_tz,
                "astro_natal": natal.model_dump(mode="json") if natal else None,
            },
            content, report_id,
        )
        schedule_profile_update(user.id, "personality", content)
        yield sse_line({"type": "done", "report_id": report_id})

    return StreamingResponse(gen(), media_type="text/event-stream")


@router.post("/report/compatibility")
async def report_compatibility(
    body: CompatibilityReportBody,
    db: AsyncSession = Depends(get_db),
    user: User = Depends(get_current_user),
):
    order = await resolve_paid_order(db, user, body.order_id, ProductType.compatibility)
    p1, p2 = body.person1, body.person2
    d1, d2 = parse_birth_date_http(p1.birth_date), parse_birth_date_http(p2.birth_date)
    s1, s2 = sun_sign_from_date(d1), sun_sign_from_date(d2)
    m1, m2 = get_sign_meta(s1) or {}, get_sign_meta(s2) or {}
    natal1 = natal2 = syn = None
    try:
        natal1, natal2, syn = compute_synastry_data(
            d1, d2, time1=p1.birth_time, time2=p2.birth_time,
            place1=p1.birth_place_name, place2=p2.birth_place_name,
            lat1=p1.birth_place_lat, lon1=p1.birth_place_lon,
            lat2=p2.birth_place_lat, lon2=p2.birth_place_lon,
            tz1=p1.birth_tz, tz2=p2.birth_tz,
        )
    except Exception as e:
        logger.warning("synastry compute failed: %s", e)
    user_input = build_compatibility_user_input(
        p1.name or "A", p1.birth_date, s1, m1.get("sign_cn", s1),
        p2.name or "B", p2.birth_date, s2, m2.get("sign_cn", s2),
        natal1=natal1, natal2=natal2, synastry=syn,
    )
    settings = get_settings()
    primary = LLMServiceFactory.for_compatibility(settings)
    fallback = (
        None if settings.llm_platform.lower() == "bailian"
        else LLMServiceFactory.bailian_for_scene(settings, "compatibility")
    )
    report_id = f"rpt_{uuid.uuid4().hex[:16]}"

    async def gen() -> AsyncGenerator[str, None]:
        full: list[str] = []
        try:
            plan_input = build_plan_user_input("compatibility", user_input)
            planner = LLMServiceFactory.for_planner(settings)
            async for event in two_stage_report(
                planner_llm=planner, writer_llm=primary, writer_fallback=fallback,
                plan_user_input=plan_input, report_type="compatibility",
                fallback_full_prompt=user_input,
            ):
                if event.get("type") == "content":
                    full.append(event.get("text", ""))
                yield sse_line(event)
        except Exception:
            text = fallback_static_text()
            full.append(text)
            yield sse_line({"type": "content", "text": text})
        content = "".join(full)
        await save_report(
            db, user.id, order.order_id, ReportType.compatibility, f"{s1}+{s2}",
            {
                "person1": p1.model_dump(mode="json"), "person2": p2.model_dump(mode="json"),
                "synastry_score": syn.relationship_score if syn else None,
                "natal1": natal1.model_dump(mode="json") if natal1 else None,
                "natal2": natal2.model_dump(mode="json") if natal2 else None,
            },
            content, report_id,
        )
        schedule_profile_update(user.id, "compatibility", content)
        yield sse_line({"type": "done", "report_id": report_id})

    return StreamingResponse(gen(), media_type="text/event-stream")


@router.post("/report/annual")
async def report_annual(
    body: AnnualReportBody,
    db: AsyncSession = Depends(get_db),
    user: User = Depends(get_current_user),
):
    order = await resolve_paid_order(db, user, body.order_id, ProductType.annual)
    await db.refresh(user)
    bd = parse_birth_date_http(body.birth_date)
    sign = sun_sign_from_date(bd)
    meta = get_sign_meta(sign) or {}
    sign_cn = meta.get("sign_cn", sign)
    cy = datetime.utcnow().year
    raw_y = body.year if body.year is not None else cy
    year = min(max(int(raw_y), cy), cy + 1)
    natal = natal_for_user(
        user, bd, birth_time_override=body.birth_time,
        place_name=body.birth_place_name,
        lat=body.birth_place_lat, lon=body.birth_place_lon, tz=body.birth_tz,
    )
    ann = astro_compute_annual_summary(natal, year) if natal else None
    user_input = build_annual_user_input(
        sign, sign_cn, year, natal_chart=natal,
        annual_highlights=ann.highlights if ann else None,
    )
    settings = get_settings()
    primary = LLMServiceFactory.for_annual(settings)
    fallback = (
        None if settings.llm_platform.lower() == "bailian"
        else LLMServiceFactory.bailian_for_scene(settings, "annual")
    )
    stream_params = _stream_llm_params_for_annual(settings)
    report_id = f"rpt_{uuid.uuid4().hex[:16]}"

    async def gen() -> AsyncGenerator[str, None]:
        full: list[str] = []
        try:
            plan_input = build_plan_user_input("annual", user_input)
            planner = LLMServiceFactory.for_planner(settings)
            async for event in two_stage_report(
                planner_llm=planner, writer_llm=primary, writer_fallback=fallback,
                plan_user_input=plan_input, report_type="annual",
                fallback_full_prompt=user_input, fallback_stream_params=stream_params,
            ):
                if event.get("type") == "content":
                    full.append(event.get("text", ""))
                yield sse_line(event)
        except Exception:
            text = fallback_static_text()
            full.append(text)
            yield sse_line({"type": "content", "text": text})
        content = "".join(full)
        await save_report(
            db, user.id, order.order_id, ReportType.annual, sign,
            {
                "birth_date": body.birth_date, "year": year,
                "birth_time": body.birth_time, "birth_place_name": body.birth_place_name,
                "astro_natal": natal.model_dump(mode="json") if natal else None,
                "annual_highlights": ann.highlights if ann else [],
            },
            content, report_id,
        )
        schedule_profile_update(user.id, "annual", content)
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
    from fastapi import HTTPException

    pack = (body.pack or "").strip().lower()
    if pack not in _PACK_TO_PRODUCT:
        raise HTTPException(status_code=400, detail="pack must be career|love|growth")
    product = _PACK_TO_PRODUCT[pack]
    order = await resolve_paid_order(db, user, body.order_id, product)
    await db.refresh(user)
    bd = parse_birth_date_http(body.birth_date)
    sign = sun_sign_from_date(bd)
    meta = get_sign_meta(sign) or {}
    sign_cn = meta.get("sign_cn", sign)
    natal = natal_for_user(
        user, bd, birth_time_override=body.birth_time,
        place_name=body.birth_place_name,
        lat=body.birth_place_lat, lon=body.birth_place_lon, tz=body.birth_tz,
    )
    user_input = build_personality_dlc_user_input(
        pack, body.birth_date, sign, sign_cn,
        birth_time=body.birth_time, gender=body.gender, natal_chart=natal,
    )
    settings = get_settings()
    primary = LLMServiceFactory.for_report(settings)
    fallback = (
        None if settings.llm_platform.lower() == "bailian"
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
        await save_report(
            db, user.id, order.order_id, rtype, sign,
            {
                "pack": pack, "birth_date": body.birth_date,
                "birth_time": body.birth_time, "gender": body.gender,
                "birth_place_name": body.birth_place_name,
                "astro_natal": natal.model_dump(mode="json") if natal else None,
            },
            content, report_id,
        )
        yield sse_line({"type": "done", "report_id": report_id})

    return StreamingResponse(gen(), media_type="text/event-stream")


@router.post("/report/astro-event")
async def report_astro_event(
    body: AstroEventBody,
    db: AsyncSession = Depends(get_db),
    user: User = Depends(get_current_user),
):
    order = await resolve_paid_order(db, user, body.order_id, ProductType.astro_event)
    await db.refresh(user)
    bd = parse_birth_date_http(body.birth_date)
    sign = sun_sign_from_date(bd)
    meta = get_sign_meta(sign) or {}
    sign_cn = meta.get("sign_cn", sign)
    natal = natal_for_user(
        user, bd, birth_time_override=body.birth_time,
        place_name=body.birth_place_name,
        lat=body.birth_place_lat, lon=body.birth_place_lon, tz=body.birth_tz,
    )
    user_input = build_astro_event_user_input(
        body.event_key, body.birth_date, sign, sign_cn, natal_chart=natal,
    )
    settings = get_settings()
    primary = LLMServiceFactory.for_report(settings)
    fallback = (
        None if settings.llm_platform.lower() == "bailian"
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
        await save_report(
            db, user.id, order.order_id, ReportType.astro_event, sign,
            {
                "event_key": body.event_key, "birth_date": body.birth_date,
                "birth_time": body.birth_time,
                "astro_natal": natal.model_dump(mode="json") if natal else None,
            },
            content, report_id,
        )
        yield sse_line({"type": "done", "report_id": report_id})

    return StreamingResponse(gen(), media_type="text/event-stream")
