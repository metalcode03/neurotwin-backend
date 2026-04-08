"""
Constants for credit-based AI architecture.

Defines credit allocations, tier requirements, base costs, and multipliers.
Requirements: 1.3-1.6, 3.2-3.6, 3.8-3.10
"""

from typing import Dict, List


# Credit allocations by subscription tier
# Requirements: 1.3-1.6
TIER_CREDIT_ALLOCATIONS: Dict[str, int] = {
    'FREE': 50,
    'PRO': 2000,
    'TWIN_PLUS': 5000,
    'EXECUTIVE': 10000,
}


# Brain mode tier requirements
# Maps brain mode to list of allowed subscription tiers
# Requirements: 5.6, 5.7, 5.10
BRAIN_MODE_TIER_REQUIREMENTS: Dict[str, List[str]] = {
    'brain': ['FREE', 'PRO', 'TWIN_PLUS', 'EXECUTIVE'],
    'brain_pro': ['PRO', 'TWIN_PLUS', 'EXECUTIVE'],
    'brain_gen': ['EXECUTIVE'],
}


# Base credit costs by operation type
# Requirements: 3.2-3.6
BASE_COSTS: Dict[str, int] = {
    'simple_response': 1,
    'long_response': 3,
    'summarization': 2,
    'complex_reasoning': 5,
    'automation': 8,
}


# Brain mode multipliers for credit calculation
# Requirements: 3.8-3.10
BRAIN_MULTIPLIERS: Dict[str, float] = {
    'brain': 1.0,
    'brain_pro': 1.5,
    'brain_gen': 2.0,
}


# Model routing rules by brain mode and operation type
# Requirements: 6.2-6.6
ROUTING_RULES: Dict[str, Dict[str, str]] = {
    'brain': {
        'simple_response': 'cerebras',
        'long_response': 'gemini-2.5-flash',
        'summarization': 'mistral',
        'complex_reasoning': 'gemini-2.5-pro',
        'automation': 'gemini-2.5-pro',
    },
    'brain_pro': {
        'simple_response': 'gemini-3-pro',
        'long_response': 'gemini-3-pro',
        'summarization': 'gemini-3-pro',
        'complex_reasoning': 'gemini-3-pro',
        'automation': 'gemini-3-pro',
    },
    'brain_gen': {
        'simple_response': 'gemini-3.1-pro',
        'long_response': 'gemini-3.1-pro',
        'summarization': 'gemini-3.1-pro',
        'complex_reasoning': 'gemini-3.1-pro',
        'automation': 'gemini-3.1-pro',
    },
}


# Model fallback order
# Requirements: 6.7
MODEL_FALLBACKS: Dict[str, List[str]] = {
    'cerebras': ['gemini-2.5-flash', 'gemini-2.5-pro'],
    'gemini-2.5-flash': ['gemini-2.5-pro', 'cerebras'],
    'gemini-2.5-pro': ['gemini-2.5-flash', 'gemini-3-pro'],
    'gemini-3-pro': ['gemini-2.5-pro', 'gemini-3.1-pro'],
    'gemini-3.1-pro': ['gemini-3-pro', 'gemini-2.5-pro'],
    'mistral': ['gemini-2.5-flash', 'cerebras'],
}


# Cache TTL values (in seconds)
# Requirements: 20.1, 20.6
CREDIT_BALANCE_CACHE_TTL: int = 60  # 1 minute
ROUTING_CONFIG_CACHE_TTL: int = 300  # 5 minutes


# Performance thresholds
# Requirements: 23.4, 23.5
CREDIT_CHECK_LATENCY_THRESHOLD_MS: int = 50
AI_REQUEST_LATENCY_THRESHOLD_MS: int = 5000
CREDIT_CHECK_P95_ALERT_THRESHOLD_MS: int = 100
AI_REQUEST_FAILURE_RATE_THRESHOLD: float = 0.05  # 5%
PROVIDER_FAILURE_RATE_THRESHOLD: float = 0.10  # 10%


# Rate limiting
# Requirements: 22.5
CREDIT_ENDPOINT_RATE_LIMIT: int = 100  # requests per hour per user


# Retry configuration
# Requirements: 7.6
MAX_RETRIES: int = 3
RETRY_BACKOFF_SECONDS: List[int] = [1, 2, 4]


# Circuit breaker configuration
# Requirements: 23.6
CIRCUIT_BREAKER_FAILURE_THRESHOLD: int = 5
CIRCUIT_BREAKER_TIMEOUT_SECONDS: int = 60
