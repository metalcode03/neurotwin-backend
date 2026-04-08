# Quick Redis Installation Guide

Celery Beat requires Redis to be running. Here's how to install and start Redis on Windows.

## Option 1: Using WSL (Recommended)

### 1. Install WSL (if not already installed)

```powershell
# Run in PowerShell as Administrator
wsl --install
```

### 2. Install Redis in WSL

```bash
# Open WSL terminal
wsl

# Update package list
sudo apt-get update

# Install Redis
sudo apt-get install redis-server -y

# Start Redis
sudo service redis-server start

# Verify Redis is running
redis-cli ping
# Should return: PONG
```

### 3. Keep Redis Running

Redis will need to be started each time you restart your computer:

```bash
# Start Redis
sudo service redis-server start

# Check status
sudo service redis-server status

# Stop Redis (when needed)
sudo service redis-server stop
```

## Option 2: Using Docker (Alternative)

### 1. Install Docker Desktop

Download from: https://www.docker.com/products/docker-desktop/

### 2. Run Redis Container

```powershell
# Run Redis in a container
docker run -d --name redis-neurotwin -p 6379:6379 redis:latest

# Verify it's running
docker ps

# Test connection
docker exec -it redis-neurotwin redis-cli ping
# Should return: PONG
```

### 3. Manage Redis Container

```powershell
# Start Redis (if stopped)
docker start redis-neurotwin

# Stop Redis
docker stop redis-neurotwin

# View logs
docker logs redis-neurotwin

# Remove container (when no longer needed)
docker rm -f redis-neurotwin
```

## Option 3: Native Windows Installation

### 1. Download Redis for Windows

Download from: https://github.com/microsoftarchive/redis/releases

Or use Chocolatey:

```powershell
# Install Chocolatey (if not installed)
# Run in PowerShell as Administrator
Set-ExecutionPolicy Bypass -Scope Process -Force
[System.Net.ServicePointManager]::SecurityProtocol = [System.Net.ServicePointManager]::SecurityProtocol -bor 3072
iex ((New-Object System.Net.WebClient).DownloadString('https://community.chocolatey.org/install.ps1'))

# Install Redis
choco install redis-64 -y
```

### 2. Start Redis

```powershell
# Start Redis server
redis-server

# Or run as Windows service
redis-server --service-install
redis-server --service-start
```

## Verify Redis is Working

After installing Redis using any method above:

```powershell
# Test Redis connection
redis-cli ping
# Should return: PONG

# Test from Python
python -c "import redis; r = redis.Redis(host='localhost', port=6379); print(r.ping())"
# Should return: True
```

## Update Your .env File

The `.env` file has been updated to enable Redis:

```bash
USE_REDIS=True
REDIS_HOST=localhost
REDIS_PORT=6379
```

## Now Run Celery Beat

Once Redis is running, you can start Celery Beat:

```powershell
# Start Celery Beat
python manage.py celery_beat --loglevel=info
```

## Troubleshooting

### Error: "Connection refused"

**Solution**: Redis is not running. Start Redis using one of the methods above.

```bash
# WSL
sudo service redis-server start

# Docker
docker start redis-neurotwin

# Windows Service
redis-server --service-start
```

### Error: "No such transport: django"

**Solution**: Ensure `USE_REDIS=True` in your `.env` file.

### Port 6379 Already in Use

**Solution**: Another Redis instance is running. Stop it first:

```bash
# WSL
sudo service redis-server stop

# Docker
docker stop redis-neurotwin

# Windows
redis-cli shutdown
```

## Recommended: WSL Method

For Windows development, WSL is the recommended approach because:
- Most similar to production Linux environment
- Better performance than Docker on Windows
- Easier to manage and debug
- Native Redis experience

## Next Steps

1. Install Redis using one of the methods above
2. Verify Redis is running: `redis-cli ping`
3. Start Celery Beat: `python manage.py celery_beat --loglevel=info`
4. In another terminal, start Celery workers: `celery -A neurotwin worker --loglevel=info`

## Production Note

For production, you'll use AWS ElastiCache (already configured). The Redis setup above is only for local development.
