# Monitoring and Alerting System

This document describes the monitoring and alerting infrastructure for the Scalable Integration Engine.

## Overview

The monitoring system provides real-time visibility into:
- Celery task execution statistics
- Queue backlog and worker status
- Alert rules for critical conditions
- Log retention and cleanup

**Requirements:** 27.1-27.7, 22.6, 30.7

## API Endpoints

All monitoring endpoints require admin authentication.

### 1. Task Statistics

**Endpoint:** `GET /api/v1/admin/tasks/stats/`

Returns task execution statistics grouped by task name and time period.

**Query Parameters:**
- `task_name` (optional): Filter by specific task name
- `period` (optional): Time period - `hour`, `day`, or `week` (default: `hour`)

**Example Response:**
```json
{
  "period": "hour",
  "summary": {
    "total_tasks": 150,
    "successful_tasks": 145,
    "failed_tasks": 5,
    "total_duration": 450.5,
    "average_duration": 3.1
  },
  "tasks": [
    {
      "task_name": "apps.automation.tasks.process_incoming_message",
      "total_tasks": 100,
      "successful_tasks": 98,
      "failed_tasks": 2,
      "total_duration": 300.0,
      "average_duration": 3.06,
      "period": "hour"
    }
  ]
}
```

### 2. Queue Status

**Endpoint:** `GET /api/v1/admin/queues/status/`

Returns current queue lengths and backlog information.

**Example Response:**
```json
{
  "queues": {
    "high_priority": 5,
    "incoming_messages": 120,
    "outgoing_messages": 80,
    "default": 10
  },
  "total_backlog": 215,
  "alerts": [
    {
      "queue": "incoming_messages",
      "length": 120,
      "threshold": 100,
      "message": "Queue backlog exceeds threshold"
    }
  ]
}
```

### 3. Worker Status

**Endpoint:** `GET /api/v1/admin/workers/status/`

Returns information about active Celery workers.

**Example Response:**
```json
{
  "active_workers": 2,
  "workers": {
    "celery@worker1": [
      {
        "name": "apps.automation.tasks.process_incoming_message",
        "id": "task-id-123"
      }
    ]
  }
}
```

### 4. Alert Status

**Endpoint:** `GET /api/v1/admin/alerts/status/`

Returns current status of all configured alert rules.

**Example Response:**
```json
{
  "alerts": [
    {
      "name": "rate_limit_violations",
      "triggered": true,
      "current_value": 150,
      "threshold": 100,
      "severity": "warning",
      "description": "Alert when rate limit violations exceed 100 per hour"
    },
    {
      "name": "message_delivery_failures",
      "triggered": false,
      "current_value": 2.5,
      "threshold": 5.0,
      "total_messages": 1000,
      "failed_messages": 25,
      "severity": "ok"
    }
  ],
  "triggered_count": 1,
  "total_rules": 6
}
```

## Alert Rules

The system monitors the following conditions:

### 1. Rate Limit Violations
- **Threshold:** >100 violations per hour
- **Severity:** Warning
- **Action:** Review rate limit configuration and integration usage patterns

### 2. Message Delivery Failures
- **Threshold:** >5% failure rate
- **Severity:** Critical
- **Action:** Investigate external API issues or integration health

### 3. Token Refresh Failures
- **Threshold:** >3 failures per hour
- **Severity:** Warning
- **Action:** Check OAuth provider availability and credential validity

### 4. Webhook Processing Delays
- **Threshold:** >10 seconds average processing time
- **Severity:** Warning
- **Action:** Review worker capacity and database performance

### 5. Queue Backlog
- **Threshold:** >1000 messages total
- **Severity:** Critical
- **Action:** Scale up Celery workers or investigate processing bottlenecks

### 6. Integration Health Degradation
- **Threshold:** ≥5 integrations degraded or disconnected
- **Severity:** Warning
- **Action:** Review integration health status and trigger reconnection flows

## Log Retention Policies

The system implements the following retention policies:

### 1. Integration Logs
- **Retention:** 90 days
- **Implementation:** RotatingFileHandler with 90 backupCount
- **Location:** `logs/security_events.json.log`
- **Requirements:** 30.7

### 2. Webhook Events
- **Retention:** 30 days
- **Implementation:** Database cleanup + RotatingFileHandler with 30 backupCount
- **Location:** `logs/automation_events.json.log`
- **Requirements:** 22.6

### 3. Celery Task Results
- **Retention:** 7 days
- **Implementation:** Redis key expiry
- **Location:** Redis (keys: `celery-task-meta-*`)
- **Requirements:** 27.7

## Automated Cleanup

A scheduled Celery Beat task runs daily at 2:00 AM to clean up old data:

```python
# Celery Beat Schedule
CELERY_BEAT_SCHEDULE = {
    'cleanup-old-logs': {
        'task': 'automation.cleanup_old_logs',
        'schedule': crontab(hour=2, minute=0),
    },
}
```

### Manual Cleanup

You can also run cleanup manually:

```bash
# Dry run (shows what would be deleted)
python manage.py cleanup_old_logs --dry-run

# Actual cleanup
python manage.py cleanup_old_logs
```

## Recording Metrics

The alerting service provides methods to record metrics:

```python
from apps.automation.services.alerting import AlertingService

alerting = AlertingService()

# Record rate limit violation
alerting.record_rate_limit_violation()

# Record message delivery result
alerting.record_message_delivery(success=True)

# Record token refresh failure
alerting.record_token_refresh_failure()

# Record webhook processing time
alerting.record_webhook_processing(processing_time=2.5)
```

## Task Execution Recording

The task monitoring service records task execution:

```python
from apps.automation.services.task_monitoring import TaskMonitoringService

monitoring = TaskMonitoringService()

# Record task execution
monitoring.record_task_execution(
    task_name='apps.automation.tasks.process_incoming_message',
    success=True,
    duration=3.2
)
```

## Integration with Existing Code

### In Rate Limiter

```python
# apps/automation/utils/rate_limiter.py
from apps.automation.services.alerting import AlertingService

def check_rate_limit(self, integration_id, limit_per_minute):
    allowed, wait_seconds = self._check_sliding_window(...)
    
    if not allowed:
        # Record violation for alerting
        alerting = AlertingService()
        alerting.record_rate_limit_violation()
    
    return allowed, wait_seconds
```

### In Message Tasks

```python
# apps/automation/tasks/message_tasks.py
from apps.automation.services.alerting import AlertingService
from apps.automation.services.task_monitoring import TaskMonitoringService

@shared_task
def send_outgoing_message(message_id):
    start_time = time.time()
    alerting = AlertingService()
    monitoring = TaskMonitoringService()
    
    try:
        # Send message logic
        success = True
        alerting.record_message_delivery(success=True)
    except Exception as e:
        success = False
        alerting.record_message_delivery(success=False)
        raise
    finally:
        duration = time.time() - start_time
        monitoring.record_task_execution(
            task_name='apps.automation.tasks.send_outgoing_message',
            success=success,
            duration=duration
        )
```

### In Webhook Processing

```python
# apps/automation/views/webhooks.py
from apps.automation.services.alerting import AlertingService

def post(self, request):
    start_time = time.time()
    
    # Process webhook
    # ...
    
    # Record processing time
    processing_time = time.time() - start_time
    alerting = AlertingService()
    alerting.record_webhook_processing(processing_time)
```

## Monitoring Dashboard

For a complete monitoring solution, consider integrating with:

- **Prometheus + Grafana:** For metrics visualization
- **Sentry:** For error tracking and alerting
- **ELK Stack:** For log aggregation and analysis
- **Celery Flower:** For real-time Celery monitoring

## Troubleshooting

### High Queue Backlog

1. Check worker status: `GET /api/v1/admin/workers/status/`
2. Scale up workers: `celery -A neurotwin worker --concurrency=8`
3. Review task execution times: `GET /api/v1/admin/tasks/stats/`

### High Failure Rate

1. Check alert status: `GET /api/v1/admin/alerts/status/`
2. Review integration health: `GET /api/v1/integrations/{id}/health/`
3. Check external API status
4. Review error logs: `logs/provider_errors.json.log`

### Slow Webhook Processing

1. Check processing times: `GET /api/v1/admin/alerts/status/`
2. Review database query performance
3. Check Redis connection pool
4. Scale up workers if needed

## Best Practices

1. **Regular Monitoring:** Check alert status at least daily
2. **Proactive Scaling:** Scale workers before queue backlog becomes critical
3. **Log Analysis:** Regularly review logs for patterns and anomalies
4. **Alert Tuning:** Adjust thresholds based on actual usage patterns
5. **Capacity Planning:** Monitor trends to plan infrastructure scaling
