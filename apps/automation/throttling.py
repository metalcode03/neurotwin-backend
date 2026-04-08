"""
Custom throttling classes for automation system.

Provides rate limiting for authentication and installation endpoints.
Requirements: 33.5, 14.1-14.7
"""

from rest_framework.throttling import UserRateThrottle, AnonRateThrottle
from .security import SecurityEventLogger, get_client_ip


class AuthenticationThrottle(AnonRateThrottle):
    """
    Rate limit for authentication endpoints to prevent brute force attacks.
    
    Requirements: 33.5
    """
    scope = 'auth'
    rate = '20/minute'  # 20 attempts per minute
    
    def throttle_failure(self):
        """Log rate limit violation when throttle fails"""
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


class InstallationThrottle(UserRateThrottle):
    """
    Rate limit for integration installation endpoints.
    
    Requirements: 14.1-14.7
    """
    scope = 'installation'
    rate = '10/hour'  # 10 installations per hour per user
    
    def throttle_failure(self):
        """Log rate limit violation when throttle fails"""
        request = self.request
        
        SecurityEventLogger.log_rate_limit_violation(
            user_id=str(request.user.id) if hasattr(request, 'user') and request.user.is_authenticated else None,
            integration_id=None,
            limit_type='installation',
            attempted_rate=self.num_requests,
            limit=self.num_requests,
            ip_address=get_client_ip(request)
        )
        
        return super().throttle_failure()


class MetaInstallationThrottle(AnonRateThrottle):
    """
    Global rate limit for Meta integration installations.
    
    Limits Meta installations to 5 per minute globally to comply with Meta's onboarding quotas.
    Requirements: 14.1-14.7
    """
    scope = 'meta_installation'
    rate = '5/minute'  # 5 Meta installations per minute globally
    
    def get_cache_key(self, request, view):
        """
        Use a global cache key for Meta installations.
        
        This ensures the rate limit applies across all users.
        """
        return 'throttle_meta_installation_global'
    
    def allow_request(self, request, view):
        """
        Check if request should be allowed.
        
        Exempt admin users from rate limit.
        """
        # Exempt admin users
        if hasattr(request, 'user') and request.user.is_authenticated and request.user.is_staff:
            return True
        
        return super().allow_request(request, view)
    
    def throttle_failure(self):
        """Log rate limit violation when throttle fails"""
        request = self.request
        
        SecurityEventLogger.log_rate_limit_violation(
            user_id=str(request.user.id) if hasattr(request, 'user') and request.user.is_authenticated else None,
            integration_id=None,
            limit_type='meta_installation_global',
            attempted_rate=self.num_requests,
            limit=5,  # 5 per minute
            ip_address=get_client_ip(request)
        )
        
        return super().throttle_failure()


class APIThrottle(UserRateThrottle):
    """
    General API rate limit.
    
    Requirements: 18.7
    """
    scope = 'api'
    rate = '1000/hour'


class APIBurstThrottle(UserRateThrottle):
    """
    Burst protection for API endpoints.
    
    Requirements: 18.7
    """
    scope = 'api_burst'
    rate = '100/minute'


# Aliases for backward compatibility
InstallationRateThrottle = InstallationThrottle
APIRateThrottle = APIThrottle
