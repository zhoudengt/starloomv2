"""知乎热榜：抓取热门话题标题供内容角度匹配。

使用公开的知乎热榜页面解析，无需 API token。
"""

from __future__ import annotations

import logging
import re
from typing import List

import httpx

from ops.data_sources.base import NewsHeadline

logger = logging.getLogger(__name__)

USER_AGENT = (
    "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) "
    "AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
)

ZHIHU_HOT_API = "https://www.zhihu.com/api/v3/feed/topstory/hot-lists/total"


def fetch_zhihu_hot(limit: int = 20, timeout: float = 10.0) -> List[NewsHeadline]:
    """Fetch Zhihu trending topics. Returns headlines on success, empty on failure."""
    out: list[NewsHeadline] = []
    try:
        with httpx.Client(
            timeout=timeout,
            headers={
                "User-Agent": USER_AGENT,
                "Accept": "application/json",
            },
            follow_redirects=True,
        ) as client:
            r = client.get(ZHIHU_HOT_API, params={"limit": min(limit, 50)})
            r.raise_for_status()
            data = r.json()

        items = data.get("data", [])
        for item in items[:limit]:
            target = item.get("target", {})
            title = target.get("title", "").strip()
            if not title:
                continue
            qid = target.get("id", "")
            link = f"https://www.zhihu.com/question/{qid}" if qid else ""
            out.append(
                NewsHeadline(
                    source="zhihu",
                    title=title,
                    link=link,
                )
            )
    except Exception as e:
        logger.warning("Zhihu hot fetch failed: %s", e)

    return out
