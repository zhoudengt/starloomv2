#!/usr/bin/env python3
"""
Batch-generate daily fortunes for all 12 signs (cron ~00:30).
Run from repo root with backend on PYTHONPATH or: cd backend && ../.venv/bin/python ../scripts/generate_daily.py
"""

import asyncio
import os
import sys
from datetime import datetime

# Allow running as: python scripts/generate_daily.py from repo root
_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
_BACKEND = os.path.join(_ROOT, "backend")
if _BACKEND not in sys.path:
    sys.path.insert(0, _BACKEND)

from app.config import get_settings  # noqa: E402
from app.database import AsyncSessionLocal  # noqa: E402
from app.models.daily_fortune import DailyFortune  # noqa: E402
from app.prompts.daily_fortune import build_daily_user_input  # noqa: E402
from app.services import cache_service  # noqa: E402
from app.services.llm_service import generate_json_daily  # noqa: E402
from app.utils.zodiac_calc import list_all_signs  # noqa: E402
from sqlalchemy.dialects.mysql import insert as mysql_insert  # noqa: E402
def _normalize(data: dict, sign_cn: str, today) -> dict:
    defaults = {
        "overall_score": 70,
        "love_score": 70,
        "career_score": 70,
        "wealth_score": 70,
        "health_score": 70,
        "lucky_color": "金色",
        "lucky_number": 7,
        "summary": f"{sign_cn}今日运势参考。",
        "love": "",
        "career": "",
        "wealth": "",
        "health": "",
        "advice": "",
    }
    return {**defaults, **{k: v for k, v in data.items() if not str(k).startswith("_")}}


async def main() -> None:
    settings = get_settings()
    today = datetime.utcnow().date()
    async with AsyncSessionLocal() as session:
        for meta in list_all_signs():
            slug = meta["sign"]
            user_input = build_daily_user_input(meta["sign_cn"], today.isoformat())
            raw = await generate_json_daily(
                settings, user_input, meta["sign_cn"], today.isoformat()
            )
            data = _normalize(raw, meta["sign_cn"], today)
            await cache_service.set_daily_cached(slug, today, data)
            stmt = mysql_insert(DailyFortune).values(
                sign=slug.lower(),
                fortune_date=today,
                content=data,
            )
            stmt = stmt.on_duplicate_key_update(content=stmt.inserted.content)
            await session.execute(stmt)
        await session.commit()
    print(f"Done: {today.isoformat()} — 12 signs written to Redis + MySQL.")


if __name__ == "__main__":
    asyncio.run(main())
