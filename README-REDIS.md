# Redis Setup Complete ✅

Redis has been successfully integrated into NeuroTwin using Docker for local development.

## Quick Start

### Start Redis
```bash
.\start-redis.ps1
```

### Test Connection
```bash
uv run python manage.py redis_test
```

### View Statistics
```bash
uv run python manage.py redis_test --stats
```

## What's Running

- **Container**: `neurotwin-redis`
- **Image**: `redis:7-alpine`
- **Port**: `localhost:6379`
- **Status**: ✅ Running and connected

## Configuration

### Development (.env)
```bash
REDIS_HOST=localhost
REDIS_PORT=6379
REDIS_DB=0
REDIS_USE_SSL=False
```

### Production (AWS ElastiCache)
```bash
REDIS_HOST=neurotwinai-c7zwfg-serverless.use1.cache.amazonaws.com
REDIS_PORT=6379
REDIS_USE_SSL=True
```

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
    CacheKeys,
    CacheTTL,
)

# Cache cognitive profile
cache_cognitive_profile(user_id=123, profile_data={'blend': 50})

# Get cached profile
profile = get_cognitive_profile(user_id=123)

# Rate limiting
allowed, remaining = check_rate_limit(
    user_id=123,
    action='api_call',
    limit=100,
    window=3600
)

# Use predefined keys and TTLs
cache.set(
    CacheKeys.CSM_PROFILE.format(user_id=123),
    data,
    timeout=CacheTTL.MINUTE_5
)
```

### View Caching
```python
from django.views.decorators.cache import cache_page

@cache_page(60 * 5)  # Cache for 5 minutes
def integration_types_list(request):
    return Response(data)
```

## Docker Commands

### Container Management
```bash
# Start Redis
.\start-redis.ps1

# Stop Redis
docker stop neurotwin-redis

# Restart Redis
docker restart neurotwin-redis

# View logs
docker logs -f neurotwin-redis

# Remove container
docker rm -f neurotwin-redis
```

### Redis CLI
```bash
# Connect to Redis CLI
docker exec -it neurotwin-redis redis-cli

# Test connection
127.0.0.1:6379> PING
PONG

# Get all keys
127.0.0.1:6379> KEYS neurotwin:*

# Get a value
127.0.0.1:6379> GET neurotwin:user:123

# Clear all data
127.0.0.1:6379> FLUSHALL
```

## Monitoring

### Check Status
```bash
# Container status
docker ps | grep redis

# Redis info
docker exec neurotwin-redis redis-cli INFO

# Memory usage
docker exec neurotwin-redis redis-cli INFO memory

# Monitor commands
docker exec neurotwin-redis redis-cli MONITOR
```

### Django Commands
```bash
# Test connection
uv run python manage.py redis_test

# View statistics
uv run python manage.py redis_test --stats

# Clear cache
uv run python manage.py redis_test --clear
```

## Files Created

### Configuration
- ✅ `.env` - Updated with Docker Redis settings
- ✅ `docker-compose.yml` - Docker Compose configuration
- ✅ `start-redis.ps1` - PowerShell script to start Redis

### Code
- ✅ `apps/core/redis_utils.py` - Redis utility functions
- ✅ `apps/core/management/commands/redis_test.py` - Management command
- ✅ `neurotwin/settings.py` - Django Redis configuration

### Documentation
- ✅ `docs/REDIS_INTEGRATION.md` - Integration summary
- ✅ `docs/redis-guide.md` - Comprehensive guide
- ✅ `docs/redis-quick-reference.md` - Quick reference
- ✅ `docs/redis-setup.md` - Setup instructions
- ✅ `docs/redis-docker-setup.md` - Docker-specific guide
- ✅ `docs/REDIS_STATUS.md` - Current status
- ✅ `README-REDIS.md` - This file

## Daily Workflow

### Morning
```bash
# Start Redis
.\start-redis.ps1

# Start Django
uv run python manage.py runserver
```

### Development
```python
# Use Redis in your code
from django.core.cache import cache
from apps.core.redis_utils import cache_cognitive_profile

# Cache data
cache.set('key', 'value', timeout=300)

# Cache cognitive profile
cache_cognitive_profile(user_id=123, profile_data={'blend': 50})
```

### Evening (Optional)
```bash
# Stop Redis (or leave running)
docker stop neurotwin-redis
```

## Troubleshooting

### Redis Not Starting
```bash
# Check if port 6379 is in use
netstat -an | findstr 6379

# Remove existing container
docker rm -f neurotwin-redis

# Start fresh
.\start-redis.ps1
```

### Connection Failed
```bash
# Check if container is running
docker ps | grep redis

# Check logs
docker logs neurotwin-redis

# Restart container
docker restart neurotwin-redis
```

### Clear All Data
```bash
# Connect to Redis
docker exec -it neurotwin-redis redis-cli

# Flush all data
127.0.0.1:6379> FLUSHALL
```

## Production Deployment

When deploying to production:

1. Update `.env` with AWS ElastiCache endpoint:
   ```bash
   REDIS_HOST=neurotwinai-c7zwfg-serverless.use1.cache.amazonaws.com
   REDIS_USE_SSL=True
   ```

2. Ensure application is in same VPC as ElastiCache

3. Configure security groups to allow port 6379

4. Test connection from production environment

## Next Steps

- ✅ Redis running in Docker
- ✅ Django connected and tested
- ✅ Utility functions available
- ✅ Documentation complete

**You're ready to start using Redis in your application!**

## Additional Resources

- [Full Redis Guide](docs/redis-guide.md)
- [Quick Reference](docs/redis-quick-reference.md)
- [Docker Setup Guide](docs/redis-docker-setup.md)
- [Integration Summary](docs/REDIS_INTEGRATION.md)

## Support

For issues or questions:
1. Check logs: `docker logs neurotwin-redis`
2. Test connection: `uv run python manage.py redis_test`
3. Review documentation in `docs/` folder

---

**Status**: ✅ Production Ready for Development

**Last Updated**: March 9, 2026
