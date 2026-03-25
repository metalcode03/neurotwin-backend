# Redis Docker Setup for Development

Quick guide to run Redis using Docker for local development.

## Quick Start

### 1. Start Redis Container

Using the provided `docker-compose.yml`:

```bash
# Start Redis in background
docker-compose up -d redis

# Check if Redis is running
docker-compose ps

# View Redis logs
docker-compose logs -f redis
```

Or using Docker directly (what you did in Docker Desktop):

```bash
# Run Redis container
docker run -d \
  --name neurotwin-redis \
  -p 6379:6379 \
  -v redis_data:/data \
  redis:7-alpine \
  redis-server --appendonly yes --maxmemory 256mb --maxmemory-policy allkeys-lru

# Check if running
docker ps | grep redis

# View logs
docker logs -f neurotwin-redis
```

### 2. Configure Environment

Your `.env` is already configured for Docker Redis:

```bash
REDIS_HOST=localhost
REDIS_PORT=6379
REDIS_DB=0
REDIS_USE_SSL=False
```

### 3. Test Connection

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

### 4. View Statistics

```bash
# Show cache statistics
uv run python manage.py redis_test --stats

# Output:
# Cache Statistics:
# ==================================================
# Connected Clients: 1
# Memory Used: 1.2M
# Total Commands: 15
# Cache Hits: 10
# Cache Misses: 5
# Hit Rate: 66.67%
# Total Keys: 3
# ==================================================
```

## Docker Commands

### Start/Stop Redis

```bash
# Start Redis
docker-compose up -d redis

# Stop Redis
docker-compose stop redis

# Restart Redis
docker-compose restart redis

# Stop and remove container
docker-compose down
```

### Monitor Redis

```bash
# View logs
docker-compose logs -f redis

# Execute Redis CLI
docker-compose exec redis redis-cli

# Check Redis info
docker-compose exec redis redis-cli INFO

# Monitor commands in real-time
docker-compose exec redis redis-cli MONITOR
```

### Redis CLI Commands

```bash
# Connect to Redis CLI
docker-compose exec redis redis-cli

# Test connection
127.0.0.1:6379> PING
PONG

# Get all keys
127.0.0.1:6379> KEYS neurotwin:*

# Get a value
127.0.0.1:6379> GET neurotwin:user:123

# Set a value
127.0.0.1:6379> SET neurotwin:test "Hello"
OK

# Delete a key
127.0.0.1:6379> DEL neurotwin:test

# Get database info
127.0.0.1:6379> INFO keyspace

# Exit
127.0.0.1:6379> exit
```

## Docker Compose Configuration

The `docker-compose.yml` includes:

```yaml
services:
  redis:
    image: redis:7-alpine          # Redis 7.x (latest stable)
    container_name: neurotwin-redis
    ports:
      - "6379:6379"                # Expose Redis port
    volumes:
      - redis_data:/data           # Persist data
    command: redis-server 
      --appendonly yes             # Enable persistence
      --maxmemory 256mb            # Limit memory usage
      --maxmemory-policy allkeys-lru  # Eviction policy
    restart: unless-stopped        # Auto-restart
    healthcheck:
      test: ["CMD", "redis-cli", "ping"]
      interval: 10s
      timeout: 3s
      retries: 3
```

### Configuration Explained

- **Image**: `redis:7-alpine` - Lightweight Redis 7.x
- **Port**: `6379` - Standard Redis port
- **Volume**: Persists data between container restarts
- **appendonly**: Enables AOF (Append Only File) persistence
- **maxmemory**: Limits Redis memory to 256MB
- **maxmemory-policy**: `allkeys-lru` - Evicts least recently used keys when memory limit reached
- **healthcheck**: Monitors Redis health

## Data Persistence

Redis data is persisted in a Docker volume:

```bash
# List volumes
docker volume ls | grep redis

# Inspect volume
docker volume inspect neurotwin_redis_data

# Backup data
docker run --rm -v neurotwin_redis_data:/data -v $(pwd):/backup alpine tar czf /backup/redis-backup.tar.gz /data

# Restore data
docker run --rm -v neurotwin_redis_data:/data -v $(pwd):/backup alpine tar xzf /backup/redis-backup.tar.gz -C /
```

## Troubleshooting

### Container Won't Start

```bash
# Check if port 6379 is already in use
netstat -an | grep 6379

# Stop any existing Redis processes
docker stop neurotwin-redis
docker rm neurotwin-redis

# Start fresh
docker-compose up -d redis
```

### Connection Refused

```bash
# Check if container is running
docker ps | grep redis

# Check container logs
docker logs neurotwin-redis

# Verify port mapping
docker port neurotwin-redis

# Test connection from host
redis-cli -h localhost -p 6379 ping
```

### Clear All Data

```bash
# Connect to Redis CLI
docker-compose exec redis redis-cli

# Flush all data
127.0.0.1:6379> FLUSHALL

# Or from command line
docker-compose exec redis redis-cli FLUSHALL
```

### Reset Everything

```bash
# Stop and remove container
docker-compose down

# Remove volume (deletes all data)
docker volume rm neurotwin_redis_data

# Start fresh
docker-compose up -d redis
```

## Development Workflow

### Daily Usage

```bash
# Morning: Start Redis
docker-compose up -d redis

# Develop your application
uv run python manage.py runserver

# Evening: Stop Redis (optional - can leave running)
docker-compose stop redis
```

### Testing

```bash
# Start Redis
docker-compose up -d redis

# Run tests (uses in-memory cache, not Redis)
uv run pytest

# Test Redis specifically
uv run python manage.py redis_test
```

### Debugging

```bash
# Monitor Redis commands in real-time
docker-compose exec redis redis-cli MONITOR

# Check memory usage
docker-compose exec redis redis-cli INFO memory

# Check connected clients
docker-compose exec redis redis-cli CLIENT LIST

# Get slow queries
docker-compose exec redis redis-cli SLOWLOG GET 10
```

## Integration with Django

Your Django application is already configured to use Docker Redis:

```python
# neurotwin/settings.py
CACHES = {
    'default': {
        'BACKEND': 'django_redis.cache.RedisCache',
        'LOCATION': 'redis://localhost:6379/0',  # Docker Redis
        # ... other settings
    }
}
```

### Usage in Code

```python
from django.core.cache import cache

# Set value
cache.set('user_profile_123', profile_data, timeout=300)

# Get value
profile = cache.get('user_profile_123')

# Delete value
cache.delete('user_profile_123')
```

## Production vs Development

### Development (Docker Redis)
```bash
# .env
REDIS_HOST=localhost
REDIS_PORT=6379
REDIS_USE_SSL=False
```

### Production (AWS ElastiCache)
```bash
# .env.production
REDIS_HOST=neurotwinai-c7zwfg-serverless.use1.cache.amazonaws.com
REDIS_PORT=6379
REDIS_USE_SSL=True
```

## Performance Tips

### 1. Monitor Memory Usage

```bash
# Check memory
docker stats neurotwin-redis

# Redis memory info
docker-compose exec redis redis-cli INFO memory
```

### 2. Optimize Configuration

For development, the default settings are fine. For heavier usage:

```yaml
command: redis-server 
  --appendonly yes
  --maxmemory 512mb              # Increase if needed
  --maxmemory-policy allkeys-lru
  --save 60 1000                 # Save to disk every 60s if 1000 keys changed
```

### 3. Monitor Hit Rate

```bash
# Check hit rate
uv run python manage.py redis_test --stats

# Target: >80% hit rate
```

## Docker Desktop Integration

Since you're using Docker Desktop:

1. **View Container**: Open Docker Desktop → Containers
2. **See Logs**: Click on `neurotwin-redis` → Logs tab
3. **Inspect**: Click on `neurotwin-redis` → Inspect tab
4. **Terminal**: Click on `neurotwin-redis` → Terminal tab (opens Redis CLI)
5. **Stats**: View CPU/Memory usage in real-time

## Next Steps

1. ✅ Redis container running
2. ✅ Environment configured
3. ✅ Test connection: `uv run python manage.py redis_test`
4. ✅ Start developing with Redis caching

## Additional Resources

- [Redis Docker Hub](https://hub.docker.com/_/redis)
- [Redis Commands](https://redis.io/commands/)
- [Django Cache Framework](https://docs.djangoproject.com/en/6.0/topics/cache/)
- [Full Redis Guide](./redis-guide.md)
- [Quick Reference](./redis-quick-reference.md)
