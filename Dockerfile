# =============================================================================
# Stage 1: Builder — install production dependencies with uv
# =============================================================================
FROM python:3.13-slim AS builder

COPY --from=ghcr.io/astral-sh/uv:latest /uv /uvx /bin/

WORKDIR /app

# Copy dependency files first for layer caching
COPY pyproject.toml uv.lock ./

# Install production dependencies into .venv
RUN uv sync --frozen --no-dev

# =============================================================================
# Stage 2: Runtime — minimal production image
# =============================================================================
FROM python:3.13-slim AS runtime

# Install runtime system dependencies
RUN apt-get update && \
    apt-get install -y --no-install-recommends libpq5 curl && \
    rm -rf /var/lib/apt/lists/*

WORKDIR /app

# Copy virtual environment from builder
COPY --from=builder /app/.venv /app/.venv

# Copy application code
COPY . .

# Create non-root user
RUN groupadd --gid 1000 appuser && \
    useradd --uid 1000 --gid appuser --no-create-home appuser

# Create logs directory with write permissions
RUN mkdir -p /app/logs && chown appuser:appuser /app/logs

# Make entrypoint executable
RUN chmod +x /app/docker/entrypoint.sh

# Switch to non-root user
USER appuser

# Environment variables
ENV DJANGO_SETTINGS_MODULE=neurotwin.settings
ENV PATH="/app/.venv/bin:$PATH"

EXPOSE 8000

ENTRYPOINT ["docker/entrypoint.sh"]

CMD ["sh", "-c", "gunicorn neurotwin.wsgi:application --bind 0.0.0.0:8000 --workers ${GUNICORN_WORKERS:-4} --timeout ${GUNICORN_TIMEOUT:-120} --graceful-timeout 25 --access-logfile - --error-logfile -"]
