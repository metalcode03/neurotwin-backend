# Redis Integration Summary

## Overview

Redis has been successfully integrated into the NeuroTwin backend using AWS ElastiCache Serverless.

## What Was Done

### 1. Dependencies Added
- ✅ `django-redis>=5.4.0` added to `pyproject.toml`
- ✅ `redis>=7.3.0` already present

### 2. Configuration Updated

#### Environment Variables (.env)
```bash
REDIS_HOST=neurotwinai-c7zwfg-serverless.use1.cache.amazonaws.com
REDIS_PORT=6379
REDIS_DB=0
REDIS_USE_SSL=True
REDIS_SOCKET_CONNECT_TIMEOUT=5
REDIS_SOCKET_TIMEOUT=5
REDIS_CONNECTION_POOL_MAX_CONNECTIONS=50
```

#### Django Settings (neurotwin/settings.py)
- ✅ Cache backend configured with `django_redis.cache.RedisCache`
- ✅ SSL/TLS enabled for AWS ElastiCache
- ✅ Connection pooling configured (max 50 connections)
- ✅ Compression enabled (zlib)
- ✅ JSON serialization configured
- ✅ Django-Q2 configured to use Redis as broker

### 3. Utility Module Created

**File**: `apps/core/redis_utils.py`

Provides centralized Redis operations:
- Cache key definitions (`CacheKeys` class)
- TTL constants (`CacheTTL` class)
- Helper functions for common operations
- Rate limiting utilities
- Cache invalidation functions
- Monitoring and statistics

### 4. Management Command Created

**File**: `apps/core/management/commands/redis_test.py`

```bash
# Test connection
python manage.py redis_test

# Show statistics
python manage.py redis_test --stats

# Clear cache
python manage.py redis_test --clear
```

### 5. Documentation Created

| Document | Purpose |
|----------|---------|
| `docs/redis-guide.md` | Comprehensive guide (usage patterns, best practices) |
| `docs/redis-quick-reference.md` | Quick reference for common operations |
| `docs/redis-setup.md` | Step-by-step setup instructions |
| `docs/REDIS_INTEGRATION.md` | This summary document |

## AWS ElastiCache Details

### Resource Information
- **Service**: AWS ElastiCache Serverless
- **Name**: `neurotwinai`
- **ARN**: `arn:aws:elasticache:us-east-1:540821623893:serverlesscache:neurotwinai`
- **Region**: us-east-1 (US East - N. Virginia)
- **Endpoint**: `neurotwinai-c7zwfg-serverless.use1.cache.amazonaws.com:6379`
- **Engine**: Redis 7.x
- **Type**: Serverless (auto-scaling)
- **Security**: TLS/SSL enabled, VPC isolated

### Key Features
- ✅ Automatic scaling based on workload
- ✅ Multi-AZ deployment with automatic failover
- ✅ Encryption in transit (TLS/SSL)
- ✅ Encryption at rest
- ✅ Automatic backups
- ✅ CloudWatch monitoring

## Usage Examples

### Basic Caching
```python
from django.core.cache import cache

# Set value (5 minutes)
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
    cache_oauth_state,
    get_oauth_state,
)

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

# OAuth state management
cache_oauth_state('state_token', {'user_id': 123}, timeout=600)
data = get_oauth_state('state_token', consume=True)
```

### View Caching
```python
from django.views.decorators.cache import cache_page

@cache_page(60 * 5)  # Cache for 5 minutes
def integration_types_list(request):
    return Response(data)
```

## Quick Start

### 1. Install Dependencies
```bash
uv sync
```

### 2. Test Connection
```bash
uv run python manage.py redis_test
```

Expected output:
```
Testing Redis connection...
✓ Redis connection successful

Testing cache operations...
✓ SET operation successful
✓ GET operation successful
✓ DELETE operation successful

✓ All tests passed
```

### 3. Check Statistics
```bash
uv run python manage.py redis_test --stats
```

### 4. Start Using Redis
```python
from django.core.cache import cache

# Your code here
cache.set('key', 'value', timeout=300)
```

## Cache Strategy by Use Case

| Use Case | Pattern | TTL | Key Format |
|----------|---------|-----|------------|
| Cognitive Profile | Cache-aside | 5 min | `csm:profile:{user_id}` |
| User Session | Write-through | 1 hour | `session:{user_id}` |
| Integration Types | Cache-aside | 5 min | `integration_types:{category}` |
| OAuth State | Temporary | 10 min | `oauth_state:{state}` |
| Rate Limiting | Counter | Variable | `rate_limit:{action}:{user_id}` |
| User Installations | Cache-aside | 1 min | `installations:{user_id}` |

## Monitoring

### Check Cache Health
```bash
# Test connection
uv run python manage.py redis_test

# View statistics
uv run python manage.py redis_test --stats
```

### CloudWatch Metrics
Monitor in AWS Console:
- **CacheHitRate**: Target >80%
- **CPUUtilization**: Keep <70%
- **NetworkBytesIn/Out**: Monitor traffic
- **CurrConnections**: Current connections
- **Evictions**: Should be low

### Set Up Alarms
Recommended CloudWatch alarms:
- CacheHitRate < 80%
- CPUUtilization > 80%
- CurrConnections > 1000

## Security

### Network Security
- ✅ VPC isolated (no public internet access)
- ✅ Security groups restrict access to application servers only
- ✅ TLS/SSL encryption in transit

### Data Security
- ✅ Encryption at rest enabled
- ✅ Key prefix (`neurotwin:`) prevents collisions
- ✅ Sensitive data should be encrypted before caching

### Access Control
- ✅ IAM-based access control
- ✅ Optional AUTH token support
- ✅ Connection pooling with limits

## Performance Best Practices

1. **Use Appropriate TTLs**
   - Frequently changing: 1-5 minutes
   - Rarely changing: 1 hour
   - Static data: 24 hours

2. **Batch Operations**
   ```python
   # Good
   cache.set_many({'key1': 'val1', 'key2': 'val2'})
   
   # Bad
   for key, value in items:
       cache.set(key, value)
   ```

3. **Use Predefined Keys**
   ```python
   from apps.core.redis_utils import CacheKeys, CacheTTL
   
   cache.set(
       CacheKeys.CSM_PROFILE.format(user_id=123),
       data,
       timeout=CacheTTL.MINUTE_5
   )
   ```

4. **Invalidate on Updates**
   ```python
   from apps.core.redis_utils import invalidate_cognitive_profile
   
   @receiver(post_save, sender=CognitiveProfile)
   def invalidate_cache(sender, instance, **kwargs):
       invalidate_cognitive_profile(instance.user_id)
   ```

5. **Monitor Hit Rate**
   - Target: >80% hit rate
   - Low hit rate = review TTLs or strategy

## Troubleshooting

### Connection Issues
```bash
# Test connection
uv run python manage.py redis_test

# Check environment variables
echo $REDIS_HOST
echo $REDIS_PORT

# Verify security group allows port 6379
# Check VPC/subnet configuration
```

### Cache Not Working
```python
# Verify cache backend
from django.conf import settings
print(settings.CACHES)

# Test operations
cache.set('test', 'value')
print(cache.get('test'))
```

### High Memory Usage
- Review TTL values (too long?)
- Check for memory leaks
- Consider increasing cache size
- Set maxmemory-policy to `allkeys-lru`

### Low Hit Rate
- Review TTL values (too short?)
- Check cache invalidation logic
- Verify cache keys are consistent
- Monitor eviction rate

## Next Steps

### Immediate Actions
- [x] Redis configured and connected
- [x] Utility functions created
- [x] Management commands available
- [x] Documentation complete

### Recommended Actions
- [ ] Set up CloudWatch alarms
- [ ] Configure backup retention policy
- [ ] Review and optimize TTL values
- [ ] Monitor cache hit rate for 1 week
- [ ] Implement cache warming for critical data
- [ ] Add cache metrics to application dashboard

### Future Enhancements
- [ ] Implement cache warming on deployment
- [ ] Add cache versioning for breaking changes
- [ ] Create cache performance dashboard
- [ ] Implement distributed locking for critical operations
- [ ] Add cache analytics and reporting

## Documentation Reference

| Document | Description |
|----------|-------------|
| [redis-guide.md](./redis-guide.md) | Comprehensive guide with patterns and examples |
| [redis-quick-reference.md](./redis-quick-reference.md) | Quick reference for common operations |
| [redis-setup.md](./redis-setup.md) | Step-by-step setup instructions |

## Support

### Internal Resources
- Utility module: `apps/core/redis_utils.py`
- Management command: `python manage.py redis_test`
- Configuration: `neurotwin/settings.py`

### External Resources
- [Django Cache Framework](https://docs.djangoproject.com/en/6.0/topics/cache/)
- [django-redis Documentation](https://github.com/jazzband/django-redis)
- [AWS ElastiCache Best Practices](https://docs.aws.amazon.com/AmazonElastiCache/latest/red-ug/BestPractices.html)
- [Redis Commands Reference](https://redis.io/commands/)

## Summary

Redis integration is complete and ready for use. The system is configured to use AWS ElastiCache Serverless with automatic scaling, high availability, and comprehensive monitoring. All utility functions, management commands, and documentation are in place for immediate use.

**Status**: ✅ Production Ready

**Last Updated**: March 9, 2026
