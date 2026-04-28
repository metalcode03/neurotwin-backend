# Tech Stack & Build System

## Language & Runtime
- Python 3.13+
- Package manager: uv

## Backend Framework
- Django 6.0+
- Django Rest Framework (DRF) with `djangorestframework`
- JWT auth via `djangorestframework-simplejwt` (with token blacklisting)
- OpenAPI schema via `drf-spectacular`

## Task Queue & Scheduling
- Celery 5.4+ with Redis broker (DB 1) and result backend (DB 2)
- `django-celery-beat` for scheduled tasks (DatabaseScheduler)
- `django-q2` retained for legacy async tasks

## Caching & Messaging
- Redis 7+ via `django-redis`
- Local memory cache fallback for dev/testing (`USE_REDIS=False`)

## AI/ML
- Google GenAI SDK (`google-genai`) — primary LLM provider
- Cerebras and Mistral via adapter pattern
- Credit-based usage tracking (`apps/credits`)

## Database
- PostgreSQL (primary relational DB via `psycopg[binary]`)
- SQLite for test runs only
- Vector DB for embeddings (planned — do not store embeddings in PostgreSQL)

## Security & Encryption
- `cryptography` (Fernet) for OAuth tokens, Meta credentials, API keys
- Separate encryption keys per credential type (`OAUTH_ENCRYPTION_KEY`, `META_ENCRYPTION_KEY`, `API_KEY_ENCRYPTION_KEY`)

## Observability
- `prometheus-client` for metrics
- `python-json-logger` for structured JSON logging
- Rotating log files per domain: credits, AI requests, automation events, security events

## Voice Services (planned)
- Twilio for telephony
- ElevenLabs for voice cloning

## Frontend
- Next.js (App Router) with TypeScript strict mode
- Tailwind CSS + Framer Motion
- Located in `neuro-frontend/`

## Common Commands

```bash
# Install backend dependencies
uv sync

# Run Django dev server
uv run python manage.py runserver

# Run Celery worker
uv run celery -A neurotwin worker -l info

# Run Celery Beat scheduler
uv run celery -A neurotwin beat -l info

# Run migrations
uv run python manage.py migrate

# Add a new dependency
uv add <package-name>

# Run tests
uv run pytest

# Frontend dev server (run manually)
cd neuro-frontend && npm run dev
```

## Environment
- Use `.env` for all secrets and configuration
- Never commit `.env` to version control
- See `.env.example` for required variables
- Key env vars: `DJANGO_SECRET_KEY`, `DB_*`, `REDIS_*`, `GOOGLE_API_KEY`, `CEREBRAS_API_KEY`, `MISTRAL_API_KEY`, `META_APP_SECRET`, `*_ENCRYPTION_KEY`
