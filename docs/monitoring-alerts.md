# NeuroTwin Monitoring Alerts

This document defines alerting rules for the credit system and AI request monitoring.

Requirements: 23.4, 23.5, 23.6, 23.7, 23.8

## Alert Definitions

### 1. High Credit Check Latency

**Metric**: `credit_check_latency_seconds`  
**Condition**: p95 latency > 100ms over 5 minute window  
**Severity**: Warning  
**Action**: Investigate Redis cache performance, database query optimization

**PromQL Query**:
```promql
histogram_quantile(0.95, rate(credit_check_latency_seconds_bucket[5m])) > 0.1
```

**Alert Rule**:
```yaml
- alert: HighCreditCheckLatency
  expr: histogram_quantile(0.95, rate(credit_check_latency_seconds_bucket[5m])) > 0.1
  for: 5m
  labels:
    severity: warning
    component: credit_system
  annotations:
    summary: "Credit check p95 latency exceeds 100ms"
    description: "Credit balance checks are taking longer than expected. Check Redis and database performance."
```

### 2. High AI Request Failure Rate

**Metric**: `ai_requests_total`  
**Condition**: Failure rate > 5% over 5 minute window  
**Severity**: Critical  
**Action**: Check provider API status, review error logs, verify API keys

**PromQL Query**:
```promql
(
  rate(ai_requests_total{status="failed"}[5m]) 
  / 
  rate(ai_requests_total[5m])
) * 100 > 5
```

**Alert Rule**:
```yaml
- alert: HighAIRequestFailureRate
  expr: |
    (
      rate(ai_requests_total{status="failed"}[5m]) 
      / 
      rate(ai_requests_total[5m])
    ) * 100 > 5
  for: 5m
  labels:
    severity: critical
    component: ai_service
  annotations:
    summary: "AI request failure rate exceeds 5%"
    description: "More than 5% of AI requests are failing. Check provider APIs and error logs."
```

### 3. High Provider Failure Rate

**Metric**: `model_failures_total`  
**Condition**: Any provider failure rate > 10% over 5 minute window  
**Severity**: Critical  
**Action**: Check specific provider API status, verify API keys, review rate limits

**PromQL Query**:
```promql
(
  rate(model_failures_total[5m]) 
  / 
  rate(model_selections_total[5m])
) * 100 > 10
```

**Alert Rule**:
```yaml
- alert: HighProviderFailureRate
  expr: |
    (
      rate(model_failures_total[5m]) 
      / 
      rate(model_selections_total[5m])
    ) * 100 > 10
  for: 5m
  labels:
    severity: critical
    component: provider
  annotations:
    summary: "Provider {{$labels.model}} failure rate exceeds 10%"
    description: "Provider {{$labels.model}} is experiencing high failure rate. Check API status and logs."
```

### 4. Credit System Unavailable

**Metric**: `credit_checks_total`  
**Condition**: No credit checks in last 5 minutes (system down)  
**Severity**: Critical  
**Action**: Check application health, database connectivity, Redis availability

**PromQL Query**:
```promql
rate(credit_checks_total[5m]) == 0
```

**Alert Rule**:
```yaml
- alert: CreditSystemUnavailable
  expr: rate(credit_checks_total[5m]) == 0
  for: 5m
  labels:
    severity: critical
    component: credit_system
  annotations:
    summary: "Credit system appears to be down"
    description: "No credit checks detected in the last 5 minutes. System may be down."
```

### 5. High AI Request Latency

**Metric**: `ai_request_latency_seconds`  
**Condition**: p95 latency > 10 seconds over 5 minute window  
**Severity**: Warning  
**Action**: Check provider API performance, review model selection, optimize prompts

**PromQL Query**:
```promql
histogram_quantile(0.95, rate(ai_request_latency_seconds_bucket[5m])) > 10
```

**Alert Rule**:
```yaml
- alert: HighAIRequestLatency
  expr: histogram_quantile(0.95, rate(ai_request_latency_seconds_bucket[5m])) > 10
  for: 5m
  labels:
    severity: warning
    component: ai_service
  annotations:
    summary: "AI request p95 latency exceeds 10 seconds"
    description: "AI requests are taking longer than expected for {{$labels.brain_mode}} mode."
```

### 6. Cerebras API Errors

**Metric**: `model_failures_total{model="cerebras"}`  
**Condition**: Cerebras failures > 5 per minute  
**Severity**: Warning  
**Action**: Check Cerebras API status, verify API key, review rate limits

**PromQL Query**:
```promql
rate(model_failures_total{model="cerebras"}[1m]) > 5
```

**Alert Rule**:
```yaml
- alert: CerebrasAPIErrors
  expr: rate(model_failures_total{model="cerebras"}[1m]) > 5
  for: 2m
  labels:
    severity: warning
    component: cerebras_provider
  annotations:
    summary: "High Cerebras API error rate"
    description: "Cerebras provider is experiencing errors: {{$labels.error_type}}"
```

### 7. Credit Deduction Latency

**Metric**: `credit_deduction_latency_seconds`  
**Condition**: p95 latency > 50ms over 5 minute window  
**Severity**: Warning  
**Action**: Check database performance, review transaction locks, optimize queries

**PromQL Query**:
```promql
histogram_quantile(0.95, rate(credit_deduction_latency_seconds_bucket[5m])) > 0.05
```

**Alert Rule**:
```yaml
- alert: HighCreditDeductionLatency
  expr: histogram_quantile(0.95, rate(credit_deduction_latency_seconds_bucket[5m])) > 0.05
  for: 5m
  labels:
    severity: warning
    component: credit_system
  annotations:
    summary: "Credit deduction p95 latency exceeds 50ms"
    description: "Credit deductions are taking longer than expected. Check database locks and performance."
```

## Dashboard Panels

### Panel 1: Credit Consumption Rate
- **Type**: Time series graph
- **Metric**: `rate(credit_deductions_total[5m])`
- **Breakdown**: By user_tier, brain_mode, operation_type
- **Purpose**: Monitor credit usage patterns and detect anomalies

### Panel 2: AI Request Rate
- **Type**: Time series graph
- **Metric**: `rate(ai_requests_total[5m])`
- **Breakdown**: By brain_mode, status
- **Purpose**: Monitor request volume and success/failure distribution

### Panel 3: AI Request Success Rate
- **Type**: Time series graph with threshold
- **Metric**: Success rate percentage
- **Alert**: Triggers when < 95%
- **Purpose**: Monitor system reliability

### Panel 4: Credit Check Latency (p95)
- **Type**: Time series graph
- **Metric**: `histogram_quantile(0.95, credit_check_latency_seconds_bucket)`
- **Breakdown**: By cache_hit status
- **Alert**: Triggers when > 100ms
- **Purpose**: Monitor credit validation performance

### Panel 5: AI Request Latency Percentiles
- **Type**: Time series graph
- **Metrics**: p50, p95, p99 latencies
- **Breakdown**: By brain_mode, model_used
- **Purpose**: Monitor AI response times

### Panel 6: Model Failures by Type
- **Type**: Time series graph
- **Metric**: `rate(model_failures_total[5m])`
- **Breakdown**: By model, error_type
- **Alert**: Triggers when failure rate > 10%
- **Purpose**: Monitor provider health

### Panel 7: Total Tokens Consumed
- **Type**: Time series graph
- **Metric**: `rate(ai_request_tokens_total[5m])`
- **Breakdown**: By brain_mode, model_used
- **Purpose**: Monitor token usage and costs

### Panel 8: Model Selection Distribution
- **Type**: Pie chart
- **Metric**: `sum by (selected_model) (model_selections_total)`
- **Purpose**: Visualize model usage distribution

### Panel 9: Credit Operations by Tier
- **Type**: Time series graph
- **Metric**: `rate(credit_deductions_total[5m])`
- **Breakdown**: By user_tier
- **Purpose**: Monitor usage patterns across subscription tiers

### Panel 10: Monthly Credit Resets
- **Type**: Stat panel
- **Metric**: `sum(increase(credit_resets_total[24h]))`
- **Purpose**: Track daily reset operations

## Alert Notification Channels

Configure notification channels in Grafana:

1. **Slack**: For real-time alerts to engineering team
2. **PagerDuty**: For critical alerts requiring immediate response
3. **Email**: For warning-level alerts and daily summaries

## Runbook Links

Each alert should include runbook links for troubleshooting:

- Credit Check Latency → `/docs/runbooks/credit-performance.md`
- AI Request Failures → `/docs/runbooks/ai-service-failures.md`
- Provider Failures → `/docs/runbooks/provider-troubleshooting.md`

## Metrics Retention

- **Short-term**: 15 days at full resolution (15s intervals)
- **Medium-term**: 90 days at 5-minute resolution
- **Long-term**: 1 year at 1-hour resolution

## Dashboard Import

To import this dashboard into Grafana:

1. Navigate to Dashboards → Import
2. Upload `grafana-dashboard.json`
3. Select Prometheus data source
4. Configure alert notification channels
5. Save dashboard

## Prometheus Configuration

Add to `prometheus.yml`:

```yaml
scrape_configs:
  - job_name: 'neurotwin'
    scrape_interval: 15s
    static_configs:
      - targets: ['localhost:8000']
    metrics_path: '/metrics'
    # In production, use service discovery or dynamic targets
```
