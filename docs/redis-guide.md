# Redis Integration Guide

## Overview

NeuroTwin uses Redis for high-performance caching and asynchronous task queuing. The production environment uses **AWS ElastiCache Serverless** for automatic scaling and managed infrastructure.

## AWS ElastiCache Configuration

### Resource Details
- **Service**: AWS ElastiCache Serverless
- **Cache Name**: `neurotwinai`
- **ARN**: `arn:aws:elasticache:us-east-1:540821623893:serverlesscache:neurotwinai`
- **Region**: `us-east-1` (US East - N. Virginia)
- **Endpoint**: `neurotwinai-c7zwfg-serverless.use1.cache.amazonaws.com:6379`
- **Engine**: Redis 7.x
- **Connection**: TLS/SSL enabled

### Key Features
- **Serverless**: Automatically scales based on workload
- **High Availability**: Multi-AZ deployment with automatic failover
- **Security**: VPC isolation, encryption in transit and at rest
- **Monitoring**: CloudWatch metrics and alarms

## Environment Configuration

### Production (.env)
```bash
# Redis Configuration (AWS ElastiCache)
REDIS_HOST=neurotwinai-c7zwfg-serverless.use1.cache.amazonaws.com
REDIS_PORT=6379
REDIS_DB=0
REDIS_USE_SSL=True
REDIS_SOCKET_CONNECT_TIMEOUT=5
REDIS_SOCKET_TIMEOUT=5
REDIS_CONNECTION_POOL_MAX_CONNECTIONS=50
# REDIS_PASSWORD=  # Set if using AUTH token
```

### Development (Local Redis)
```bash
# Redis Configuration (Local)
REDIS_HOST=localhost
REDIS_PORT=6379
REDIS_DB=0
REDIS_USE_SSL=False
REDIS_SOCKET_CONNECT_TIMEOUT=5
REDIS_SOCKET_TIMEOUT=5
REDIS_CONNECTION_POOL_MAX_CONNECTIONS=50
```

### Testing
Tests automatically use in-memory cache (no Redis required):
```python
# Configured in settings.py
CACHES = {
    'default': {
        'BACKEND': 'django.core.cache.backends.locmem.LocMemCache',
        'LOCATION': 'neurotwin-test-cache',
    }
}
```

## Usage Patterns

### 1. Django Cache Framework

#### Basic Caching
```python
from django.core.cache import cache

# Set cache value (5 minutes default)
cache.set('user_profile_123', profile_data, timeout=300)

# Get cache value
profile = cache.get('user_profile_123')

# Get with default
profile = cache.get('user_profile_123', default={})

# Delete cache value
cache.delete('user_profile_123')

# Check if key exists
if cache.has_key('user_profile_123'):
    profile = cache.get('user_profile_123')
```

#### Batch Operations
```python
# Set multiple values
cache.set_many({
    'user_123': user_data,
    'profile_123': profile_data,
    'settings_123': settings_data,
}, timeout=300)

# Get multiple values
data = cache.get_many(['user_123', 'profile_123', 'settings_123'])

# Delete multiple values
cache.delete_many(['user_123', 'profile_123', 'settings_123'])
```

#### Atomic Operations
```python
# Increment counter
cache.incr('api_calls_user_123')
cache.incr('api_calls_user_123', delta=5)

# Decrement counter
cache.decr('api_calls_user_123')

# Get or set (atomic)
profile = cache.get_or_set('user_profile_123', 
                           lambda: fetch_profile_from_db(123),
                           timeout=300)
```

### 2. View-Level Caching

#### Cache Entire View
```python
from django.views.decorators.cache import cache_page

@cache_page(60 * 5)  # Cache for 5 minutes
def integration_types_list(request):
    # View logic
    return Response(data)
```

#### Cache with Vary Headers
```python
from django.views.decorators.cache import cache_page
from django.views.decorators.vary import vary_on_headers

@cache_page(60 * 5)
@vary_on_headers('Authorization')  # Different cache per user
def user_workflows(request):
    # View logic
    return Response(data)
```

### 3. Template Fragment Caching

```django
{% load cache %}

{% cache 300 sidebar user.id %}
    <!-- Sidebar content -->
{% endcache %}
```

### 4. Low-Level Cache API (django-redis)

```python
from django_redis import get_redis_connection

# Get raw Redis connection
redis_conn = get_redis_connection('default')

# Use Redis commands directly
redis_conn.set('key', 'value', ex=300)
redis_conn.get('key')
redis_conn.delete('key')

# Redis data structures
redis_conn.lpush('queue', 'item')
redis_conn.rpop('queue')
redis_conn.sadd('set', 'member')
redis_conn.smembers('set')
```

## Cache Strategies by Use Case

### 1. Cognitive Signature Model (CSM) Caching
**Pattern**: Cache-aside with TTL
**TTL**: 5 minutes (300 seconds)

```python
from django.core.cache import cache
from apps.csm.models import CognitiveProfile

def get_cognitive_profile(user_id: int) -> dict:
    """
    Get cognitive profile with caching.
    Requirements: 17.1 - Cache frequently accessed cognitive profiles
    """
    cache_key = f'csm:profile:{user_id}'
    
    # Try cache first
    profile = cache.get(cache_key)
    if profile is not None:
        return profile
    
    # Cache miss - fetch from database
    profile = CognitiveProfile.objects.get(user_id=user_id)
    profile_data = {
        'cognitive_blend': profile.cognitive_blend,
        'personality_traits': profile.personality_traits,
        'communication_style': profile.communication_style,
    }
    
    # Store in cache
    cache.set(cache_key, profile_data, timeout=300)
    return profile_data
```

### 2. Integration Types Caching
**Pattern**: Cache-aside with longer TTL
**TTL**: 5 minutes (300 seconds)

```python
from django.core.cache import cache
from apps.automation.models import IntegrationType

def get_integration_types(category: str = None) -> list:
    """
    Get integration types with caching.
    Requirements: 18.3 - Cache integration type listings
    """
    cache_key = f'integration_types:{category or "all"}'
    
    # Try cache first
    types = cache.get(cache_key)
    if types is not None:
        return types
    
    # Cache miss - fetch from database
    queryset = IntegrationType.objects.filter(is_active=True)
    if category:
        queryset = queryset.filter(category=category)
    
    types = list(queryset.values())
    
    # Store in cache
    cache.set(cache_key, types, timeout=300)
    return types
```

### 3. User Session Caching
**Pattern**: Write-through cache
**TTL**: 1 hour (3600 seconds)

```python
from django.core.cache import cache

def cache_user_session(user_id: int, session_data: dict):
    """
    Cache user session data.
    Requirements: 17.2 - Session management
    """
    cache_key = f'session:{user_id}'
    cache.set(cache_key, session_data, timeout=3600)

def get_user_session(user_id: int) -> dict:
    """Get cached user session."""
    cache_key = f'session:{user_id}'
    return cache.get(cache_key, default={})

def invalidate_user_session(user_id: int):
    """Invalidate user session cache."""
    cache_key = f'session:{user_id}'
    cache.delete(cache_key)
```

### 4. Rate Limiting
**Pattern**: Counter with expiry
**TTL**: Based on rate limit window

```python
from django.core.cache import cache
from django.utils import timezone

def check_rate_limit(user_id: int, action: str, limit: int, window: int) -> bool:
    """
    Check if user has exceeded rate limit.
    Requirements: 18.7 - Rate limiting
    
    Args:
        user_id: User identifier
        action: Action being rate limited (e.g., 'installation', 'api_call')
        limit: Maximum number of actions allowed
        window: Time window in seconds
    
    Returns:
        True if within limit, False if exceeded
    """
    cache_key = f'rate_limit:{action}:{user_id}'
    
    # Get current count
    count = cache.get(cache_key, 0)
    
    if count >= limit:
        return False
    
    # Increment counter
    if count == 0:
        # First request - set with expiry
        cache.set(cache_key, 1, timeout=window)
    else:
        # Subsequent request - increment
        cache.incr(cache_key)
    
    return True
```

### 5. OAuth State Caching
**Pattern**: Temporary storage with short TTL
**TTL**: 10 minutes (600 seconds)

```python
from django.core.cache import cache
import secrets

def create_oauth_state(user_id: int, integration_type_id: str) -> str:
    """
    Create and cache OAuth state token.
    Requirements: 18.4 - OAuth flow state management
    """
    state = secrets.token_urlsafe(32)
    cache_key = f'oauth_state:{state}'
    
    cache.set(cache_key, {
        'user_id': user_id,
        'integration_type_id': integration_type_id,
        'created_at': timezone.now().isoformat(),
    }, timeout=600)
    
    return state

def validate_oauth_state(state: str) -> dict:
    """Validate and consume OAuth state token."""
    cache_key = f'oauth_state:{state}'
    data = cache.get(cache_key)
    
    if data:
        # Delete after use (one-time token)
        cache.delete(cache_key)
    
    return data
```

## Cache Invalidation Strategies

### 1. Time-Based Invalidation (TTL)
Most common pattern - cache expires after set time:
```python
cache.set('key', value, timeout=300)  # 5 minutes
```

### 2. Event-Based Invalidation
Invalidate cache when data changes:
```python
from django.db.models.signals import post_save
from django.dispatch import receiver

@receiver(post_save, sender=CognitiveProfile)
def invalidate_profile_cache(sender, instance, **kwargs):
    """Invalidate cache when profile is updated."""
    cache_key = f'csm:profile:{instance.user_id}'
    cache.delete(cache_key)
```

### 3. Pattern-Based Invalidation
Delete multiple related keys:
```python
from django_redis import get_redis_connection

def invalidate_user_caches(user_id: int):
    """Invalidate all caches for a user."""
    redis_conn = get_redis_connection('default')
    
    # Find all keys matching pattern
    pattern = f'neurotwin:*:{user_id}:*'
    keys = redis_conn.keys(pattern)
    
    if keys:
        redis_conn.delete(*keys)
```

### 4. Cache Versioning
Use version numbers in cache keys:
```python
CACHE_VERSION = 1

def get_cache_key(base_key: str) -> str:
    """Generate versioned cache key."""
    return f'{base_key}:v{CACHE_VERSION}'

# Usage
cache.set(get_cache_key('user_profile_123'), data)
```

## Asynchronous Task Queue (Django-Q2)

Redis is also used as the broker for Django-Q2 task queue.

### Queue Tasks
```python
from django_q.tasks import async_task, schedule

# Queue a task
async_task('apps.memory.tasks.process_memory_write', 
           user_id=123, 
           memory_data=data)

# Schedule recurring task
schedule('apps.memory.tasks.cleanup_old_memories',
         schedule_type='D',  # Daily
         repeats=-1)  # Infinite
```

### Task Functions
```python
# apps/memory/tasks.py
def process_memory_write(user_id: int, memory_data: dict):
    """
    Process memory write asynchronously.
    Requirements: 14.5 - Memory writes must be async
    """
    # Process memory
    # Generate embeddings
    # Store in vector DB
    pass
```

## Monitoring and Debugging

### Check Cache Status
```python
from django.core.cache import cache

# Get cache statistics
stats = cache.get_stats()
print(stats)

# Test connection
try:
    cache.set('test_key', 'test_value', timeout=10)
    value = cache.get('test_key')
    assert value == 'test_value'
    print("✓ Redis connection working")
except Exception as e:
    print(f"✗ Redis connection failed: {e}")
```

### Django Management Commands
```bash
# Clear all cache
python manage.py clear_cache

# Inspect cache keys (django-redis)
python manage.py redis_cli keys "neurotwin:*"

# Get cache value
python manage.py redis_cli get "neurotwin:user_profile_123"
```

### CloudWatch Metrics (AWS ElastiCache)
Monitor these metrics in AWS CloudWatch:
- **CacheHits**: Number of successful cache lookups
- **CacheMisses**: Number of failed cache lookups
- **CacheHitRate**: Percentage of successful lookups
- **CPUUtilization**: CPU usage percentage
- **NetworkBytesIn/Out**: Network traffic
- **CurrConnections**: Current client connections
- **Evictions**: Number of evicted keys

## Performance Best Practices

### 1. Use Appropriate TTLs
```python
# Frequently changing data - short TTL
cache.set('user_online_status', status, timeout=60)  # 1 minute

# Rarely changing data - longer TTL
cache.set('integration_types', types, timeout=3600)  # 1 hour

# Static data - very long TTL
cache.set('app_config', config, timeout=86400)  # 24 hours
```

### 2. Batch Operations
```python
# Bad - Multiple round trips
for user_id in user_ids:
    cache.set(f'user_{user_id}', data[user_id])

# Good - Single round trip
cache.set_many({
    f'user_{user_id}': data[user_id]
    for user_id in user_ids
})
```

### 3. Compression for Large Values
```python
# Automatic compression configured in settings.py
# 'COMPRESSOR': 'django_redis.compressors.zlib.ZlibCompressor'

# Large objects are automatically compressed
cache.set('large_dataset', large_data)  # Compressed automatically
```

### 4. Connection Pooling
```python
# Configured in settings.py
'CONNECTION_POOL_KWARGS': {
    'max_connections': 50,
    'retry_on_timeout': True,
}
```

### 5. Avoid Cache Stampede
```python
import random

def get_with_jitter(key: str, fetch_func, base_timeout: int):
    """Get cache value with jitter to avoid stampede."""
    value = cache.get(key)
    if value is not None:
        return value
    
    # Add random jitter (±10%)
    jitter = random.uniform(0.9, 1.1)
    timeout = int(base_timeout * jitter)
    
    value = fetch_func()
    cache.set(key, value, timeout=timeout)
    return value
```

## Security Considerations

### 1. TLS/SSL Encryption
```python
# Configured in settings.py for AWS ElastiCache
REDIS_USE_SSL=True
# Connection URL: rediss:// (note the 's')
```

### 2. VPC Isolation
AWS ElastiCache is deployed in a VPC with:
- Private subnets only
- Security groups restricting access
- No public internet access

### 3. Authentication
```bash
# If using AUTH token
REDIS_PASSWORD=your-secure-password
```

### 4. Key Namespacing
```python
# All keys prefixed with 'neurotwin:'
'KEY_PREFIX': 'neurotwin',

# Prevents key collisions with other applications
```

### 5. Sensitive Data
```python
# Never cache sensitive data without encryption
from cryptography.fernet import Fernet

def cache_sensitive_data(key: str, data: dict, cipher: Fernet):
    """Cache sensitive data with encryption."""
    encrypted = cipher.encrypt(json.dumps(data).encode())
    cache.set(key, encrypted, timeout=300)

def get_sensitive_data(key: str, cipher: Fernet) -> dict:
    """Get and decrypt sensitive data."""
    encrypted = cache.get(key)
    if encrypted:
        decrypted = cipher.decrypt(encrypted)
        return json.loads(decrypted)
    return None
```

## Troubleshooting

### Connection Issues
```python
# Test Redis connection
from django_redis import get_redis_connection

try:
    redis_conn = get_redis_connection('default')
    redis_conn.ping()
    print("✓ Redis connection successful")
except Exception as e:
    print(f"✗ Redis connection failed: {e}")
    # Check:
    # 1. REDIS_HOST is correct
    # 2. Security group allows port 6379
    # 3. VPC/subnet configuration
    # 4. SSL/TLS settings
```

### Cache Not Working
```python
# Check cache backend
from django.core.cache import cache
print(cache.__class__)  # Should be RedisCache

# Check cache operations
cache.set('test', 'value', timeout=60)
print(cache.get('test'))  # Should print 'value'
```

### High Memory Usage
```bash
# Check memory usage in Redis
redis-cli INFO memory

# Find large keys
redis-cli --bigkeys

# Set maxmemory policy in ElastiCache parameter group
# Recommended: allkeys-lru (evict least recently used)
```

### Slow Performance
- Check CloudWatch metrics for CPU/memory
- Review cache hit rate (should be >80%)
- Consider increasing cache size
- Review TTL values (too short = more DB queries)
- Check network latency to ElastiCache

## Local Development Setup

### Install Redis Locally
```bash
# macOS
brew install redis
brew services start redis

# Ubuntu/Debian
sudo apt-get install redis-server
sudo systemctl start redis

# Windows (WSL)
sudo apt-get install redis-server
sudo service redis-server start
```

### Configure for Local Development
```bash
# .env.local
REDIS_HOST=localhost
REDIS_PORT=6379
REDIS_DB=0
REDIS_USE_SSL=False
```

### Test Local Redis
```bash
# Connect to Redis CLI
redis-cli

# Test commands
127.0.0.1:6379> PING
PONG
127.0.0.1:6379> SET test "Hello"
OK
127.0.0.1:6379> GET test
"Hello"
```

## Migration from Local to AWS ElastiCache

### Pre-Migration Checklist
- [ ] Create ElastiCache instance in correct VPC
- [ ] Configure security groups
- [ ] Update environment variables
- [ ] Test connection from application server
- [ ] Set up CloudWatch alarms
- [ ] Configure backup schedule

### Migration Steps
1. Update `.env` with ElastiCache endpoint
2. Enable SSL/TLS (`REDIS_USE_SSL=True`)
3. Deploy application with new configuration
4. Monitor CloudWatch metrics
5. Verify cache operations working
6. Remove local Redis dependency

### Rollback Plan
Keep local Redis configuration in `.env.backup`:
```bash
# Rollback command
cp .env.backup .env
# Restart application
```

## Additional Resources

- [Django Cache Framework](https://docs.djangoproject.com/en/6.0/topics/cache/)
- [django-redis Documentation](https://github.com/jazzband/django-redis)
- [AWS ElastiCache Best Practices](https://docs.aws.amazon.com/AmazonElastiCache/latest/red-ug/BestPractices.html)
- [Redis Commands Reference](https://redis.io/commands/)
- [Django-Q2 Documentation](https://django-q2.readthedocs.io/)
