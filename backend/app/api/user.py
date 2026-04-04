"""User login, profile, orders, reports."""

from datetime import time as dt_time
from typing import Any, List

from fastapi import APIRouter, Depends
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.schemas import UserLoginBody, UserProfilePatch
from app.auth.jwt import create_access_token
from app.database import get_db
from app.deps import get_current_user
from app.models.order import Order
from app.models.report import Report
from app.models.user import Gender, User
from app.utils.zodiac_calc import parse_birth_date_http, sun_sign_from_date

router = APIRouter(prefix="/api/v1/user", tags=["user"])


@router.post("/login")
async def login(body: UserLoginBody, db: AsyncSession = Depends(get_db)) -> dict[str, Any]:
    result = await db.execute(select(User).where(User.device_id == body.device_id))
    user = result.scalar_one_or_none()
    if not user:
        user = User(device_id=body.device_id)
        db.add(user)
        await db.flush()
        if body.referral_code:
            from app.services.growth_helpers import bind_referral_if_new_user

            await bind_referral_if_new_user(db, user, body.referral_code)

    token = create_access_token(str(user.id), extra={"device_id": user.device_id})
    return {
        "access_token": token,
        "token_type": "bearer",
        "user_id": user.id,
        "device_id": user.device_id,
    }


@router.get("/profile")
async def profile(
    db: AsyncSession = Depends(get_db),
    user: User = Depends(get_current_user),
) -> dict[str, Any]:
    from app.services.growth_helpers import get_or_create_growth_profile

    gp = await get_or_create_growth_profile(db, user)
    return {
        "id": user.id,
        "device_id": user.device_id,
        "phone": user.phone,
        "nickname": user.nickname,
        "birth_date": user.birth_date.isoformat() if user.birth_date else None,
        "birth_time": user.birth_time.strftime("%H:%M") if user.birth_time else None,
        "birth_place_name": user.birth_place_name,
        "birth_place_lat": user.birth_place_lat,
        "birth_place_lon": user.birth_place_lon,
        "birth_tz": user.birth_tz,
        "sun_sign": user.sun_sign,
        "gender": user.gender.value if user.gender else None,
        "referral_code": gp.referral_code,
        "credit_yuan": str(gp.credit_yuan),
        "season_pass_until": gp.season_pass_until.isoformat() if gp.season_pass_until else None,
    }


@router.patch("/profile")
async def patch_profile(
    body: UserProfilePatch,
    db: AsyncSession = Depends(get_db),
    user: User = Depends(get_current_user),
) -> dict[str, Any]:
    if body.nickname is not None:
        user.nickname = body.nickname.strip() or None
    if body.birth_date is not None:
        bd = parse_birth_date_http(body.birth_date)
        user.birth_date = bd
        user.sun_sign = sun_sign_from_date(bd)
    if body.birth_time is not None and body.birth_time.strip():
        parts = body.birth_time.strip().split(":")
        h = int(parts[0])
        m = int(parts[1]) if len(parts) > 1 else 0
        user.birth_time = dt_time(h % 24, min(m, 59))
    if body.gender is not None:
        if body.gender in ("male", "female", "unknown"):
            user.gender = Gender(body.gender)
    if body.birth_place_name is not None:
        user.birth_place_name = body.birth_place_name.strip() or None
    if body.birth_place_lat is not None:
        user.birth_place_lat = body.birth_place_lat
    if body.birth_place_lon is not None:
        user.birth_place_lon = body.birth_place_lon
    if body.birth_tz is not None:
        user.birth_tz = body.birth_tz.strip() or None
    await db.flush()
    return {
        "id": user.id,
        "device_id": user.device_id,
        "phone": user.phone,
        "nickname": user.nickname,
        "birth_date": user.birth_date.isoformat() if user.birth_date else None,
        "birth_time": user.birth_time.strftime("%H:%M") if user.birth_time else None,
        "birth_place_name": user.birth_place_name,
        "birth_place_lat": user.birth_place_lat,
        "birth_place_lon": user.birth_place_lon,
        "birth_tz": user.birth_tz,
        "sun_sign": user.sun_sign,
        "gender": user.gender.value if user.gender else None,
    }


@router.get("/orders")
async def orders(
    db: AsyncSession = Depends(get_db),
    user: User = Depends(get_current_user),
) -> dict[str, Any]:
    result = await db.execute(
        select(Order).where(Order.user_id == user.id).order_by(Order.created_at.desc())
    )
    rows: List[Order] = list(result.scalars().all())
    return {
        "items": [
            {
                "order_id": o.order_id,
                "product_type": o.product_type.value,
                "amount": str(o.amount),
                "status": o.status.value,
                "created_at": o.created_at.isoformat() if o.created_at else None,
            }
            for o in rows
        ]
    }


def _excerpt(content: str, max_len: int = 120) -> str:
    t = (content or "").replace("\n", " ").replace("#", "").strip()
    if len(t) <= max_len:
        return t
    return t[: max_len - 1] + "…"


@router.get("/reports")
async def user_reports(
    db: AsyncSession = Depends(get_db),
    user: User = Depends(get_current_user),
) -> dict[str, Any]:
    result = await db.execute(
        select(Report).where(Report.user_id == user.id).order_by(Report.created_at.desc())
    )
    rows: List[Report] = list(result.scalars().all())
    return {
        "items": [
            {
                "report_id": r.report_id,
                "report_type": r.report_type.value,
                "sign": r.sign,
                "created_at": r.created_at.isoformat() if r.created_at else None,
                "excerpt": _excerpt(r.content),
                "order_id": r.order_id,
            }
            for r in rows
        ]
    }
