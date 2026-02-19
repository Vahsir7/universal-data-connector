
FROM python:3.11-slim

WORKDIR /app

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    UVICORN_WORKERS=4 \
    UVICORN_BACKLOG=4096 \
    UVICORN_TIMEOUT_KEEP_ALIVE=5

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY . .

RUN useradd -m appuser \
    && chown -R appuser:appuser /app \
    && mkdir -p /app/data \
    && chown -R appuser:appuser /app/data

USER appuser

EXPOSE 8000

HEALTHCHECK --interval=15s --timeout=5s --start-period=30s --retries=5 \
    CMD python -c "import urllib.request; urllib.request.urlopen('http://127.0.0.1:8000/health/ready', timeout=2).read()" || exit 1

CMD ["sh", "-c", "uvicorn app.main:app --host 0.0.0.0 --port 8000 --workers ${UVICORN_WORKERS:-4} --loop uvloop --http httptools --backlog ${UVICORN_BACKLOG:-4096} --timeout-keep-alive ${UVICORN_TIMEOUT_KEEP_ALIVE:-5} --proxy-headers"]
