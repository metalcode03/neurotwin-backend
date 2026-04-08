# Celery Tasks with Retry System

This module provides Celery tasks for the automation app with automatic retry logic using exponential backoff.

## Overview

The retry system is built on the `RetryableTask` base class, which extends Celery's `Task` class to provide:

- **Automatic retry** on transient failures (network errors, timeouts, rate limits, server errors)
- **Exponential backoff** with jitter (1s, 2s, 4s, 8s, 16s)
- **Error classification** (transient vs permanent errors)
- **Comprehensive logging** of retry attempts and failures
- **Max 5 retry attempts** before marking as permanently failed

## Requirements

- Celery 5.4+
- Redis (as message broker)
- httpx (for HTTP error handling)

## Installation

Add Celery to your dependencies:

```bash
uv add celery redis
```

## Configuration

### 1. Create Celery App

Create `neurotwin/celery.py`:

```python
from celery import Celery
import os

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'neurotwin.settings')

app = Celery('neurotwin')
app.config_from_object('django.conf:settings', namespace='CELERY')
app.autodiscover_tasks()
```

### 2. Update Django Settings

Add to `neurotwin/settings.py`:

```python
# Celery Configuration
CELERY_BROKER_URL = os.getenv('CELERY_BROKER_URL', 'redis://localhost:6379/1')
CELERY_RESULT_BACKEND = os.getenv('CELERY_RESULT_BACKEND', 'redis://localhost:6379/1')
CELERY_ACCEPT_CONTENT = ['json']
CELERY_TASK_SERIALIZER = 'json'
CELERY_RESULT_SERIALIZER = 'json'
CELERY_TIMEZONE = 'UTC'

# Task routing
CELERY_TASK_ROUTES = {
    'apps.automation.tasks.message_tasks.process_incoming_message': {
        'queue': 'incoming_messages'
    },
    'apps.automation.tasks.message_tasks.send_outgoing_message': {
        'queue': 'outgoing_messages'
    },
    'apps.automation.tasks.message_tasks.trigger_ai_response': {
        'queue': 'high_priority'
    },
}

# Task time limits
CELERY_TASK_TIME_LIMIT = 300  # 5 minutes
CELERY_TASK_SOFT_TIME_LIMIT = 240  # 4 minutes

# Task result expiration
CELERY_RESULT_EXPIRES = 3600  # 1 hour
```

### 3. Update `__init__.py`

Add to `neurotwin/__init__.py`:

```python
from .celery import app as celery_app

__all__ = ('celery_app',)
```

## Usage

### Creating a Retryable Task

```python
from celery import shared_task
from apps.automation.tasks.retryable_task import RetryableTask

@shared_task(base=RetryableTask, bind=True)
def my_task(self, arg1, arg2):
    """
    Task with automatic retry on transient failures.
    
    The 'bind=True' parameter gives access to 'self' (the task instance),
    which is needed for retry logic.
    """
    try:
        # Your task logic here
        result = do_something(arg1, arg2)
        return result
        
    except Exception as e:
        # Retry if transient error
        if self.should_retry(e):
            raise  # Will be automatically retried
        else:
            # Permanent error - don't retry
            raise
```

### Error Classification

The `RetryableTask` automatically classifies errors:

**Transient Errors (will retry):**
- Network errors: `httpx.NetworkError`, `httpx.ConnectError`
- Timeouts: `httpx.TimeoutException`, `httpx.ReadTimeout`, `httpx.WriteTimeout`
- Rate limits: HTTP 429
- Server errors: HTTP 5xx

**Permanent Errors (won't retry):**
- Authentication errors: HTTP 401, 403
- Bad requests: HTTP 400, 404
- Other client errors: HTTP 4xx (except 429)

### Custom Error Classification

You can use custom exceptions for explicit error classification:

```python
from apps.automation.tasks.retryable_task import TransientError, PermanentError

@shared_task(base=RetryableTask, bind=True)
def my_task(self, data):
    try:
        result = process_data(data)
        return result
    except ValueError as e:
        # Explicitly mark as permanent error
        raise PermanentError(f"Invalid data: {e}")
    except ConnectionError as e:
        # Explicitly mark as transient error
        raise TransientError(f"Connection failed: {e}")
```

## Running Celery Workers

### Development

Start a worker for all queues:

```bash
celery -A neurotwin worker --loglevel=info
```

### Production

Start workers for specific queues:

```bash
# Incoming messages queue
celery -A neurotwin worker -Q incoming_messages --loglevel=info --concurrency=4

# Outgoing messages queue
celery -A neurotwin worker -Q outgoing_messages --loglevel=info --concurrency=4

# High priority queue
celery -A neurotwin worker -Q high_priority --loglevel=info --concurrency=2
```

## Monitoring

### View Active Tasks

```bash
celery -A neurotwin inspect active
```

### View Registered Tasks

```bash
celery -A neurotwin inspect registered
```

### View Task Stats

```bash
celery -A neurotwin inspect stats
```

## Retry Behavior

### Retry Schedule

With exponential backoff and max 5 retries:

| Attempt | Delay | Total Time |
|---------|-------|------------|
| 1       | 0s    | 0s         |
| 2       | 1s    | 1s         |
| 3       | 2s    | 3s         |
| 4       | 4s    | 7s         |
| 5       | 8s    | 15s        |
| 6       | 16s   | 31s        |

After 6 attempts (initial + 5 retries), the task is marked as permanently failed.

### Logging

All retry attempts are logged with context:

```
WARNING Task send_outgoing_message retry 2/5 (next attempt in 2s)
  task_id: abc123
  exception_type: TimeoutException
  exception_message: Request timeout
```

Permanent failures are logged as errors:

```
ERROR Task send_outgoing_message failed permanently after 5 retries
  task_id: abc123
  exception_type: TimeoutException
```

## Testing

### Unit Tests

```python
from apps.automation.tasks.message_tasks import send_outgoing_message
from apps.automation.tasks.retryable_task import TransientError

def test_retry_on_transient_error(mocker):
    # Mock the task to raise a transient error
    mocker.patch(
        'apps.automation.services.MessageDeliveryService.send_message',
        side_effect=httpx.TimeoutException("Timeout")
    )
    
    # Task should retry
    with pytest.raises(httpx.TimeoutException):
        send_outgoing_message.apply(args=['message-id'])
```

### Integration Tests

```python
def test_message_processing_with_retry(db, celery_worker):
    # Create test data
    message = Message.objects.create(...)
    
    # Enqueue task
    result = send_outgoing_message.delay(str(message.id))
    
    # Wait for completion
    result.get(timeout=10)
    
    # Verify message was sent
    message.refresh_from_db()
    assert message.status == 'sent'
```

## Best Practices

1. **Always use `bind=True`** when using RetryableTask to access `self.should_retry()`
2. **Handle exceptions explicitly** - decide whether to retry or fail
3. **Log context** - include relevant IDs and metadata in log messages
4. **Keep tasks idempotent** - tasks may be retried, so ensure they can run multiple times safely
5. **Use database transactions** - ensure atomic operations
6. **Check for duplicates** - use external_message_id or similar to prevent duplicate processing
7. **Update retry counts** - track retry attempts in your models for monitoring
8. **Monitor health** - update integration health status based on consecutive failures

## Troubleshooting

### Task Not Retrying

- Ensure `bind=True` is set in the task decorator
- Check that the exception is classified as transient
- Verify Celery worker is running and connected to Redis

### Too Many Retries

- Adjust `max_retries` in `retry_kwargs` if needed
- Consider if the error is actually permanent
- Check if external service is down (may need circuit breaker)

### Tasks Stuck in Queue

- Check Celery worker logs for errors
- Verify Redis connection
- Check task routing configuration
- Ensure workers are consuming from the correct queues

## Related Files

- `retryable_task.py` - Base task class with retry logic
- `message_tasks.py` - Example tasks using RetryableTask
- `token_refresh.py` - Token refresh background tasks

## Scheduled Tasks (Celery Beat)

### Token Refresh Task

The `refresh_expiring_tokens` task automatically refreshes OAuth and Meta tokens that are expiring within 24 hours.

**Configuration:**

The task is scheduled in `neurotwin/settings.py`:

```python
from celery.schedules import crontab

CELERY_BEAT_SCHEDULE = {
    'refresh-expiring-tokens': {
        'task': 'automation.refresh_expiring_tokens',
        'schedule': crontab(minute=0),  # Run every hour
        'options': {
            'queue': 'high_priority',
            'expires': 3600,
        },
    },
}
```

**Running Celery Beat:**

Start the Celery Beat scheduler using the management command:

```bash
# Development
python manage.py celery_beat --loglevel=info

# Production (run as a separate process)
celery -A neurotwin beat --loglevel=info --scheduler django_celery_beat.schedulers:DatabaseScheduler
```

**What it does:**

1. Queries integrations with tokens expiring within 24 hours
2. Skips API key integrations (they don't expire)
3. Refreshes OAuth tokens using refresh_token
4. Refreshes Meta tokens (60-day expiry)
5. Updates integration health status on success/failure
6. Logs all refresh attempts and results

**Monitoring:**

Check the task execution logs:

```bash
# View recent token refresh results
celery -A neurotwin inspect scheduled

# View task history (requires django-celery-results)
python manage.py shell
>>> from django_celery_results.models import TaskResult
>>> TaskResult.objects.filter(task_name='automation.refresh_expiring_tokens').order_by('-date_done')[:10]
```

**Requirements:** 5.3, 6.5

## Requirements

This implementation satisfies the following spec requirements:

- **13.1-13.7**: Retry system with exponential backoff
- **11.2-11.3**: Celery tasks for message processing
- **16.1-16.7**: Processing pipeline architecture
