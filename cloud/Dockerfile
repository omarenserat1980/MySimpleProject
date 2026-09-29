FROM python:3.12-slim

WORKDIR /app

RUN apt-get update \
    && apt-get install -y --no-install-recommends ffmpeg ca-certificates docker.io \
    && rm -rf /var/lib/apt/lists/*

COPY . .

RUN python -m pip install --no-cache-dir --upgrade pip \
    && python -m pip install --no-cache-dir -r brain_v12/requirements.txt \
    && python -m pip install --no-cache-dir -r brain_v7/requirements.txt

ENV PYTHONPATH=/app
ENV BRAIN_SLEEP_SECONDS=60
ENV FACTORY_INTERVAL_SECONDS=21600
ENV FACTORY_ALLOW_PRODUCTION=1
ENV FACTORY_ALLOW_YOUTUBE_PUBLISH=0
ENV FACTORY_REQUIRE_REAL_MEDIA=1

CMD ["sh","-c","uvicorn cloud.api_server:app --host 0.0.0.0 --port ${PORT:-8000} & exec python cloud/brain_cloud.py"]

HEALTHCHECK --interval=10s --timeout=3s --start-period=20s --retries=5 CMD python -c "import urllib.request; urllib.request.urlopen('http://127.0.0.1:8000/healthz', timeout=2)"
