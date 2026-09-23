FROM python:3.12-slim
WORKDIR /app
COPY . .
RUN pip install --no-cache-dir -r brain_v7/requirements.txt
ENV PYTHONPATH=/app
ENV BRAIN_SLEEP_SECONDS=60
CMD ["python","-c","from brain_v7.braincore_v2.fully_autonomous_runtime import run_forever; run_forever()"]
