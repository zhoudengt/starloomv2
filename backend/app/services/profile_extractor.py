"""从报告内容中提取用户画像标签（后台异步调用，不影响 SSE 流）。"""

import json
import logging
import re
from datetime import datetime
from typing import Optional

from app.services.llm_service import BaseLLMService

logger = logging.getLogger(__name__)


async def extract_profile_from_report(
    llm: BaseLLMService,
    report_type: str,
    content: str,
) -> Optional[dict]:
    """截取前 1500 字发给画像提取器百炼应用，返回 {"tags": [...], "insight": "..."}。"""
    user_input = f"报告类型: {report_type}\n报告内容（节选）:\n{content[:1500]}"
    try:
        raw = await llm.generate(user_input)
        m = re.search(r"\{[\s\S]*\}", raw)
        if m:
            return json.loads(m.group())
    except Exception as e:
        logger.warning("Profile extraction failed: %s", e)
    return None


def merge_profile(existing: Optional[dict], new_extraction: dict, report_type: str) -> dict:
    """增量合并画像：新标签在前旧标签在后，超限自然淘汰。"""
    profile = existing.copy() if existing else {
        "tags": [], "summary": "", "report_insights": []
    }

    new_tags = new_extraction.get("tags", [])
    old_tags = profile.get("tags", [])
    all_tags = new_tags + old_tags
    seen: set[str] = set()
    unique_tags: list[str] = []
    for t in all_tags:
        if t not in seen:
            seen.add(t)
            unique_tags.append(t)
    profile["tags"] = unique_tags[:15]

    insight = new_extraction.get("insight", "")
    if insight:
        insights = profile.get("report_insights", [])
        insights.insert(0, {
            "type": report_type,
            "date": datetime.utcnow().strftime("%Y-%m-%d"),
            "insight": insight,
        })
        profile["report_insights"] = insights[:10]

    profile["updated_at"] = datetime.utcnow().isoformat()
    return profile
