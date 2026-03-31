"""Daily fortune prompt — LLM outputs JSON per spec."""


def build_daily_prompt(sign_cn: str, fortune_date: str) -> str:
    return f"""你是一位专业的星座分析师，请为{sign_cn}生成今日({fortune_date})的运势分析。

要求：
1. 综合运势评分（0-100）
2. 分项评分：爱情、事业、财运、健康（各 0-100）
3. 幸运色和幸运数字
4. 今日概述（50-80字）
5. 爱情详解（60-100字）
6. 事业详解（60-100字）
7. 财运简述（30-50字）
8. 健康提示（30-50字）
9. 今日建议（一句话）

请以 JSON 格式输出，字段如下：
{{
  "overall_score": 85,
  "love_score": 70,
  "career_score": 90,
  "wealth_score": 80,
  "health_score": 85,
  "lucky_color": "红色",
  "lucky_number": 7,
  "summary": "...",
  "love": "...",
  "career": "...",
  "wealth": "...",
  "health": "...",
  "advice": "..."
}}

语气要求：积极向上但不空泛，具体实用，像朋友间的贴心建议。
避免：绝对化表述（一定会、必须、肯定），负面恐吓。
只输出 JSON，不要其他文字。"""
