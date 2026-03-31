# WatchFinder: Next.js static UI + FastAPI (single port 8080).

# --- Next.js static UI ---
FROM node:20-bookworm-slim AS frontend-build
WORKDIR /fe
COPY frontend/package.json frontend/package-lock.json ./
RUN npm ci
COPY frontend/ ./
RUN npm run build

# --- API + static ---
FROM python:3.12-slim-bookworm

ARG VERSION=dev
LABEL org.opencontainers.image.title="WatchFinder" \
      org.opencontainers.image.description="eBay watch sourcing — Browse API, Postgres, web UI" \
      org.opencontainers.image.version="${VERSION}"

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PYTHONPATH=/app/backend

WORKDIR /app

RUN apt-get update && apt-get install -y --no-install-recommends \
    build-essential \
    curl \
    libpq-dev \
    && rm -rf /var/lib/apt/lists/*

COPY requirements.txt /app/requirements.txt
RUN pip install --no-cache-dir -r /app/requirements.txt \
    && apt-get purge -y build-essential \
    && apt-get autoremove -y \
    && rm -rf /var/lib/apt/lists/*

COPY backend /app/backend
COPY alembic /app/alembic
COPY alembic.ini /app/alembic.ini
COPY docker/start.sh /app/docker/start.sh
RUN chmod +x /app/docker/start.sh

COPY --from=frontend-build /fe/out /app/frontend/out

RUN useradd --create-home --shell /bin/sh --uid 1000 watchfinder \
    && chown -R watchfinder:watchfinder /app

USER watchfinder

EXPOSE 8080

HEALTHCHECK --interval=30s --timeout=5s --start-period=90s --retries=3 \
    CMD sh -c 'curl -fsS "http://127.0.0.1:${APP_PORT:-8080}/health" || exit 1'

CMD ["/app/docker/start.sh"]
