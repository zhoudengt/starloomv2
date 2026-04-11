"""两阶段报告生成：规划 JSON → 并行章节撰写 → 服务端组装。"""

from __future__ import annotations

import asyncio
import json
import logging
import re
from dataclasses import dataclass
from typing import Any, AsyncGenerator, Dict, Optional

from app.services.llm_service import BaseLLMService, generate_with_fallback, stream_with_fallback

logger = logging.getLogger(__name__)

MAX_PLAN_RETRIES = 1


@dataclass
class ChapterBlock:
    title: str
    content: str = ""
    word_count: int = 0


def _parse_plan(text: str) -> Optional[list[dict]]:
    """从 LLM 输出中提取 JSON sections 数组。"""
    try:
        data = json.loads(text.strip())
        sections = data.get("sections")
        if sections and isinstance(sections, list) and len(sections) >= 2:
            return sections
    except json.JSONDecodeError:
        pass
    m = re.search(r"\{[\s\S]*\}", text)
    if m:
        try:
            data = json.loads(m.group())
            sections = data.get("sections")
            if sections and isinstance(sections, list) and len(sections) >= 2:
                return sections
        except json.JSONDecodeError:
            pass
    return None


async def _generate_single_chapter(
    writer: BaseLLMService,
    fallback: Optional[BaseLLMService],
    section: dict,
    all_other_titles: list[str],
) -> ChapterBlock:
    """生成单个章节（非流式），用于并行调用。"""
    word_target = section.get("word_target", 400)
    title = section.get("title", "")
    prompt = (
        f"请撰写「{title}」章节。\n"
        f"目标字数: {word_target}字\n"
        f"关键星盘数据:\n{section.get('key_data', '')}\n\n"
        f"分析角度: {section.get('angle', '')}\n\n"
        f"其他章节标题（避免重复内容）: {', '.join(all_other_titles)}\n\n"
        f"要求: 深入分析，语气温暖专业，引用具体星盘数据。"
        f"直接输出正文，以 Markdown 二级标题 `## {title}` 开头。"
    )
    try:
        content = await generate_with_fallback(writer, fallback, prompt)
        return ChapterBlock(
            title=title,
            content=content.strip(),
            word_count=len(content),
        )
    except Exception as e:
        logger.warning("Chapter '%s' generation failed: %s", title, e)
        return ChapterBlock(title=title, content="", word_count=0)


async def two_stage_report(
    planner_llm: BaseLLMService,
    writer_llm: BaseLLMService,
    writer_fallback: Optional[BaseLLMService],
    plan_user_input: str,
    report_type: str,
    fallback_full_prompt: str,
    fallback_stream_params: Optional[Dict[str, Any]] = None,
) -> AsyncGenerator[dict[str, Any], None]:
    """
    两阶段报告生成器。
    yield 的 dict 结构：
      {"type": "stage", "stage": "planning"|"generating"|"composing", "message": "..."}
      {"type": "progress", "progress": int, "message": "..."}
      {"type": "content", "text": "..."}
    规划失败时自动回退到一次性流式生成。
    """
    _ = report_type  # reserved for future routing / logging

    yield {"type": "stage", "stage": "planning", "message": "正在分析你的星盘…"}

    plan: Optional[list[dict]] = None
    for attempt in range(1 + MAX_PLAN_RETRIES):
        try:
            plan_text = await planner_llm.generate(plan_user_input)
            plan = _parse_plan(plan_text)
            if plan:
                break
        except Exception as e:
            logger.warning("Plan attempt %d failed: %s", attempt, e)

    if not plan:
        logger.warning("Plan failed after retries, falling back to single-stage")
        yield {"type": "stage", "stage": "generating", "message": "正在撰写报告…"}
        sp = fallback_stream_params or {}
        async for chunk in stream_with_fallback(writer_llm, writer_fallback, fallback_full_prompt, sp):
            yield {"type": "content", "text": chunk}
        return

    total = len(plan)
    yield {"type": "progress", "progress": 5, "message": f"规划完成，共 {total} 个章节"}

    yield {"type": "stage", "stage": "generating", "message": "正在撰写报告…"}

    all_titles = [str(s.get("title", "")) for s in plan]
    tasks = [
        _generate_single_chapter(
            writer_llm,
            writer_fallback,
            section,
            [t for t in all_titles if t != section.get("title")],
        )
        for section in plan
    ]
    chapters: list[ChapterBlock] = await asyncio.gather(*tasks)

    yield {"type": "stage", "stage": "composing", "message": "正在整理排版…"}

    for i, chapter in enumerate(chapters):
        if chapter.content:
            yield {"type": "content", "text": chapter.content}
        else:
            yield {
                "type": "content",
                "text": f"\n\n## {chapter.title}\n\n（该章节暂时无法生成，请稍后重试）\n\n",
            }
        if i < total - 1:
            yield {"type": "content", "text": "\n\n"}
        progress = int(10 + 90 * (i + 1) / total)
        yield {"type": "progress", "progress": progress, "message": f"{i + 1}/{total} 章节已完成"}
