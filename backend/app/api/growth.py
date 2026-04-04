"""Growth: group buy, assist, compatibility share preview, cards, profile."""

from __future__ import annotations

import uuid
from datetime import datetime, timedelta
from typing import Any

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.schemas import AssistCreateBody, CompatShareCreateBody, GroupBuyCreateBody
from app.database import get_db
from app.deps import get_current_user
from app.models.growth import (
    AssistRecord,
    AssistTask,
    CompatibilityShareToken,
    GroupBuy,
    GroupBuyMember,
    UserGrowthProfile,
    UserZodiacCard,
)
from app.models.user import User
from app.services.growth_helpers import get_or_create_growth_profile

router = APIRouter(prefix="/api/v1/growth", tags=["growth"])


@router.get("/me")
async def growth_me(
    db: AsyncSession = Depends(get_db),
    user: User = Depends(get_current_user),
) -> dict[str, Any]:
    gp = await get_or_create_growth_profile(db, user)
    return {
        "referral_code": gp.referral_code,
        "credit_yuan": str(gp.credit_yuan),
        "season_pass_until": gp.season_pass_until.isoformat() if gp.season_pass_until else None,
        "referred_by_bound": gp.referred_by_user_id is not None,
    }


@router.get("/cards")
async def list_zodiac_cards(
    db: AsyncSession = Depends(get_db),
    user: User = Depends(get_current_user),
) -> dict[str, Any]:
    result = await db.execute(select(UserZodiacCard).where(UserZodiacCard.user_id == user.id))
    rows = list(result.scalars().all())
    return {
        "items": [{"sign": r.sign, "source": r.source, "created_at": r.created_at.isoformat()} for r in rows],
        "count": len(rows),
    }


@router.post("/group-buy")
async def create_group_buy(
    body: GroupBuyCreateBody,
    db: AsyncSession = Depends(get_db),
    user: User = Depends(get_current_user),
) -> dict[str, Any]:
    product_type = body.product_type
    if product_type not in ("compatibility", "personality"):
        raise HTTPException(status_code=400, detail="Invalid product_type for group buy")
    target = body.target_count if body.target_count in (2, 3) else 2
    public_id = uuid.uuid4().hex
    expires = datetime.utcnow() + timedelta(hours=24)
    gb = GroupBuy(
        public_id=public_id,
        leader_user_id=user.id,
        product_type=product_type,
        target_count=target,
        member_count=0,
        status="open",
        expires_at=expires,
    )
    db.add(gb)
    await db.flush()
    return {
        "public_id": public_id,
        "target_count": target,
        "expires_at": expires.isoformat(),
        "product_type": product_type,
    }


@router.get("/group-buy/{public_id}")
async def get_group_buy(public_id: str, db: AsyncSession = Depends(get_db)) -> dict[str, Any]:
    result = await db.execute(select(GroupBuy).where(GroupBuy.public_id == public_id.strip()))
    gb = result.scalar_one_or_none()
    if not gb:
        raise HTTPException(status_code=404, detail="Group not found")
    return {
        "public_id": gb.public_id,
        "product_type": gb.product_type,
        "target_count": gb.target_count,
        "member_count": gb.member_count,
        "status": gb.status,
        "expires_at": gb.expires_at.isoformat(),
    }


@router.post("/assist/create")
async def create_assist(
    body: AssistCreateBody,
    db: AsyncSession = Depends(get_db),
    user: User = Depends(get_current_user),
) -> dict[str, Any]:
    report_id = (body.report_id or "").strip() or None
    task_id = f"ast_{uuid.uuid4().hex[:20]}"
    task = AssistTask(
        task_id=task_id,
        owner_user_id=user.id,
        required_count=3,
        current_count=0,
        report_id=report_id,
        reward_unlocked=False,
    )
    db.add(task)
    await db.flush()
    return {"task_id": task_id, "required_count": 3, "current_count": 0}


@router.get("/assist/{task_id}")
async def get_assist(task_id: str, db: AsyncSession = Depends(get_db)) -> dict[str, Any]:
    result = await db.execute(select(AssistTask).where(AssistTask.task_id == task_id.strip()))
    t = result.scalar_one_or_none()
    if not t:
        raise HTTPException(status_code=404, detail="Task not found")
    return {
        "task_id": t.task_id,
        "current_count": t.current_count,
        "required_count": t.required_count,
        "reward_unlocked": t.reward_unlocked,
    }


@router.post("/assist/{task_id}/help")
async def help_assist(
    task_id: str,
    db: AsyncSession = Depends(get_db),
    user: User = Depends(get_current_user),
) -> dict[str, Any]:
    result = await db.execute(select(AssistTask).where(AssistTask.task_id == task_id.strip()))
    t = result.scalar_one_or_none()
    if not t:
        raise HTTPException(status_code=404, detail="Task not found")
    if user.id == t.owner_user_id:
        raise HTTPException(status_code=400, detail="Cannot help your own task")
    if t.reward_unlocked:
        return {"ok": True, "current_count": t.current_count, "reward_unlocked": True}
    existing = await db.execute(
        select(AssistRecord).where(
            AssistRecord.task_id == t.task_id,
            AssistRecord.helper_user_id == user.id,
        )
    )
    if existing.scalar_one_or_none():
        return {"ok": True, "current_count": t.current_count, "reward_unlocked": t.reward_unlocked}
    db.add(AssistRecord(task_id=t.task_id, helper_user_id=user.id))
    t.current_count += 1
    if t.current_count >= t.required_count:
        t.reward_unlocked = True
    await db.flush()
    return {
        "ok": True,
        "current_count": t.current_count,
        "reward_unlocked": t.reward_unlocked,
    }


@router.post("/share/compatibility")
async def create_compat_share(
    body: CompatShareCreateBody,
    db: AsyncSession = Depends(get_db),
    user: User = Depends(get_current_user),
) -> dict[str, Any]:
    payload = {
        "person1_name": body.person1_name,
        "person2_name": body.person2_name,
        "preview_score": body.preview_score,
    }
    token = uuid.uuid4().hex + uuid.uuid4().hex[:8]
    expires = datetime.utcnow() + timedelta(days=7)
    row = CompatibilityShareToken(
        token=token,
        owner_user_id=user.id,
        payload=payload,
        expires_at=expires,
    )
    db.add(row)
    await db.flush()
    return {"token": token, "expires_at": expires.isoformat()}


@router.get("/share/compatibility/{token}")
async def get_compat_share(token: str, db: AsyncSession = Depends(get_db)) -> dict[str, Any]:
    result = await db.execute(
        select(CompatibilityShareToken).where(CompatibilityShareToken.token == token.strip())
    )
    row = result.scalar_one_or_none()
    if not row or row.expires_at < datetime.utcnow():
        raise HTTPException(status_code=404, detail="Link expired or invalid")
    p = dict(row.payload)
    preview_score = int(p.get("preview_score") or 87)
    return {
        "preview_score": preview_score,
        "hint": "双人合盘性格与沟通参考（摘要）",
        "person1_name": p.get("person1_name") or "TA",
        "person2_name": p.get("person2_name") or "你",
        "blur": True,
        "cta": "解锁完整相处与沟通建议",
    }
