"""Manually trigger daily guide generation (12 signs × 4 categories, fills gaps).

Also optional: refresh H5 carousel articles via ops pipeline (RSS + LLM).

Usage:
    cd backend && source .venv/bin/activate
    python ../scripts/seed_guides.py
    python ../scripts/seed_guides.py --articles
    python ../scripts/seed_guides.py --date 2026-04-11 --articles
"""

from __future__ import annotations

import argparse
import asyncio
import sys
import time
from datetime import date
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "backend"))

from app.database import AsyncSessionLocal, engine  # noqa: E402
from app.models.base import Base  # noqa: E402
from app.services.guide_generator import generate_all_guides_for_date  # noqa: E402
from app.utils.beijing_date import fortune_date_beijing  # noqa: E402


async def main() -> None:
    parser = argparse.ArgumentParser(description="Seed daily guides / H5 content")
    parser.add_argument(
        "--date",
        type=str,
        default="",
        help="YYYY-MM-DD (Beijing calendar day). Default: today Beijing.",
    )
    parser.add_argument(
        "--articles",
        action="store_true",
        help="Also run ops h5 pipeline (tips + carousel articles → MySQL).",
    )
    args = parser.parse_args()

    target: date = date.fromisoformat(args.date) if args.date else fortune_date_beijing()

    print(f"=== Seed Daily Guides for {target} (Beijing) ===")
    t0 = time.time()

    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    print("  DB tables ensured.")

    async with AsyncSessionLocal() as db:
        try:
            # Commits also happen inside generate_all_guides_for_date (per sign, so partial runs persist).
            count = await generate_all_guides_for_date(db, target, force=True)
            await db.commit()
            elapsed = time.time() - t0
            print(f"\n  Guides: saved {count} new rows in {elapsed:.1f}s")
        except Exception as e:
            await db.rollback()
            print(f"\n  Guides error: {e}")
            raise

    if args.articles:
        print("\n=== H5 articles + tips (ops.pipeline.run_h5_content) ===")
        t1 = time.time()
        from ops.pipeline import run_h5_content

        result = await run_h5_content(target, skip_articles=False)
        print(f"  Done in {time.time() - t1:.1f}s: {result}")

    await engine.dispose()


if __name__ == "__main__":
    asyncio.run(main())
