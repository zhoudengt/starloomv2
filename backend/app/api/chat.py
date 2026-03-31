"""AI chat advisor (SSE)."""

import uuid
from typing import AsyncGenerator

from fastapi import APIRouter, Depends, HTTPException
from fastapi.responses import StreamingResponse
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.schemas import ChatBody
from app.config import get_settings
from app.database import get_db
from app.deps import get_current_user
from app.models.order import Order, OrderStatus, ProductType
from app.models.user import User
from app.services.llm_service import LLMServiceFactory, stream_with_fallback
from app.utils.stream_helper import sse_line

router = APIRouter(prefix="/api/v1", tags=["chat"])


@router.post("/chat")
async def chat_advisor(
    body: ChatBody,
    db: AsyncSession = Depends(get_db),
    user: User = Depends(get_current_user),
):
    if not body.order_id:
        raise HTTPException(status_code=400, detail="order_id required for paid chat")
    result = await db.execute(
        select(Order).where(
            Order.order_id == body.order_id,
            Order.user_id == user.id,
            Order.product_type == ProductType.chat,
        )
    )
    order = result.scalar_one_or_none()
    if not order or order.status != OrderStatus.paid:
        raise HTTPException(status_code=402, detail="Payment required for chat")

    settings = get_settings()
    primary = LLMServiceFactory.for_chat(settings)
    fallback = LLMServiceFactory.bailian_fallback(settings)
    prompt = (
        "你是一位温和专业的星座性格分析顾问。请基于星座文化给出参考性建议，"
        "避免绝对化预测；不做医疗或投资建议。用户问题：\n"
        + body.message
    )

    async def gen() -> AsyncGenerator[str, None]:
        async for chunk in stream_with_fallback(primary, fallback, prompt):
            yield sse_line({"type": "content", "text": chunk})
        yield sse_line({"type": "done", "report_id": f"chat_{uuid.uuid4().hex[:12]}"})

    return StreamingResponse(gen(), media_type="text/event-stream")
