# StarLoom v2

AI 星座性格分析与运势参考 H5（抖音引流）。技术说明见 `docs/spec.md`、`docs/architecture.md`。

## 本地开发

### 后端

```bash
cd backend
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
cp .env.example .env   # 填写 Coze / 百炼 / xorpay 等
# 启动 MySQL(3307) 与 Redis(6380) 后：
uvicorn app.main:app --reload --host 0.0.0.0 --port 8000
```

### 前端

```bash
cd frontend
npm install
npm run dev
```

浏览器打开 `http://localhost:5173`，API 经 Vite 代理到 `http://127.0.0.1:8000`。

### Docker

```bash
cp backend/.env.example backend/.env
# 构建前端：cd frontend && npm run build
docker compose up -d --build
```

- 前端 + 反代：`http://localhost:8080`
- API：`http://localhost:8080/api/v1/...`

## 定时任务

每日批量生成 12 星座运势（示例，需配置 LLM）：

```bash
cd backend && source .venv/bin/activate
PYTHONPATH=. python ../scripts/generate_daily.py
```

## 合规

面向用户文案使用「性格分析」「运势参考」，避免「算命」「占卜」等表述。
