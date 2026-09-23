FROM python:3.12-slim
WORKDIR /app
COPY . .
RUN apt-get update \
    && apt-get install -y --no-install-recommends ffmpeg \
    && rm -rf /var/lib/apt/lists/*
RUN pip install --no-cache-dir -r brain_v7/requirements.txt
ENV PYTHONPATH=/app
ENV BRAIN_SLEEP_SECONDS=60
ENV FACTORY_INTERVAL_SECONDS=21600
ENV FACTORY_ALLOW_PRODUCTION=0
ENV FACTORY_ALLOW_YOUTUBE_PUBLISH=0
CMD ["python","-m","brain_v7.braincore_v2.background_factory_worker"]
