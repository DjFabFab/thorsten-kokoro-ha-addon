# Thorsten Kokoro HA Add-on — CPU-only, multi-arch (amd64 + aarch64)
# Basis: https://github.com/thorstenMueller/Thorsten-Voice/tree/master/docker/kokoro
# KEIN CUDA, KEIN GPU-Layer: torch kommt ausschliesslich vom CPU-Index
# (siehe requirements.txt --extra-index-url https://download.pytorch.org/whl/cpu).
# Keine arch-spezifischen RUNs, kein nvidia — pure CPU-Wheels laufen auf
# amd64 und aarch64. Multi-arch Build: `docker buildx build --platform
# linux/amd64,linux/arm64 -t thorsten-kokoro-addon:test .`
FROM python:3.11-slim

ENV PYTHONUNBUFFERED=1 \
    PIP_NO_CACHE_DIR=1 \
    DEBIAN_FRONTEND=noninteractive \
    HF_HUB_CACHE=/data/hf-cache \
    HF_HOME=/data/hf-cache \
    KOKORO_EPOCH=5 \
    SPEED=1.0 \
    HF_REPO_ID=Thorsten-Voice/Kokoro \
    ENABLE_HTTP=false \
    PORT=8000

# espeak-ng (+data): Phonemizer-Backend fuer misaki de-G2P
# libsndfile1: Laufzeit-Dep von soundfile
# git: noetig fuer "pip install git+https://..." (misaki/kokoro Forks)
# curl: fuer HEALTHCHECK; build-essential: fuer sdist-Fallbacks (CPU-only)
RUN apt-get update && apt-get install -y --no-install-recommends \
        espeak-ng \
        espeak-ng-data \
        libsndfile1 \
        git \
        curl \
        ca-certificates \
        build-essential \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /app

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY wyoming_bridge/ ./wyoming_bridge/
# HTTP + Wyoming entrypoint: http_server.py (FastAPI, Port 8000) + run.sh
# (dual startup 8000+10200).
COPY http_server.py ./
COPY run.sh ./
RUN chmod +x ./run.sh && mkdir -p /data/hf-cache

EXPOSE 8000 10200

VOLUME ["/data/hf-cache"]

HEALTHCHECK --interval=30s --timeout=5s --start-period=120s --retries=5 \
    CMD python3 -c "import socket;socket.create_connection(('127.0.0.1',10200),timeout=4).close()" && { [ "${ENABLE_HTTP:-false}" != "true" ] || curl -f "http://localhost:${PORT:-8000}/health"; } || exit 1

ENTRYPOINT ["./run.sh"]
