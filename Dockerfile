FROM python:3.12-slim

WORKDIR /app

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1

# 安装运行环境与依赖
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# 复制业务源码
COPY src/ ./src/

CMD ["python", "-m", "src.main"]
