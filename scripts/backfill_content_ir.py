"""One-off: populate body_ir / content_ir from existing Markdown columns.

Requires DB migration: scripts/migrations/add_content_ir_columns.sql

Usage:
  cd backend && source .venv/bin/activate
  python ../scripts/backfill_content_ir.py
"""

from __future__ import annotations

import asyncio
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "backend"))

from sqlalchemy import select, update  # noqa: E402

from app.database import AsyncSessionLocal, engine  # noqa: E402
from app.models.article import Article  # noqa: E402
from app.models.daily_guide import DailyGuide  # noqa: E402
from app.models.report import Report  # noqa: E402
from app.services.ir_converter import markdown_to_ir  # noqa: E402


async def main() -> None:
    async with AsyncSessionLocal() as db:
        # Articles
        r = await db.execute(select(Article).where(Article.body_ir.is_(None)))
        for a in r.scalars().all():
            ir = markdown_to_ir(
                a.body,
                {"title": a.title, "cover_image": a.cover_image},
            )
            await db.execute(update(Article).where(Article.id == a.id).values(body_ir=ir))
        # Daily guides
        r2 = await db.execute(select(DailyGuide).where(DailyGuide.content_ir.is_(None)))
        for g in r2.scalars().all():
            ir = markdown_to_ir(
                g.content,
                {"title": g.title, "transit_basis": g.transit_basis or ""},
            )
            await db.execute(update(DailyGuide).where(DailyGuide.id == g.id).values(content_ir=ir))
        # Reports
        r3 = await db.execute(select(Report).where(Report.content_ir.is_(None)))
        for rep in r3.scalars().all():
            ir = markdown_to_ir(rep.content, {})
            await db.execute(update(Report).where(Report.id == rep.id).values(content_ir=ir))

        await db.commit()
        print("backfill_content_ir: ok")
    await engine.dispose()


if __name__ == "__main__":
    asyncio.run(main())
