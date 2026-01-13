---
inclusion: always
---

# NeuroTwin Engineering Rules

## Architecture
- Business logic belongs in services/modules, never in views or serializers.
- One feature = one module. Keep boundaries clear.
- Max 300 lines per file. Split if larger.
- Shared utilities go in `core/`.
- Use adapters for all external integrations (APIs, third-party services).

## Code Style
- Single responsibility per function.
- No hardcoded secrets—use environment variables via `.env`.
- Prefer explicit over implicit; avoid magic values.
- Type hints required for function signatures.

## Cognitive Safety (Critical)
- All automations require explicit `permission_flag=True` before execution.
- Every Twin action must be logged with timestamp, action type, and outcome.
- Twin CANNOT perform financial, legal, or irreversible actions without user approval.
- Kill-switch must be available for all automated behaviors.

## Data & Learning
- Store cognitive data as: embeddings (vector DB) + structured profile (relational).
- All behavior updates must be reversible—maintain change history.
- Memory writes must be async to avoid blocking requests.

## Performance
- Never block HTTP requests with synchronous LLM calls.
- Use async/background tasks for: memory writes, embedding generation, external API calls.
- Cache frequently accessed cognitive profiles.

## Ethics & Safety
- User intention is paramount—never override or assume.
- Provide clear audit trails for all Twin decisions.
- Fail safe: when uncertain, ask rather than act.
