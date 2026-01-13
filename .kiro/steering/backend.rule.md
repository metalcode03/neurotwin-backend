---
inclusion: fileMatch
fileMatchPattern: ['**/*.py', '**/models.py', '**/views.py', '**/serializers.py', '**/urls.py']
---

# Django Backend Rules

## Framework & Authentication
- Use Django Rest Framework (DRF) for all API endpoints—no function-based views for APIs.
- JWT authentication is mandatory; use `djangorestframework-simplejwt`.
- Token refresh and blacklisting must be implemented.

## Models & Migrations
- All models must include `created_at` and `updated_at` timestamp fields.
- Use `django-simple-history` or equivalent for model versioning/audit trails.
- Migrations must be atomic and reversible—no data migrations mixed with schema changes.
- Name migrations descriptively (avoid auto-generated names for complex changes).

## Database Architecture
- Relational data (users, profiles, permissions) → PostgreSQL.
- Vector memory (embeddings, cognitive data) → Separate vector DB (e.g., pgvector, Pinecone).
- Never store embeddings in the main relational tables.

## Project Structure
- Cognitive engine logic lives in `/cognition` module.
- API views in `views.py`, business logic in `services.py`.
- Serializers handle validation only—no business logic.
- Use `selectors.py` for complex queries.

## Code Patterns
```python
# Serializer: validation only
class TwinSerializer(serializers.ModelSerializer):
    class Meta:
        model = Twin
        fields = ['id', 'name', 'cognitive_blend']

# Service: business logic
class TwinService:
    @staticmethod
    def create_twin(user, data: dict) -> Twin:
        # Business logic here
        pass
```

## Performance
- Use `select_related()` and `prefetch_related()` to avoid N+1 queries.
- Paginate all list endpoints using DRF's `PageNumberPagination`.
- Async views for LLM calls and external API integrations.
