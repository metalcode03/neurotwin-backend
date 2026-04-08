# Retry System Setup Guide

This guide walks you through setting up the Celery-based retry system for the Scalable Integration Engine.

## What Was Implemented

✅ **RetryableTask Base Class** (`retryable_task.py`)
- Automatic retry with exponential backoff (1s, 2s, 4s, 8s, 16s)
- Smart error classification (transient vs permanent)
- Max 5 retry attempts
- Comprehensive logging of all retry attempts
- Custom exceptions: `TransientError`, `PermanentError`

✅ **Example Message Tasks** (`message_tasks.py`)
- `process_incoming_message` - Process webhook events
- `send_outgoing_message` - Send messages with rate limiting
- `trigger_ai_response` - Generate AI responses

✅ **Celery Dependency** Added to `pyproject.toml`

✅ **Documentation** (`README.md`)

## Quick Start

### 1. Install Dependencies

```bash
uv sync
```

This will install Celery 5.4+ and all required dependencies.

### 2. Configure Celery

Create `neurotwin/celery.py`:

```python
"""
Celery configuration for NeuroTwin.

This module initializes the Celery app and configures it to work
with Django settings and auto-discover tasks from all installed apps.
"""

from celery import Celery
import os

# Set default Django settings module
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'neurotwin.settings')

# Create Celery app
app = Celery('neurotwin')

# Load config from Django settings with CELERY_ prefix
app.config_from_object('django.conf:settings', namespace='CELERY')

# Auto-discover tasks from all installed apps
app.autodiscover_tasks()


@app.task(bind=True, ignore_result=True)
def debug_task(self):
    """Debug task for testing Celery setup."""
    print(f'Request: {self.request!r}')
```

### 3. Update Django Settings

Add to `neurotwin/settings.py`:

```python
# ============================================================================
# CELERY CONFIGURATION
# ============================================================================

# Broker and backend
CELERY_BROKER_URL = os.getenv('CELERY_BROKER_URL', 'redis://localhost:6379/1')
CELERY_RESULT_BACKEND = os.getenv('CELERY_RESULT_BACKEND', 'redis://localhost:6379/1')

# Serialization
CELERY_ACCEPT_CONTENT = ['json']
CELERY_TASK_SERIALIZER = 'json'
CELERY_RESULT_SERIALIZER = 'json'
CELERY_TIMEZONE = 'UTC'

# Task routing - route tasks to specific queues
CELERY_TASK_ROUTES = {
    'apps.automation.tasks.message_tasks.process_incoming_message': {
        'queue': 'incoming_messages',
        'routing_key': 'incoming.message',
    },
    'apps.automation.tasks.message_tasks.send_outgoing_message': {
        'queue': 'outgoing_messages',
        'routing_key': 'outgoing.message',
    },
    'apps.automation.tasks.message_tasks.trigger_ai_response': {
        'queue': 'high_priority',
        'routing_key': 'ai.response',
    },
}

# Task execution limits
CELERY_TASK_TIME_LIMIT = 300  # 5 minutes hard limit
CELERY_TASK_SOFT_TIME_LIMIT = 240  # 4 minutes soft limit

# Task result expiration
CELERY_RESULT_EXPIRES = 3600  # 1 hour

# Task acknowledgment
CELERY_TASK_ACKS_LATE = True  # Acknowledge after task completes
CELERY_WORKER_PREFETCH_MULTIPLIER = 1  # One task at a time per worker

# Task compression
CELERY_TASK_COMPRESSION = 'gzip'
CELERY_RESULT_COMPRESSION = 'gzip'

# Logging
CELERY_WORKER_LOG_FORMAT = '[%(asctime)s: %(levelname)s/%(processName)s] %(message)s'
CELERY_WORKER_TASK_LOG_FORMAT = '[%(asctime)s: %(levelname)s/%(processName)s][%(task_name)s(%(task_id)s)] %(message)s'
```

### 4. Update `neurotwin/__init__.py`

Add Celery app initialization:

```python
"""
NeuroTwin Django project initialization.

This module ensures Celery is loaded when Django starts.
"""

from .celery import app as celery_app

__all__ = ('celery_app',)
```

### 5. Update `.env`

Add Celery configuration:

```bash
# Celery Configuration
CELERY_BROKER_URL=redis://localhost:6379/1
CELERY_RESULT_BACKEND=redis://localhost:6379/1
```

### 6. Start Redis

Ensure Redis is running (required for Celery broker):

```bash
# Windows (if Redis is installed)
redis-server

# Or use Docker
docker run -d -p 6379:6379 redis:latest
```

### 7. Start Celery Worker

In a separate terminal:

```bash
# Development - single worker for all queues
celery -A neurotwin worker --loglevel=info

# Production - separate workers per queue
celery -A neurotwin worker -Q incoming_messages --loglevel=info --concurrency=4
celery -A neurotwin worker -Q outgoing_messages --loglevel=info --concurrency=4
celery -A neurotwin worker -Q high_priority --loglevel=info --concurrency=2
```

## Testing the Setup

### 1. Test Celery Connection

```python
# In Django shell
python manage.py shell

from apps.automation.tasks.message_tasks import process_incoming_message

# Enqueue a test task (will fail gracefully if webhook doesn't exist)
result = process_incoming_message.delay('test-webhook-id')
print(f"Task ID: {result.id}")
print(f"Task State: {result.state}")
```

### 2. Monitor Tasks

```bash
# View active tasks
celery -A neurotwin inspect active

# View registered tasks
celery -A neurotwin inspect registered

# View worker stats
celery -A neurotwin inspect stats
```

## Using the Retry System

### Basic Usage

```python
from celery import shared_task
from apps.automation.tasks.retryable_task import RetryableTask

@shared_task(base=RetryableTask, bind=True)
def my_retryable_task(self, data):
    """
    Task with automatic retry on transient failures.
    """
    try:
        # Your task logic
        result = process_data(data)
        return result
    except Exception as e:
        # Automatically retries on transient errors
        if self.should_retry(e):
            raise
        else:
            # Permanent error - don't retry
            raise
```

### Error Classification

**Transient (will retry):**
- Network errors: `httpx.NetworkError`, `httpx.TimeoutException`
- Rate limits: HTTP 429
- Server errors: HTTP 5xx

**Permanent (won't retry):**
- Auth errors: HTTP 401, 403
- Bad requests: HTTP 400, 404
- Other client errors: HTTP 4xx

### Custom Error Handling

```python
from apps.automation.tasks.retryable_task import TransientError, PermanentError

@shared_task(base=RetryableTask, bind=True)
def my_task(self, data):
    try:
        result = process(data)
        return result
    except ValueError:
        # Explicitly mark as permanent
        raise PermanentError("Invalid data format")
    except ConnectionError:
        # Explicitly mark as transient
        raise TransientError("Connection failed, will retry")
```

## Next Steps

1. **Implement remaining tasks** (Task 7 in spec):
   - Complete `process_incoming_message` with actual webhook parsing
   - Implement `MessageDeliveryService` for sending messages
   - Implement rate limiting integration
   - Add AI response generation

2. **Add Celery Beat** for scheduled tasks (Task 23 in spec):
   - Token refresh scheduling
   - Health monitoring
   - Cleanup tasks

3. **Add monitoring** (Task 30 in spec):
   - Prometheus metrics
   - Task statistics endpoint
   - Alert configuration

4. **Write tests** (Tasks 6.2, 6.3 in spec):
   - Property-based tests for retry behavior
   - Integration tests for message processing

## Troubleshooting

### Celery Worker Not Starting

- Check Redis is running: `redis-cli ping` (should return "PONG")
- Verify `CELERY_BROKER_URL` in `.env`
- Check for syntax errors: `python -m py_compile apps/automation/tasks/*.py`

### Tasks Not Being Processed

- Verify worker is running: `celery -A neurotwin inspect active`
- Check task routing configuration
- Ensure worker is consuming from correct queue

### Import Errors

- Run `uv sync` to install dependencies
- Verify `neurotwin/__init__.py` imports celery_app
- Check `INSTALLED_APPS` includes 'apps.automation'

## Requirements Satisfied

This implementation satisfies:

- ✅ **Requirement 13.1**: Retry with exponential backoff (1s, 2s, 4s, 8s, 16s)
- ✅ **Requirement 13.2**: Max 5 retries before permanent failure
- ✅ **Requirement 13.3**: Retry count and timestamp tracking
- ✅ **Requirement 13.4**: User notification on permanent failure (placeholder)
- ✅ **Requirement 13.5**: Retry on transient errors (timeout, 429, 5xx)
- ✅ **Requirement 13.6**: No retry on permanent errors (401, 403, 400)
- ✅ **Requirement 13.7**: Comprehensive retry logging

## Related Documentation

- `README.md` - Detailed usage guide
- `retryable_task.py` - Base task implementation
- `message_tasks.py` - Example task implementations
- Spec: `.kiro/specs/scalable-integration-engine/tasks.md` (Task 6)
