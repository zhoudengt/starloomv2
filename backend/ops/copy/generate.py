from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Dict, List, Optional

from app.config import get_settings
from app.services.llm_service import BailianApplicationService

from ops.config import get_ops_settings
from ops.copy.compliance import check_compliance, strip_banned
from ops.ranking.rank import RankedAngle
from ops.signals.astro_slice import ephemeris_one_liner


@dataclass
class CopyBundle:
    copy_md: str
    titles: List[str]
    comment_cta: str
    share_lines: List[str]


def build_copy_bundle(
    d_iso: str,
    ranked: List[RankedAngle],
    calendar: Dict[str, Any],
    ephemeris_line: str,
    frontend_url: str,
) -> CopyBundle:
    primary = ranked[0] if ranked else None
    cta_map = calendar.get("cta_map") or {}
    ban = list(calendar.get("banned_words") or [])

    titles: list[str] = []
    body_parts: list[str] = []
    share_lines: list[str] = []

    if primary:
        a = primary.angle
        titles = [
            a.title_hint,
            f"今日星象参考｜{', '.join(a.sign_cn_involved)}",
            f"性格与运势参考｜{a.kind}",
        ]
        body_parts.append(f"【天象事实】{ephemeris_line}")
        body_parts.append("")
        for fact in a.engine_facts:
            body_parts.append(f"【引擎摘录】{fact}")
        body_parts.append("")
        body_parts.append("【口播结构建议】")
        body_parts.append("1）钩子：用反差或具体问题开场（3 秒内）。")
        body_parts.append("2）中间：职场/感情各举 1 个可代入场景，避免绝对化断言。")
        body_parts.append(
            f"3）收束：引导至 {frontend_url} 查看今日运势与深度报告（性格分析/运势参考）。"
        )
        cta_key = primary.cta_code
        cta_text = cta_map.get(cta_key, "主页免费今日运势")
        body_parts.append("")
        body_parts.append(f"【主推转化】{cta_text}")
        share_lines = [
            f"今日星象参考｜{a.title_hint}",
            f"想看 {', '.join(a.sign_cn_involved)} 今日运势参考 → 主页链接",
        ]

    text = "\n".join(body_parts) + "\n"
    text = strip_banned(text, ban)
    cr = check_compliance(text, ban)
    if not cr.ok:
        text += "\n<!-- compliance: " + "; ".join(cr.violations) + " -->\n"

    return CopyBundle(
        copy_md=text,
        titles=titles,
        comment_cta=f"置顶：今日完整运势与报告入口 {frontend_url}",
        share_lines=share_lines,
    )


async def maybe_enrich_with_llm(bundle: CopyBundle, ranked: List[RankedAngle]) -> str:
    """若开启 OPS_LLM_ENABLED 且配置了 OPS_BAILIAN_APP_ID，则追加一段 LLM 润色（不覆盖引擎事实）。"""
    ops = get_ops_settings()
    if not ops.llm_enabled or not (ops.bailian_app_id or "").strip():
        return bundle.copy_md

    settings = get_settings()
    if not settings.bailian_api_key:
        return bundle.copy_md

    primary = ranked[0].angle if ranked else None
    if not primary:
        return bundle.copy_md

    prompt = (
        "你是 StarLoom 抖音口播编辑。根据下列「引擎事实」写一版 200 字内口播稿，"
        "禁止编造新的行星度数或相位；不要出现「算命」「占卜」。\n\n"
        f"事实与结构：\n{bundle.copy_md}\n"
    )
    try:
        svc = BailianApplicationService(settings, ops.bailian_app_id.strip())
        extra = await svc.generate(prompt)
        return bundle.copy_md + "\n\n【LLM 口播润色】\n" + extra.strip() + "\n"
    except Exception:
        return bundle.copy_md
