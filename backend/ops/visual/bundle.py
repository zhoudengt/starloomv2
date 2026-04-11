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
    video_spec: Dict[str, Any]
    media_prompts: Dict[str, Any]
    voice_txt: str


def _image_prompt(title: str, subtitle: str) -> str:
    return (
        f"Vertical 9:16 mobile poster, {BRAND['bg']}, "
        f"colors {BRAND['primary']} and {BRAND['accent']}, elegant Chinese typography, "
        f"main title: {title}, sub: {subtitle}, constellation motif abstract, no text errors, high detail"
    )


def build_multimodal_bundle(
    d_iso: str,
    ranked: List[RankedAngle],
    utm: str,
) -> MultimodalBundle:
    primary = ranked[0] if ranked else None
    pages: list[dict[str, Any]] = []
    if primary:
        a = primary.angle
        pages = [
            {
                "page": 1,
                "title": a.title_hint[:40],
                "body": "性格分析与运势参考，娱乐向解读。",
                "colors": {"primary": BRAND["primary"], "accent": BRAND["accent"]},
                "image_prompt": _image_prompt(a.title_hint[:32], "StarLoom · 运势参考"),
            },
            {
                "page": 2,
                "title": "引擎摘录",
                "body": "；".join(a.engine_facts[:3]),
                "colors": {"primary": BRAND["primary"], "accent": BRAND["accent"]},
                "image_prompt": _image_prompt("今日星象参考", d_iso),
            },
            {
                "page": 3,
                "title": "行动引导",
                "body": f"打开主页链接（{utm}）查看完整内容。",
                "colors": {"primary": BRAND["primary"], "accent": BRAND["accent"]},
                "image_prompt": _image_prompt("立即查看", "StarLoom H5"),
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

    return MultimodalBundle(
        carousel={"pages": pages, "brand": BRAND},
        video_spec={"15s": video_15, "60s": video_60},
        media_prompts=media_prompts,
        voice_txt=voice_txt,
    )
