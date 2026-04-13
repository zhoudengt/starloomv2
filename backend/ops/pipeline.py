"""每日运营包生成编排（不挂载 FastAPI）。"""

from __future__ import annotations

import asyncio
from datetime import date
from pathlib import Path
from typing import Any, Dict, List

from app.config import get_settings
from app.utils.beijing_date import fortune_date_beijing

from ops.config import get_ops_settings
from ops.copy.generate import build_article_body, build_copy_bundle, maybe_enrich_with_llm
from ops.data_sources.registry import fetch_all_external
from ops.export.writer import write_day_bundle
from ops.publish.douyin_kit import write_douyin_kit
from ops.ranking.rank import RankedAngle, rank_angles
from ops.signals.astro_slice import compute_twelve_transit_slice, ephemeris_one_liner
from ops.signals.daily_fortune import fetch_twelve_daily
from ops.signals.merge import CandidateAngle, build_candidate_angles
from ops.visual.bundle import build_multimodal_bundle
from ops.media.wan_media import merge_wan_media_into_manifest, run_wan_media_bundle


def _hot_keyword_pool(ext) -> List[str]:
    keys: list[str] = list(ext.weibo.keywords)
    for h in ext.rss_headlines[:15]:
        keys.extend(h.title.split())
    for h in ext.zhihu_headlines[:10]:
        keys.extend(h.title.split())
    keys.extend(ext.xhs_keywords.keywords[:15])
    for h in ext.xhs_headlines[:10]:
        keys.extend(h.title.split())
    seen: set[str] = set()
    out: list[str] = []
    for k in keys:
        k = k.strip()
        if len(k) < 2 or k in seen:
            continue
        seen.add(k)
        out.append(k)
    return out[:120]


async def _write_carousel_articles(
    d: date,
    ranked: List[RankedAngle],
    ep_line: str,
    fe: str,
    out_path,
    wan_summary: Dict[str, Any] | None,
) -> int:
    """Write ranked angles as carousel articles to DB (tags=carousel)."""
    from sqlalchemy import select, func

    from app.config import get_settings
    from app.database import AsyncSessionLocal
    from app.models.article import Article, ArticleCategory, ArticleStatus

    CAROUSEL_TAG = "carousel"
    max_articles = get_settings().carousel_max_articles

    async with AsyncSessionLocal() as db:
        existing = await db.scalar(
            select(func.count(Article.id)).where(
                Article.tags == CAROUSEL_TAG,
                Article.publish_date == d,
            )
        )
        if existing and existing > 0:
            return 0

        count = 0
        images = (wan_summary or {}).get("images") or []

        for i, r in enumerate(ranked[:max_articles]):
            a = r.angle
            sign_names = "、".join(a.sign_cn_involved) if a.sign_cn_involved else "星座"
            title = f"{sign_names}今日运势参考"

            body = await build_article_body(r, d.isoformat(), ep_line, fe)

            cover = ""
            if i < len(images) and images[i].get("ok") and images[i].get("local_file"):
                local_file = str(images[i]["local_file"])
                if out_path:
                    try:
                        cover = str(Path(local_file).relative_to(Path(out_path).parent.parent))
                    except ValueError:
                        cover = local_file
            if not cover:
                slug = (a.signs_involved[0] if a.signs_involved else "aries").lower()
                cover = f"/zodiac/{slug}.webp"

            body_ir = None
            try:
                from app.services.ir_converter import markdown_to_ir
                body_ir = markdown_to_ir(body)
            except Exception:
                pass

            slug = f"daily-{d.isoformat()}-{a.angle_id[:30]}"

            article = Article(
                slug=slug,
                title=title,
                cover_image=cover,
                body=body,
                body_ir=body_ir,
                category=ArticleCategory.general,
                tags=CAROUSEL_TAG,
                cta_product="free_daily",
                status=ArticleStatus.published,
                source_keywords=f"ops_daily|{a.kind}|{','.join(a.sign_cn_involved)}",
                publish_date=d,
            )
            db.add(article)
            count += 1

        if count > 0:
            await db.commit()
        return count


async def run_daily(
    for_date: date | None = None,
    *,
    preview: bool = False,
    skip_wan_media: bool = False,
    video_override: bool | None = None,
) -> Dict[str, Any]:
    d = for_date or fortune_date_beijing()
    settings = get_settings()
    ops = get_ops_settings()

    ext = fetch_all_external(d)
    daily = await fetch_twelve_daily(d)
    transits = compute_twelve_transit_slice(d)
    hot_kw = _hot_keyword_pool(ext)
    candidates = build_candidate_angles(
        daily,
        transits,
        hot_kw,
        ext.rss_headlines,
    )
    if not candidates:
        first_slug, first_pl = next(iter(daily.items()))
        candidates = [
            CandidateAngle(
                angle_id="fallback_daily",
                kind="fallback",
                title_hint=f"{first_pl.get('sign_cn', first_slug)}今日运势参考",
                signs_involved=[first_slug],
                sign_cn_involved=[str(first_pl.get("sign_cn", first_slug))],
                score_hint=1.0,
                engine_facts=[
                    ephemeris_one_liner(d),
                    "十二宫日运数据不足或外源为空时降级选题。",
                ],
                engine_ref={"type": "fallback"},
                hot_keywords_matched=[],
            )
        ]
    ranked = rank_angles(candidates, ext.calendar, ops.top_k_angles)

    fe = (ops.frontend_base_url or settings.frontend_url or "http://localhost:5173").rstrip("/")
    utm = f"?utm_source=douyin&utm_medium=ops&utm_campaign=daily_{d.isoformat()}"
    ep_line = ephemeris_one_liner(d)

    copy_bundle = build_copy_bundle(
        d.isoformat(),
        ranked,
        ext.calendar,
        ep_line,
        fe,
    )
    copy_md_final = await maybe_enrich_with_llm(copy_bundle, ranked)
    copy_bundle.copy_md = copy_md_final

    multi = build_multimodal_bundle(d.isoformat(), ranked, utm, frontend_url=fe)

    manifest: Dict[str, Any] = {
        "date": d.isoformat(),
        "fetched_at": ext.fetched_at,
        "data_sources": {
            "weibo": {
                "enabled": bool(ops.weibo_access_token),
                "count": len(ext.weibo.keywords),
            },
            "rss": {
                "feeds": len(ops.rss_urls_list),
                "headlines": len(ext.rss_headlines),
            },
            "zhihu": {"headlines": len(ext.zhihu_headlines)},
            "xiaohongshu": {
                "keywords": len(ext.xhs_keywords.keywords),
                "headlines": len(ext.xhs_headlines),
            },
            "calendar": ext.calendar.get("holiday_label"),
        },
        "ephemeris_line": ep_line,
        "banned_words": ext.calendar.get("banned_words") or [],
        "frontend_url": fe,
        "utm": utm,
        "angles": [
            {
                "angle_id": r.angle.angle_id,
                "kind": r.angle.kind,
                "final_score": r.final_score,
                "cta_code": r.cta_code,
                "signs": r.angle.sign_cn_involved,
                "engine_ref": r.angle.engine_ref,
            }
            for r in ranked
        ],
        "primary_cta": ranked[0].cta_code if ranked else "free_daily",
    }

    out_path = write_day_bundle(d, manifest, copy_bundle, multi, preview=preview)

    wan_summary: Dict[str, Any] | None = None
    if not preview and not skip_wan_media:
        title_hint = ranked[0].angle.title_hint if ranked else "StarLoom"
        wan_summary = await asyncio.to_thread(
            run_wan_media_bundle,
            settings,
            out_path,
            multi.carousel,
            multi.video_spec,
            title_hint=title_hint,
            video_enabled_override=video_override,
        )
        merge_wan_media_into_manifest(out_path, wan_summary)

    douyin_meta: Dict[str, Any] | None = None
    if not preview:
        douyin_meta = write_douyin_kit(
            out_path,
            d=d,
            fe=fe,
            utm=utm,
            copy_bundle=copy_bundle,
            ranked=ranked,
            ext=ext,
            weibo_api_configured=bool((ops.weibo_access_token or "").strip()),
            wan_summary=wan_summary,
            ops=ops,
            preview=False,
        )

    carousel_written = 0
    if not preview:
        try:
            carousel_written = await _write_carousel_articles(
                d, ranked, ep_line, fe, out_path, wan_summary,
            )
        except Exception:
            import logging
            logging.getLogger(__name__).exception("carousel DB write failed for %s", d.isoformat())

    result: Dict[str, Any] = {
        "date": d.isoformat(),
        "out_dir": str(out_path) if not preview else "(preview)",
        "angles": len(ranked),
        "preview": preview,
        "skip_wan_media": skip_wan_media,
        "carousel_articles_written": carousel_written,
    }
    if wan_summary is not None:
        result["wan_media"] = {
            "image_enabled": wan_summary.get("image_enabled"),
            "video_enabled": wan_summary.get("video_enabled"),
            "images_ok": sum(1 for x in wan_summary.get("images") or [] if x.get("ok")),
            "video_ok": (wan_summary.get("video") or {}).get("ok"),
        }
    if douyin_meta is not None:
        result["douyin_kit"] = douyin_meta
    return result
