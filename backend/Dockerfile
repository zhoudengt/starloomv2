FROM python:3.11-slim

WORKDIR /app

ENV PYTHONDONTWRITEBYTECODE=1
ENV PYTHONUNBUFFERED=1

# 加速国内服务器 apt（阿里云 Debian 镜像；失败则仍用默认源）
RUN find /etc/apt -type f \( -name '*.sources' -o -name 'sources.list' -o -name '*.list' \) \
    -exec sed -i 's|deb.debian.org|mirrors.aliyun.com|g' {} \; 2>/dev/null || true

# pyswisseph（kerykeion）编译需要 gcc + g++
RUN apt-get update && apt-get install -y --no-install-recommends gcc g++ default-libmysqlclient-dev \
    && rm -rf /var/lib/apt/lists/*

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt gunicorn

COPY app ./app

EXPOSE 8000

CMD ["gunicorn", "app.main:app", "-k", "uvicorn.workers.UvicornWorker", "-w", "2", "-b", "0.0.0.0:8000"]
