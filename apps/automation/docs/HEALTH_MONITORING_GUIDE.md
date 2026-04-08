# Health Monitoring and Observability Guide

This guide explains the health monitoring and observability features implemented for the Scalable Integration Engine.

## Overview

The health monitoring system provides comprehensive visibility into:
- System component health (database, Redis, Celery)
- Integration health status tracking
- Structured logging for all integration events
- Prometheus metrics for monitoring and alerting

## Components

### 1. Health Check Endpoint

**Endpoint:** `GET /api/v1/automation/health/`

**Purpose:** Check overall system health status

**Response:**
```json
{
  "status": "healthy",  // or "degraded", "unhealthy"
  "components": {
    "database": {
      "status": "healthy",
      "message": "Database connection healthy"
    },
    "redis": {
      "status": "healthy",
      "message": "Redis connection healthy"
    },
    "celery": {
      "status": "healthy",
      "message": "Celery workers healthy (2 active)"
    }
  }
}
```

**Status Codes:**
- `200 OK`: System is healthy or degraded
- `503 Service Unavailable`: System is unhealthy

**Use Cases:**
- Load balancer health checks
- Monitoring system probes
- Deployment readiness checks

### 2. Integration Health Monitoring

**Service:** `IntegrationHealthService`

**Features:**
- Automatic health status tracking based on consecutive failures
- Health status transitions:
  - `healthy`: 0-2 consecutive failures
  - `degraded`: 3-9 consecutive failures
  - `disconnected`: 10+ consecutive failures

**Usage in Code:**

```python
from apps.automation.services import IntegrationHealthService

# Record successful operation
IntegrationHealthService.record_success(integration)

# Record failed operation
IntegrationHealthService.record_failure(
    integration,
    error_message="Connection timeout"
)

# Get health metrics
metrics = IntegrationHealthService.get_health_metrics(integration)
# Returns: {
#   'health_status': 'healthy',
#   'consecutive_failures': 0,
#   'last_successful_sync_at': datetime,
#   'is_healthy': True,
#   'is_degraded': False,
#   'is_disconnected': False
# }
```

### 3. Structured Logging

**Service:** `StructuredLogger`

**Log File:** `logs/automation_events.json.log`

**Features:**
- JSON-formatted logs for easy parsing
- Structured data for all integration events
- 30-day retention (configurable)

**Event Types:**

#### Authentication Attempts
```python
from apps.automation.services import StructuredLogger

StructuredLogger.log_authentication_attempt(
    user_id=str(user.id),
    integration_type_id=str(integration_type.id),
    auth_type='oauth',
    result='success',
    duration_ms=1234.5
)
```

#### Webhook Events
```python
StructuredLogger.log_webhook_event(
    integration_type='whatsapp',
    integration_id=str(integration.id),
    event_type='message',
    processing_status='processed',
    duration_ms=567.8
)
```

#### Message Sends
```python
StructuredLogger.log_message_send(
    integration_id=str(integration.id),
    message_id=str(message.id),
    status='sent',
    duration_ms=890.1,
    retry_count=0
)
```

#### Rate Limit Violations
```python
StructuredLogger.log_rate_limit_violation(
    integration_id=str(integration.id),
    limit_type='per_integration',
    attempted_rate=25,
    limit=20,
    wait_seconds=30
)
```

#### Health Status Changes
```python
StructuredLogger.log_integration_health_change(
    integration_id=str(integration.id),
    old_status='healthy',
    new_status='degraded',
    consecutive_failures=3
)
```

#### Token Refresh
```python
StructuredLogger.log_token_refresh(
    integration_id=str(integration.id),
    auth_type='oauth',
    result='success'
)
```

### 4. Prometheus Metrics

**Endpoint:** `GET /api/v1/automation/metrics/`

**Purpose:** Export metrics in Prometheus format

**Available Metrics:**

#### Authentication Metrics
- `automation_auth_attempts_total{auth_type, result}` - Counter
  - Labels: `auth_type` (oauth, meta, api_key), `result` (success, failure)

#### Message Processing Metrics
- `automation_messages_processed_total{direction, status}` - Counter
  - Labels: `direction` (inbound, outbound), `status` (sent, failed, etc.)
- `automation_message_processing_duration_seconds{direction, status}` - Histogram
  - Buckets: 0.1, 0.5, 1.0, 2.0, 5.0, 10.0, 30.0, 60.0 seconds

#### Rate Limit Metrics
- `automation_rate_limit_violations_total{integration_id, limit_type}` - Counter
  - Labels: `integration_id`, `limit_type` (per_integration, global)

#### Celery Queue Metrics
- `automation_celery_queue_length{queue_name}` - Gauge
  - Labels: `queue_name`

#### Webhook Metrics
- `automation_webhook_events_total{integration_type, status}` - Counter
- `automation_webhook_processing_duration_seconds{integration_type, status}` - Histogram
  - Buckets: 0.1, 0.5, 1.0, 2.0, 5.0 seconds

#### Integration Health Metrics
- `automation_integration_health_status{integration_id, integration_type}` - Gauge
  - Values: 0 (healthy), 1 (degraded), 2 (disconnected)

**Usage in Code:**

```python
from apps.automation.services import MetricsCollector

# Record authentication attempt
MetricsCollector.record_auth_attempt(
    auth_type='oauth',
    result='success'
)

# Record message processed
MetricsCollector.record_message_processed(
    direction='outbound',
    status='sent',
    duration_seconds=1.234
)

# Record rate limit violation
MetricsCollector.record_rate_limit_violation(
    integration_id=str(integration.id),
    limit_type='per_integration'
)

# Update Celery queue length
MetricsCollector.update_celery_queue_length(
    queue_name='outgoing_messages',
    length=42
)

# Record webhook event
MetricsCollector.record_webhook_event(
    integration_type='whatsapp',
    status='processed',
    duration_seconds=0.567
)

# Update integration health
MetricsCollector.update_integration_health(
    integration_id=str(integration.id),
    integration_type='whatsapp',
    health_status='healthy'
)
```

## Integration with Existing Code

### In Authentication Flows

```python
import time
from apps.automation.services import StructuredLogger, MetricsCollector

start_time = time.time()
try:
    # Perform authentication
    result = strategy.complete_authentication(code, state, redirect_uri)
    
    duration_ms = (time.time() - start_time) * 1000
    
    # Log success
    StructuredLogger.log_authentication_attempt(
        user_id=str(user.id),
        integration_type_id=str(integration_type.id),
        auth_type=integration_type.auth_type,
        result='success',
        duration_ms=duration_ms
    )
    
    # Record metric
    MetricsCollector.record_auth_attempt(
        auth_type=integration_type.auth_type,
        result='success'
    )
    
except Exception as e:
    duration_ms = (time.time() - start_time) * 1000
    
    # Log failure
    StructuredLogger.log_authentication_attempt(
        user_id=str(user.id),
        integration_type_id=str(integration_type.id),
        auth_type=integration_type.auth_type,
        result='failure',
        duration_ms=duration_ms,
        error_message=str(e)
    )
    
    # Record metric
    MetricsCollector.record_auth_attempt(
        auth_type=integration_type.auth_type,
        result='failure'
    )
    
    raise
```

### In Message Processing

```python
import time
from apps.automation.services import (
    IntegrationHealthService,
    StructuredLogger,
    MetricsCollector
)

start_time = time.time()
try:
    # Send message
    result = MessageDeliveryService.send_message(integration, message)
    
    duration_seconds = time.time() - start_time
    
    # Update message status
    message.status = 'sent'
    message.save()
    
    # Record success
    IntegrationHealthService.record_success(integration)
    
    # Log event
    StructuredLogger.log_message_send(
        integration_id=str(integration.id),
        message_id=str(message.id),
        status='sent',
        duration_ms=duration_seconds * 1000,
        retry_count=message.retry_count
    )
    
    # Record metric
    MetricsCollector.record_message_processed(
        direction='outbound',
        status='sent',
        duration_seconds=duration_seconds
    )
    
except Exception as e:
    duration_seconds = time.time() - start_time
    
    # Record failure
    IntegrationHealthService.record_failure(integration, str(e))
    
    # Log event
    StructuredLogger.log_message_send(
        integration_id=str(integration.id),
        message_id=str(message.id),
        status='failed',
        duration_ms=duration_seconds * 1000,
        retry_count=message.retry_count,
        error_message=str(e)
    )
    
    # Record metric
    MetricsCollector.record_message_processed(
        direction='outbound',
        status='failed',
        duration_seconds=duration_seconds
    )
    
    raise
```

### In Webhook Processing

```python
import time
from apps.automation.services import StructuredLogger, MetricsCollector

start_time = time.time()
try:
    # Process webhook
    process_webhook_event(webhook_event)
    
    duration_seconds = time.time() - start_time
    
    # Log event
    StructuredLogger.log_webhook_event(
        integration_type=integration_type.name,
        integration_id=str(integration.id),
        event_type='message',
        processing_status='processed',
        duration_ms=duration_seconds * 1000
    )
    
    # Record metric
    MetricsCollector.record_webhook_event(
        integration_type=integration_type.name,
        status='processed',
        duration_seconds=duration_seconds
    )
    
except Exception as e:
    duration_seconds = time.time() - start_time
    
    # Log failure
    StructuredLogger.log_webhook_event(
        integration_type=integration_type.name,
        integration_id=str(integration.id) if integration else None,
        event_type='message',
        processing_status='failed',
        duration_ms=duration_seconds * 1000,
        error_message=str(e)
    )
    
    # Record metric
    MetricsCollector.record_webhook_event(
        integration_type=integration_type.name,
        status='failed',
        duration_seconds=duration_seconds
    )
    
    raise
```

## Monitoring Setup

### Prometheus Configuration

Add to your `prometheus.yml`:

```yaml
scrape_configs:
  - job_name: 'neurotwin-automation'
    scrape_interval: 15s
    static_configs:
      - targets: ['localhost:8000']
    metrics_path: '/api/v1/automation/metrics/'
```

### Grafana Dashboards

Example queries for Grafana:

**Authentication Success Rate:**
```promql
rate(automation_auth_attempts_total{result="success"}[5m]) 
/ 
rate(automation_auth_attempts_total[5m])
```

**Message Processing Rate:**
```promql
rate(automation_messages_processed_total[5m])
```

**Average Message Processing Duration:**
```promql
rate(automation_message_processing_duration_seconds_sum[5m])
/
rate(automation_message_processing_duration_seconds_count[5m])
```

**Rate Limit Violations:**
```promql
rate(automation_rate_limit_violations_total[5m])
```

**Unhealthy Integrations:**
```promql
count(automation_integration_health_status > 0)
```

### Alert Rules

Example Prometheus alert rules:

```yaml
groups:
  - name: automation_alerts
    rules:
      - alert: HighAuthenticationFailureRate
        expr: |
          rate(automation_auth_attempts_total{result="failure"}[5m])
          /
          rate(automation_auth_attempts_total[5m])
          > 0.1
        for: 5m
        labels:
          severity: warning
        annotations:
          summary: "High authentication failure rate"
          description: "Authentication failure rate is {{ $value | humanizePercentage }}"
      
      - alert: HighMessageFailureRate
        expr: |
          rate(automation_messages_processed_total{status="failed"}[5m])
          /
          rate(automation_messages_processed_total[5m])
          > 0.05
        for: 5m
        labels:
          severity: critical
        annotations:
          summary: "High message failure rate"
          description: "Message failure rate is {{ $value | humanizePercentage }}"
      
      - alert: IntegrationDisconnected
        expr: automation_integration_health_status == 2
        for: 1m
        labels:
          severity: critical
        annotations:
          summary: "Integration disconnected"
          description: "Integration {{ $labels.integration_id }} is disconnected"
      
      - alert: HighRateLimitViolations
        expr: rate(automation_rate_limit_violations_total[1h]) > 100
        for: 5m
        labels:
          severity: warning
        annotations:
          summary: "High rate limit violations"
          description: "Rate limit violations: {{ $value }} per hour"
```

## Log Analysis

### Querying JSON Logs

Using `jq` to analyze logs:

```bash
# Count authentication attempts by auth_type
cat logs/automation_events.json.log | jq -r 'select(.event_type=="authentication") | .auth_type' | sort | uniq -c

# Find failed webhook events
cat logs/automation_events.json.log | jq 'select(.event_type=="webhook" and .processing_status=="failed")'

# Calculate average message send duration
cat logs/automation_events.json.log | jq -r 'select(.event_type=="message_send" and .status=="sent") | .duration_ms' | awk '{sum+=$1; count++} END {print sum/count}'

# Find rate limit violations
cat logs/automation_events.json.log | jq 'select(.event_type=="rate_limit_violation")'
```

### Log Aggregation

For production, consider using:
- **ELK Stack** (Elasticsearch, Logstash, Kibana)
- **Loki** (with Grafana)
- **CloudWatch Logs** (AWS)
- **Stackdriver** (GCP)

## Requirements Satisfied

- ✅ **31.1-31.7**: Health check endpoint with database, Redis, and Celery checks
- ✅ **23.1-23.5**: Integration health monitoring with automatic status transitions
- ✅ **30.1-30.7**: Structured JSON logging for all integration events
- ✅ **30.6**: Prometheus metrics collectors for monitoring and alerting

## Next Steps

1. Set up Prometheus scraping
2. Create Grafana dashboards
3. Configure alert rules
4. Set up log aggregation
5. Integrate health checks with load balancer
6. Add custom metrics as needed
