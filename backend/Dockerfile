# ============================================================================
# QStock Backend Dockerfile
# ============================================================================
# Multi-stage production image with a non-root runtime user.
# ============================================================================

FROM python:3.12-slim AS builder

ARG DEBIAN_FRONTEND=noninteractive

RUN apt-get update && apt-get install -y --no-install-recommends \
    gcc \
    g++ \
    libpq-dev \
    python3-dev \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /build
COPY requirements.txt .

RUN python -m venv /opt/venv
ENV PATH="/opt/venv/bin:$PATH"
RUN pip install --no-cache-dir --upgrade pip setuptools wheel && \
    pip install --no-cache-dir -r requirements.txt

FROM python:3.12-slim

ARG DEBIAN_FRONTEND=noninteractive

LABEL maintainer="QStock Team" \
      version="1.0.0" \
      description="QStock Inventory Intelligence Platform Backend"

RUN apt-get update && apt-get install -y --no-install-recommends \
    libpq5 \
    postgresql-client \
    curl \
    && rm -rf /var/lib/apt/lists/*

RUN groupadd -r appuser && \
    useradd -r -g appuser -u 1001 appuser

WORKDIR /app

COPY --from=builder /opt/venv /opt/venv
COPY --chown=appuser:appuser . .

RUN mkdir -p /app/uploads /app/logs && \
    chown -R appuser:appuser /app

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PIP_NO_CACHE_DIR=1 \
    PIP_DISABLE_PIP_VERSION_CHECK=1 \
    PATH="/opt/venv/bin:$PATH" \
    PYTHONPATH="/app"

USER appuser

EXPOSE 8000

HEALTHCHECK --interval=30s --timeout=10s --start-period=40s --retries=3 \
    CMD curl -f http://localhost:8000/health || exit 1

# Fail closed: if migrations fail, the API process is not started.
CMD ["sh", "-c", "alembic upgrade head && exec uvicorn src.main:app --host 0.0.0.0 --port 8000 --workers 4"]
