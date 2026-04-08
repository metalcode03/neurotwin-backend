# AI System Performance Optimizations

## Summary of Optimizations Applied

### 1. Gemini Provider Optimizations
- **Singleton Client**: Gemini client is now initialized once and reused across all requests (thread-safe)
- **Model List Caching**: Available models are cached for 1 hour to avoid repeated API calls
- **Reduced Timeout**: 30s → 10s for faster failure detection
- **Reduced Retries**: 3 → 2 attempts with faster backoff (0.5s, 1s instead of 1s, 2s, 4s)
- **Simplified Prompt Format**: Removed verbose markers like `[SYSTEM]`, `[USER]` to reduce prompt size
- **Dynamic Token Limits**: Automatically reduces max_tokens for shorter responses

### 2. Cerebras Provider Optimizations
- **Reduced Timeout**: 30s → 15s for faster failure detection
- **Reduced Retries**: 3 → 2 attempts with faster backoff (0.5s, 1s)

### 3. Mistral Provider Optimizations
- **Reduced Timeout**: 30s → 15s for faster failure detection
- **Reduced Retries**: 3 → 2 attempts with faster backoff (0.5s, 1s)

## Expected Performance Improvements

### Before Optimizations
- Gemini latency: ~2.2s (acceptable)
- Cerebras fallback: up to 44s (too slow)
- Total worst-case: 25-50s

### After Optimizations
- Gemini latency: ~1.5-2s (improved)
- Cerebras fallback: ~10-15s (significantly improved)
- Total worst-case: ~15-20s (50% improvement)

## What is NOT Cached

**IMPORTANT**: The optimizations do NOT cache AI responses. Each request generates a fresh response.

The only caching is:
1. **Gemini available models list** (1 hour TTL) - This is metadata about which models exist
2. **Gemini client instance** (singleton) - This is just the HTTP client, not responses
3. **Credit balances** (5 minutes TTL) - User credit information

## Troubleshooting Repeated Responses

If you're seeing the same response for different messages, the issue is NOT from our backend caching. Check:

### 1. Frontend Caching
```typescript
// Check if your API client is caching responses
// Look for cache headers or response interceptors
```

### 2. Browser Cache
- Clear browser cache (Ctrl+Shift+Delete)
- Try incognito/private mode
- Check Network tab in DevTools to see actual requests

### 3. Request Inspection
Open browser DevTools → Network tab:
- Verify each request has a different `message` payload
- Check if responses are coming from cache (look for "from disk cache" or "from memory cache")
- Verify response headers don't include cache directives

### 4. Backend Logs
Check Django logs to verify:
```bash
# Look for these log messages
[AIService] Processing request {request_id} for user {user_id}
[GeminiService] Request succeeded | prompt_preview='...'
```

Each request should have a unique `request_id` and different `prompt_preview`.

### 5. Database Verification
```python
# Check AIRequestLog to see if requests are being logged correctly
from apps.credits.models import AIRequestLog

# Get recent requests for a user
logs = AIRequestLog.objects.filter(user_id=YOUR_USER_ID).order_by('-created_at')[:10]
for log in logs:
    print(f"{log.created_at}: {log.prompt_length} chars → {log.response_length} chars")
```

Each request should have different prompt_length values if messages are different.

## Performance Monitoring

### Key Metrics to Track
1. **Average Latency**: Should be < 2s for Gemini
2. **Fallback Rate**: How often Gemini fails and falls back to Cerebras/Mistral
3. **Timeout Rate**: How often requests timeout
4. **Token Usage**: Average tokens per request

### Prometheus Metrics Available
- `ai_requests_total` - Total requests by model and status
- `ai_request_tokens_total` - Total tokens consumed
- `ai_request_latency_seconds` - Request latency histogram

## Further Optimizations (Future)

### 1. Parallel Fallback Strategy
Instead of sequential fallback (try A → fail → try B), fire multiple providers simultaneously and return the first successful response.

### 2. Connection Pooling
Ensure HTTP clients reuse connections for better performance.

### 3. Async Processing
Convert synchronous AI calls to async for better concurrency.

### 4. Smart Routing
Route requests to fastest provider based on historical latency data.

### 5. Response Streaming
Stream responses token-by-token for better perceived performance.

## Configuration

### Environment Variables
```bash
# Provider API Keys
GOOGLE_API_KEY=your_gemini_key
CEREBRAS_API_KEY=your_cerebras_key
MISTRAL_API_KEY=your_mistral_key

# Timeouts (optional, defaults shown)
GEMINI_TIMEOUT=10
CEREBRAS_TIMEOUT=15
MISTRAL_TIMEOUT=15

# Retries (optional, defaults shown)
MAX_RETRIES=2
```

### Cache TTLs
Defined in `apps/credits/providers/gemini.py`:
```python
_cache_ttl: int = 3600  # 1 hour for model list cache
```

## Testing Performance

### 1. Single Request Test
```bash
curl -X POST http://localhost:8000/api/v1/twin/chat \
  -H "Authorization: Bearer YOUR_TOKEN" \
  -H "Content-Type: application/json" \
  -d '{"message": "Hello", "brain_mode": "brain"}'
```

Check the `latency_ms` in the response metadata.

### 2. Load Test
```bash
# Install Apache Bench
apt-get install apache2-utils

# Run 100 requests with 10 concurrent
ab -n 100 -c 10 -H "Authorization: Bearer YOUR_TOKEN" \
  -p request.json -T application/json \
  http://localhost:8000/api/v1/twin/chat
```

### 3. Monitor Logs
```bash
# Watch real-time logs
tail -f logs/django.log | grep -E "\[GeminiService\]|\[AIService\]"
```

## Rollback Instructions

If optimizations cause issues, revert by:

1. Increase timeouts back to 30s
2. Increase retries back to 3
3. Restore original backoff delays (1s, 2s, 4s)
4. Remove singleton client pattern

```python
# In gemini.py __init__
self.timeout = 30
self.max_retries = 3

# In retry logic
backoff_delay = 2 ** attempt  # 1s, 2s, 4s
```
