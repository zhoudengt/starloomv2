"""为 Chat 组装用户上下文，让 LLM 带着"记忆"回答。"""

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.report import Report
from app.models.user import User


async def build_chat_context(user: User, db: AsyncSession) -> str:
    """
    组装用户背景信息前缀。
    返回空字符串时行为等同现状，零退化风险。
    """
    parts: list[str] = []

    if user.sun_sign:
        parts.append(f"用户星座: {user.sun_sign}")
    if user.birth_date:
        parts.append(f"出生日期: {user.birth_date}")
    if getattr(user, "birth_time", None):
        parts.append(f"出生时间: {user.birth_time}")

    if user.ai_profile:
        tags = user.ai_profile.get("tags", [])
        if tags:
            parts.append(f"用户特征: {', '.join(tags[:10])}")
        summary = user.ai_profile.get("summary", "")
        if summary:
            parts.append(f"画像摘要: {summary[:200]}")

    result = await db.execute(
        select(Report)
        .where(Report.user_id == user.id)
        .order_by(Report.created_at.desc())
        .limit(3)
    )
    recent_reports = result.scalars().all()
    if recent_reports:
        snippets: list[str] = []
        for r in recent_reports:
            snippet = (r.content or "")[:150].replace("\n", " ")
            snippets.append(f"[{r.report_type.value}] {snippet}")
        parts.append("近期报告摘要:\n" + "\n".join(snippets))

    if not parts:
        return ""

    context = "\n".join(parts)
    if len(context) > 800:
        context = context[:800] + "\n..."

    return "=== 用户背景 ===\n" + context + "\n=== 用户问题 ===\n"
