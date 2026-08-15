FROM python:3.11-slim

WORKDIR /app

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PIP_NO_CACHE_DIR=1

# Build tooling is needed to compile some wheels, then removed so it does not
# ship in the final image.
RUN apt-get update && apt-get install -y --no-install-recommends \
    build-essential \
    libpq-dev \
    curl \
    && rm -rf /var/lib/apt/lists/*

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt \
    && apt-get purge -y --auto-remove build-essential \
    && rm -rf /var/lib/apt/lists/*

COPY . .

# Run as an unprivileged user; storage must be writable by it.
RUN useradd --create-home --uid 10001 sigma \
    && mkdir -p /app/storage/models /app/storage/datasets \
    && chown -R sigma:sigma /app
USER sigma

EXPOSE 8000

HEALTHCHECK --interval=30s --timeout=10s --start-period=20s --retries=3 \
    CMD curl -fsS "http://localhost:${PORT:-8000}/api/health" || exit 1

# Shell form so $PORT expands. Render (and most PaaS hosts) inject the port to
# bind and will fail the health check if the app hardcodes one.
# Single worker by design: each worker loads the full sklearn/XGBoost/LightGBM
# stack, which does not fit twice in a 512MB instance.
CMD uvicorn app.main:app --host 0.0.0.0 --port ${PORT:-8000} --workers ${WEB_CONCURRENCY:-1}
