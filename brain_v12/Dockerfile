FROM --platform=linux/amd64 python:3.11-slim

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PORT=10000

WORKDIR /app

COPY brain_v12/requirements.txt /app/brain_v12/requirements.txt
RUN python -m pip install --no-cache-dir --upgrade pip \
    && python -m pip install --no-cache-dir -r /app/brain_v12/requirements.txt

COPY . /app

RUN python -m compileall -q brain_v12 \
    && BRAIN_DB=/tmp/brain-v12-build.db \
       BRAIN_LIVE_INCOME_SEARCH_ENABLED=false \
       BRAIN_WORKFORCE_ENABLED=false \
              python -m brain_v12.tools.ci_preflight

EXPOSE 10000

HEALTHCHECK --interval=30s --timeout=5s --start-period=20s --retries=5 \
  CMD python -c "import json,os,urllib.request; u='http://127.0.0.1:'+os.getenv('PORT','10000')+'/health'; d=json.load(urllib.request.urlopen(u, timeout=4)); raise SystemExit(0 if d.get('ok') is True else 1)"

CMD ["sh", "-c", "exec uvicorn brain_v12.app:app --host 0.0.0.0 --port ${PORT:-10000}"]
