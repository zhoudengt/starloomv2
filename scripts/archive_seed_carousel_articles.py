"""一次性：将种子文章 slug 标为 archived，避免与首页轮播「日更运营位」混排。

Usage:
    cd backend && source .venv/bin/activate
    python ../scripts/archive_seed_carousel_articles.py
"""

from __future__ import annotations

import asyncio
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "backend"))

from sqlalchemy import update  # noqa: E402

from app.database import AsyncSessionLocal  # noqa: E402
from app.models.article import Article, ArticleStatus  # noqa: E402

# 与 scripts/seed_articles.py SEED_ARTICLES 中 slug 对齐
SEED_SLUGS = [
    "sun-sign-and-self",
    "pairing-communication",
    "annual-focus-habits",
    "astro-events-calendar",
    "moon-and-rest",
]


async def main() -> None:
    from app.database import engine

    try:
        async with AsyncSessionLocal() as session:
            res = await session.execute(
                update(Article)
                .where(Article.slug.in_(SEED_SLUGS))
                .values(status=ArticleStatus.archived)
            )
            await session.commit()
            print(f"Archived rows (matched slugs): {res.rowcount}")
            print("Slugs:", ", ".join(SEED_SLUGS))
    finally:
        await engine.dispose()


if __name__ == "__main__":
    asyncio.run(main())
