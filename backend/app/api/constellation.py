"""Constellation: signs, quicktest, report detail.

Heavy endpoints (daily fortune, paid reports, season pass) have been split into
daily.py, reports.py, and season.py respectively. This file re-exports their
routers for backward-compatible registration in main.py.
"""

from __future__ import annotations

from datetime import time as dt_time
from typing import Any

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.api._report_helpers import natal_for_user
from app.api.schemas import QuickTestBody
from app.database import get_db
from app.deps import get_current_user
from app.models.report import Report
from app.models.user import Gender, User
from app.services.astro_service import compute_quicktest_bundle
from app.utils.zodiac_calc import get_sign_meta, list_all_signs, parse_birth_date_http, sun_sign_from_date

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
    natal = natal_for_user(
        user, bd,
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
        "content_ir": rep.content_ir,
        "created_at": rep.created_at.isoformat() if rep.created_at else None,
        "order_id": rep.order_id,
    }
