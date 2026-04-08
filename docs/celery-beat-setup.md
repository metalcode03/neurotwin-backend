# Celery Beat Setup Guide

This guide explains how to set up and run Celery Beat for scheduled background tasks in the NeuroTwin platform.

## Overview

Celery Beat is a scheduler that triggers periodic tasks. The NeuroTwin platform uses it for:

- **Token Refresh**: Automatically refresh OAuth and Meta tokens before they expire (every hour)
- Future scheduled tasks can be added to the same configuration

## Prerequisites

1. Redis must be running (used as Celery broker)
2. Django database must be migrated (Beat uses django-celery-beat for dynamic scheduling)
3. Celery workers must be running to execute the scheduled tasks

## Installation

The required packages are already in `pyproject.toml`:

```bash
uv sync
```

This installs:
- `celery>=5.4.0`
- `django-celery-beat>=2.7.0`
- `redis>=5.2.1`

## Database Setup

Run migrations to create the django-celery-beat tables:

```bash
python manage.py migrate django_celery_beat
```

This creates tables for:
- Periodic tasks
- Crontab schedules
- Interval schedules
- Solar schedules

## Configuration

### 1. Celery Beat Scheduler

In `neurotwin/settings.py`:

```python
CELERY_BEAT_SCHEDULER = 'django_celery_beat.schedulers:DatabaseScheduler'
```

### 2. Scheduled Tasks

In `neurotwin/settings.py`:

```python
from celery.schedules import crontab

CELERY_BEAT_SCHEDULE = {
    'refresh-expiring-tokens': {
        'task': 'automation.refresh_expiring_tokens',
        'schedule': crontab(minute=0),  # Every hour at minute 0
        'options': {
            'queue': 'high_priority',
            'expires': 3600,
        },
    },
}
```

## Running Celery Beat

### Development

Use the Django management command:

```bash
python manage.py celery_beat --loglevel=info
```

This command:
- Starts Celery Beat with the DatabaseScheduler
- Loads schedules from both settings.py and the database
- Logs scheduled task execution

### Production

Run Celery Beat as a separate process:

```bash
celery -A neurotwin beat \
  --loglevel=info \
  --scheduler django_celery_beat.schedulers:DatabaseScheduler
```

**Important:** Only run ONE Celery Beat process per deployment. Multiple Beat processes will cause duplicate task execution.

## Complete Startup Sequence

For a full production setup, you need three processes:

### 1. Start Redis

```bash
redis-server
```

### 2. Start Celery Workers

```bash
# Terminal 1: High priority queue
celery -A neurotwin worker -Q high_priority --loglevel=info --concurrency=2

# Terminal 2: Incoming messages queue
celery -A neurotwin worker -Q incoming_messages --loglevel=info --concurrency=4

# Terminal 3: Outgoing messages queue
celery -A neurotwin worker -Q outgoing_messages --loglevel=info --concurrency=4

# Terminal 4: Default queue
celery -A neurotwin worker -Q default --loglevel=info --concurrency=2
```

Or start a single worker for all queues (development):

```bash
celery -A neurotwin worker --loglevel=info
```

### 3. Start Celery Beat

```bash
# Terminal 5: Beat scheduler
python manage.py celery_beat --loglevel=info
```

## Monitoring

### View Scheduled Tasks

```bash
# List all scheduled tasks
celery -A neurotwin inspect scheduled

# View Beat schedule
celery -A neurotwin inspect clock
```

### Check Task Execution

```python
# Django shell
python manage.py shell

from django_celery_results.models import TaskResult

# View recent token refresh executions
TaskResult.objects.filter(
    task_name='automation.refresh_expiring_tokens'
).order_by('-date_done')[:10]
```

### View Logs

Celery Beat logs show when tasks are scheduled:

```
[2024-01-15 10:00:00,123: INFO/MainProcess] Scheduler: Sending due task refresh-expiring-tokens (automation.refresh_expiring_tokens)
```

Worker logs show task execution:

```
[2024-01-15 10:00:00,456: INFO/MainProcess] Task automation.refresh_expiring_tokens[abc-123] received
[2024-01-15 10:00:05,789: INFO/ForkPoolWorker-1] Task automation.refresh_expiring_tokens[abc-123] succeeded in 5.2s: {'total_checked': 15, 'refreshed': 12, 'failed': 0, 'skipped': 3}
```

## Dynamic Scheduling (Admin Interface)

You can also manage schedules through the Django admin:

1. Go to `/admin/django_celery_beat/`
2. Add/edit periodic tasks
3. Changes take effect immediately (no restart needed)

This is useful for:
- Temporarily disabling tasks
- Adjusting schedules without code changes
- Adding one-off scheduled tasks

## Token Refresh Task Details

### What It Does

The `refresh_expiring_tokens` task:

1. Finds integrations with tokens expiring within 24 hours
2. Skips API key integrations (they don't expire)
3. Refreshes OAuth tokens using the refresh_token
4. Refreshes Meta tokens (60-day expiry)
5. Updates integration health status
6. Logs all operations

### Schedule

- **Frequency**: Every hour (at minute 0)
- **Queue**: high_priority
- **Timeout**: 1 hour (task expires if not executed)

### Success Criteria

A successful run returns:

```json
{
  "total_checked": 15,
  "refreshed": 12,
  "failed": 0,
  "skipped": 3,
  "timestamp": "2024-01-15T10:00:05.123Z"
}
```

### Failure Handling

If token refresh fails:
- Integration `consecutive_failures` counter increments
- After 3 failures: `health_status` → 'degraded'
- After 10 failures: `health_status` → 'disconnected', `status` → 'disconnected'
- User is notified (future: notification system)

## Troubleshooting

### Beat Not Starting

**Error:** `ImportError: cannot import name 'crontab'`

**Solution:** Ensure the import is at the top of settings.py:

```python
from celery.schedules import crontab
```

### Tasks Not Executing

**Check:**
1. Is Celery Beat running? (`ps aux | grep celery`)
2. Are workers running? (`celery -A neurotwin inspect active`)
3. Is Redis accessible? (`redis-cli ping`)
4. Check Beat logs for errors

### Duplicate Task Execution

**Cause:** Multiple Beat processes running

**Solution:** Ensure only ONE Beat process per deployment. Use process managers (systemd, supervisor) to enforce this.

### Tasks Executing at Wrong Time

**Check:**
1. Server timezone matches `CELERY_TIMEZONE` setting
2. Crontab schedule is correct
3. Database scheduler is being used (not default)

## Production Deployment

### Using Systemd

Create `/etc/systemd/system/celery-beat.service`:

```ini
[Unit]
Description=Celery Beat Service
After=network.target redis.service

[Service]
Type=simple
User=neurotwin
Group=neurotwin
WorkingDirectory=/opt/neurotwin
Environment="PATH=/opt/neurotwin/.venv/bin"
ExecStart=/opt/neurotwin/.venv/bin/celery -A neurotwin beat \
  --loglevel=info \
  --scheduler django_celery_beat.schedulers:DatabaseScheduler

Restart=always
RestartSec=10

[Install]
WantedBy=multi-user.target
```

Enable and start:

```bash
sudo systemctl enable celery-beat
sudo systemctl start celery-beat
sudo systemctl status celery-beat
```

### Using Docker

```dockerfile
# Separate container for Beat
FROM python:3.13-slim

WORKDIR /app
COPY . /app

RUN pip install -r requirements.txt

CMD ["celery", "-A", "neurotwin", "beat", \
     "--loglevel=info", \
     "--scheduler", "django_celery_beat.schedulers:DatabaseScheduler"]
```

In `docker-compose.yml`:

```yaml
services:
  celery-beat:
    build: .
    command: celery -A neurotwin beat --loglevel=info --scheduler django_celery_beat.schedulers:DatabaseScheduler
    depends_on:
      - redis
      - db
    environment:
      - CELERY_BROKER_URL=redis://redis:6379/1
    restart: always
```

## Environment Variables

Required environment variables:

```bash
# Redis connection
REDIS_HOST=localhost
REDIS_PORT=6379
REDIS_DB=0
REDIS_PASSWORD=  # Optional

# Celery configuration
CELERY_BROKER_URL=redis://localhost:6379/1
CELERY_RESULT_BACKEND=redis://localhost:6379/2

# Timezone
TZ=UTC
```

## References

- [Celery Beat Documentation](https://docs.celeryproject.org/en/stable/userguide/periodic-tasks.html)
- [django-celery-beat Documentation](https://django-celery-beat.readthedocs.io/)
- [Token Refresh Task Implementation](../apps/automation/tasks/token_refresh.py)

## Requirements

This setup satisfies:
- **Requirement 5.3**: OAuth token refresh before expiry
- **Requirement 6.5**: Meta token refresh before 60-day expiry
- **Requirement 11.1-11.7**: Celery configuration and task scheduling
