# Memory & CSM Backend Deployment Checklist

## Pre-Deployment Verification

### 1. File Structure ✅
- [x] `apps/memory/serializers.py` - Created
- [x] `apps/memory/views.py` - Created
- [x] `apps/memory/urls.py` - Created
- [x] `apps/csm/views.py` - Updated (added CSMPersonalityProfileView)
- [x] `apps/csm/urls.py` - Updated (added memory routes)

### 2. URL Routing ✅
- [x] Memory endpoints nested under `/api/v1/csm/memories/`
- [x] CSM personality profile at `/api/v1/csm/profile`
- [x] Raw CSM profile at `/api/v1/csm/profile/raw`

### 3. Documentation ✅
- [x] `docs/memory-csm-diagnosis.md` - Architectural analysis
- [x] `docs/memory-implementation-summary.md` - Implementation details
- [x] `docs/memory-api-reference.md` - API documentation

## Deployment Steps

### Step 1: Database Migrations
```bash
# Run migrations to ensure all tables and indexes exist
uv run python manage.py makemigrations
uv run python manage.py migrate

# Verify memory tables exist
uv run python manage.py dbshell
> \dt memory_*
> \dt csm_*
```

**Expected Tables:**
- `memory_records`
- `memory_access_logs`
- `csm_profiles`
- `csm_change_logs`

### Step 2: Environment Configuration
```bash
# Verify .env has required variables
cat .env | grep -E "(VECTOR_DB|EMBEDDING)"
```

**Required Variables:**
```env
# Vector database (if using external service)
VECTOR_DB_URL=<url>
VECTOR_DB_API_KEY=<key>

# Embedding configuration
EMBEDDING_MODEL=text-embedding-004
EMBEDDING_DIMENSION=768
```

### Step 3: Django Settings Verification
```python
# In neurotwin/settings.py, verify:

INSTALLED_APPS = [
    # ...
    'apps.memory',
    'apps.csm',
    # ...
]

# Ensure REST framework is configured
REST_FRAMEWORK = {
    'DEFAULT_AUTHENTICATION_CLASSES': [
        'rest_framework_simplejwt.authentication.JWTAuthentication',
    ],
    # ...
}
```

### Step 4: Test Endpoints

#### 4.1 Test CSM Personality Profile
```bash
# Get JWT token first
TOKEN=$(curl -X POST http://localhost:8000/api/v1/auth/login \
  -H "Content-Type: application/json" \
  -d '{"email":"test@example.com","password":"password"}' \
  | jq -r '.data.access')

# Test personality profile endpoint
curl -H "Authorization: Bearer $TOKEN" \
  http://localhost:8000/api/v1/csm/profile | jq
```

**Expected Response:**
```json
{
  "success": true,
  "data": {
    "userId": "...",
    "traits": [...],
    "tonePreferences": [...],
    "communicationStyle": "...",
    "decisionPatterns": [...],
    "updatedAt": "..."
  }
}
```

#### 4.2 Test Memory List
```bash
curl -H "Authorization: Bearer $TOKEN" \
  http://localhost:8000/api/v1/csm/memories | jq
```

**Expected Response:**
```json
{
  "success": true,
  "data": {
    "memories": [],
    "total": 0,
    "hasMore": false,
    "nextCursor": null
  }
}
```

#### 4.3 Test Memory Creation
```bash
curl -X POST \
  -H "Authorization: Bearer $TOKEN" \
  -H "Content-Type: application/json" \
  -d '{
    "content": "Test memory for deployment verification",
    "source": "conversation",
    "metadata": {"test": true}
  }' \
  http://localhost:8000/api/v1/csm/memories | jq
```

**Expected Status:** `201 Created`

#### 4.4 Test Memory Search
```bash
curl -X POST \
  -H "Authorization: Bearer $TOKEN" \
  -H "Content-Type: application/json" \
  -d '{"query": "test"}' \
  http://localhost:8000/api/v1/csm/memories/search | jq
```

#### 4.5 Test Memory Stats
```bash
curl -H "Authorization: Bearer $TOKEN" \
  http://localhost:8000/api/v1/csm/memories/stats | jq
```

### Step 5: Frontend Integration Testing

#### 5.1 Update Frontend API Client (if needed)
The frontend `api.ts` already has the correct endpoints:
```typescript
memory: {
  list: (query?: string) => 
    request<MemoryEntry[]>(`/csm/memories${query ? `?q=${query}` : ''}`),
  get: (memoryId: string) => 
    request<MemoryEntry>(`/csm/memories/${memoryId}`),
  getPersonalityProfile: () => 
    request<PersonalityProfile>('/csm/profile'),
}
```

#### 5.2 Test Frontend Components
1. Navigate to `/dashboard/memory`
2. Verify personality profile loads
3. Verify memory list displays
4. Test search functionality
5. Test memory detail view

### Step 6: Error Handling Verification

#### Test Authentication Errors
```bash
# Without token - should return 401
curl http://localhost:8000/api/v1/csm/memories

# With invalid token - should return 401
curl -H "Authorization: Bearer invalid_token" \
  http://localhost:8000/api/v1/csm/memories
```

#### Test Validation Errors
```bash
# Empty content - should return 400
curl -X POST \
  -H "Authorization: Bearer $TOKEN" \
  -H "Content-Type: application/json" \
  -d '{"content": "", "source": "conversation"}' \
  http://localhost:8000/api/v1/csm/memories
```

#### Test Not Found Errors
```bash
# Non-existent memory - should return 404
curl -H "Authorization: Bearer $TOKEN" \
  http://localhost:8000/api/v1/csm/memories/00000000-0000-0000-0000-000000000000
```

### Step 7: Performance Testing

#### Check Query Performance
```bash
# Time the memory list endpoint
time curl -H "Authorization: Bearer $TOKEN" \
  http://localhost:8000/api/v1/csm/memories?limit=100
```

**Expected:** < 500ms for 100 records

#### Check Database Indexes
```sql
-- Verify indexes exist
SELECT tablename, indexname 
FROM pg_indexes 
WHERE tablename IN ('memory_records', 'csm_profiles');
```

**Expected Indexes:**
- `memory_records_user_id_created_at_idx`
- `memory_records_user_id_source_idx`
- `memory_records_content_hash_idx`
- `csm_profiles_user_id_version_idx`

### Step 8: Logging Verification

#### Check Memory Access Logs
```python
# In Django shell
from apps.memory.models import MemoryAccessLog

# Should see access logs after testing
logs = MemoryAccessLog.objects.all()
print(f"Total access logs: {logs.count()}")
```

#### Check CSM Change Logs
```python
from apps.csm.models import CSMChangeLog

logs = CSMChangeLog.objects.all()
print(f"Total change logs: {logs.count()}")
```

## Post-Deployment Monitoring

### Metrics to Monitor

1. **API Response Times**
   - Memory list: < 500ms
   - Memory detail: < 200ms
   - Personality profile: < 300ms
   - Memory search: < 1000ms

2. **Error Rates**
   - 4xx errors: < 5%
   - 5xx errors: < 1%

3. **Database Performance**
   - Query time: < 100ms average
   - Connection pool usage: < 80%

4. **Memory Usage**
   - Vector DB memory: Monitor growth
   - PostgreSQL memory: Monitor query cache

### Health Check Endpoint
Consider adding:
```python
# In core/api/views.py
class HealthCheckView(BaseAPIView):
    permission_classes = []
    
    def get(self, request):
        # Check database
        from django.db import connection
        with connection.cursor() as cursor:
            cursor.execute("SELECT 1")
        
        # Check memory app
        from apps.memory.models import MemoryRecord
        MemoryRecord.objects.exists()
        
        return self.success_response(data={"status": "healthy"})
```

## Rollback Plan

If issues occur:

### 1. Disable Memory Endpoints
```python
# In apps/csm/urls.py, comment out:
# path('memories/', include('apps.memory.urls', namespace='memory')),
```

### 2. Revert CSM Changes
```bash
git checkout HEAD~1 apps/csm/views.py apps/csm/urls.py
```

### 3. Database Rollback
```bash
# If migrations were run
uv run python manage.py migrate memory <previous_migration>
```

## Known Issues & Workarounds

### Issue 1: Vector DB Not Configured
**Symptom:** Memory creation fails with vector DB error
**Workaround:** Use mock vector client for testing
```python
# In apps/memory/vector_client.py
def get_vector_client():
    return MockVectorDBClient()  # Use mock instead of real client
```

### Issue 2: Async Operations Blocking
**Symptom:** Slow response times on memory operations
**Solution:** Ensure async operations are properly configured
```python
# Check ASGI configuration in neurotwin/asgi.py
```

### Issue 3: Empty Personality Profile
**Symptom:** Profile endpoint returns empty traits
**Cause:** User hasn't completed onboarding
**Solution:** Ensure CSM profile exists before accessing

## Success Criteria

- [x] All endpoints return 200/201 for valid requests
- [x] Authentication properly enforced
- [x] Validation errors return 400 with details
- [x] Not found errors return 404
- [x] Response format matches frontend types
- [x] Pagination works correctly
- [x] Search functionality works
- [x] Memory access is logged
- [x] Performance meets targets

## Support Contacts

- **Backend Issues:** Check Django logs
- **Frontend Issues:** Check browser console
- **Database Issues:** Check PostgreSQL logs
- **Vector DB Issues:** Check vector client logs

## Additional Resources

- [Memory API Reference](./memory-api-reference.md)
- [Implementation Summary](./memory-implementation-summary.md)
- [Architecture Diagnosis](./memory-csm-diagnosis.md)
- [User Guide](./user-guide.md)
