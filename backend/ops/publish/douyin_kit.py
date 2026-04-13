"""一体化抖音发布包：正文、配图清单、置顶链接、热点摘要、引流二维码、合规提示。"""

from __future__ import annotations

import json
from datetime import date
from pathlib import Path
from typing import Any, Dict, List, Optional, Set, Tuple

from app.utils.zodiac_calc import list_all_signs

from ops.config import OpsSettings
from ops.copy.generate import CopyBundle
from ops.data_sources.registry import ExternalBundle
from ops.ranking.rank import RankedAngle

SPEC_CTA_CN = "免费查看今日运势，深度报告按需解锁"


def _cn_slug_maps() -> Tuple[Dict[str, str], Set[str]]:
    m = list_all_signs()
    cn_to_slug = {x["sign_cn"]: x["sign"] for x in m}
    slugs = {x["sign"] for x in m}
    return cn_to_slug, slugs


def primary_zodiac_slug(ranked: List[RankedAngle]) -> str:
    """与 frontend/public/zodiac/{slug}.webp 对齐的英文 slug。"""
    if not ranked:
        return "aries"
    cn_to_slug, slugs = _cn_slug_maps()
    for s in ranked[0].angle.signs_involved:
        raw = (s or "").strip()
        low = raw.lower()
        if low in slugs:
            return low
        if raw in cn_to_slug:
            return cn_to_slug[raw]
    for cn in ranked[0].angle.sign_cn_involved:
        if cn in cn_to_slug:
            return cn_to_slug[cn]
    return "aries"


def full_traffic_url(fe: str, utm: str) -> str:
    base = (fe or "").rstrip("/")
    q = (utm or "").strip()
    if not q:
        return base
    if q.startswith("?"):
        return base + q
    return f"{base}?{q.lstrip('?')}"


def build_hotspot_report(
    ext: ExternalBundle,
    ranked: List[RankedAngle],
    weibo_api_configured: bool,
) -> Dict[str, Any]:
    matched: list[str] = []
    for r in ranked:
        matched.extend(list(r.angle.hot_keywords_matched or []))
    matched = list(dict.fromkeys(matched))[:30]

    rss_n = len(ext.rss_headlines)
    weibo_n = len(ext.weibo.keywords)

    status = "none"
    if matched:
        status = "matched"
    elif rss_n > 0 or (weibo_api_configured and weibo_n > 0):
        status = "weak"

    if status == "matched":
        summary_cn = (
            f"今日选题与外部热点词存在交集（示例：{', '.join(matched[:5])}…）。"
            "口播可自然带一句，避免夸大绑定。"
        )
    elif status == "weak":
        summary_cn = (
            "今日有 RSS/微博数据源可读，但未形成强热点锚点；"
            "建议以星象事实与场景代入为主，不硬蹭。"
        )
    else:
        summary_cn = "今日无强外部热点锚点；以引擎天象与星座日运叙事为主。"

    rss_titles = [h.title for h in ext.rss_headlines[:8]]

    return {
        "status": status,
        "weibo_api_configured": weibo_api_configured,
        "weibo_keyword_count": weibo_n,
        "rss_headlines_count": rss_n,
        "rss_sample_titles": rss_titles,
        "hot_keywords_matched": matched,
        "summary_cn": summary_cn,
    }


def _compliance_text() -> str:
    return "\n".join(
        [
            "【平台规则】抖音等短视频平台对外链、二维码、营销推广的要求以各平台最新公示为准；"
            "发布前请运营自行核对当时规则（是否允许外链、是否需备案等）。",
            "",
            "【内容定位】本站为「性格分析与运势参考」类娱乐向解读，非封建迷信；"
            "请勿使用「算命」「占卜」等表述（与项目 calendar 禁忌一致）。",
            "",
            "【引流说明】二维码与置顶链接仅跳转至本产品自有 H5；"
            "请勿在素材中冒充政府机关、新闻媒体或平台官方。",
            "",
            "【责任】本文件为产品侧提示，不构成法律意见。",
        ]
    )


def _write_qr_png(url: str, dest: Path) -> bool:
    try:
        import qrcode  # type: ignore
    except ImportError:
        return False
    dest.parent.mkdir(parents=True, exist_ok=True)
    img = qrcode.make(url, border=2)
    img.save(str(dest))
    return True


def write_douyin_kit(
    out_dir: Path,
    *,
    d: date,
    fe: str,
    utm: str,
    copy_bundle: CopyBundle,
    ranked: List[RankedAngle],
    ext: ExternalBundle,
    weibo_api_configured: bool,
    wan_summary: Optional[Dict[str, Any]],
    ops: OpsSettings,
    preview: bool,
) -> Dict[str, Any]:
    """写入 douyin_publish.md、pinned_comment、hotspot_report、合规说明、可选引流二维码，并合并 manifest。"""
    full_url = full_traffic_url(fe, utm)
    slug = primary_zodiac_slug(ranked)
    hotspot = build_hotspot_report(ext, ranked, weibo_api_configured)

    kit_meta: Dict[str, Any] = {
        "traffic_url": full_url,
        "primary_zodiac_slug": slug,
        "hotspot_status": hotspot["status"],
        "wan_carousel_mode": ops.wan_carousel_mode,
    }

    if preview:
        return {"preview": True, **kit_meta}

    (out_dir / "hotspot_report.json").write_text(
        json.dumps(hotspot, ensure_ascii=False, indent=2),
        encoding="utf-8",
    )
    (out_dir / "douyin_compliance.txt").write_text(
        _compliance_text(),
        encoding="utf-8",
    )

    qr_rel = "media/traffic_qr.png"
    qr_ok = False
    if ops.traffic_qr_enabled:
        qr_ok = _write_qr_png(full_url, out_dir / qr_rel)
    kit_meta["traffic_qr_file"] = qr_rel if qr_ok else None

    primary = ranked[0].angle if ranked else None
    signs_cn = ", ".join(primary.sign_cn_involved) if primary else ""
    title_main = copy_bundle.titles[0] if copy_bundle.titles else f"{signs_cn}今日运势参考"

    fe_display = fe.replace("https://", "").replace("http://", "").rstrip("/")

    body_short = (
        f"{signs_cn}今天需要注意什么？一条运势参考送给你。\n"
        f"今天的星象提醒：别急着做大决定，先观察一下节奏。\n"
        f"想看完整版？看我主页简介找入口 👉\n"
    )

    pinned = "\n".join(
        [
            f"✨ {signs_cn}今日运势参考",
            "想看完整版？看我主页简介有入口",
            "免费看今日运势，性格报告 / 配对解读按需解锁",
        ]
    )
    (out_dir / "pinned_comment.txt").write_text(pinned, encoding="utf-8")

    hashtags = f"#星座 #{signs_cn.replace(', ', ' #')} #运势参考 #性格分析 #星座解读 #女生必看"

    md_parts = [
        f"# {d.isoformat()} 抖音发布",
        "",
        "## 标题（复制）",
        "",
        f"```",
        title_main,
        f"```",
        "",
        "## 正文（复制）",
        "",
        f"```",
        body_short.strip(),
        f"```",
        "",
        "## 话题标签（复制）",
        "",
        f"```",
        hashtags,
        f"```",
        "",
        "## 配图",
        "",
        "上传以下图片到抖音：",
        "",
    ]

    media_dir = out_dir / "media" / "images"
    if media_dir.exists():
        carousel_imgs = sorted(media_dir.glob("page_*.jpg"))
        if not carousel_imgs:
            carousel_imgs = sorted(media_dir.glob("page_*.png"))
        for img in carousel_imgs:
            md_parts.append(f"- `{img.relative_to(out_dir)}`")
    else:
        md_parts.append("- （图片未生成，运行 `python -m ops.cli daily` 生成）")

    if qr_ok:
        md_parts.extend(["", f"引流二维码：`{qr_rel}`"])

    md_parts.extend(
        [
            "",
            "## 置顶评论（发布后复制到评论区）",
            "",
            "```",
            pinned,
            "```",
            "",
        ]
    )

    (out_dir / "douyin_publish.md").write_text("\n".join(md_parts), encoding="utf-8")

    mpath = out_dir / "manifest.json"
    if mpath.exists():
        data = json.loads(mpath.read_text(encoding="utf-8"))
        data["hotspot_report"] = hotspot
        data["douyin_kit"] = kit_meta
        mpath.write_text(json.dumps(data, ensure_ascii=False, indent=2), encoding="utf-8")

    return kit_meta
