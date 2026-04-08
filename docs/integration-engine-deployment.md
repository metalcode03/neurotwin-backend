# Integration Engine - Deployment Guide

## Overview

This guide covers deploying the Scalable Integration Engine to production, including environment setup, encryption key generation, Celery worker configuration, Redis setup, and database migrations.

## Table of Contents

- [Prerequisites](#prerequisites)
- [Environment Variables](#environment-variables)
- [Encryption Key Generation](#encryption-key-generation)
- [Database Setup](#database-setup)
- [Redis Configuration](#redis-configuration)
- [Celery Worker Setup](#celery-worker-setup)
- [Deployment Checklist](#deployment-checklist)
- [Monitoring & Alerts](#monitoring--alerts)
- [Scaling Considerations](#scaling-considerations)

---

## Prerequisites

### System Requirements

- **Python**: 3.13+
- **PostgreSQL**: 14+ (recommended) or 12+
- **Redis**: 7.0+ (recommended) or 6.2+
- **OS**: Linux (Ubuntu 22.04 LTS recommended) or macOS
- **Memory**: Minimum 2GB RAM (4GB+ recommended for production)
- **CPU**: 2+ cores recommended

### Python Dependencies

Install using `uv`:

```bash
# Install uv if not already installed
curl -LsSf https://astral.sh/uv/install.sh | sh

# Sync dependencies
uv sync

# Or install specific packages
uv add celery redis django djangorestframework cryptography httpx
```

---

## Environment Variables

### Required Variables

Create a `.env` file in the project root:

```bash
# Django Settings
SECRET_KEY=<generate-strong-secret-key>
DEBUG=False
ALLOWED_HOSTS=api.neurotwin.com,neurotwin.com

# Database
DATABASE_URL=postgresql://user:password@localhost:5432/neurotwin
DB_MAX_CONNECTIONS=50
DB_CONN_MAX_AGE=600

# Redis
REDIS_URL=redis://localhost:6379/0
CELERY_BROKER_URL=redis://localhost:6379/1
CELERY_RESULT_BACKEND=redis://localhost:6379/1

# Encryption Keys (CRITICAL - Generate unique keys for each)
OAUTH_ENCRYPTION_KEY=<fernet-key-1>
META_ENCRYPTION_KEY=<fernet-key-2>
API_KEY_ENCRYPTION_KEY=<fernet-key-3>

# Meta Webhook Configuration
META_APP_SECRET=<your-meta-app-secret>
META_WEBHOOK_VERIFY_TOKEN=<random-secure-token>

# CORS (if using separate frontend)
CORS_ALLOWED_ORIGINS=https://app.neurotwin.com,https://neurotwin.com

# Email (for notifications)
EMAIL_BACKEND=django.core.mail.backends.smtp.EmailBackend
EMAIL_HOST=smtp.gmail.com
EMAIL_PORT=587
EMAIL_USE_TLS=True
EMAIL_HOST_USER=noreply@neurotwin.com
EMAIL_HOST_PASSWORD=<email-password>

# Monitoring (optional)
SENTRY_DSN=<sentry-dsn>
PROMETHEUS_METRICS_ENABLED=True
```

### Optional Variables

```bash
# Rate Limiting
DEFAULT_RATE_LIMIT_PER_MINUTE=20
GLOBAL_RATE_LIMIT_PER_MINUTE=100

# Task Configuration
CELERY_TASK_TIME_LIMIT=300
CELERY_TASK_SOFT_TIME_LIMIT=240

# Logging
LOG_LEVEL=INFO
STRUCTURED_LOGGING=True

# Feature Flags
ENABLE_CIRCUIT_BREAKER=True
ENABLE_WEBHOOK_SIGNATURE_VERIFICATION=True
```

---

## Encryption Key Generation

### Generate Fernet Keys

Encryption keys are used to encrypt OAuth tokens, Meta tokens, and API keys at rest.

**Generate keys using Python**:

```python
from cryptography.fernet import Fernet

# Generate three separate keys
oauth_key = Fernet.generate_key()
meta_key = Fernet.generate_key()
api_key_key = Fernet.generate_key()

print(f"OAUTH_ENCRYPTION_KEY={oauth_key.decode()}")
print(f"META_ENCRYPTION_KEY={meta_key.decode()}")
print(f"API_KEY_ENCRYPTION_KEY={api_key_key.decode()}")
```

**Or use command line**:

```bash
python -c "from cryptography.fernet import Fernet; print(Fernet.generate_key().decode())"
```

### Key Management Best Practices

1. **Never commit keys to version control** - Use `.env` file (excluded in `.gitignore`)
2. **Use different keys per environment** (dev, staging, production)
3. **Rotate keys periodically** (every 90 days recommended)
4. **Store keys securely** - Use secrets manager (AWS Secrets Manager, HashiCorp Vault, etc.)
5. **Backup keys securely** - Losing keys means losing access to encrypted data

### Key Rotation Procedure

When rotating encryption keys:

1. Generate new keys
2. Add new keys to environment with different names (e.g., `OAUTH_ENCRYPTION_KEY_NEW`)
3. Update code to decrypt with old key, encrypt with new key
4. Re-encrypt all existing credentials
5. Remove old keys after migration complete

---

## Database Setup

### PostgreSQL Installation

**Ubuntu/Debian**:

```bash
sudo apt update
sudo apt install postgresql postgresql-contrib
sudo systemctl start postgresql
sudo systemctl enable postgresql
```

**macOS (Homebrew)**:

```bash
brew install postgresql@14
brew services start postgresql@14
```

### Create Database and User

```bash
# Connect to PostgreSQL
sudo -u postgres psql

# Create database and user
CREATE DATABASE neurotwin;
CREATE USER neurotwin_user WITH PASSWORD 'secure_password';
ALTER ROLE neurotwin_user SET client_encoding TO 'utf8';
ALTER ROLE neurotwin_user SET default_transaction_isolation TO 'read committed';
ALTER ROLE neurotwin_user SET timezone TO 'UTC';
GRANT ALL PRIVILEGES ON DATABASE neurotwin TO neurotwin_user;

# Exit
\q
```

### Configure Connection Pooling

Update `neurotwin/settings.py`:

```python
DATABASES = {
    'default': {
        'ENGINE': 'django.db.backends.postgresql',
        'NAME': os.getenv('DB_NAME', 'neurotwin'),
        'USER': os.getenv('DB_USER', 'neurotwin_user'),
        'PASSWORD': os.getenv('DB_PASSWORD'),
        'HOST': os.getenv('DB_HOST', 'localhost'),
        'PORT': os.getenv('DB_PORT', '5432'),
        'CONN_MAX_AGE': int(os.getenv('DB_CONN_MAX_AGE', 600)),
        'OPTIONS': {
            'connect_timeout': 10,
            'options': '-c statement_timeout=30000'  # 30 seconds
        }
    }
}

# Connection pooling
DATABASES['default']['CONN_MAX_AGE'] = 600  # 10 minutes
```

### Run Migrations

```bash
# Apply all migrations
python manage.py migrate

# Verify migrations
python manage.py showmigrations

# Check for issues
python manage.py check
```

### Create Indexes

Indexes are created automatically via migrations, but verify:

```sql
-- Connect to database
psql -U neurotwin_user -d neurotwin

-- Check indexes
\di

-- Verify critical indexes exist
SELECT indexname FROM pg_indexes WHERE tablename = 'automation_integration';
SELECT indexname FROM pg_indexes WHERE tablename = 'automation_message';
SELECT indexname FROM pg_indexes WHERE tablename = 'automation_conversation';
```

---

## Redis Configuration

### Redis Installation

**Ubuntu/Debian**:

```bash
sudo apt update
sudo apt install redis-server
sudo systemctl start redis-server
sudo systemctl enable redis-server
```

**macOS (Homebrew)**:

```bash
brew install redis
brew services start redis
```

### Configure Redis

Edit `/etc/redis/redis.conf`:

```conf
# Bind to localhost (or specific IP)
bind 127.0.0.1

# Set password (recommended for production)
requirepass your_secure_password

# Memory management
maxmemory 2gb
maxmemory-policy allkeys-lru

# Persistence (optional - for task results)
save 900 1
save 300 10
save 60 10000

# Connection settings
timeout 300
tcp-keepalive 60
maxclients 10000
```

Restart Redis:

```bash
sudo systemctl restart redis-server
```

### Test Redis Connection

```bash
# Test connection
redis-cli ping
# Should return: PONG

# Test with password
redis-cli -a your_secure_password ping

# Check info
redis-cli info
```

### Redis for Different Purposes

Use separate Redis databases:

- **Database 0**: Rate limiting and caching
- **Database 1**: Celery broker
- **Database 2**: Celery results

Update `.env`:

```bash
REDIS_URL=redis://:password@localhost:6379/0
CELERY_BROKER_URL=redis://:password@localhost:6379/1
CELERY_RESULT_BACKEND=redis://:password@localhost:6379/2
```

---

## Celery Worker Setup

### Celery Configuration

Celery is configured in `neurotwin/celery.py` and `neurotwin/settings.py`.

### Start Celery Workers

**Development (single worker)**:

```bash
celery -A neurotwin worker --loglevel=info
```

**Production (multiple workers with queues)**:

```bash
# Worker for incoming messages
celery -A neurotwin worker \
  -Q incoming_messages \
  --loglevel=info \
  --concurrency=4 \
  --max-tasks-per-child=1000 \
  --time-limit=300 \
  --soft-time-limit=240 \
  --logfile=/var/log/celery/incoming_worker.log \
  --pidfile=/var/run/celery/incoming_worker.pid

# Worker for outgoing messages
celery -A neurotwin worker \
  -Q outgoing_messages \
  --loglevel=info \
  --concurrency=4 \
  --max-tasks-per-child=1000 \
  --time-limit=300 \
  --soft-time-limit=240 \
  --logfile=/var/log/celery/outgoing_worker.log \
  --pidfile=/var/run/celery/outgoing_worker.pid

# Worker for high priority tasks
celery -A neurotwin worker \
  -Q high_priority \
  --loglevel=info \
  --concurrency=2 \
  --max-tasks-per-child=1000 \
  --time-limit=300 \
  --soft-time-limit=240 \
  --logfile=/var/log/celery/priority_worker.log \
  --pidfile=/var/run/celery/priority_worker.pid
```

### Start Celery Beat (Scheduled Tasks)

```bash
celery -A neurotwin beat \
  --loglevel=info \
  --logfile=/var/log/celery/beat.log \
  --pidfile=/var/run/celery/beat.pid
```

### Systemd Service Files

Create `/etc/systemd/system/celery-worker-incoming.service`:

```ini
[Unit]
Description=Celery Worker - Incoming Messages
After=network.target redis.target postgresql.target

[Service]
Type=forking
User=neurotwin
Group=neurotwin
WorkingDirectory=/opt/neurotwin
Environment="PATH=/opt/neurotwin/.venv/bin"
ExecStart=/opt/neurotwin/.venv/bin/celery -A neurotwin worker \
  -Q incoming_messages \
  --loglevel=info \
  --concurrency=4 \
  --max-tasks-per-child=1000 \
  --time-limit=300 \
  --soft-time-limit=240 \
  --logfile=/var/log/celery/incoming_worker.log \
  --pidfile=/var/run/celery/incoming_worker.pid \
  --detach
ExecStop=/bin/kill -TERM $MAINPID
Restart=always
RestartSec=10

[Install]
WantedBy=multi-user.target
```

Create similar files for other workers and beat.

Enable and start services:

```bash
sudo systemctl daemon-reload
sudo systemctl enable celery-worker-incoming
sudo systemctl start celery-worker-incoming
sudo systemctl status celery-worker-incoming
```

### Monitor Celery

```bash
# View active tasks
celery -A neurotwin inspect active

# View registered tasks
celery -A neurotwin inspect registered

# View stats
celery -A neurotwin inspect stats

# View queue lengths
celery -A neurotwin inspect active_queues

# Flower (web-based monitoring)
pip install flower
celery -A neurotwin flower --port=5555
```

---

## Deployment Checklist

### Pre-Deployment

- [ ] Generate and securely store encryption keys
- [ ] Configure environment variables in `.env`
- [ ] Set `DEBUG=False` in production
- [ ] Configure `ALLOWED_HOSTS` with production domains
- [ ] Set up PostgreSQL database with connection pooling
- [ ] Set up Redis with password authentication
- [ ] Configure CORS for frontend domain
- [ ] Set up SSL/TLS certificates (Let's Encrypt recommended)
- [ ] Configure firewall rules (allow 80, 443, block others)

### Database

- [ ] Run migrations: `python manage.py migrate`
- [ ] Verify indexes created: `python manage.py sqlmigrate automation 0023`
- [ ] Create superuser: `python manage.py createsuperuser`
- [ ] Load initial data (integration types): `python manage.py loaddata integration_types`
- [ ] Test database connection: `python manage.py dbshell`

### Celery

- [ ] Start Celery workers for all queues
- [ ] Start Celery Beat for scheduled tasks
- [ ] Verify workers are consuming tasks: `celery -A neurotwin inspect active`
- [ ] Test task execution: `python manage.py shell` → trigger test task
- [ ] Configure systemd services for auto-restart
- [ ] Set up log rotation for Celery logs

### Application

- [ ] Collect static files: `python manage.py collectstatic`
- [ ] Run system checks: `python manage.py check --deploy`
- [ ] Test health endpoint: `curl http://localhost:8000/api/v1/health/`
- [ ] Configure web server (Nginx/Apache) as reverse proxy
- [ ] Configure WSGI server (Gunicorn/uWSGI)
- [ ] Set up process manager (systemd/supervisor)

### Security

- [ ] Enable HTTPS (SSL/TLS)
- [ ] Configure CSRF protection
- [ ] Set secure cookie flags: `SESSION_COOKIE_SECURE=True`
- [ ] Enable HSTS: `SECURE_HSTS_SECONDS=31536000`
- [ ] Configure webhook signature verification
- [ ] Set up rate limiting
- [ ] Review and restrict admin access
- [ ] Enable security headers (X-Frame-Options, X-Content-Type-Options)

### Monitoring

- [ ] Set up application monitoring (Sentry, New Relic, etc.)
- [ ] Configure log aggregation (ELK, Datadog, etc.)
- [ ] Set up Prometheus metrics collection
- [ ] Configure Grafana dashboards
- [ ] Set up alerting rules (PagerDuty, Slack, etc.)
- [ ] Test alert notifications

### Testing

- [ ] Run full test suite: `pytest`
- [ ] Test OAuth flow with real provider
- [ ] Test Meta webhook with Meta sandbox
- [ ] Test API key authentication
- [ ] Load test message processing (1000+ concurrent)
- [ ] Test rate limiting behavior
- [ ] Test retry logic with simulated failures
- [ ] Test GDPR export and deletion

---

## Monitoring & Alerts

### Prometheus Metrics

Metrics are exposed at `/api/v1/metrics/` (requires authentication).

**Key Metrics**:

- `auth_attempts_total` - Total authentication attempts by type and result
- `messages_processed_total` - Total messages processed by status
- `message_processing_duration` - Message processing time histogram
- `rate_limit_violations_total` - Rate limit violations by integration
- `celery_queue_length` - Current queue length by queue name

### Grafana Dashboard

Import dashboard from `docs/grafana-dashboard.json`:

1. Open Grafana
2. Go to Dashboards → Import
3. Upload `grafana-dashboard.json`
4. Select Prometheus data source

### Alert Rules

Configure alerts in `apps/automation/services/alerting.py`:

**Critical Alerts**:

- Celery queue backlog > 1000 messages
- Message delivery failure rate > 5%
- Integration health degradation
- Database connection pool exhausted
- Redis connection failures

**Warning Alerts**:

- Rate limit violations > 100/hour
- Token refresh failures
- Webhook processing delays > 10 seconds
- Worker memory usage > 80%

### Log Aggregation

Structured logs are written to stdout in JSON format.

**Example log entry**:

```json
{
  "timestamp": "2026-04-08T10:30:00Z",
  "level": "INFO",
  "logger": "apps.automation.tasks.message_tasks",
  "message": "Message sent successfully",
  "integration_id": "uuid",
  "message_id": "uuid",
  "duration_ms": 450,
  "status": "sent"
}
```

Configure log shipping to ELK, Datadog, or CloudWatch.

---

## Scaling Considerations

### Horizontal Scaling

**Application Servers**:

- Run multiple Django instances behind load balancer
- Use sticky sessions if needed (or stateless JWT auth)
- Share Redis and PostgreSQL across instances

**Celery Workers**:

- Add more workers for each queue as load increases
- Monitor queue length and worker utilization
- Scale workers independently per queue

**Database**:

- Use read replicas for read-heavy workloads
- Consider connection pooling (PgBouncer)
- Partition large tables (messages, webhook_events)

**Redis**:

- Use Redis Cluster for high availability
- Consider Redis Sentinel for automatic failover
- Separate Redis instances for different purposes

### Vertical Scaling

**Increase Resources**:

- Add more CPU cores for Celery workers
- Increase memory for Redis caching
- Increase database connections pool size

### Performance Optimization

**Database**:

- Add indexes for frequently queried fields
- Use `select_related` and `prefetch_related` to avoid N+1 queries
- Enable query caching for read-heavy endpoints
- Archive old webhook events and messages

**Caching**:

- Cache integration types (5-minute TTL)
- Cache rate limit status (1-minute TTL)
- Use Redis for session storage

**Celery**:

- Tune concurrency based on CPU cores
- Use `--max-tasks-per-child` to prevent memory leaks
- Monitor task execution time and optimize slow tasks

---

## Backup and Recovery

### Database Backups

**Automated backups**:

```bash
# Daily backup script
#!/bin/bash
BACKUP_DIR=/backups/postgres
DATE=$(date +%Y%m%d_%H%M%S)
pg_dump -U neurotwin_user neurotwin | gzip > $BACKUP_DIR/neurotwin_$DATE.sql.gz

# Retain last 30 days
find $BACKUP_DIR -name "neurotwin_*.sql.gz" -mtime +30 -delete
```

**Restore from backup**:

```bash
gunzip -c neurotwin_20260408.sql.gz | psql -U neurotwin_user neurotwin
```

### Encryption Key Backups

Store encryption keys in secure location:

- AWS Secrets Manager
- HashiCorp Vault
- Encrypted backup file (offline storage)

**Never lose encryption keys** - encrypted data cannot be recovered without them.

---

## Troubleshooting

See [Troubleshooting Guide](./integration-engine-troubleshooting.md) for common issues and solutions.

---

## Support

For deployment support, contact: devops@neurotwin.com

For architecture questions, see: [Design Document](../.kiro/specs/scalable-integration-engine/design.md)
