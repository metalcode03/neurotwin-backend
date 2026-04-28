---
inclusion: always
---

# NeuroTwin Engineering Rules

## Architecture
- Business logic belongs in `services.py`, never in views or serializers.
- One feature = one Django app. Keep module boundaries clear.
- Max 300 lines per file. Split if larger.
- Shared utilities go in `core/` (project-level) or `apps/core/` (app-level).
- Use adapters for all external integrations (LLMs, OAuth, webhooks, voice).
- LLM calls must go through `apps/credits/providers/` or `core/ai/` adapters — never called directly from views.

## Code Style
- Single responsibility per function.
- No hardcoded secrets — use environment variables via `.env`.
- Prefer explicit over implicit; avoid magic values.
- Type hints required for all function signatures.
- Use `selectors.py` for complex DB queries; keep views thin.

## Cognitive Safety (Critical)
- All automations require explicit `permission_flag=True` before execution.
- Every Twin action must be logged with timestamp, action type, and outcome.
- Twin CANNOT perform financial, legal, or irreversible actions without user approval.
- Kill-switch must be available for all automated behaviors and terminate immediately.
- Cognitive Blend > 80% requires user confirmation before any action.

## Data & Learning
- Relational data (users, profiles, permissions) → PostgreSQL.
- Embeddings and cognitive vector data → separate vector DB. Never store in PostgreSQL.
- All behavior updates must be reversible — maintain change history.
- Memory writes must be async (Celery tasks) to avoid blocking requests.

## Performance
- Never block HTTP requests with synchronous LLM calls.
- Use Celery for: memory writes, embedding generation, external API calls, token refresh.
- Cache frequently accessed cognitive profiles via Redis.
- Use `select_related()` / `prefetch_related()` to avoid N+1 queries.
- Paginate all list endpoints.

## Security
- Encrypt all OAuth tokens and third-party credentials using Fernet (`cryptography`).
- Use separate encryption keys per credential type.
- Sanitize all user input before including in LLM prompts.
- Rate-limit all API endpoints; stricter limits on auth and installation endpoints.
- Log all security events to `security_events` log handler with 90-day retention.

## Ethics & Safety
- User intention is paramount — never override or assume.
- Provide clear audit trails for all Twin decisions.
- Fail safe: when uncertain, ask rather than act.
- Distinguish Twin-generated content from user-authored content at all times.
