"""
Custom throttling classes for NeuroTwin REST API.

Provides rate limiting for different endpoint types.
Requirements: 13.5 - Rate limiting to prevent abuse
"""

from rest_framework.throttling import AnonRateThrottle, UserRateThrottle


class AuthRateThrottle(AnonRateThrottle):
    """
    Stricter rate limiting for authentication endpoints.
    
    Prevents brute force attacks on login/registration.
    """
    scope = 'auth'


class BurstRateThrottle(UserRateThrottle):
    """
    Rate limiting for burst requests.
    
    Allows short bursts but limits sustained high-frequency requests.
    """
    scope = 'burst'


class SustainedRateThrottle(UserRateThrottle):
    """
    Rate limiting for sustained requests over longer periods.
    """
    scope = 'sustained'
