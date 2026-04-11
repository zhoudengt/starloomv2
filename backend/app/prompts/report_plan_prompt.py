"""Report planner: user input builder — system prompt lives in 百炼 (report_planner)."""

SECTION_HINTS: dict[str, str] = {
    "personality": "太阳星座深度解读, 性格优势与挑战, 感情与亲密关系, 事业与财富节奏, 人际关系与社交, 年度成长建议, 专属行动清单",
    "compatibility": "缘分指数, 你们的化学反应, 双人能量与节奏, 沟通与相处模式, 冲突与修复建议, 长期关系参考",
    "annual": "整体基调, 事业与学业, 感情与人际, 财务与资源, 健康与节奏, 月度提示, 成长建议",
}


def build_plan_user_input(report_type: str, natal_chart_text: str) -> str:
    hints = SECTION_HINTS.get(report_type, "")
    return (
        f"报告类型: {report_type}\n"
        f"章节标题（必须完全使用这些标题）: {hints}\n\n"
        f"星盘数据:\n{natal_chart_text}"
    )
