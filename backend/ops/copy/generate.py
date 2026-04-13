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
        sign_names = "、".join(a.sign_cn_involved) if a.sign_cn_involved else "星座"
        titles = [
            f"{sign_names}今日运势参考",
            f"今天{sign_names}需要注意什么？",
            f"{sign_names}：今日状态一览",
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


async def build_article_body(
    ranked_angle: RankedAngle,
    d_iso: str,
    ephemeris_line: str,
    frontend_url: str,
) -> str:
    """为 ranked angle 生成 800-1500 字长文（用于 H5 轮播文章正文）。"""
    ops = get_ops_settings()
    settings = get_settings()
    a = ranked_angle.angle
    sign_names = "、".join(a.sign_cn_involved) if a.sign_cn_involved else "星座"
    facts = "\n".join(f"- {f}" for f in a.engine_facts) if a.engine_facts else "暂无详细天象数据"

    prompt = (
        f"你是 StarLoom 星座内容编辑。请根据以下天象事实，为「{sign_names}」写一篇 800-1500 字的今日运势参考长文。\n\n"
        f"日期：{d_iso}\n"
        f"天象概览：{ephemeris_line}\n"
        f"引擎事实：\n{facts}\n\n"
        "要求：\n"
        "1. 用 Markdown 格式，包含 2-3 个小节（如事业/学业、感情/人际、情绪/健康）\n"
        "2. 语气亲切自然，像朋友聊天，不要学术化\n"
        "3. 每个小节给出具体可操作的建议\n"
        "4. 禁止使用「算命」「占卜」等词，只用「运势参考」「性格分析」\n"
        "5. 结尾引导读者到 StarLoom 查看更详细的个人报告\n"
        "6. 不要编造具体行星度数，天象事实以上面提供的为准\n"
    )

    if ops.llm_enabled and (ops.bailian_app_id or "").strip() and settings.bailian_api_key:
        try:
            svc = BailianApplicationService(settings, ops.bailian_app_id.strip())
            body = await svc.generate(prompt)
            body = strip_banned(body, [])
            if len(body) >= 200:
                return body.strip()
        except Exception:
            pass

    return (
        f"## {sign_names}今日运势参考\n\n"
        f"**日期**：{d_iso}\n\n"
        f"### 天象概览\n\n{ephemeris_line}\n\n"
        "### 事业与学业\n\n"
        f"今天{sign_names}在工作和学习方面需要保持专注。"
        "建议把精力集中在最重要的事情上，不要分散注意力。"
        "如果遇到需要沟通的场合，先理清思路再开口。\n\n"
        "### 感情与人际\n\n"
        "人际关系方面，今天适合倾听多于表达。"
        "给身边的人多一点耐心，关系会更顺畅。\n\n"
        "### 情绪与能量\n\n"
        "注意调节自己的节奏，累了就休息一下。"
        "运势参考只是提醒，真正的好运来自你每一天的用心经营。\n\n"
        f"---\n\n想看更个性化的分析？来 StarLoom 生成你的专属报告。\n"
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
