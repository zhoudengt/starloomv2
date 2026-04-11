"""首页轮播：聚合热点（NewsNow 风格 API + RSS 回退）→ 抓取摘要与封面 → 百炼改写入库。"""

from __future__ import annotations

import asyncio
import hashlib
import json
import logging
import re
import xml.etree.ElementTree as ET
from datetime import date
from typing import Any
from urllib.parse import urljoin, urlparse, urlunparse

import httpx
from sqlalchemy import delete, func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.config import Settings, get_settings
from app.models.article import Article, ArticleCategory, ArticleStatus
from app.services.ir_converter import markdown_to_ir

logger = logging.getLogger(__name__)

CAROUSEL_TAG = "carousel"
MIN_BODY_CHARS = 1000
LLM_TIMEOUT = 120.0
PAGE_TIMEOUT = 18.0
NEWSNOW_TIMEOUT = 20.0

_BANNED_WORDS = ["算命", "占卜", "迷信", "神棍"]

BROWSER_UA = (
    "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 "
    "(KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
)

_POS_KW = (
    "星座 星象 月亮 太阳 水星 金星 火星 木星 土星 天王 海王 冥王 水逆 满月 新月 "
    "情感 恋爱 分手 复合 婚姻 职场 同事 老板 离职 情绪 心理 焦虑 睡眠 人际 社交 "
    "健康 养生 消费 旅行 家庭 亲子 明星 热议 爆 生活 成长 自我 AI 科技 互联网"
).split()

_NEG_KW = "足球 彩票 股指 期货 原油 黄金走势".split()

_SYSTEM_REWRITE = """\
你是 StarLoom 星座内容主编。你会收到「热点素材」：标题、较长摘录、原文链接（仅供把握话题与事实脉络，勿在正文中输出 URL）。

任务：把素材改写成一篇面向国内 H5 用户的**原创**长文：话题与观点来自素材，表达必须彻底重写，不得逐句抄袭新闻媒体。

硬性规则：
1. 语气：有观点、可读、可转发；结合「星象节奏/情绪觉察/人际沟通/自我成长」中至少两处视角，自然扣题，不要硬套星座标签。
2. 正文为 Markdown：至少 4 个 ### 小节；每节 2–4 段；**全文总字数 1200–2200 个汉字**（偏少不合格）。
3. 结构建议：开篇点题 → 现象拆解 → 可执行的小建议/清单 → 温和收尾；避免空洞金句堆砌。
4. 禁用「算命」「占卜」「迷信」等词；避免「一定」「必须」等绝对化用语。
5. 只输出一个 JSON 对象，不要其它说明文字。

JSON 格式：
{"title":"18字内标题","body":"Markdown正文","slug_hint":"英文或拼音短词，用于URL"}
"""


def _compliance_filter(text: str) -> str:
    for word in _BANNED_WORDS:
        text = text.replace(word, "星象参考")
    return text


def _normalize_url(u: str) -> str:
    u = (u or "").strip()
    if not u:
        return ""
    p = urlparse(u)
    return urlunparse((p.scheme or "https", p.netloc, p.path, "", "", ""))


def _source_hash(url: str) -> str:
    return hashlib.sha256(_normalize_url(url).encode("utf-8")).hexdigest()[:20]


def _score_title(title: str) -> float:
    t = title or ""
    s = 0.0
    for w in _POS_KW:
        if w and w in t:
            s += 1.2
    for w in _NEG_KW:
        if w and w in t:
            s -= 2.0
    if len(t) < 6:
        s -= 3.0
    return s


def _lt(tag: str) -> str:
    return tag.split("}")[-1] if "}" in tag else tag


def _parse_rss_xml(content: bytes, feed_url: str, limit: int) -> list[dict[str, str]]:
    host = urlparse(feed_url).netloc or "rss"
    out: list[dict[str, str]] = []
    try:
        root = ET.fromstring(content)
    except ET.ParseError as e:
        logger.warning("RSS parse error %s: %s", feed_url, e)
        return out

    items: list[ET.Element] = []
    ch = root.find("channel")
    if ch is not None:
        items.extend(ch.findall("item"))
    for el in root.iter():
        if _lt(el.tag) == "entry":
            items.append(el)

    for item in items:
        title_el = ""
        link_el = ""
        for child in item:
            ct = _lt(child.tag)
            if ct == "title" and (child.text or "").strip():
                title_el = (child.text or "").strip()
            if ct == "link":
                link_el = (child.text or child.get("href") or "").strip()
        if title_el and link_el:
            out.append(
                {
                    "title": title_el,
                    "url": link_el,
                    "source": f"rss:{host}",
                }
            )
        if len(out) >= limit:
            break
    return out


def _normalize_newsnow_payload(data: Any) -> list[dict[str, str]]:
    raw_list: list[Any]
    if isinstance(data, list):
        raw_list = data
    elif isinstance(data, dict):
        raw_list = (
            data.get("items")
            or data.get("data")
            or data.get("list")
            or data.get("news")
            or []
        )
        if not isinstance(raw_list, list):
            raw_list = []
    else:
        return []

    out: list[dict[str, str]] = []
    for x in raw_list:
        if not isinstance(x, dict):
            continue
        title = (x.get("title") or x.get("name") or x.get("text") or "").strip()
        url = (x.get("url") or x.get("link") or x.get("href") or "").strip()
        if title and url:
            src = (x.get("source") or x.get("from") or "newsnow").strip()
            out.append({"title": title, "url": url, "source": f"newsnow:{src}"})
    return out


async def _fetch_newsnow_source(
    client: httpx.AsyncClient, base: str, source_id: str
) -> list[dict[str, str]]:
    url = f"{base.rstrip('/')}?id={source_id.strip()}&latest"
    try:
        r = await client.get(
            url,
            headers={
                "User-Agent": BROWSER_UA,
                "Accept": "application/json,text/plain,*/*",
            },
        )
        text = r.text.strip()
        if r.status_code != 200:
            logger.warning("NewsNow HTTP %s for id=%s", r.status_code, source_id)
            return []
        if text.startswith("<!DOCTYPE") or text.startswith("<html"):
            logger.warning("NewsNow returned HTML for id=%s (blocked or wrong URL)", source_id)
            return []
        data = r.json()
    except Exception as e:
        logger.warning("NewsNow fetch failed id=%s: %s", source_id, e)
        return []
    items = _normalize_newsnow_payload(data)
    for it in items:
        it["source"] = f"newsnow:{source_id}"
    return items


async def _fetch_rss_headlines(
    client: httpx.AsyncClient, feed_url: str, limit: int
) -> list[dict[str, str]]:
    try:
        r = await client.get(feed_url, headers={"User-Agent": BROWSER_UA})
        r.raise_for_status()
    except Exception as e:
        logger.warning("RSS GET failed %s: %s", feed_url, e)
        return []
    return _parse_rss_xml(r.content, feed_url, limit)


def _extract_og(html: str, page_url: str) -> dict[str, str]:
    out: dict[str, str] = {}
    for prop, key in (
        ("og:image", "image"),
        ("og:title", "title"),
        ("og:description", "description"),
    ):
        pat1 = re.compile(
            rf'<meta[^>]+property=["\']{re.escape(prop)}["\'][^>]+content=["\']([^"\']+)["\']',
            re.I,
        )
        pat2 = re.compile(
            rf'<meta[^>]+content=["\']([^"\']+)["\'][^>]+property=["\']{re.escape(prop)}["\']',
            re.I,
        )
        m = pat1.search(html) or pat2.search(html)
        if m:
            val = m.group(1).strip()
            if key == "image" and val and not val.startswith("http"):
                val = urljoin(page_url, val)
            out[key] = val
    return out


def _abs_url(page_url: str, u: str) -> str:
    u = (u or "").strip()
    if not u or u.startswith("data:"):
        return ""
    if not u.startswith("http"):
        return urljoin(page_url, u)
    return u


_SKIP_IMG = (
    "avatar",
    "logo",
    "/icon",
    "favicon",
    "spacer",
    "pixel",
    "1x1",
    "blank.",
    "loading",
    "emoji",
    "qrcode",
    "wx_qrcode",
)


def _looks_like_content_image(url: str) -> bool:
    lu = url.lower()
    return not any(s in lu for s in _SKIP_IMG)


def _extract_image_candidates(html: str, page_url: str) -> list[str]:
    """按优先级收集与正文相关的配图 URL（用于轮播封面，须来自源页）。"""
    ordered: list[str] = []
    seen: set[str] = set()

    def push(u: str) -> None:
        au = _abs_url(page_url, u)
        if not au or au in seen:
            return
        if not _looks_like_content_image(au):
            return
        seen.add(au)
        ordered.append(au)

    og = _extract_og(html, page_url)
    if og.get("image"):
        push(og["image"])
    for prop in ("og:image:secure_url", "og:image:url"):
        pat1 = re.compile(
            rf'<meta[^>]+property=["\']{re.escape(prop)}["\'][^>]+content=["\']([^"\']+)["\']',
            re.I,
        )
        pat2 = re.compile(
            rf'<meta[^>]+content=["\']([^"\']+)["\'][^>]+property=["\']{re.escape(prop)}["\']',
            re.I,
        )
        m = pat1.search(html) or pat2.search(html)
        if m:
            push(m.group(1).strip())
            break

    for pat in (
        r'<meta[^>]+name=["\']twitter:image["\'][^>]+content=["\']([^"\']+)["\']',
        r'<meta[^>]+name=["\']twitter:image:src["\'][^>]+content=["\']([^"\']+)["\']',
        r'<meta[^>]+property=["\']twitter:image["\'][^>]+content=["\']([^"\']+)["\']',
    ):
        m = re.search(pat, html, re.I)
        if m:
            push(m.group(1).strip())
            break

    m = re.search(
        r'<link[^>]+rel=["\']image_src["\'][^>]+href=["\']([^"\']+)["\']',
        html,
        re.I,
    )
    if m:
        push(m.group(1).strip())

    m = re.search(
        r'<meta[^>]+itemprop=["\']image["\'][^>]+content=["\']([^"\']+)["\']',
        html,
        re.I,
    )
    if m:
        push(m.group(1).strip())

    # 正文区域 <article> / <main>
    for block_pat in (
        r"(?is)<article[^>]*>(.*?)</article>",
        r"(?is)<main[^>]*>(.*?)</main>",
    ):
        bm = re.search(block_pat, html)
        if not bm:
            continue
        inner = bm.group(1)
        for im in re.finditer(
            r'<img[^>]+(?:data-src|data-original|src)=["\']([^"\']+)["\']',
            inner,
            re.I,
        ):
            push(im.group(1).strip())
        if len(ordered) >= 12:
            break

    # 全页补充（仍过滤图标）
    if len(ordered) < 3:
        for im in re.finditer(
            r'<img[^>]+(?:data-src|data-original|src)=["\']([^"\']+)["\']',
            html,
            re.I,
        ):
            push(im.group(1).strip())
            if len(ordered) >= 16:
                break

    return ordered


def _pick_unique_cover(candidates: list[str], used_in_batch: set[str]) -> str | None:
    """同一批轮播里尽量避免与已选用 URL 完全相同的图（多源共用默认 og 时换用正文图）。"""
    for u in candidates:
        if u not in used_in_batch:
            return u
    return None


def _strip_html_snippet(html: str, max_len: int = 1200) -> str:
    text = re.sub(r"(?is)<script[^>]*>.*?</script>", " ", html)
    text = re.sub(r"(?is)<style[^>]*>.*?</style>", " ", text)
    text = re.sub(r"<[^>]+>", " ", text)
    text = re.sub(r"\s+", " ", text).strip()
    return text[:max_len]


async def _fetch_page_meta(
    client: httpx.AsyncClient, page_url: str, max_bytes: int
) -> tuple[str, list[str], str]:
    try:
        r = await client.get(
            page_url,
            headers={"User-Agent": BROWSER_UA, "Accept": "text/html,*/*"},
            follow_redirects=True,
        )
        r.raise_for_status()
        raw = r.content[:max_bytes]
        html = raw.decode("utf-8", errors="ignore")
    except Exception as e:
        logger.debug("page fetch failed %s: %s", page_url, e)
        return "", [], ""

    og = _extract_og(html, page_url)
    title = (og.get("title") or "").strip()
    if not title:
        tm = re.search(r"(?is)<title[^>]*>([^<]+)</title>", html)
        if tm:
            title = re.sub(r"\s+", " ", tm.group(1)).strip()[:200]

    candidates = _extract_image_candidates(html, page_url)
    excerpt = (og.get("description") or "").strip()
    body_snip = _strip_html_snippet(html, 5200)
    if len(excerpt) < 500:
        excerpt = (excerpt + "\n\n" + body_snip).strip() if body_snip else excerpt
    elif len(excerpt) < 1200 and body_snip:
        excerpt = (excerpt + "\n\n" + body_snip[:2800]).strip()

    return title, candidates, excerpt


def _slugify_hint(hint: str, fallback: str) -> str:
    s = (hint or fallback).strip().lower()
    s = re.sub(r"[^a-z0-9\u4e00-\u9fff]+", "-", s)
    s = re.sub(r"-+", "-", s).strip("-")
    if not s:
        s = "topic"
    return s[:40]


def _extract_json_object(text: str) -> dict[str, Any] | None:
    text = text.strip()
    fence = re.search(r"```(?:json)?\s*(\{.*\})\s*```", text, re.DOTALL)
    chunk = fence.group(1) if fence else text
    start = chunk.find("{")
    if start < 0:
        return None
    dec = json.JSONDecoder()
    try:
        obj, _ = dec.raw_decode(chunk[start:])
    except json.JSONDecodeError:
        return None
    return obj if isinstance(obj, dict) else None


async def _next_unique_slug(db: AsyncSession, base: str) -> str:
    candidate = base[:120]
    n = 0
    while True:
        r = await db.execute(select(Article.id).where(Article.slug == candidate).limit(1))
        if r.scalar_one_or_none() is None:
            return candidate
        n += 1
        suffix = f"-{n}"
        candidate = (base[: 120 - len(suffix)] + suffix)[:128]


async def _call_rewrite(
    settings: Settings,
    *,
    material_title: str,
    excerpt: str,
    page_url: str,
) -> dict[str, Any] | None:
    api_key = (settings.bailian_api_key or "").strip()
    if not api_key:
        raise ValueError("BAILIAN_API_KEY not configured")

    base = settings.bailian_api_base.rstrip("/")
    url = f"{base}/chat/completions"
    user_msg = f"""热点标题：{material_title}

摘录/摘要：
{excerpt}

原文链接（勿写入正文）：{page_url}
"""
    body = {
        "model": settings.guide_llm_model,
        "messages": [
            {"role": "system", "content": _SYSTEM_REWRITE},
            {"role": "user", "content": user_msg},
        ],
        "max_tokens": 6000,
        "temperature": 0.72,
    }
    headers = {
        "Authorization": f"Bearer {api_key}",
        "Content-Type": "application/json",
    }
    async with httpx.AsyncClient(timeout=LLM_TIMEOUT) as client:
        r = await client.post(url, json=body, headers=headers)
        r.raise_for_status()
        data = r.json()
    choices = data.get("choices") or []
    if not choices:
        return None
    content = (choices[0].get("message") or {}).get("content") or ""
    return _extract_json_object(content)


async def _already_have_source(db: AsyncSession, fortune_date: date, src_hash: str) -> bool:
    q = select(func.count(Article.id)).where(
        Article.publish_date == fortune_date,
        Article.tags == CAROUSEL_TAG,
        Article.status == ArticleStatus.published,
        Article.source_keywords.like(f"%src:{src_hash}%"),
    )
    n = await db.scalar(q)
    return (n or 0) > 0


async def generate_carousel_articles(
    db: AsyncSession,
    fortune_date: date,
    *,
    force: bool = False,
    max_articles: int | None = None,
) -> int:
    """写入当日轮播 Article（category=general, tags=carousel）。返回保存条数。"""
    settings = get_settings()
    cap = max_articles if max_articles is not None else settings.carousel_max_articles
    max_bytes = settings.carousel_page_fetch_max_bytes

    if not force and not settings.carousel_generation_enabled:
        logger.info("carousel_generation_enabled=false, skip")
        return 0

    if not (settings.bailian_api_key or "").strip():
        logger.warning("BAILIAN_API_KEY empty, skip carousel articles")
        return 0

    existing = await db.scalar(
        select(func.count(Article.id)).where(
            Article.publish_date == fortune_date,
            Article.status == ArticleStatus.published,
            Article.tags == CAROUSEL_TAG,
        )
    )
    if not force and (existing or 0) > 0:
        logger.info(
            "Carousel articles already present for %s (count=%s), skip",
            fortune_date,
            existing,
        )
        return 0

    if force:
        await db.execute(
            delete(Article).where(
                Article.publish_date == fortune_date,
                Article.tags == CAROUSEL_TAG,
            )
        )
        await db.flush()

    # --- collect headlines ---
    headlines: list[dict[str, str]] = []
    seen_urls: set[str] = set()

    async with httpx.AsyncClient(timeout=NEWSNOW_TIMEOUT) as client:
        base = settings.newsnow_api_base.strip()
        source_ids = [
            s.strip()
            for s in settings.carousel_newsnow_source_ids.split(",")
            if s.strip()
        ]
        if base and source_ids:
            tasks = [_fetch_newsnow_source(client, base, sid) for sid in source_ids]
            batches = await asyncio.gather(*tasks, return_exceptions=True)
            for b in batches:
                if isinstance(b, Exception):
                    logger.warning("NewsNow batch error: %s", b)
                    continue
                for it in b:
                    nu = _normalize_url(it.get("url", ""))
                    if nu and nu not in seen_urls:
                        seen_urls.add(nu)
                        headlines.append({**it, "url": nu})

        rss_urls = [
            u.strip()
            for u in settings.carousel_rss_fallback_urls.split(",")
            if u.strip()
        ]
        for feed in rss_urls:
            items = await _fetch_rss_headlines(client, feed, limit=18)
            for it in items:
                nu = _normalize_url(it.get("url", ""))
                if nu and nu not in seen_urls:
                    seen_urls.add(nu)
                    headlines.append({**it, "url": nu})

    if not headlines:
        logger.warning("No headlines from NewsNow/RSS for %s", fortune_date)
        return 0

    ranked = sorted(
        headlines,
        key=lambda h: _score_title(h.get("title", "")),
        reverse=True,
    )
    pool = ranked[: max(cap * 6, cap + 8)]

    saved = 0
    date_prefix = fortune_date.strftime("%Y%m%d")
    idx = 0
    seen_src: set[str] = set()
    seen_covers: set[str] = set()

    async with httpx.AsyncClient(timeout=PAGE_TIMEOUT) as page_client:
        for h in pool:
            if saved >= cap:
                break
            page_url = h["url"]
            src_h = _source_hash(page_url)
            if src_h in seen_src:
                continue
            if await _already_have_source(db, fortune_date, src_h):
                continue

            ptitle, image_cands, excerpt = await _fetch_page_meta(page_client, page_url, max_bytes)
            material_title = h.get("title") or ptitle or "热点"
            excerpt = (excerpt or "").strip() or material_title
            cover = _pick_unique_cover(image_cands, seen_covers)
            if not cover:
                logger.info(
                    "Carousel skip: no usable image for %s (candidates=%d)",
                    page_url,
                    len(image_cands),
                )
                continue

            try:
                obj = await _call_rewrite(
                    settings,
                    material_title=material_title,
                    excerpt=excerpt,
                    page_url=page_url,
                )
            except Exception:
                logger.exception("Carousel rewrite LLM failed for %s", page_url)
                continue

            if not obj:
                logger.warning("Carousel: no JSON object from LLM for %s", page_url)
                continue

            title = _compliance_filter((obj.get("title") or "").strip())
            body = _compliance_filter((obj.get("body") or "").strip())
            hint = (obj.get("slug_hint") or "").strip()
            if not title or len(body) < MIN_BODY_CHARS:
                continue

            idx += 1
            base_slug = f"hot-{date_prefix}-{_slugify_hint(hint, str(idx))}-{idx}"
            slug = await _next_unique_slug(db, base_slug)

            kw = f"carousel_hot|src:{src_h}|{h.get('source', 'unknown')[:80]}"

            seen_covers.add(cover)
            body_ir = markdown_to_ir(
                body,
                {"title": title[:200], "cover_image": cover[:500]},
            )
            article = Article(
                slug=slug,
                title=title[:200],
                cover_image=cover[:500],
                body=body,
                body_ir=body_ir,
                category=ArticleCategory.general,
                tags=CAROUSEL_TAG,
                cta_product=None,
                status=ArticleStatus.published,
                source_keywords=kw[:500],
                publish_date=fortune_date,
            )
            db.add(article)
            seen_src.add(src_h)
            saved += 1
            await db.flush()

    if saved:
        await db.flush()
    logger.info("Carousel articles saved: %d for %s (from aggregator+rewrite)", saved, fortune_date)
    return saved
