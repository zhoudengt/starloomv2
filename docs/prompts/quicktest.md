# 速测（历史说明）

> **当前实现**：免费速测不再使用百炼智能体。五维分数、人格标签与摘要由
> `backend/app/services/astro_service.py` 中的 `compute_quicktest_bundle` 等函数，
> 基于本命盘（Swiss Ephemeris / kerykeion）**纯规则**计算，不经过百炼。

本文件保留作归档；若需调整文案倾向，请改 `compute_quicktest_summary` / 各 `_qt_score_*` 规则。
