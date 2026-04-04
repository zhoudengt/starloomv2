# 百炼系统提示词（文档）

本目录存放与各 **DashScope 百炼智能体** 对应的系统提示词 Markdown，便于复制到控制台与版本管理。

| 文件 | 环境变量 | 说明 |
|------|----------|------|
| [chat.md](chat.md) | `BAILIAN_APP_ID_CHAT` | 星织聊天 |
| [daily_fortune.md](daily_fortune.md) | `BAILIAN_APP_ID_DAILY` | 每日运势 JSON |
| [personality.md](personality.md) | `BAILIAN_APP_ID_PERSONALITY` | 性格分析 Markdown |
| [compatibility.md](compatibility.md) | `BAILIAN_APP_ID_COMPATIBILITY` | 配对分析 Markdown |
| [annual.md](annual.md) | `BAILIAN_APP_ID_ANNUAL` | 年度运势 Markdown |
| [quicktest.md](quicktest.md) | （已废弃） | 免费速测已改为 `astro_service.compute_quicktest_*` 纯规则，不再调百炼 |
| [personality_dlc.md](personality_dlc.md) | `BAILIAN_APP_ID_PERSONALITY` | 扩展包（职场/恋爱/成长） |
| [astro_event.md](astro_event.md) | `BAILIAN_APP_ID_PERSONALITY` | 天文事件主题报告 |

后端 user input 由 `backend/app/prompts/*.py` 与 `chart_formatter.py` 组装；系统提示词应包含语气、免责与输出格式，**不要**在代码里重复指令性长文案。
