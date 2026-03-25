# Redis Setup Guide

Step-by-step guide to set up Redis for NeuroTwin.

## Overview

NeuroTwin uses Redis for:
- **Caching**: High-performance data caching
- **Session Management**: User session storage
- **Rate Limiting**: API and action rate limiting
- **Task Queue**: Django-Q2 broker for async tasks

## Production Setup (AWS ElastiCache)

### 1. AWS ElastiCache Configuration

Your ElastiCache instance is already created:
- **Name**: `neurotwinai`
- **ARN**: `arn:aws:elasticache:us-east-1:540821623893:serverlesscache:neurotwinai`
- **Endpoint**: `neurotwinai-c7zwfg-serverless.use1.cache.amazonaws.com:6379`
- **Type**: Serverless (auto-scaling)
- **Region**: us-east-1

### 2. Update Environment Variables

Update your `.env` file:

```bash
# Redis Configuration (AWS ElastiCache)
REDIS_HOST=neurotwinai-c7zwfg-serverless.use1.cache.amazonaws.com
REDIS_PORT=6379
REDIS_DB=0
REDIS_USE_SSL=True
REDIS_SOCKET_CONNECT_TIMEOUT=5
REDIS_SOCKET_TIMEOUT=5
REDIS_CONNECTION_POOL_MAX_CONNECTIONS=50
```

### 3. Install Dependencies

```bash
# Add django-redis package
uv add django-redis

# Sync all dependencies
uv sync
```

### 4. Verify Configuration

The Django settings are already configured in `neurotwin/settings.py`:
- Cache backend: `django_redis.cache.RedisCache`
- Django-Q2 broker: Redis
- SSL/TLS enabled for AWS ElastiCache

### 5. Test Connection

```bash
# Test Redis connection
uv run python manage.py redis_test

# Expected output:
# Testing Redis connection...
# ✓ Redis connection successful
# Testing cache operations...
# ✓ SET operation successful
# ✓ GET operation successful
# ✓ DELETE operation successful
# ✓ All tests passed
```

### 6. Security Group Configuration

Ensure your EC2/ECS instances can connect to ElastiCache:

1. Go to AWS Console → ElastiCache → neurotwinai
2. Click on "Security" tab
3. Verify security group allows:
   - **Type**: Custom TCP
   - **Port**: 6379
   - **Source**: Your application security group

### 7. VPC Configuration

ElastiCache must be in the same VPC as your application:
- Check VPC ID matches your application VPC
- Ensure subnets are configured correctly
- Verify route tables allow communication

## Local Development Setup

### 1. Install Redis Locally

#### macOS
```bash
brew install redis
brew services start redis
```

#### Ubuntu/Debian
```bash
sudo apt-get update
sudo apt-get install redis-server
sudo systemctl start redis
sudo systemctl enable redis
```

#### Windows (WSL)
```bash
sudo apt-get update
sudo apt-get install redis-server
sudo service redis-server start
```

### 2. Configure Local Environment

Create `.env.local` or update `.env`:

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

### 3. Test Local Redis

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
127.0.0.1:6379> exit
```

### 4. Test Django Connection

```bash
uv run python manage.py redis_test
```

## Configuration Files

### Django Settings (neurotwin/settings.py)

The Redis configuration is already set up:

```python
# Cache Configuration
CACHES = {
    'default': {
        'BACKEND': 'django_redis.cache.RedisCache',
        'LOCATION': 'rediss://neurotwinai-c7zwfg-serverless.use1.cache.amazonaws.com:6379/0',
        'OPTIONS': {
            'CLIENT_CLASS': 'django_redis.client.DefaultClient',
            'SOCKET_CONNECT_TIMEOUT': 5,
            'SOCKET_TIMEOUT': 5,
            'CONNECTION_POOL_KWARGS': {
                'max_connections': 50,
                'retry_on_timeout': True,
            },
            'COMPRESSOR': 'django_redis.compressors.zlib.ZlibCompressor',
            'SERIALIZER': 'django_redis.serializers.json.JSONSerializer',
        },
        'KEY_PREFIX': 'neurotwin',
        'TIMEOUT': 300,
    }
}

# Django-Q2 Configuration
Q_CLUSTER = {
    'name': 'neurotwin',
    'workers': 4,
    'redis': {
        'host': 'neurotwinai-c7zwfg-serverless.use1.cache.amazonaws.com',
        'port': 6379,
        'db': 1,  # Separate DB for task queue
        'password': None,
        'socket_timeout': 5,
    },
    # ... other settings
}
```

### Environment Variables (.env)

```bash
# Redis Configuration
REDIS_HOST=neurotwinai-c7zwfg-serverless.use1.cache.amazonaws.com
REDIS_PORT=6379
REDIS_DB=0
REDIS_USE_SSL=True
REDIS_SOCKET_CONNECT_TIMEOUT=5
REDIS_SOCKET_TIMEOUT=5
REDIS_CONNECTION_POOL_MAX_CONNECTIONS=50
```

## Usage Examples

### Basic Caching

```python
from django.core.cache import cache

# Set value
cache.set('user_profile_123', profile_data, timeout=300)

# Get value
profile = cache.get('user_profile_123')

# Delete value
cache.delete('user_profile_123')
```

### Using Utility Functions

```python
from apps.core.redis_utils import (
    cache_cognitive_profile,
    get_cognitive_profile,
    check_rate_limit,
)

# Cache cognitive profile
cache_cognitive_profile(user_id=123, profile_data={'blend': 50})

# Get cached profile
profile = get_cognitive_profile(user_id=123)

# Check rate limit
allowed, remaining = check_rate_limit(
    user_id=123,
    action='api_call',
    limit=100,
    window=3600
)
```

### View Caching

```python
from django.views.decorators.cache import cache_page

@cache_page(60 * 5)  # Cache for 5 minutes
def integration_types_list(request):
    return Response(data)
```

## Monitoring

### Check Cache Statistics

```bash
# Display cache statistics
uv run python manage.py redis_test --stats

# Output:
# Cache Statistics:
# ==================================================
# Connected Clients: 5
# Memory Used: 2.5M
# Total Commands: 12345
# Cache Hits: 10000
# Cache Misses: 2345
# Hit Rate: 81.0%
# Total Keys: 150
# ==================================================
```

### AWS CloudWatch Metrics

Monitor these metrics in CloudWatch:
- **CacheHitRate**: Should be >80%
- **CPUUtilization**: Should be <70%
- **NetworkBytesIn/Out**: Monitor traffic
- **CurrConnections**: Current connections
- **Evictions**: Should be low

### Set Up CloudWatch Alarms

1. Go to CloudWatch → Alarms
2. Create alarms for:
   - CacheHitRate < 80%
   - CPUUtilization > 80%
   - CurrConnections > 1000

## Troubleshooting

### Connection Timeout

**Symptom**: `ConnectionError: Error connecting to Redis`

**Solutions**:
1. Check security group allows port 6379
2. Verify VPC configuration
3. Check REDIS_HOST is correct
4. Verify SSL/TLS settings

```bash
# Test connection
uv run python manage.py redis_test
```

### Authentication Failed

**Symptom**: `AuthenticationError: Authentication required`

**Solutions**:
1. Set REDIS_PASSWORD if using AUTH token
2. Check IAM permissions for ElastiCache
3. Verify AUTH token is correct

### High Memory Usage

**Symptom**: Memory usage >80%

**Solutions**:
1. Review TTL values (too long?)
2. Check for memory leaks
3. Consider increasing cache size
4. Set maxmemory-policy to `allkeys-lru`

### Low Hit Rate

**Symptom**: Cache hit rate <60%

**Solutions**:
1. Review TTL values (too short?)
2. Check cache invalidation logic
3. Verify cache keys are consistent
4. Monitor eviction rate

## Performance Optimization

### 1. Use Appropriate TTLs

```python
from apps.core.redis_utils import CacheTTL

# Frequently changing data
cache.set('key', value, timeout=CacheTTL.MINUTE_1)

# Rarely changing data
cache.set('key', value, timeout=CacheTTL.HOUR_1)

# Static data
cache.set('key', value, timeout=CacheTTL.DAY_1)
```

### 2. Batch Operations

```python
# Good - single round trip
cache.set_many({'key1': 'val1', 'key2': 'val2'})

# Bad - multiple round trips
cache.set('key1', 'val1')
cache.set('key2', 'val2')
```

### 3. Connection Pooling

Already configured in settings:
```python
'CONNECTION_POOL_KWARGS': {
    'max_connections': 50,
    'retry_on_timeout': True,
}
```

### 4. Compression

Automatic compression for large values:
```python
'COMPRESSOR': 'django_redis.compressors.zlib.ZlibCompressor'
```

## Maintenance

### Clear Cache

```bash
# Clear all cache (use with caution)
uv run python manage.py redis_test --clear
```

### Backup (AWS ElastiCache)

ElastiCache Serverless automatically handles backups:
- Daily automatic backups
- Point-in-time recovery
- Configurable retention period

### Monitoring Script

Create a monitoring script:

```python
# scripts/monitor_redis.py
from apps.core.redis_utils import get_cache_stats

stats = get_cache_stats()
hit_rate = stats.get('hit_rate', 0)

if hit_rate < 80:
    print(f"⚠️  Low cache hit rate: {hit_rate}%")
else:
    print(f"✓ Cache hit rate: {hit_rate}%")
```

## Next Steps

1. ✅ Redis configured and connected
2. ✅ Utility functions created
3. ✅ Management commands available
4. ✅ Documentation complete

**Recommended Actions**:
- [ ] Set up CloudWatch alarms
- [ ] Configure backup retention
- [ ] Review and optimize TTL values
- [ ] Monitor cache hit rate
- [ ] Implement cache warming for critical data

## Additional Resources

- [Redis Guide](./redis-guide.md) - Comprehensive guide
- [Quick Reference](./redis-quick-reference.md) - Common operations
- [AWS ElastiCache Docs](https://docs.aws.amazon.com/elasticache/)
- [django-redis Docs](https://github.com/jazzband/django-redis)
