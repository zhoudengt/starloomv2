"""Constellation: signs, daily fortune, paid reports (SSE)."""

from __future__ import annotations

import uuid
from datetime import date, datetime
from typing import Any, AsyncGenerator

from fastapi import APIRouter, Depends, HTTPException
from fastapi.responses import StreamingResponse
from sqlalchemy import select
from sqlalchemy.dialects.mysql import insert as mysql_insert
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.schemas import AnnualReportBody, CompatibilityReportBody, PersonalityReportBody
from app.config import get_settings
from app.database import get_db
from app.deps import get_current_user
from app.models.daily_fortune import DailyFortune
from app.models.order import Order, OrderStatus, ProductType
from app.models.report import Report, ReportType
from app.models.user import User
from app.prompts.annual import build_annual_prompt
from app.prompts.compatibility import build_compatibility_prompt
from app.prompts.daily_fortune import build_daily_prompt
from app.prompts.personality import build_personality_prompt
from app.services import cache_service
from app.services.llm_service import (
    LLMServiceFactory,
    fallback_static_text,
    generate_json_daily,
    stream_with_fallback,
)
from app.utils.stream_helper import sse_line
from app.utils.zodiac_calc import get_sign_meta, list_all_signs, parse_birth_date, sun_sign_from_date

router = APIRouter(prefix="/api/v1", tags=["constellation"])


@router.get("/signs")
async def list_signs() -> dict[str, Any]:
    return {"signs": list_all_signs()}


@router.get("/signs/{sign}")
async def get_sign(sign: str) -> dict[str, Any]:
    meta = get_sign_meta(sign)
    if not meta:
        raise HTTPException(status_code=404, detail="Unknown sign")
    return meta


@router.get("/daily/{sign}")
async def get_daily(sign: str, db: AsyncSession = Depends(get_db)) -> dict[str, Any]:
    meta = get_sign_meta(sign)
    if not meta:
        raise HTTPException(status_code=404, detail="Unknown sign")
    today = datetime.utcnow().date()
    cached = await cache_service.get_daily_cached(sign, today)
    if cached:
        return _wrap_daily_response(sign, meta["sign_cn"], today, cached)

    # MySQL backup
    row = await db.execute(
        select(DailyFortune).where(
            DailyFortune.sign == sign.lower(),
            DailyFortune.fortune_date == today,
        )
    )
    existing = row.scalar_one_or_none()
    if existing:
        await cache_service.set_daily_cached(sign, today, existing.content)
        return _wrap_daily_response(sign, meta["sign_cn"], today, existing.content)

    prompt = build_daily_prompt(meta["sign_cn"], today.isoformat())
    settings = get_settings()
    data = await generate_json_daily(
        settings, prompt, meta["sign_cn"], today.isoformat()
    )
    data = _normalize_daily_payload(data, meta["sign_cn"], today)

    await cache_service.set_daily_cached(sign, today, data)
    stmt = mysql_insert(DailyFortune).values(
        sign=sign.lower(),
        fortune_date=today,
        content=data,
    )
    stmt = stmt.on_duplicate_key_update(content=stmt.inserted.content)
    await db.execute(stmt)

    return _wrap_daily_response(sign, meta["sign_cn"], today, data)


def _normalize_daily_payload(data: dict, sign_cn: str, today: date) -> dict[str, Any]:
    defaults: dict[str, Any] = {
        "overall_score": 70,
        "love_score": 70,
        "career_score": 70,
        "wealth_score": 70,
        "health_score": 70,
        "lucky_color": "金色",
        "lucky_number": 7,
        "summary": f"{sign_cn}今日运势参考。",
        "love": "",
        "career": "",
        "wealth": "",
        "health": "",
        "advice": "",
    }
    merged = {**defaults, **{k: v for k, v in data.items() if not str(k).startswith("_")}}
    return merged


def _wrap_daily_response(sign: str, sign_cn: str, today: date, data: dict[str, Any]) -> dict[str, Any]:
    return {
        "sign": sign.lower(),
        "sign_cn": sign_cn,
        "date": today.isoformat(),
        **data,
    }


@router.get("/daily/all")
async def daily_all(db: AsyncSession = Depends(get_db)) -> dict[str, Any]:
    today = datetime.utcnow().date()
    summaries = []
    for meta in list_all_signs():
        slug = meta["sign"]
        m = get_sign_meta(slug)
        if not m:
            continue
        cached = await cache_service.get_daily_cached(slug, today)
        if cached:
            data = cached
        else:
            row = await db.execute(
                select(DailyFortune).where(
                    DailyFortune.sign == slug.lower(),
                    DailyFortune.fortune_date == today,
                )
            )
            existing = row.scalar_one_or_none()
            if existing:
                data = existing.content
            else:
                prompt = build_daily_prompt(m["sign_cn"], today.isoformat())
                settings = get_settings()
                data = await generate_json_daily(
                    settings, prompt, m["sign_cn"], today.isoformat()
                )
                data = _normalize_daily_payload(data, m["sign_cn"], today)
                await cache_service.set_daily_cached(slug, today, data)
                stmt = mysql_insert(DailyFortune).values(
                    sign=slug.lower(),
                    fortune_date=today,
                    content=data,
                )
                stmt = stmt.on_duplicate_key_update(content=stmt.inserted.content)
                await db.execute(stmt)
        summaries.append(
            {
                "sign": slug,
                "sign_cn": meta["sign_cn"],
                "overall_score": data.get("overall_score", 0),
                "summary": (data.get("summary") or "")[:80],
            }
        )
    return {"date": today.isoformat(), "items": summaries}


async def _verify_paid_order(
    db: AsyncSession,
    user: User,
    order_id: str,
    product: ProductType,
) -> Order:
    result = await db.execute(
        select(Order).where(
            Order.order_id == order_id,
            Order.user_id == user.id,
            Order.product_type == product,
        )
    )
    order = result.scalar_one_or_none()
    if not order or order.status != OrderStatus.paid:
        raise HTTPException(status_code=402, detail="Payment required or invalid order")
    return order


@router.post("/report/personality")
async def report_personality(
    body: PersonalityReportBody,
    db: AsyncSession = Depends(get_db),
    user: User = Depends(get_current_user),
):
    await _verify_paid_order(db, user, body.order_id, ProductType.personality)
    bd = parse_birth_date(body.birth_date)
    sign = sun_sign_from_date(bd)
    meta = get_sign_meta(sign) or {}
    sign_cn = meta.get("sign_cn", sign)
    prompt = build_personality_prompt(
        body.birth_date,
        sign,
        sign_cn,
        birth_time=body.birth_time,
        gender=body.gender,
    )
    settings = get_settings()
    primary = LLMServiceFactory.for_report(settings)
    fallback = LLMServiceFactory.bailian_fallback(settings)
    report_id = f"rpt_{uuid.uuid4().hex[:16]}"

    async def gen() -> AsyncGenerator[str, None]:
        full: list[str] = []
        try:
            async for chunk in stream_with_fallback(primary, fallback, prompt):
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
            body.order_id,
            ReportType.personality,
            sign,
            {"birth_date": body.birth_date, "birth_time": body.birth_time, "gender": body.gender},
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
    await _verify_paid_order(db, user, body.order_id, ProductType.compatibility)
    p1 = body.person1
    p2 = body.person2
    d1 = parse_birth_date(p1.birth_date)
    d2 = parse_birth_date(p2.birth_date)
    s1 = sun_sign_from_date(d1)
    s2 = sun_sign_from_date(d2)
    m1 = get_sign_meta(s1) or {}
    m2 = get_sign_meta(s2) or {}
    prompt = build_compatibility_prompt(
        p1.name or "A",
        p1.birth_date,
        s1,
        m1.get("sign_cn", s1),
        p2.name or "B",
        p2.birth_date,
        s2,
        m2.get("sign_cn", s2),
    )
    settings = get_settings()
    primary = LLMServiceFactory.for_compatibility(settings)
    fallback = LLMServiceFactory.bailian_fallback(settings)
    report_id = f"rpt_{uuid.uuid4().hex[:16]}"

    async def gen() -> AsyncGenerator[str, None]:
        full: list[str] = []
        try:
            async for chunk in stream_with_fallback(primary, fallback, prompt):
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
            body.order_id,
            ReportType.compatibility,
            f"{s1}+{s2}",
            {
                "person1": p1.model_dump(),
                "person2": p2.model_dump(),
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
    await _verify_paid_order(db, user, body.order_id, ProductType.annual)
    bd = parse_birth_date(body.birth_date)
    sign = sun_sign_from_date(bd)
    meta = get_sign_meta(sign) or {}
    sign_cn = meta.get("sign_cn", sign)
    year = body.year or datetime.utcnow().year
    prompt = build_annual_prompt(sign, sign_cn, year)
    settings = get_settings()
    primary = LLMServiceFactory.for_annual(settings)
    fallback = LLMServiceFactory.bailian_fallback(settings)
    report_id = f"rpt_{uuid.uuid4().hex[:16]}"

    async def gen() -> AsyncGenerator[str, None]:
        full: list[str] = []
        try:
            async for chunk in stream_with_fallback(primary, fallback, prompt):
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
            body.order_id,
            ReportType.annual,
            sign,
            {"birth_date": body.birth_date, "year": year},
            content,
            report_id,
        )
        yield sse_line({"type": "done", "report_id": report_id})

    return StreamingResponse(gen(), media_type="text/event-stream")


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
