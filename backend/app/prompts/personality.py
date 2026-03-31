"""Personality report prompt."""


def build_personality_prompt(
    birth_date: str,
    sun_sign: str,
    sun_sign_cn: str,
    birth_time: str | None = None,
    gender: str | None = None,
) -> str:
    time_part = ""
    if birth_time:
        time_part = f"出生时间为{birth_time}，可参考月亮星座和上升星座。"
    gender_part = f"性别：{gender}。" if gender else ""
    return f"""你是一位资深的星座性格分析师。用户出生日期为{birth_date}，太阳星座为{sun_sign_cn}（{sun_sign}）。
{time_part}{gender_part}

请生成一份深度个性化的星座性格分析报告，包含以下章节（使用 Markdown 标题）：

## 1. 太阳星座解读
解读核心性格特质、行为模式、价值观。

## 2. 性格优势
3-5 个突出优点，结合具体场景说明。

## 3. 性格挑战
2-3 个需要注意的方面，给出建设性建议。

## 4. 感情特质
恋爱观、理想伴侣类型、相处模式。

## 5. 事业方向
适合的职业方向、工作风格、职场建议。

## 6. 人际关系
社交风格、与不同星座的相处之道。

## 7. 成长建议
个人发展方向、需要培养的能力。

要求：
- 每个章节 150-300 字
- 语气温暖专业，像一位懂你的老朋友
- 内容要有具体洞察，不要泛泛而谈
- 适当引用星座特质但不死板
- 总字数 1500-2500 字
- 文末附一行免责声明：本内容基于星座文化提供性格分析参考，仅供娱乐，不构成任何决策建议。"""
