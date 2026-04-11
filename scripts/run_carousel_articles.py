"""一次性生成当日首页轮播短文（tags=carousel）：NewsNow/RSS + 页面 meta + 百炼改写，需 BAILIAN_API_KEY。

Usage:
    cd backend && .venv/bin/python ../scripts/run_carousel_articles.py
    cd backend && .venv/bin/python ../scripts/run_carousel_articles.py --force
"""

from __future__ import annotations

import argparse
import asyncio
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "backend"))

from app.database import AsyncSessionLocal, engine  # noqa: E402
from app.services.article_scraper import generate_carousel_articles  # noqa: E402
from app.utils.beijing_date import fortune_date_beijing  # noqa: E402


async def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "--force",
        action="store_true",
        help="删除当日已有 carousel 标记文章后重新生成",
    )
    args = parser.parse_args()
    d = fortune_date_beijing()
    async with AsyncSessionLocal() as db:
        try:
            n = await generate_carousel_articles(db, d, force=args.force)
            await db.commit()
            print(f"Beijing date={d.isoformat()} saved={n}")
        except Exception:
            await db.rollback()
            raise
        finally:
            await engine.dispose()


if __name__ == "__main__":
    asyncio.run(main())
