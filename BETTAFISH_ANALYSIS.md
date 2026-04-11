# BettaFish 项目分析 — 可借鉴之处

> 分析日期：2026-04-10
> 对比项目：StarLoom v2、MiroFish

---

## 项目概览

**BettaFish（微舆）** 是一个多引擎舆情分析系统。用户提出研究问题后，3 个分析引擎从不同角度并行研究，ForumEngine 在旁实时综合，最终由 ReportEngine 汇总成结构化 HTML 报告。

### 架构总览

```
用户提出研究问题
        │
        ▼
   Flask Hub 分发
   ┌────┼────┐
   ▼    ▼    ▼
Insight Query Media     ← 3 个引擎各自独立研究
(本地DB) (Tavily) (Bocha)
   │    │    │
   ▼    ▼    ▼
 .log  .log  .log  ──→  ForumEngine（监控日志 + HOST LLM 综合）──→ forum.log
   │    │    │                                                        │
   ▼    ▼    ▼                                                        │
 .md   .md   .md  ──────────────────────────────────────────────────→ │
                                                                      ▼
                                                              ReportEngine
                                                    模板→布局→篇幅→章节→IR→HTML
                                                              │
                                                              ▼
                                                        最终 HTML 报告
```

### 技术栈

- 后端：Flask + Flask-SocketIO + Streamlit（子进程）
- LLM：OpenAI 兼容接口（每个引擎独立配置模型）
- 搜索：Tavily / Bocha / Anspire / 本地 MediaCrawlerDB
- NLP：sentence-transformers（聚类）+ 情感分析模型
- 配置：Pydantic BaseSettings + .env
- 数据库：PostgreSQL/MySQL（爬虫数据）
- 部署：Docker Compose

---

## 5 个值得借鉴的设计

### 1. 反思循环（Reflection Loop）

每个引擎的每个段落不是"搜一次就写"，而是：

```
搜索 → 总结 → 反思"信息够不够?" → 补充搜索 → 更新总结 → 再反思...（N 轮）
```

**核心代码**（`InsightEngine/agent.py`）：

```python
def _process_paragraphs(self):
    for i in range(total_paragraphs):
        self._initial_search_and_summary(i)      # 第一次搜索+总结
        self._reflection_loop(i)                   # N 轮反思补充
        self.state.paragraphs[i].research.mark_completed()

def _reflection_loop(self, paragraph_index):
    for reflection_i in range(self.config.MAX_REFLECTIONS):   # 可配置轮数
        reflection_output = self.reflection_node.run(...)      # LLM 判断还缺什么
        search_response = self.execute_search_tool(...)        # 补充搜索
        self.state = self.reflection_summary_node.mutate_state(...)  # 更新总结
```

**对 StarLoom 的启发**：
- 比"两阶段"更精细，可以在报告每个章节内部做 1 轮反思
- 写完初稿后 LLM 自问"这段分析有没有遗漏的星盘数据？"，然后补充
- MAX_REFLECTIONS 可配置，生产环境设为 1 即可平衡质量与延迟

---

### 2. 多引擎并行 + 论坛综合

3 个引擎各自独立运行（不同数据源、不同视角），ForumEngine 通过**监控日志文件**实时捕获中间产出，HOST LLM 定期发表"综合点评"：

```python
# ForumEngine/monitor.py — 每 5 条 agent 发言触发一次主持人综合
if len(self.agent_speeches_buffer) >= self.host_speech_threshold:
    host_speech = generate_host_speech(recent_speeches)  # HOST LLM 综合
    self.write_to_forum_log(host_speech, "HOST")
```

**通信方式是文件而非 API**——引擎之间零耦合，只通过 `.log` 和 `.md` 文件交换信息。

**对 StarLoom 的启发**：
- 如果未来做"多维度运势分析"（事业 + 感情 + 健康并行分析），可借鉴"各自独立分析，最后汇总"的模式
- 文件级解耦的思路简单可靠，适合引擎之间不需要实时交互的场景

---

### 3. ReportEngine 的多阶段流水线

报告生成不是一次 LLM 调用，是 **5 个独立阶段**，每阶段的输出约束下一阶段：

```
模板选择 → 文档布局（标题/目录/主题色）→ 篇幅规划（每章字数目标）→ 逐章生成 → IR 装订 → HTML 渲染
```

```python
# ReportEngine/agent.py 核心阶段
template_result = self._select_template(query, reports, forum_logs, custom_template)
layout_design = self.document_layout_node.run(sections, ...)       # 标题/目录/主题
word_plan = self.word_budget_node.run(sections, layout_design, ...)  # 每章字数分配
for section in sections:
    chapter_payload = self.chapter_generation_node.run(section, generation_context, ...)
document_ir = self.document_composer.build_document(report_id, manifest_meta, chapters)
html_report = self.renderer.render(document_ir)
```

每个阶段都有**重试 + 降级**机制：
- 章节生成失败自动重试（可配置最大次数）
- 多次失败后保留"字数最多的版本"作为兜底
- 跨引擎 LLM fallback：Report LLM 失败后尝试 Forum/Insight/Media 的 LLM

**对 StarLoom 的启发**：
- 这是我们讨论的"两阶段"思路的完整工程实现
- **篇幅规划阶段**值得借鉴——给每章分配字数目标，防止 LLM 某些章节写太长、某些太短
- 重试 + 降级机制可直接套用：JSON 解析失败 → 重试 → 兜底

---

### 4. IR（中间表示）分离内容与渲染

BettaFish 不是让 LLM 直接输出 HTML/Markdown，而是输出**结构化 JSON**（IR），再由渲染器转 HTML：

```
LLM → 章节 JSON（heading/paragraph/table/quote blocks）→ IR Validator → Document IR → HTML Renderer
```

好处：
- LLM 输出可校验（JSON Schema 检查）
- 同一份 IR 可渲染成 HTML、PDF、Markdown 等多种格式
- 渲染逻辑与 LLM 逻辑完全解耦

**对 StarLoom 的启发**：
- 当前报告是 LLM 直接输出 Markdown 流，混排质量不可控
- 如果未来需要多格式导出（PDF/分享卡/小程序预览），可引入 IR 层
- 当前阶段**优先级较低**，但架构上值得预留空间

---

### 5. SSE 进度推送 + 章节级状态

ReportEngine 的 SSE 设计比简单的流式文本精细——推送**阶段事件**：

```python
emit('stage', {'stage': 'template_selected', 'template': ...})
emit('progress', {'progress': 10, 'message': '模板选择完成'})
emit('chapter_status', {'chapterId': ..., 'status': 'running'})
emit('chapter_chunk', {'chapterId': ..., 'delta': ...})  # 章节内容流
emit('chapter_status', {'chapterId': ..., 'status': 'completed'})
emit('progress', {'progress': 60, 'message': '章节 3/5 已完成'})
```

前端可据此显示：整体进度条 + 每章节独立状态（运行中/重试中/完成）。

SSE 还有 subscriber Queue + 历史回放机制（`history_since`），断线重连不丢失事件。

**对 StarLoom 的启发**：
- 如果实施两阶段报告，可以把 SSE 从纯文本流改为事件流
- 前端可显示"正在分析你的第 3 章：情感模式..."而非"一直在出字"
- 用户体验明显更好

---

## 三项目对比

| 设计维度 | MiroFish | BettaFish | StarLoom v2（现状） |
|---------|----------|-----------|-------------------|
| Agent 数量 | 多个 OASIS Agent + 1 ReportAgent | 3 Engine + 1 Forum + 1 Report | 0（纯 LLM 调用） |
| 工作流 | ReACT 循环 | Node 顺序执行 + 反思循环 | 单次调用 |
| Agent 通信 | Zep 图谱 + IPC 文件 | 日志文件 + Markdown 文件 | 无 |
| 报告生成 | 大纲→分段 ReACT→拼合 | 模板→布局→篇幅→章节→IR→HTML | prompt→一次性流式 |
| 记忆机制 | Zep 知识图谱 | 无持久记忆 | 无 |
| 前端交互 | Vue 多步骤 | Flask+SocketIO+SSE 事件流 | React SSE 纯文本流 |
| 错误处理 | 基础 try/catch | 重试+降级+跨引擎LLM fallback | 基础 fallback |

---

## 对 StarLoom 的借鉴优先级

### 高优先级（可直接补入 OPTIMIZATION_PLAN）

1. **篇幅规划阶段**：在"规划 JSON"和"逐章写"之间加一步"每章分配字数目标"，防止章节长短不均
2. **章节生成重试+降级**：JSON 解析失败自动重试，多次失败保留最佳版本作为兜底

### 中优先级（改善体验）

3. **SSE 事件化**：报告生成时推送阶段事件而非纯文本，前端显示进度和当前阶段
4. **反思循环**：重要章节写完后做 1 轮"自检+补充"，提升关键章节深度

### 低优先级（远期规划）

5. **IR 结构化输出**：当需要多格式导出（PDF/分享卡）时再考虑
6. **多引擎并行分析**：当产品需要多维度运势报告时引入

---

## 关键源文件索引

| 文件 | 作用 |
|------|------|
| `InsightEngine/agent.py` | 深度搜索 agent，含反思循环 |
| `QueryEngine/agent.py` | Tavily 搜索 agent，结构同 Insight |
| `MediaEngine/agent.py` | 多媒体搜索 agent，结构同 Insight |
| `ForumEngine/monitor.py` | 日志监控 + HOST LLM 综合 |
| `ForumEngine/llm_host.py` | HOST LLM 发言生成 |
| `ReportEngine/agent.py` | 报告总调度：模板→布局→篇幅→章节→IR→HTML |
| `ReportEngine/flask_interface.py` | 报告 API + SSE 进度推送 |
| `ReportEngine/ir/schema.py` | IR 文档结构 JSON Schema |
| `ReportEngine/renderers/` | HTML/PDF 渲染器 |
| `config.py` | Pydantic 全局配置 |
| `app.py` | Flask 主入口，进程管理，SocketIO |
