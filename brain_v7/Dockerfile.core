# Compatibility image name retained for existing deployment references.
# Runtime is Brain V12 only; the retired V7 factory is not an entrypoint.
FROM python:3.12-slim
WORKDIR /app
COPY . .
RUN apt-get update \
    && apt-get install -y --no-install-recommends ffmpeg ca-certificates \
    && rm -rf /var/lib/apt/lists/* \
    && python -m pip install --no-cache-dir -r brain_v12/requirements.txt
ENV PYTHONPATH=/app
ENV PORT=8012
CMD ["python", "-m", "brain_v12.app"]
