from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Dict, List

from ops.ranking.rank import RankedAngle

BRAND = {
    "primary": "#2D1B69",
    "accent": "#F0C75E",
    "bg": "deep purple night sky with subtle stars, mystical, premium mobile UI",
}


@dataclass
class MultimodalBundle:
    carousel: Dict[str, Any]
    carousel_covers: List[Dict[str, Any]]
    video_spec: Dict[str, Any]
    media_prompts: Dict[str, Any]
    voice_txt: str


def _image_prompt(description: str) -> str:
    return (
        f"Vertical 9:16 mobile poster illustration, {BRAND['bg']}, "
        f"colors {BRAND['primary']} and {BRAND['accent']}, "
        f"{description}, no text, no watermark, no logo, high detail"
    )


def build_carousel_cover_prompts(ranked: List[RankedAngle]) -> List[Dict[str, Any]]:
    """为每个 ranked angle 生成一张封面图的 prompt。"""
    covers: list[dict[str, Any]] = []
    for r in ranked:
        a = r.angle
        sign_names = "、".join(a.sign_cn_involved) if a.sign_cn_involved else "星座"
        covers.append(
            {
                "index": len(covers),
                "sign_names": sign_names,
                "image_prompt": _image_prompt(
                    f"constellation theme for {sign_names}, "
                    f"zodiac symbol prominent, elegant minimalist style"
                ),
            }
        )
    return covers


def build_multimodal_bundle(
    d_iso: str,
    ranked: List[RankedAngle],
    utm: str,
    frontend_url: str = "",
) -> MultimodalBundle:
    primary = ranked[0] if ranked else None
    fe_display = frontend_url.replace("https://", "").replace("http://", "").rstrip("/") or "starloom.com.cn"
    pages: list[dict[str, Any]] = []
    if primary:
        a = primary.angle
        sign_names = "、".join(a.sign_cn_involved) if a.sign_cn_involved else "星座"
        friendly_title = f"{sign_names}今日运势参考"
        p1_visual = (
            f"constellation theme for {sign_names}, abstract zodiac glyphs and star patterns, "
            "elegant mystical atmosphere, soft gold highlights on deep purple"
        )
        p2_visual = (
            f"celestial chart and subtle planetary orbits, abstract starfield, calm premium mood "
            f"evoking the date {d_iso}, minimal composition"
        )
        p3_visual = (
            "minimal call-to-action end card, dark clean center with generous negative space, "
            "subtle purple vignette and thin gold accent line, premium mobile app aesthetic"
        )
        pages = [
            {
                "page": 1,
                "title": friendly_title[:40],
                "body": f"今天{sign_names}需要注意什么？来看看运势参考。",
                "colors": {"primary": BRAND["primary"], "accent": BRAND["accent"]},
                "image_prompt": _image_prompt(p1_visual),
            },
            {
                "page": 2,
                "title": f"今日星象参考",
                "body": f"{d_iso}｜性格分析与运势参考，帮你了解今天的节奏。",
                "colors": {"primary": BRAND["primary"], "accent": BRAND["accent"]},
                "image_prompt": _image_prompt(p2_visual),
            },
            {
                "page": 3,
                "title": f"浏览器打开 {fe_display}",
                "body": f"免费查看今日运势 · 性格报告按需解锁",
                "colors": {"primary": BRAND["primary"], "accent": BRAND["accent"]},
                "image_prompt": _image_prompt(p3_visual),
                "overlay_text": "starloom.com.cn",
            },
        ]

    video_15 = {
        "duration_sec": 15,
        "beats": [
            {"t": "0-3s", "visual": "星空标题卡 + 星座符号", "voice": "钩子：今日谁更稳？", "b_roll_prompt": BRAND["bg"]},
            {"t": "3-10s", "visual": "对比条/分数条动画占位", "voice": "引擎事实一句 + 场景一句", "b_roll_prompt": "abstract zodiac glyphs gold on purple"},
            {"t": "10-15s", "visual": "CTA 屏", "voice": "主页链接查免费今日运势", "b_roll_prompt": "minimal call to action mobile end card"},
        ],
    }
    video_60 = {
        "duration_sec": 60,
        "beats": [
            {"t": "0-5s", "hook": "反差/具体问题"},
            {"t": "5-25s", "body": "职场场景 + 感情场景各一段"},
            {"t": "25-45s", "body": "引擎摘录展开"},
            {"t": "45-60s", "cta": "免费运势 + 付费报告选项"},
        ],
    }

    media_prompts = {
        "image_model_notes": "百炼/通义万相等：使用 image_prompt 字段，保持竖版 9:16。",
        "video_model_notes": "图生视频：每 beat 的 b_roll_prompt 可单独生成 3-5s 素材拼接。",
        "voice_tts": "阿里云语音合成：口播分段与 beats 对齐，语速中等偏慢。",
        "brand": BRAND,
        "utm": utm,
    }

    voice_txt = (
        f"日期 {d_iso}\n语速：中等\n时长目标：15s 与 60s 两档见 video_spec.json\n"
        "分段：钩子 / 事实一句 / 场景两句 / CTA 一句\n"
    )

    carousel_covers = build_carousel_cover_prompts(ranked)

    return MultimodalBundle(
        carousel={"pages": pages, "brand": BRAND},
        carousel_covers=carousel_covers,
        video_spec={"15s": video_15, "60s": video_60},
        media_prompts=media_prompts,
        voice_txt=voice_txt,
    )
