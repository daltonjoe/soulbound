FROM python:3.11-slim

WORKDIR /app

RUN apt-get update && apt-get install -y --no-install-recommends \
    gcc \
    g++ \
    && rm -rf /var/lib/apt/lists/*

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    SE_EPHE_PATH=/app/ephemeris

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY ephemeris/ /app/ephemeris/
COPY prompts/ /app/prompts/
COPY module1_engine/ /app/module1_engine/
COPY astro_integration/ /app/astro_integration/
COPY static/ /app/static/
COPY main.py /app/

EXPOSE 8080 7860

CMD gunicorn main:app \
    --workers 2 \
    --worker-class uvicorn.workers.UvicornWorker \
    --bind 0.0.0.0:${PORT:-8080} \
    --timeout 300 \
    --graceful-timeout 60 \
    --preload

