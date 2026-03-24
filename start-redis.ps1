# Start Redis Docker container for NeuroTwin development
# Usage: .\start-redis.ps1

Write-Host "Starting Redis container for NeuroTwin..." -ForegroundColor Cyan

# Check if Docker is running
try {
    docker ps | Out-Null
    if ($LASTEXITCODE -ne 0) {
        Write-Host "Error: Docker is not running. Please start Docker Desktop." -ForegroundColor Red
        exit 1
    }
} catch {
    Write-Host "Error: Docker is not installed or not in PATH." -ForegroundColor Red
    exit 1
}

# Check if container already exists
$containerExists = docker ps -a --filter "name=neurotwin-redis" --format "{{.Names}}"

if ($containerExists) {
    Write-Host "Redis container already exists. Starting..." -ForegroundColor Yellow
    docker start neurotwin-redis
    
    if ($LASTEXITCODE -eq 0) {
        Write-Host "Redis container started successfully!" -ForegroundColor Green
    } else {
        Write-Host "Failed to start Redis container." -ForegroundColor Red
        exit 1
    }
} else {
    Write-Host "Creating new Redis container..." -ForegroundColor Yellow
    docker run -d `
        --name neurotwin-redis `
        -p 6379:6379 `
        -v redis_data:/data `
        redis:7-alpine `
        redis-server --appendonly yes --maxmemory 256mb --maxmemory-policy allkeys-lru
    
    if ($LASTEXITCODE -eq 0) {
        Write-Host "Redis container created and started successfully!" -ForegroundColor Green
    } else {
        Write-Host "Failed to create Redis container." -ForegroundColor Red
        exit 1
    }
}

# Wait for Redis to be ready
Write-Host "Waiting for Redis to be ready..." -ForegroundColor Yellow
Start-Sleep -Seconds 2

# Test connection
Write-Host "Testing Redis connection..." -ForegroundColor Cyan
$pingResult = docker exec neurotwin-redis redis-cli ping 2>&1

if ($pingResult -match "PONG") {
    Write-Host "Redis is ready and accepting connections!" -ForegroundColor Green
    Write-Host ""
    Write-Host "Redis is running on localhost:6379" -ForegroundColor Cyan
    Write-Host ""
    Write-Host "Useful commands:" -ForegroundColor Yellow
    Write-Host "  - Test Django connection: uv run python manage.py redis_test" -ForegroundColor White
    Write-Host "  - View logs: docker logs -f neurotwin-redis" -ForegroundColor White
    Write-Host "  - Redis CLI: docker exec -it neurotwin-redis redis-cli" -ForegroundColor White
    Write-Host "  - Stop Redis: docker stop neurotwin-redis" -ForegroundColor White
} else {
    Write-Host "Redis is not responding. Check logs with: docker logs neurotwin-redis" -ForegroundColor Red
    exit 1
}
