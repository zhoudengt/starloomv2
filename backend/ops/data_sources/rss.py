"""RSS/Atom：仅解析标题，供热点叙事锚点（合规 HTTP GET）。"""

from __future__ import annotations

import logging
import xml.etree.ElementTree as ET
from typing import List
from urllib.parse import urlparse

import httpx

from ops.data_sources.base import NewsHeadline

logger = logging.getLogger(__name__)

USER_AGENT = "StarLoomOps/0.1 (RSS reader; +https://github.com)"


def fetch_rss_titles(url: str, limit: int = 12, timeout: float = 12.0) -> List[NewsHeadline]:
    host = urlparse(url).netloc or "rss"
    out: list[NewsHeadline] = []
    try:
        with httpx.Client(timeout=timeout, headers={"User-Agent": USER_AGENT}) as client:
            r = client.get(url)
            r.raise_for_status()
    except Exception as e:
        logger.warning("RSS fetch failed %s: %s", url, e)
        return out

    try:
        root = ET.fromstring(r.content)
    except ET.ParseError as e:
        logger.warning("RSS parse failed %s: %s", url, e)
        return out

    def _lt(tag: str) -> str:
        return tag.split("}")[-1] if "}" in tag else tag

    items: list[ET.Element] = []
    ch = root.find("channel")
    if ch is not None:
        items.extend(ch.findall("item"))
    for el in root.iter():
        if _lt(el.tag) == "entry":
            items.append(el)

    for item in items:
        title_el = None
        link_el = ""
        for child in item:
            ct = _lt(child.tag)
            if ct == "title" and (child.text or "").strip():
                title_el = (child.text or "").strip()
            if ct == "link":
                link_el = (child.text or child.get("href") or "").strip()
        if title_el:
            out.append(
                NewsHeadline(
                    source=f"rss:{host}",
                    title=title_el,
                    link=link_el,
                )
            )
        if len(out) >= limit:
            break

    return out[:limit]
