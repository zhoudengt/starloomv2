"""小红书热帖标题：从公开的发现页/搜索接口获取热门话题。

小红书没有公开 API，这里使用搜索建议接口获取当前热门关键词，
以及通过 web 端接口获取热门笔记标题。降级时返回空列表。
"""

from __future__ import annotations

import logging
from typing import List

import httpx

from ops.data_sources.base import HotKeywordResult, NewsHeadline

logger = logging.getLogger(__name__)

USER_AGENT = (
    "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) "
    "AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
)

XHS_SUGGEST_URL = "https://edith.xiaohongshu.com/api/sns/web/v1/search/hot_list"


def fetch_xhs_hot_keywords(timeout: float = 8.0) -> HotKeywordResult:
    """Fetch Xiaohongshu trending keywords from the public hot list endpoint."""
    keywords: list[str] = []
    try:
        with httpx.Client(
            timeout=timeout,
            headers={"User-Agent": USER_AGENT},
            follow_redirects=True,
        ) as client:
            r = client.get(XHS_SUGGEST_URL)
            if r.status_code == 200:
                data = r.json()
                items = data.get("data", {}).get("items", [])
                for item in items:
                    title = item.get("title", "").strip()
                    if title:
                        keywords.append(title)
    except Exception as e:
        logger.warning("XHS hot keywords fetch failed: %s", e)

    return HotKeywordResult(
        source="xiaohongshu",
        keywords=keywords[:30],
        fetched_at="",
    )


_ASTRO_KEYWORDS = [
    "星座", "水逆", "满月", "新月", "运势", "水星", "金星", "火星",
    "木星", "土星", "天蝎", "白羊", "金牛", "双子", "巨蟹", "狮子",
    "处女", "天秤", "射手", "摩羯", "水瓶", "双鱼",
]


def fetch_xhs_astro_titles(
    search_terms: List[str] | None = None,
    limit: int = 15,
    timeout: float = 10.0,
) -> List[NewsHeadline]:
    """Search XHS for astrology-related note titles.

    Since XHS web search requires cookies/signatures, this is a best-effort
    implementation that will gracefully degrade to empty results.
    """
    out: list[NewsHeadline] = []
    terms = search_terms or ["星座运势", "水逆"]

    for term in terms[:3]:
        try:
            with httpx.Client(
                timeout=timeout,
                headers={"User-Agent": USER_AGENT},
                follow_redirects=True,
            ) as client:
                r = client.get(
                    "https://www.xiaohongshu.com/search_result",
                    params={"keyword": term, "type": 1},
                )
                if r.status_code != 200:
                    continue

                import re
                titles = re.findall(r'"title"\s*:\s*"([^"]{4,60})"', r.text)
                for title in titles[:limit]:
                    if any(kw in title for kw in _ASTRO_KEYWORDS):
                        out.append(
                            NewsHeadline(
                                source="xiaohongshu",
                                title=title,
                                link="",
                            )
                        )
        except Exception as e:
            logger.debug("XHS search for '%s' failed: %s", term, e)
            continue

    seen: set[str] = set()
    deduped: list[NewsHeadline] = []
    for h in out:
        if h.title not in seen:
            seen.add(h.title)
            deduped.append(h)
    return deduped[:limit]
