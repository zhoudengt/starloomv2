"""微博开放平台 trends（需 access_token；未配置则返回空）。"""

from __future__ import annotations

import logging
from typing import Any, List

import httpx

from ops.data_sources.base import HotKeywordResult

logger = logging.getLogger(__name__)


def fetch_weibo_hourly_trends(access_token: str, timeout: float = 12.0) -> HotKeywordResult:
    if not access_token.strip():
        return HotKeywordResult(source="weibo", keywords=[], fetched_at="")

    url = "https://api.weibo.com/2/trends/hourly.json"
    try:
        with httpx.Client(timeout=timeout) as client:
            r = client.get(url, params={"access_token": access_token})
            r.raise_for_status()
            data = r.json()
    except Exception as e:
        logger.warning("Weibo trends failed: %s", e)
        return HotKeywordResult(source="weibo", keywords=[], raw_meta={"error": str(e)})

    keywords: list[str] = []
    # 文档结构可能为 trends 列表，兼容多种形态
    trends = data.get("trends") or data.get("trend") or []
    if isinstance(trends, list):
        for block in trends:
            if isinstance(block, dict):
                name = block.get("name") or block.get("keyword") or block.get("query")
                if isinstance(name, str) and name.strip():
                    keywords.append(name.strip())
            elif isinstance(block, str):
                keywords.append(block.strip())
    from datetime import datetime

    return HotKeywordResult(
        source="weibo",
        keywords=keywords[:30],
        fetched_at=datetime.utcnow().isoformat() + "Z",
        raw_meta={"http_status": 200},
    )
