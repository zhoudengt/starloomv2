from __future__ import annotations

from dataclasses import dataclass
from typing import List

from ops.data_sources.registry import to_calendar_context
from ops.signals.merge import CandidateAngle


@dataclass
class RankedAngle:
    angle: CandidateAngle
    final_score: float
    cta_code: str


def rank_angles(
    candidates: List[CandidateAngle],
    calendar: dict,
    top_k: int,
) -> List[RankedAngle]:
    ctx = to_calendar_context(calendar)
    w = ctx.holiday_weight
    holiday_cta = calendar.get("suggested_cta")
    cta_cycle = ["free_daily", "personality", "compatibility"]

    scored: list[tuple[CandidateAngle, float]] = []
    for c in candidates:
        hot_bonus = min(5.0, len(c.hot_keywords_matched) * 0.8)
        base = c.score_hint + hot_bonus
        final = base * w
        scored.append((c, round(final, 3)))

    scored.sort(key=lambda x: x[1], reverse=True)
    out: list[RankedAngle] = []
    for i, (c, final) in enumerate(scored[:top_k]):
        if holiday_cta:
            code = str(holiday_cta)
        else:
            code = cta_cycle[i % len(cta_cycle)]
        out.append(RankedAngle(angle=c, final_score=final, cta_code=code))
    return out
