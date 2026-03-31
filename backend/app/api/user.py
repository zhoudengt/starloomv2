"""User login, profile, orders."""

from typing import Any, List

from fastapi import APIRouter, Depends
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.schemas import UserLoginBody
from app.auth.jwt import create_access_token
from app.database import get_db
from app.deps import get_current_user
from app.models.order import Order
from app.models.user import User

router = APIRouter(prefix="/api/v1/user", tags=["user"])


@router.post("/login")
async def login(body: UserLoginBody, db: AsyncSession = Depends(get_db)) -> dict[str, Any]:
    result = await db.execute(select(User).where(User.device_id == body.device_id))
    user = result.scalar_one_or_none()
    if not user:
        user = User(device_id=body.device_id)
        db.add(user)
        await db.flush()

    token = create_access_token(str(user.id), extra={"device_id": user.device_id})
    return {
        "access_token": token,
        "token_type": "bearer",
        "user_id": user.id,
        "device_id": user.device_id,
    }


@router.get("/profile")
async def profile(user: User = Depends(get_current_user)) -> dict[str, Any]:
    return {
        "id": user.id,
        "device_id": user.device_id,
        "phone": user.phone,
        "nickname": user.nickname,
        "birth_date": user.birth_date.isoformat() if user.birth_date else None,
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
