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

# 国内 PyPI；Broken pipe 多为下载中断，提高重试/超时；仍失败可换源构建：
#   docker compose build --build-arg PIP_INDEX_URL=https://pypi.tuna.tsinghua.edu.cn/simple --build-arg PIP_TRUSTED_HOST=pypi.tuna.tsinghua.edu.cn
ARG PIP_INDEX_URL=https://mirrors.aliyun.com/pypi/simple/
ARG PIP_TRUSTED_HOST=mirrors.aliyun.com
ENV PIP_INDEX_URL=${PIP_INDEX_URL}
ENV PIP_TRUSTED_HOST=${PIP_TRUSTED_HOST}
ENV PIP_DISABLE_PIP_VERSION_CHECK=1

# BuildKit 缓存 wheel（不进入镜像层）；需 Docker 启用 BuildKit（compose v2 默认开启）
RUN --mount=type=cache,target=/root/.cache/pip \
    pip install -U pip setuptools wheel \
    && pip install --timeout=600 --retries=20 -r requirements.txt gunicorn

COPY app ./app

EXPOSE 8000

CMD ["gunicorn", "app.main:app", "-k", "uvicorn.workers.UvicornWorker", "-w", "2", "-b", "0.0.0.0:8000"]
