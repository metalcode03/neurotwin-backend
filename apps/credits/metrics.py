"""
Prometheus metrics for credit system monitoring.

This module defines metrics for tracking credit operations, AI requests,
and system performance. Metrics are exposed via /metrics endpoint.
"""

from prometheus_client import Counter, Histogram

# Credit operation metrics
credit_checks_total = Counter(
    'credit_checks_total',
    'Total number of credit balance checks',
    ['user_tier', 'result']
)

credit_deductions_total = Counter(
    'credit_deductions_total',
    'Total number of credit deductions',
    ['user_tier', 'brain_mode', 'operation_type']
)

credit_resets_total = Counter(
    'credit_resets_total',
    'Total number of monthly credit resets',
    ['user_tier']
)

# AI request metrics
ai_requests_total = Counter(
    'ai_requests_total',
    'Total number of AI requests',
    ['brain_mode', 'operation_type', 'model_used', 'status']
)

ai_request_tokens_total = Counter(
    'ai_request_tokens_total',
    'Total number of tokens consumed',
    ['brain_mode', 'model_used']
)

# Model routing metrics
model_selections_total = Counter(
    'model_selections_total',
    'Total number of model selections',
    ['brain_mode', 'operation_type', 'selected_model']
)

model_failures_total = Counter(
    'model_failures_total',
    'Total number of model failures',
    ['model', 'error_type']
)

# Latency metrics (histograms)
credit_check_latency_seconds = Histogram(
    'credit_check_latency_seconds',
    'Latency of credit balance checks in seconds',
    ['cache_hit'],
    buckets=(0.001, 0.005, 0.01, 0.025, 0.05, 0.1, 0.25, 0.5, 1.0)
)

ai_request_latency_seconds = Histogram(
    'ai_request_latency_seconds',
    'Latency of AI requests in seconds',
    ['brain_mode', 'model_used'],
    buckets=(0.1, 0.25, 0.5, 1.0, 2.5, 5.0, 10.0, 30.0, 60.0)
)

credit_deduction_latency_seconds = Histogram(
    'credit_deduction_latency_seconds',
    'Latency of credit deduction operations in seconds',
    buckets=(0.001, 0.005, 0.01, 0.025, 0.05, 0.1, 0.25, 0.5)
)

model_routing_latency_seconds = Histogram(
    'model_routing_latency_seconds',
    'Latency of model routing decisions in seconds',
    ['brain_mode'],
    buckets=(0.0001, 0.0005, 0.001, 0.005, 0.01, 0.025, 0.05)
)
