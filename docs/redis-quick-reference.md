# Redis Quick Reference

Quick reference for common Redis operations in NeuroTwin.

## Connection Details

### Production (AWS ElastiCache)
```bash
Host: neurotwinai-c7zwfg-serverless.use1.cache.amazonaws.com
Port: 6379
SSL: Enabled
ARN: arn:aws:elasticache:us-east-1:540821623893:serverlesscache:neurotwinai
```

### Local Development
```bash
Host: localhost
Port: 6379
SSL: Disabled
```

## Quick Start

### Test Connection
```bash
# Test Redis connection
python manage.py redis_test

# Show cache statistics
python manage.py redis_test --stats

# Clear all cache (use with caution)
python manage.py redis_test --clear
```

### Install Dependencies
```bash
# Install django-redis
uv add django-redis

# Sync dependencies
uv sync
```

## Common Operations

### Basic Caching
```python
from django.core.cache import cache

# Set value (5 minutes)
cache.set('key', 'value', timeout=300)

# Get value
value = cache.get('key')

# Get with default
value = cache.get('key', default='default_value')

# Delete value
cache.delete('key')

# Check if exists
exists = cache.has_key('key')
```

### Batch Operations
```python
# Set multiple
cache.set_many({'key1': 'val1', 'key2': 'val2'}, timeout=300)

# Get multiple
values = cache.get_many(['key1', 'key2'])

# Delete multiple
cache.delete_many(['key1', 'key2'])
```

### Atomic Operations
```python
# Increment
cache.incr('counter')
cache.incr('counter', delta=5)

# Decrement
cache.decr('counter')

# Get or set
value = cache.get_or_set('key', lambda: expensive_operation(), timeout=300)
```

### Using Utility Functions
```python
from apps.core.redis_utils import (
    get_cached,
    cache_cognitive_profile,
    get_cognitive_profile,
    check_rate_limit,
    cache_oauth_state,
    get_oauth_state,
)

# Cache with fetch function
data = get_cached('my_key', fetch_func=lambda: get_data(), timeout=300)

# Cache cognitive profile
cache_cognitive_profile(user_id=123, profile_data={'blend': 50})
profile = get_cognitive_profile(user_id=123)

# Rate limiting
allowed, remaining = check_rate_limit(
    user_id=123,
    action='api_call',
    limit=100,
    window=3600
)

# OAuth state
cache_oauth_state('state_token', {'user_id': 123}, timeout=600)
data = get_oauth_state('state_token', consume=True)
```

## Cache Keys

### Predefined Keys (from CacheKeys class)
```python
from apps.core.redis_utils import CacheKeys

# Cognitive Signature Model
CacheKeys.CSM_PROFILE.format(user_id=123)
# → 'csm:profile:123'

# User Session
CacheKeys.USER_SESSION.format(user_id=123)
# → 'session:123'

# Integration Types
CacheKeys.INTEGRATION_TYPES.format(category='communication')
# → 'integration_types:communication'

# OAuth State
CacheKeys.OAUTH_STATE.format(state='abc123')
# → 'oauth_state:abc123'

# Rate Limiting
CacheKeys.RATE_LIMIT.format(action='api_call', user_id=123)
# → 'rate_limit:api_call:123'
```

## TTL Values

### Predefined TTLs (from CacheTTL class)
```python
from apps.core.redis_utils import CacheTTL

CacheTTL.MINUTE_1   # 60 seconds
CacheTTL.MINUTE_5   # 300 seconds
CacheTTL.MINUTE_10  # 600 seconds
CacheTTL.MINUTE_30  # 1800 seconds
CacheTTL.HOUR_1     # 3600 seconds
CacheTTL.HOUR_6     # 21600 seconds
CacheTTL.HOUR_12    # 43200 seconds
CacheTTL.DAY_1      # 86400 seconds
CacheTTL.WEEK_1     # 604800 seconds
```

## View Caching

### Cache Entire View
```python
from django.views.decorators.cache import cache_page

@cache_page(60 * 5)  # 5 minutes
def my_view(request):
    return Response(data)
```

### Cache with User Context
```python
from django.views.decorators.cache import cache_page
from django.views.decorators.vary import vary_on_headers

@cache_page(60 * 5)
@vary_on_headers('Authorization')
def user_specific_view(request):
    return Response(data)
```

## Invalidation

### Single Key
```python
cache.delete('key')
```

### Pattern-Based
```python
from apps.core.redis_utils import invalidate_pattern

# Delete all keys matching pattern
invalidate_pattern('user:123:*')
```

### Specific Invalidations
```python
from apps.core.redis_utils import (
    invalidate_cognitive_profile,
    invalidate_user_session,
    invalidate_user_installations,
)

invalidate_cognitive_profile(user_id=123)
invalidate_user_session(user_id=123)
invalidate_user_installations(user_id=123)
```

## Rate Limiting

### Check Rate Limit
```python
from apps.core.redis_utils import check_rate_limit, reset_rate_limit

# Check if allowed
allowed, remaining = check_rate_limit(
    user_id=123,
    action='installation',
    limit=10,
    window=3600  # 1 hour
)

if not allowed:
    return Response({'error': 'Rate limit exceeded'}, status=429)

# Reset rate limit (admin action)
reset_rate_limit(user_id=123, action='installation')
```

### DRF Throttling
```python
from rest_framework.throttling import UserRateThrottle

class InstallationThrottle(UserRateThrottle):
    rate = '10/hour'

class MyView(APIView):
    throttle_classes = [InstallationThrottle]
```

## Monitoring

### Get Statistics
```python
from apps.core.redis_utils import get_cache_stats, get_cache_size

# Get detailed stats
stats = get_cache_stats()
print(f"Hit Rate: {stats['hit_rate']}%")

# Get number of keys
size = get_cache_size()
print(f"Total Keys: {size}")
```

### Test Connection
```python
from apps.core.redis_utils import test_redis_connection

if test_redis_connection():
    print("✓ Redis is working")
else:
    print("✗ Redis connection failed")
```

## Debugging

### Check Cache Backend
```python
from django.core.cache import cache
print(cache.__class__)
# Should print: <class 'django_redis.cache.RedisCache'>
```

### Direct Redis Commands
```python
from django_redis import get_redis_connection

redis_conn = get_redis_connection('default')

# Ping
redis_conn.ping()

# Get all keys
keys = redis_conn.keys('neurotwin:*')

# Get value
value = redis_conn.get('neurotwin:key')

# Set value
redis_conn.set('neurotwin:key', 'value', ex=300)
```

### Clear All Cache
```python
from apps.core.redis_utils import clear_all_cache

# WARNING: Clears ALL cached data
clear_all_cache()
```

## Environment Variables

### Required Variables
```bash
# .env
REDIS_HOST=neurotwinai-c7zwfg-serverless.use1.cache.amazonaws.com
REDIS_PORT=6379
REDIS_DB=0
REDIS_USE_SSL=True
```

### Optional Variables
```bash
REDIS_PASSWORD=          # If using AUTH token
REDIS_SOCKET_CONNECT_TIMEOUT=5
REDIS_SOCKET_TIMEOUT=5
REDIS_CONNECTION_POOL_MAX_CONNECTIONS=50
```

## Common Patterns

### Cache-Aside Pattern
```python
def get_user_data(user_id):
    # Try cache first
    data = cache.get(f'user:{user_id}')
    if data:
        return data
    
    # Cache miss - fetch from DB
    data = User.objects.get(id=user_id)
    
    # Store in cache
    cache.set(f'user:{user_id}', data, timeout=300)
    return data
```

### Write-Through Pattern
```python
def update_user_data(user_id, data):
    # Update database
    user = User.objects.get(id=user_id)
    user.update(data)
    user.save()
    
    # Update cache
    cache.set(f'user:{user_id}', user, timeout=300)
```

### Cache with Jitter
```python
import random

def get_with_jitter(key, fetch_func, base_timeout):
    value = cache.get(key)
    if value:
        return value
    
    # Add ±10% jitter to prevent stampede
    jitter = random.uniform(0.9, 1.1)
    timeout = int(base_timeout * jitter)
    
    value = fetch_func()
    cache.set(key, value, timeout=timeout)
    return value
```

## Troubleshooting

### Connection Failed
```bash
# Check environment variables
echo $REDIS_HOST
echo $REDIS_PORT

# Test connection
python manage.py redis_test

# Check security group (AWS)
# - Port 6379 must be open
# - Source: Application security group
```

### Cache Not Working
```python
# Verify cache backend
from django.conf import settings
print(settings.CACHES)

# Test basic operations
cache.set('test', 'value')
print(cache.get('test'))  # Should print 'value'
```

### High Memory Usage
```bash
# Check memory in CloudWatch
# - CacheHitRate should be >80%
# - Evictions should be low

# Review TTL values
# - Too long = high memory
# - Too short = more DB queries
```

## Best Practices

1. **Use appropriate TTLs**
   - Frequently changing: 1-5 minutes
   - Rarely changing: 1 hour
   - Static data: 24 hours

2. **Batch operations when possible**
   ```python
   # Good
   cache.set_many(data_dict)
   
   # Bad
   for key, value in data_dict.items():
       cache.set(key, value)
   ```

3. **Use predefined keys and TTLs**
   ```python
   from apps.core.redis_utils import CacheKeys, CacheTTL
   
   cache.set(
       CacheKeys.CSM_PROFILE.format(user_id=123),
       data,
       timeout=CacheTTL.MINUTE_5
   )
   ```

4. **Invalidate on updates**
   ```python
   @receiver(post_save, sender=CognitiveProfile)
   def invalidate_cache(sender, instance, **kwargs):
       invalidate_cognitive_profile(instance.user_id)
   ```

5. **Monitor hit rate**
   - Target: >80% hit rate
   - Low hit rate = review TTLs or cache strategy

## Additional Resources

- [Full Redis Guide](./redis-guide.md)
- [Django Cache Framework](https://docs.djangoproject.com/en/6.0/topics/cache/)
- [django-redis Documentation](https://github.com/jazzband/django-redis)
- [AWS ElastiCache Best Practices](https://docs.aws.amazon.com/AmazonElastiCache/latest/red-ug/BestPractices.html)
