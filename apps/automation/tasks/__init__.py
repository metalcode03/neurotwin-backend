"""
Celery tasks for automation app.

Provides background tasks for message processing, token refresh,
and integration management with automatic retry logic.
"""

from apps.automation.tasks.retryable_task import (
    RetryableTask,
    TransientError,
    PermanentError
)
from apps.automation.tasks.message_tasks import (
    process_incoming_message,
    send_outgoing_message,
    trigger_ai_response
)
from apps.automation.tasks.token_refresh import (
    refresh_expiring_tokens
)
from apps.automation.tasks.notification_tasks import (
    notify_message_failure,
    notify_integration_disconnected
)
from apps.automation.tasks.cleanup_tasks import (
    cleanup_old_logs
)

__all__ = [
    'RetryableTask',
    'TransientError',
    'PermanentError',
    'process_incoming_message',
    'send_outgoing_message',
    'trigger_ai_response',
    'refresh_expiring_tokens',
    'notify_message_failure',
    'notify_integration_disconnected',
    'cleanup_old_logs',
]
