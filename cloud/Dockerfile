FROM python:3.12-slim
WORKDIR /app
RUN apt-get update && apt-get install -y --no-install-recommends ffmpeg ca-certificates && rm -rf /var/lib/apt/lists/*
COPY . .
RUN pip install --no-cache-dir -r brain_v7/requirements.txt
ENV PYTHONPATH=/app
ENV BRAIN_SLEEP_SECONDS=60
ENV FACTORY_INTERVAL_SECONDS=21600
ENV FACTORY_ALLOW_PRODUCTION=1
ENV FACTORY_ALLOW_YOUTUBE_PUBLISH=0
ENV FACTORY_REQUIRE_REAL_MEDIA=1
CMD ["python","cloud/brain_cloud.py"]
