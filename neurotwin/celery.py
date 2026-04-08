"""
Celery configuration for NeuroTwin integration engine.

Requirements: 11.1-11.7
"""
import os
from celery import Celery
from celery.signals import setup_logging
from kombu import Queue, Exchange

# Set default Django settings module
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'neurotwin.settings')

# Create Celery app
app = Celery('neurotwin')

# Load configuration from Django settings with CELERY_ prefix
app.config_from_object('django.conf:settings', namespace='CELERY')

# Define task queues with priorities
# Requirements: 11.5 - Separate queues for different message types
default_exchange = Exchange('default', type='direct')
high_priority_exchange = Exchange('high_priority', type='direct')

app.conf.task_queues = (
    # High priority queue for time-sensitive operations
    Queue(
        'high_priority',
        exchange=high_priority_exchange,
        routing_key='high_priority',
        priority=10,
    ),
    # Incoming messages from webhooks
    Queue(
        'incoming_messages',
        exchange=default_exchange,
        routing_key='incoming_messages',
        priority=5,
    ),
    # Outgoing messages to external platforms
    Queue(
        'outgoing_messages',
        exchange=default_exchange,
        routing_key='outgoing_messages',
        priority=5,
    ),
    # Default queue for other tasks
    Queue(
        'default',
        exchange=default_exchange,
        routing_key='default',
        priority=1,
    ),
)

# Task routing configuration
# Requirements: 11.5 - Configure task routes for different queues
app.conf.task_routes = {
    # Webhook processing tasks
    'apps.automation.tasks.process_incoming_message': {
        'queue': 'incoming_messages',
        'routing_key': 'incoming_messages',
    },
    # Message delivery tasks
    'apps.automation.tasks.send_outgoing_message': {
        'queue': 'outgoing_messages',
        'routing_key': 'outgoing_messages',
    },
    # AI response generation (high priority)
    'apps.automation.tasks.trigger_ai_response': {
        'queue': 'high_priority',
        'routing_key': 'high_priority',
    },
    # Token refresh (high priority)
    'apps.automation.tasks.refresh_expiring_tokens': {
        'queue': 'high_priority',
        'routing_key': 'high_priority',
    },
    # Default queue for other tasks
    '*': {
        'queue': 'default',
        'routing_key': 'default',
    },
}

# Task execution configuration
# Requirements: 11.4 - Configure task time limits and retry settings
app.conf.update(
    # Task time limits (in seconds)
    task_soft_time_limit=300,  # 5 minutes soft limit
    task_time_limit=600,  # 10 minutes hard limit
    
    # Task acknowledgment
    # Requirements: 11.4 - Enable task acknowledgment
    task_acks_late=True,  # Acknowledge after task completion
    task_reject_on_worker_lost=True,  # Requeue if worker crashes
    
    # Task result backend
    # Requirements: 11.4 - Enable result backend
    result_backend=None,  # Will be set from Django settings
    result_expires=3600,  # Results expire after 1 hour
    
    # Task serialization
    task_serializer='json',
    accept_content=['json'],
    result_serializer='json',
    
    # Task compression
    task_compression='gzip',
    result_compression='gzip',
    
    # Worker configuration
    worker_prefetch_multiplier=4,  # Prefetch 4 tasks per worker
    worker_max_tasks_per_child=1000,  # Restart worker after 1000 tasks
    
    # Retry configuration
    task_default_retry_delay=60,  # 1 minute default retry delay
    task_max_retries=3,  # Default max retries
    
    # Task tracking
    task_track_started=True,  # Track when tasks start
    task_send_sent_event=True,  # Send task-sent events
    
    # Timezone
    timezone='UTC',
    enable_utc=True,
)

# Disable Celery's default logging configuration
# Let Django handle logging
@setup_logging.connect
def config_loggers(*args, **kwargs):
    pass

# Auto-discover tasks from all installed Django apps
app.autodiscover_tasks()


@app.task(bind=True, ignore_result=True)
def debug_task(self):
    """Debug task for testing Celery configuration"""
    print(f'Request: {self.request!r}')
