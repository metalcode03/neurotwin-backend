"""
Custom throttling classes for NeuroTwin REST API.

Provides rate limiting for different endpoint types.
Requirements: 13.5, 33.5 - Rate limiting to prevent abuse and brute force attacks
"""

from rest_framework.throttling import AnonRateThrottle, UserRateThrottle


class AuthRateThrottle(AnonRateThrottle):
    """
    Stricter rate limiting for authentication endpoints.
    
    Prevents brute force attacks on login/registration.
    Requirements: 33.5
    """
    scope = 'auth'
    
    def throttle_failure(self):
        """Log rate limit violation when throttle fails"""
        from apps.automation.security import SecurityEventLogger, get_client_ip
        
        request = self.request
        
        SecurityEventLogger.log_rate_limit_violation(
            user_id=str(request.user.id) if hasattr(request, 'user') and request.user.is_authenticated else None,
            integration_id=None,
            limit_type='authentication',
            attempted_rate=self.num_requests,
            limit=self.num_requests,
            ip_address=get_client_ip(request)
        )
        
        return super().throttle_failure()


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
