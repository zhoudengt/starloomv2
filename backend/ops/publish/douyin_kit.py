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

# 与 docs/spec.md 付费档位一致（口播/正文桥接用）
SPEC_PRICING_CN = (
    "免费今日运势；深度报告：个人性格 9.9 元、配对分析 19.9 元、年度运势 29.9 元（以站内为准）。"
)


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


def _carousel_rows(
    fe: str,
    slug: str,
    wan_summary: Optional[Dict[str, Any]],
    mode: str,
) -> List[Dict[str, str]]:
    asset_url = f"{fe.rstrip('/')}/zodiac/{slug}.webp"
    rows: List[Dict[str, str]] = []

    images = (wan_summary or {}).get("images") or []

    def ok_path(i: int) -> str:
        if i >= len(images):
            return ""
        ent = images[i]
        if ent.get("ok") and ent.get("local_file"):
            return str(ent["local_file"])
        return ""

    mode_l = (mode or "asset_first").strip().lower()
    if mode_l == "ai_only":
        for i in range(3):
            p = ok_path(i)
            rows.append(
                {
                    "slot": str(i + 1),
                    "kind": "万相文生图",
                    "path_or_url": p or "（未生成或失败，可重跑 daily）",
                }
            )
        return rows

    # asset_first：首帧项目内 webp，后两帧对应万相第 2、3 页（carousel page_02 / page_03）
    rows.append(
        {
            "slot": "1",
            "kind": "项目内星座插画（与 H5 同源）",
            "path_or_url": asset_url,
        }
    )
    rows.append(
        {
            "slot": "2",
            "kind": "万相氛围图（carousel 第 2 页）",
            "path_or_url": ok_path(1) or "media/images/page_02.png（若已生成）",
        }
    )
    rows.append(
        {
            "slot": "3",
            "kind": "万相氛围图（carousel 第 3 页）",
            "path_or_url": ok_path(2) or "media/images/page_03.png（若已生成）",
        }
    )
    return rows


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

    title_main = copy_bundle.titles[0] if copy_bundle.titles else "StarLoom 今日运营稿"
    primary = ranked[0].angle if ranked else None
    signs_cn = ", ".join(primary.sign_cn_involved) if primary else ""
    ep_one = ""  # optional; pipeline could pass — keep template self-contained
    if primary and primary.engine_facts:
        ep_one = primary.engine_facts[0][:80]

    body_short = "\n\n".join(
        [
            f"（1）钩子：{title_main[:80]}… 谁更稳、哪里容易踩坑？",
            f"（2）天象与主题：今日主推星座参考｜{signs_cn}。"
            + (f" 引擎摘录：{ep_one}…" if ep_one else "")
            + " 结合场景谈「运势参考」，避免绝对化断言。",
            f"（3）产品桥：在 StarLoom 选你的太阳星座 → {SPEC_PRICING_CN}",
            f"（4）单一 CTA：打开链接（已带统计参数）→ {full_url}",
        ]
    )

    rows = _carousel_rows(fe, slug, wan_summary, ops.wan_carousel_mode)
    table_lines = ["| 顺序 | 类型 | 路径或 URL |", "| --- | --- | --- |"]
    for r in rows:
        table_lines.append(f"| {r['slot']} | {r['kind']} | {r['path_or_url']} |")
    if ops.traffic_qr_enabled:
        table_lines.append(
            f"| 引流 | 扫码进入 H5（与置顶同链） | `{qr_rel}` → `{full_url}` |"
        )

    pinned = "\n".join(
        [
            full_url,
            "",
            "置顶：今日运势与深度报告入口（性格分析 / 运势参考）",
        ]
    )
    (out_dir / "pinned_comment.txt").write_text(pinned, encoding="utf-8")

    md_parts = [
        f"# 抖音发布一体化 · {d.isoformat()}",
        "",
        "## 一、标题",
        "",
        f"- **主标题**：{title_main}",
        "",
        "### 备选",
        "",
        *(f"- {t}" for t in (copy_bundle.titles[1:] if len(copy_bundle.titles) > 1 else [])),
        "",
        "## 二、正文（短文案，可直接贴抖音）",
        "",
        body_short,
        "",
        "## 三、配图 / 轮播（与项目资源一致）",
        "",
        f"- **万相轮播策略**：`{ops.wan_carousel_mode}`（`asset_first` = 首帧项目 webp + 万相；`ai_only` = 全部万相）",
        "",
        *table_lines,
        "",
        "## 四、引流",
        "",
        f"- **完整链接（UTM）**：{full_url}",
        "",
    ]
    if qr_ok:
        md_parts.extend(
            [
                f"- **二维码文件**：`{qr_rel}`（浏览器扫码进入上述链接）",
                "",
            ]
        )
    else:
        md_parts.extend(
            [
                "- **二维码**：未生成（请安装依赖后重跑：`pip install 'qrcode[pil]'`）",
                "",
            ]
        )

    md_parts.extend(
        [
            "## 五、热点摘要",
            "",
            f"- **状态**：`{hotspot['status']}`",
            f"- **说明**：{hotspot['summary_cn']}",
            "",
            "## 六、合规提示",
            "",
            "详见同目录 `douyin_compliance.txt`。",
            "",
            "## 七、置顶评论（复制）",
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
