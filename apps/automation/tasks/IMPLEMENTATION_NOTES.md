# Celery Tasks Implementation Notes

## Completed Tasks

All Celery tasks for message processing have been implemented:

### 1. RetryableTask Base Class ✅
**File:** `apps/automation/tasks/retryable_task.py`

- Exponential backoff retry with jitter (1s, 2s, 4s, 8s, 16s)
- Automatic classification of transient vs permanent errors
- Comprehensive logging of retry attempts and failures
- Max 5 retries before permanent failure

**Key Features:**
- Retries on: network timeouts, 429 rate limits, 5xx server errors
- No retry on: 401, 403, 400 client errors
- Logs all retry attempts with context

### 2. process_incoming_message Task ✅
**File:** `apps/automation/tasks/message_tasks.py`

Processes incoming webhook events asynchronously:
- Parses Meta WhatsApp webhook payloads
- Creates/updates Conversation records
- Creates Message records with idempotency check
- Updates conversation timestamps
- Marks WebhookEvent as processed
- Can trigger AI response (placeholder for now)

**Requirements:** 11.2, 16.1-16.3

### 3. send_outgoing_message Task ✅
**File:** `apps/automation/tasks/message_tasks.py`

Sends outgoing messages with retry logic:
- Rate limiting check (placeholder - needs RateLimiter implementation)
- Message delivery via MessageDeliveryService (placeholder)
- Updates message status (pending → sent → delivered/failed)
- Tracks retry count and health status
- Updates integration health monitoring
- Notifies user on permanent failure (placeholder)

**Requirements:** 11.3, 12.1-12.7, 13.1-13.7, 16.6, 21.5

### 4. trigger_ai_response Task ✅
**File:** `apps/automation/tasks/message_tasks.py`

Generates AI responses to incoming messages:
- Fetches conversation history (last 10 messages)
- Calls TwinResponseService (placeholder)
- Creates outgoing Message with status='pending'
- Enqueues send_outgoing_message task

**Requirements:** 16.4

### 5. refresh_expiring_tokens Task ✅
**File:** `apps/automation/tasks/token_refresh.py`

Background task for automatic token refresh:
- Queries integrations with tokens expiring within 24 hours
- Uses AuthStrategyFactory to refresh credentials
- Updates integration with new tokens
- Tracks health status and consecutive failures
- Logs all refresh attempts

**Requirements:** 5.3, 6.5

## Task Exports

All tasks are properly exported in `apps/automation/tasks/__init__.py`:

```python
from apps.automation.tasks.message_tasks import (
    process_incoming_message,
    send_outgoing_message,
    trigger_ai_response
)
from apps.automation.tasks.token_refresh import (
    refresh_expiring_tokens
)
```

## Dependencies Required

The following components need to be implemented for full functionality:

### High Priority (blocking)
1. **RateLimiter** - Redis-based rate limiting (Task 5)
   - Location: `apps/automation/utils/rate_limiter.py`
   - Used by: `send_outgoing_message`

2. **MessageDeliveryService** - Message sending logic (Task 12.1)
   - Location: `apps/automation/services/message_delivery.py`
   - Used by: `send_outgoing_message`

3. **AuthStrategyFactory** - Already implemented
   - Location: `apps/automation/auth_strategies/factory.py`
   - Used by: `refresh_expiring_tokens`

### Medium Priority (enhances functionality)
4. **TwinResponseService** - AI response generation
   - Location: `apps/twin/services.py`
   - Used by: `trigger_ai_response`

5. **should_trigger_ai_response** - Logic to determine when to trigger AI
   - Location: `apps/automation/utils/ai_triggers.py`
   - Used by: `process_incoming_message`

6. **notify_message_failure** - User notification task (Task 26.1)
   - Location: `apps/automation/tasks/notification_tasks.py`
   - Used by: `send_outgoing_message`

## Celery Configuration

To use these tasks, ensure Celery is configured in Django settings:

```python
# neurotwin/settings.py

# Celery Configuration
CELERY_BROKER_URL = os.getenv('CELERY_BROKER_URL', 'redis://localhost:6379/0')
CELERY_RESULT_BACKEND = os.getenv('CELERY_RESULT_BACKEND', 'redis://localhost:6379/0')

CELERY_TASK_SERIALIZER = 'json'
CELERY_RESULT_SERIALIZER = 'json'
CELERY_ACCEPT_CONTENT = ['json']
CELERY_TIMEZONE = 'UTC'

# Task routing
CELERY_TASK_ROUTES = {
    'apps.automation.tasks.message_tasks.process_incoming_message': {'queue': 'incoming_messages'},
    'apps.automation.tasks.message_tasks.send_outgoing_message': {'queue': 'outgoing_messages'},
    'apps.automation.tasks.message_tasks.trigger_ai_response': {'queue': 'high_priority'},
    'automation.refresh_expiring_tokens': {'queue': 'background'},
}

# Celery Beat Schedule for periodic tasks
from celery.schedules import crontab

CELERY_BEAT_SCHEDULE = {
    'refresh-expiring-tokens': {
        'task': 'automation.refresh_expiring_tokens',
        'schedule': crontab(minute=0),  # Every hour
    },
}
```

## Testing

To test the tasks:

```python
# Test process_incoming_message
from apps.automation.tasks import process_incoming_message
result = process_incoming_message.delay('webhook-event-uuid')

# Test send_outgoing_message
from apps.automation.tasks import send_outgoing_message
result = send_outgoing_message.delay('message-uuid')

# Test trigger_ai_response
from apps.automation.tasks import trigger_ai_response
result = trigger_ai_response.delay('message-uuid')

# Test refresh_expiring_tokens
from apps.automation.tasks import refresh_expiring_tokens
result = refresh_expiring_tokens.delay()
```

## Next Steps

1. **Task 5**: Implement RateLimiter with Redis sliding window
2. **Task 12.1**: Implement MessageDeliveryService for Meta WhatsApp
3. **Task 15**: Configure Celery and Redis integration
4. **Task 26**: Implement notification tasks for failures

## Notes

- All tasks use the RetryableTask base class for automatic retry
- Idempotency is handled via external_message_id checks
- Health monitoring updates integration status on failures
- Comprehensive logging for debugging and audit trails
- Tasks are designed to be fault-tolerant and recoverable
