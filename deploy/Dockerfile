# Build from the repo root: docker build -f deploy/Dockerfile .
FROM python:3.12-slim

RUN apt-get update && apt-get install -y --no-install-recommends curl && rm -rf /var/lib/apt/lists/* \
    && useradd --create-home app && mkdir -p /data && chown app:app /data

WORKDIR /app

# CPU-only torch first, so the CUDA wheels (~6 GB) are never pulled in.
RUN pip install --no-cache-dir torch --index-url https://download.pytorch.org/whl/cpu

COPY pyproject.toml README.md ./
COPY src ./src
COPY external ./external
# Editable install: the package resolves the corpus root relative to its own source tree.
RUN pip install --no-cache-dir -e '.[server]' && chown -R app:app /app

USER app

# Models, embedded-Weaviate binary + index, and the generated KG all live on the /data volume.
ENV HF_HOME=/data/hf \
    XDG_CACHE_HOME=/data/cache \
    GEMPRF_ASSISTANT_WEAVIATE_PATH=/data/weaviate \
    GEMPRF_ASSISTANT_KG_PATH=/data/kg.ttl \
    GEMPRF_ASSISTANT_EMBEDDING_ALLOW_DOWNLOAD=1

EXPOSE 8000
HEALTHCHECK --interval=30s --timeout=5s --start-period=600s \
    CMD curl -fs http://localhost:8000/readyz || exit 1

CMD ["uvicorn", "gemprf_assistant.server:create_app", "--factory", "--host", "0.0.0.0", "--port", "8000"]
