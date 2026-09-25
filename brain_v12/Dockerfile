FROM --platform=linux/amd64 python:3.11-slim

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PORT=10000

WORKDIR /app

COPY brain_v12/requirements.txt /app/brain_v12/requirements.txt
RUN python -m pip install --no-cache-dir -r /app/brain_v12/requirements.txt

COPY . /app

EXPOSE 10000

CMD ["sh", "-c", "uvicorn brain_v12.app:app --host 0.0.0.0 --port ${PORT:-10000}"]
