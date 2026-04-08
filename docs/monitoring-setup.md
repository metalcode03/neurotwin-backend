# NeuroTwin Monitoring Setup Guide

This guide explains the monitoring and observability implementation for the credit-based AI architecture.

## Overview

The monitoring system provides comprehensive visibility into:
- Credit operations (checks, deductions, resets)
- AI request performance and reliability
- Model routing decisions
- Provider API health
- System performance metrics

## Components Implemented

### 1. Prometheus Metrics (`apps/credits/metrics.py`)

**Counters**:
- `credit_checks_total` - Total credit balance checks (labels: user_tier, result)
- `credit_deductions_total` - Total credit deductions (labels: user_tier, brain_mode, operation_type)
- `credit_resets_total` - Total monthly resets (labels: user_tier)
- `ai_requests_total` - Total AI requests (labels: brain_mode, operation_type, model_used, status)
- `ai_request_tokens_total` - Total tokens consumed (labels: brain_mode, model_used)
- `model_selections_total` - Total model selections (labels: brain_mode, operation_type, selected_model)
- `model_failures_total` - Total model failures (labels: model, error_type)

**Histograms**:
- `credit_check_latency_seconds` - Credit check latency (labels: cache_hit)
- `ai_request_latency_seconds` - AI request latency (labels: brain_mode, model_used)
- `credit_deduction_latency_seconds` - Credit deduction latency
- `model_routing_latency_seconds` - Model routing latency (labels: brain_mode)

### 2. Metrics Endpoint

**URL**: `/metrics`

**Format**: Prometheus text format

**Security**: 
- In production, protect with IP whitelist or authentication
- Example nginx config provided in `apps/credits/metrics_views.py`

**Usage**:
```bash
curl http://localhost:8000/metrics
```

### 3. Structured Logging

**Configuration**: `neurotwin/settings.py` LOGGING section

**Log Files**:
- `logs/neurotwin.json.log` - General application logs
- `logs/credit_operations.json.log` - Credit-specific operations
- `logs/ai_requests.json.log` - AI request logs
- `logs/provider_errors.json.log` - Provider error logs

**Format**: JSON with fields:
- timestamp (ISO 8601)
- level
- logger name
- message
- pathname
- line number
- Additional context fields

**Log Rotation**:
- Max file size: 10MB
- Backup count: 5-10 files
- Automatic rotation when size limit reached

### 4. Grafana Dashboard

**File**: `docs/grafana-dashboard.json`

**Panels**:
1. Credit Consumption Rate - Time series of credit usage
2. AI Request Rate - Request volume by brain mode and status
3. AI Request Success Rate - Success percentage with alert
4. Credit Check Latency (p95) - Performance monitoring with alert
5. AI Request Latency Percentiles - p50, p95 latencies
6. Model Failures by Type - Provider health monitoring
7. Total Tokens Consumed - Token usage tracking
8. Model Selection Distribution - Pie chart of model usage
9. Credit Operations by Tier - Usage by subscription tier
10. Monthly Credit Resets - Daily reset count

**Alerts Configured**:
- High Credit Check Latency (> 100ms)
- High AI Request Failure Rate (> 5%)
- High Provider Failure Rate (> 10%)

### 5. Health Check Endpoint

**URL**: `/api/v1/health/`

**Authentication**: None required (for monitoring systems)

**Response Format**:
```json
{
  "status": "healthy|degraded|unhealthy",
  "timestamp": "2024-01-15T14:32:10Z",
  "components": {
    "database": "healthy",
    "redis": "healthy",
    "cerebras_api": "healthy",
    "gemini_api": "healthy"
  },
  "metrics": {
    "ai_request_success_rate": 98.5,
    "credit_check_p95_latency_ms": 45
  }
}
```

**Health Status Logic**:
- `healthy` - All components operational
- `degraded` - Some non-critical components down (Redis, provider APIs)
- `unhealthy` - Critical components down (database)

## Setup Instructions

### 1. Install Dependencies

```bash
uv add prometheus-client python-json-logger
```

### 2. Create Log Directory

```bash
mkdir logs
```

### 3. Configure Prometheus

Add to `prometheus.yml`:

```yaml
scrape_configs:
  - job_name: 'neurotwin'
    scrape_interval: 15s
    static_configs:
      - targets: ['localhost:8000']
    metrics_path: '/metrics'
```

### 4. Import Grafana Dashboard

1. Open Grafana
2. Navigate to Dashboards → Import
3. Upload `docs/grafana-dashboard.json`
4. Select Prometheus data source
5. Configure alert notification channels
6. Save dashboard

### 5. Configure Alerts

See `docs/monitoring-alerts.md` for detailed alert configurations.

## Instrumentation Details

### CreditManager Instrumentation

**Metrics Added**:
- `credit_check_latency_seconds` - Tracks cache hit/miss performance
- `credit_checks_total` - Counts checks by tier and result
- `credit_deductions_total` - Counts deductions by tier, brain mode, operation
- `credit_deduction_latency_seconds` - Tracks deduction performance
- `credit_resets_total` - Counts monthly resets by tier

**Key Methods**:
- `get_balance()` - Measures latency, tracks cache hits
- `deduct_credits()` - Measures latency, tracks deductions
- `check_and_reset_if_needed()` - Tracks reset operations

### AIService Instrumentation

**Metrics Added**:
- `ai_requests_total` - Counts requests by brain mode, operation, model, status
- `ai_request_tokens_total` - Tracks token consumption
- `ai_request_latency_seconds` - Measures end-to-end request latency

**Key Methods**:
- `process_request()` - Measures full request lifecycle
- Error handlers - Track failed requests by error type

### ModelRouter Instrumentation

**Metrics Added**:
- `model_selections_total` - Counts model selections
- `model_routing_latency_seconds` - Measures routing decision time

**Key Methods**:
- `select_model()` - Tracks routing decisions and latency

### Provider Instrumentation

**Metrics Added**:
- `model_failures_total` - Tracks failures by model and error type

**Error Types Tracked**:
- `timeout` - Request timeouts
- `auth` - Authentication failures
- `rate_limit` - Rate limit errors
- `api_error` - General API errors
- `unexpected` - Unexpected errors

## Monitoring Best Practices

### 1. Alert Thresholds

- **Credit Check Latency**: Alert at 100ms (p95)
- **AI Request Failure Rate**: Alert at 5% over 5 minutes
- **Provider Failure Rate**: Alert at 10% over 5 minutes

### 2. Dashboard Review

- Review dashboard daily for trends
- Investigate spikes in failure rates
- Monitor latency percentiles for degradation

### 3. Log Analysis

- Use structured logs for debugging
- Search by request_id for request tracing
- Filter by user_id for user-specific issues

### 4. Health Check Monitoring

- Configure external monitoring to check `/api/v1/health/`
- Alert on `unhealthy` status
- Investigate `degraded` status

## Troubleshooting

### High Credit Check Latency

**Possible Causes**:
- Redis cache miss rate high
- Database query slow
- Network latency

**Actions**:
1. Check Redis connectivity and performance
2. Review database query plans
3. Check cache hit rate in metrics

### High AI Request Failure Rate

**Possible Causes**:
- Provider API issues
- Invalid API keys
- Rate limiting
- Network issues

**Actions**:
1. Check provider API status pages
2. Verify API keys in environment variables
3. Review error logs for specific error types
4. Check rate limit metrics

### Provider Failures

**Possible Causes**:
- API downtime
- Authentication issues
- Rate limits exceeded
- Network connectivity

**Actions**:
1. Check provider status page
2. Verify API key validity
3. Review rate limit configuration
4. Check fallback model usage

## Metrics Retention

- **Prometheus**: 15 days at 15s resolution
- **Logs**: 30 days with rotation
- **Database metrics**: 90 days (AIRequestLog)

## Additional Resources

- Prometheus documentation: https://prometheus.io/docs/
- Grafana documentation: https://grafana.com/docs/
- Alert configuration: `docs/monitoring-alerts.md`
- Dashboard JSON: `docs/grafana-dashboard.json`
