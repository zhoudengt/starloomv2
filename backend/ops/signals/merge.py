"""合并日运分差、行运切片、外源关键词，生成候选运营角度。"""

from __future__ import annotations

from dataclasses import dataclass
from statistics import mean, pstdev
from typing import Any, Dict, List, Optional, Sequence

from ops.data_sources.base import NewsHeadline
from ops.signals.astro_slice import TransitSlice


@dataclass
class CandidateAngle:
    angle_id: str
    kind: str
    title_hint: str
    signs_involved: List[str]
    sign_cn_involved: List[str]
    score_hint: float
    engine_facts: List[str]
    engine_ref: Dict[str, Any]
    hot_keywords_matched: List[str]


def _scores_twelve(daily: Dict[str, Dict[str, Any]]) -> Dict[str, float]:
    s: Dict[str, float] = {}
    for slug, payload in daily.items():
        raw = payload.get("overall_score", 70)
        try:
            s[slug] = float(raw)
        except (TypeError, ValueError):
            s[slug] = 70.0
    return s


def _match_keywords(text: str, keywords: Sequence[str]) -> List[str]:
    t = text.lower()
    hit: list[str] = []
    for kw in keywords:
        if not kw or len(kw) < 2:
            continue
        if kw.lower() in t or kw in text:
            hit.append(kw)
    return hit


def build_candidate_angles(
    daily: Dict[str, Dict[str, Any]],
    transits: List[TransitSlice],
    hot_keywords: List[str],
    rss: List[NewsHeadline],
) -> List[CandidateAngle]:
    scores = _scores_twelve(daily)
    if len(scores) < 6:
        return []

    m = mean(scores.values())
    sd = pstdev(scores.values()) if len(scores) > 1 else 0.0
    ranked = sorted(scores.items(), key=lambda x: x[1])
    low_slug, low_v = ranked[0]
    high_slug, high_v = ranked[-1]

    rss_blob = " ".join(h.title for h in rss[:20])
    weibo_blob = " ".join(hot_keywords[:40])

    candidates: list[CandidateAngle] = []

    # 1) 反差：日运最高 vs 最低
    low_cn = daily.get(low_slug, {}).get("sign_cn", low_slug)
    high_cn = daily.get(high_slug, {}).get("sign_cn", high_slug)
    contrast_hint = f"今日综合分反差：{low_cn}相对承压约{low_v:.0f}分 vs {high_cn}相对顺约{high_v:.0f}分（产品内日运模型，非个体咨询）"
    candidates.append(
        CandidateAngle(
            angle_id="contrast_daily_score",
            kind="contrast",
            title_hint=f"{low_cn}VS{high_cn}：今日谁更稳？",
            signs_involved=[low_slug, high_slug],
            sign_cn_involved=[str(low_cn), str(high_cn)],
            score_hint=float(sd) * 2.0 + (high_v - low_v) * 0.05,
            engine_facts=[contrast_hint, f"十二宫整体分标准差约{sd:.2f}"],
            engine_ref={"type": "daily_scores", "mean": m, "stdev": sd},
            hot_keywords_matched=_match_keywords(rss_blob + weibo_blob, hot_keywords),
        )
    )

    # 2) 行运：tight_score 最大
    if transits:
        by_tight = sorted(transits, key=lambda x: x.tight_score, reverse=True)
        top = by_tight[0]
        candidates.append(
            CandidateAngle(
                angle_id="transit_tight_" + top.sign,
                kind="transit_focus",
                title_hint=f"{top.sign_cn}：今日行运相位更密？",
                signs_involved=[top.sign],
                sign_cn_involved=[top.sign_cn],
                score_hint=top.tight_score + top.aspect_count * 0.3,
                engine_facts=[
                    top.top_aspect_line,
                    f"代表盘行运相位数量约{top.aspect_count}（Swiss Ephemeris 计算）",
                ],
                engine_ref={"type": "transit_slice", "slice": top.engine_ref},
                hot_keywords_matched=_match_keywords(rss_blob + weibo_blob, hot_keywords),
            )
        )

    # 3) 热点叙事：RSS 标题与星座中文名同时出现（弱匹配，最多 2 条）
    news_added = 0
    for h in rss[:12]:
        if news_added >= 2:
            break
        for slug, payload in daily.items():
            cn = payload.get("sign_cn", "")
            if cn and cn in h.title:
                candidates.append(
                    CandidateAngle(
                        angle_id=f"news_{slug}_{hash(h.title) % 100000}",
                        kind="hotspot_rss",
                        title_hint=f"新闻里的「{cn}」：{h.title[:28]}…",
                        signs_involved=[slug],
                        sign_cn_involved=[cn],
                        score_hint=3.0,
                        engine_facts=[f"新闻标题: {h.title}"],
                        engine_ref={"type": "rss", "link": h.link, "source": h.source},
                        hot_keywords_matched=[cn],
                    )
                )
                news_added += 1
                break

    return candidates
