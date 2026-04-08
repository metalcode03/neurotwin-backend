"""
Custom throttle classes for credit-related endpoints.

Requirements: 22.5
"""

from rest_framework.throttling import UserRateThrottle


class CreditRateThrottle(UserRateThrottle):
    """
    Limits each authenticated user to 100 requests per hour
    across all credit endpoints (balance, estimate, usage, summary).

    Requirements: 22.5
    """
    scope = 'credits'
    rate = '100/hour'
