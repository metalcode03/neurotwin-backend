"""
Prometheus metrics collectors for integration monitoring.

Requirements: 30.6
"""
from prometheus_client import Counter, Histogram, Gauge
from typing import Optional


# Authentication metrics
auth_attempts_total = Counter(
    'automation_auth_attempts_total',
    'Total number of authentication attempts',
    ['auth_type', 'result']
)

# Message processing metrics
messages_processed_total = Counter(
    'automation_messages_processed_total',
    'Total number of messages processed',
    ['direction', 'status']
)

message_processing_duration = Histogram(
    'automation_message_processing_duration_seconds',
    'Message processing duration in seconds',
    ['direction', 'status'],
    buckets=[0.1, 0.5, 1.0, 2.0, 5.0, 10.0, 30.0, 60.0]
)

# Rate limit metrics
rate_limit_violations_total = Counter(
    'automation_rate_limit_violations_total',
    'Total number of rate limit violations',
    ['integration_id', 'limit_type']
)

# Celery queue metrics
celery_queue_length = Gauge(
    'automation_celery_queue_length',
    'Number of messages in Celery queue',
    ['queue_name']
)

# Webhook metrics
webhook_events_total = Counter(
    'automation_webhook_events_total',
    'Total number of webhook events received',
    ['integration_type', 'status']
)

webhook_processing_duration = Histogram(
    'automation_webhook_processing_duration_seconds',
    'Webhook processing duration in seconds',
    ['integration_type', 'status'],
    buckets=[0.1, 0.5, 1.0, 2.0, 5.0]
)

# Integration health metrics
integration_health_status = Gauge(
    'automation_integration_health_status',
    'Integration health status (0=healthy, 1=degraded, 2=disconnected)',
    ['integration_id', 'integration_type']
)


class MetricsCollector:
    """
    Service for collecting and recording Prometheus metrics.
    
    Requirements: 30.6
    """
    
    @staticmethod
    def record_auth_attempt(auth_type: str, result: str) -> None:
        """
        Record an authentication attempt.
        
        Args:
            auth_type: Type of authentication (oauth, meta, api_key)
            result: Result (success, failure)
        """
        auth_attempts_total.labels(
            auth_type=auth_type,
            result=result
        ).inc()
    
    @staticmethod
    def record_message_processed(
        direction: str,
        status: str,
        duration_seconds: Optional[float] = None
    ) -> None:
        """
        Record a processed message.
        
        Args:
            direction: Message direction (inbound, outbound)
            status: Message status (sent, failed, etc.)
            duration_seconds: Processing duration in seconds
        """
        messages_processed_total.labels(
            direction=direction,
            status=status
        ).inc()
        
        if duration_seconds is not None:
            message_processing_duration.labels(
                direction=direction,
                status=status
            ).observe(duration_seconds)
    
    @staticmethod
    def record_rate_limit_violation(
        integration_id: str,
        limit_type: str
    ) -> None:
        """
        Record a rate limit violation.
        
        Args:
            integration_id: Integration identifier
            limit_type: Type of limit (per_integration, global)
        """
        rate_limit_violations_total.labels(
            integration_id=integration_id,
            limit_type=limit_type
        ).inc()
    
    @staticmethod
    def update_celery_queue_length(queue_name: str, length: int) -> None:
        """
        Update Celery queue length gauge.
        
        Args:
            queue_name: Name of the queue
            length: Current queue length
        """
        celery_queue_length.labels(queue_name=queue_name).set(length)
    
    @staticmethod
    def record_webhook_event(
        integration_type: str,
        status: str,
        duration_seconds: Optional[float] = None
    ) -> None:
        """
        Record a webhook event.
        
        Args:
            integration_type: Type of integration
            status: Processing status
            duration_seconds: Processing duration in seconds
        """
        webhook_events_total.labels(
            integration_type=integration_type,
            status=status
        ).inc()
        
        if duration_seconds is not None:
            webhook_processing_duration.labels(
                integration_type=integration_type,
                status=status
            ).observe(duration_seconds)
    
    @staticmethod
    def update_integration_health(
        integration_id: str,
        integration_type: str,
        health_status: str
    ) -> None:
        """
        Update integration health status gauge.
        
        Args:
            integration_id: Integration identifier
            integration_type: Type of integration
            health_status: Health status (healthy, degraded, disconnected)
        """
        # Map health status to numeric value
        status_map = {
            'healthy': 0,
            'degraded': 1,
            'disconnected': 2
        }
        
        integration_health_status.labels(
            integration_id=integration_id,
            integration_type=integration_type
        ).set(status_map.get(health_status, 0))
