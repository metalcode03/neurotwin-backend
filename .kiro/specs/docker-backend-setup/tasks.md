# Implementation Plan: Docker Backend Setup

## Overview

Containerize the NeuroTwin Django backend with a multi-stage Dockerfile (uv + Python 3.13-slim), an entrypoint script for DB readiness/migrations/collectstatic, and a Docker Compose stack orchestrating web (Gunicorn), Celery worker, Celery beat, and Redis services. PostgreSQL remains external (AWS RDS). Each task builds incrementally so the stack is functional after each checkpoint.

## Tasks

- [x] 1. Add Gunicorn dependency and STATIC_ROOT setting
  - [x] 1.1 Add `gunicorn>=23.0.0` to the `dependencies` list in `pyproject.toml`
    - Insert after the existing `google-genai` entry (alphabetical order)
    - _Requirements: 2.4_
  - [x] 1.2 Add `STATIC_ROOT = BASE_DIR / 'staticfiles'` to `neurotwin/settings.py`
    - Place it near the existing `STATIC_URL` and `STATICFILES_DIRS` settings
    - This is required for `collectstatic` to work in the entrypoint
    - _Requirements: 8.1_

- [x] 2. Create `.dockerignore` file
  - [x] 2.1 Create `.dockerignore` at the project root with exclusions for:
    - `.venv/`, `.git/`, `__pycache__/`
    - `neuro-frontend/`, `node_modules/`
    - `.env`, `logs/`, `*.log`
    - `.hypothesis/`, `tests/`, `docs/`
    - This reduces build context size and prevents secrets from leaking into the image
    - _Requirements: 1.4_

- [x] 3. Create the multi-stage Dockerfile
  - [x] 3.1 Create `Dockerfile` at the project root with a two-stage build
    - **Builder stage**: Use `python:3.13-slim` as base, copy `uv` binary from `ghcr.io/astral-sh/uv:latest`, copy `pyproject.toml` and `uv.lock` first for layer caching, run `uv sync --frozen --no-dev` to install production deps into `.venv`
    - **Runtime stage**: Use `python:3.13-slim` as base, install `libpq5` and `curl` via apt-get (runtime system deps), copy `.venv` from builder, copy application code, create non-root user `appuser` (UID 1000), create `logs/` directory with write permissions, set `DJANGO_SETTINGS_MODULE=neurotwin.settings`, set `PATH` to include `.venv/bin`, expose port 8000, set entrypoint to `docker/entrypoint.sh`, set default CMD to Gunicorn with `--bind 0.0.0.0:8000 --workers ${GUNICORN_WORKERS:-4} --timeout ${GUNICORN_TIMEOUT:-120} --graceful-timeout 25 --access-logfile - --error-logfile -`
    - _Requirements: 1.1, 1.2, 1.3, 1.4, 1.5, 1.6, 1.7, 1.8, 2.1, 2.2, 2.3, 2.5, 2.6_

- [x] 4. Create the entrypoint script
  - [x] 4.1 Create `docker/entrypoint.sh` with the initialization sequence
    - Add shebang `#!/bin/bash` and `set -e`
    - Implement a database wait loop using Python-based check: `python -c "import django; django.setup(); from django.db import connection; connection.ensure_connection()"` with max 30 retries and 2-second sleep between attempts
    - Run `python manage.py migrate --noinput` after DB is reachable
    - Run `python manage.py collectstatic --noinput` after migrations
    - Print timestamped log messages for each step (e.g., `echo "[$(date)] Waiting for database..."`)
    - Exit with non-zero code if any step fails
    - End with `exec "$@"` to hand off to CMD (Gunicorn, Celery worker, or Celery beat)
    - Make the file executable (`chmod +x`)
    - _Requirements: 4.1, 4.2, 4.3, 4.4, 4.5, 4.6_

- [x] 5. Checkpoint — Verify Dockerfile builds
  - Ensure the Dockerfile builds successfully with `docker build -t neurotwin-backend .`
  - Ensure all tests pass, ask the user if questions arise.

- [x] 6. Replace `docker-compose.yml` with full service stack
  - [x] 6.1 Rewrite `docker-compose.yml` with all four services and supporting configuration
    - **redis** service: `redis:7-alpine` image, `redis-server --appendonly yes --maxmemory 256mb --maxmemory-policy allkeys-lru` command, port `6379:6379`, `redis_data` named volume at `/data`, health check `redis-cli ping` (interval 10s, timeout 3s, retries 3), `restart: unless-stopped`, on `neurotwin` network
    - **web** service: build from `Dockerfile` (context `.`), port `8000:8000`, `env_file: .env`, environment overrides `REDIS_HOST=redis` and `USE_REDIS=True`, depends on `redis` (condition `service_healthy`), health check `curl -f http://localhost:8000/api/v1/health/` (interval 30s, timeout 10s, retries 3, start_period 40s), `stop_grace_period: 30s`, volumes `static_files:/app/staticfiles` and `./logs:/app/logs`, `restart: unless-stopped`, on `neurotwin` network
    - **celery_worker** service: same image as `web` (use `build` same context or `image` reference), command `celery -A neurotwin worker -l info -Q default,high_priority,incoming_messages,outgoing_messages --concurrency $${CELERY_CONCURRENCY:-4}`, `env_file: .env`, environment overrides `REDIS_HOST=redis` and `USE_REDIS=True`, depends on `redis` (healthy) and `web` (healthy), health check `celery -A neurotwin inspect ping` (interval 60s, timeout 30s, retries 3, start_period 60s), volume `./logs:/app/logs`, `restart: unless-stopped`, on `neurotwin` network
    - **celery_beat** service: same image as `web`, command `celery -A neurotwin beat -l info --scheduler django_celery_beat.schedulers:DatabaseScheduler --pidfile /tmp/celerybeat.pid`, `env_file: .env`, environment overrides `REDIS_HOST=redis` and `USE_REDIS=True`, depends on `redis` (healthy) and `web` (healthy), health check `test -f /tmp/celerybeat.pid` (interval 60s, timeout 10s, retries 3, start_period 30s), volume `./logs:/app/logs`, `restart: unless-stopped`, on `neurotwin` network
    - **Volumes**: `redis_data` (driver local), `static_files` (driver local)
    - **Networks**: `neurotwin` (driver bridge)
    - _Requirements: 3.1, 3.2, 3.3, 3.4, 3.5, 3.6, 3.7, 3.8, 3.9, 5.1, 5.2, 5.3, 5.4, 5.5, 5.6, 6.1, 6.2, 6.3, 6.4, 6.5, 7.1, 7.2, 7.3, 7.4, 8.2, 8.3, 9.1, 9.2, 9.3, 9.4, 9.5, 9.6, 10.1, 10.2, 10.3, 10.4_

- [x] 7. Update `.env.example` with Docker-specific variables
  - [x] 7.1 Add a `# Docker / Gunicorn Configuration` section to `.env.example`
    - Add `GUNICORN_WORKERS=4` with comment explaining it controls the number of Gunicorn worker processes
    - Add `GUNICORN_TIMEOUT=120` with comment explaining the request timeout in seconds
    - Add `CELERY_CONCURRENCY=4` with comment explaining the number of concurrent Celery worker processes
    - Place this section after the existing Celery configuration block
    - _Requirements: 2.2, 2.5, 7.5, 9.6_

- [x] 8. Final checkpoint — Verify full stack
  - Ensure all tests pass, ask the user if questions arise.
  - Verify `docker compose build` succeeds
  - Verify `docker compose config` validates without errors

## Notes

- No property-based tests — this is infrastructure configuration (Dockerfiles, Compose, shell scripts, settings)
- PostgreSQL is external (AWS RDS) and not included in Docker Compose
- The existing Redis-only `docker-compose.yml` is fully replaced with the complete service stack
- Each task references specific requirements for traceability
- Checkpoints ensure incremental validation of the build pipeline
