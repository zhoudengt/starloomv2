"""只读 Redis：12 星座当日运势（与线上 GET /daily 同源）。"""

from __future__ import annotations

from datetime import date
from typing import Any, Dict, List

from app.services import cache_service
from app.utils.zodiac_calc import list_all_signs


async def fetch_twelve_daily(d: date) -> Dict[str, Dict[str, Any]]:
    out: Dict[str, Dict[str, Any]] = {}
    for meta in list_all_signs():
        slug = meta["sign"].lower()
        cached = await cache_service.get_daily_cached(slug, d)
        if cached:
            cn = cached.get("sign_cn") or meta["sign_cn"]
            out[slug] = {**cached, "sign_cn": cn, "sign": slug}
        else:
            out[slug] = {
                "sign": slug,
                "sign_cn": meta["sign_cn"],
                "overall_score": 70,
                "summary": f"{meta['sign_cn']}今日运势参考（缓存未命中，占位）。",
                "_placeholder": True,
            }
    return out
