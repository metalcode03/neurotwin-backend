"""
Rate limiting throttle classes for installation and API endpoints.

Provides DRF throttle classes for controlling installation rate
and general API usage per user.

Requirements: 18.7
"""

from rest_framework.throttling import UserRateThrottle
from django.core.cache import cache

from apps.automation.utils.error_logging import InstallationErrorLogger


class InstallationRateThrottle(UserRateThrottle):
    """
    Rate throttle for installation endpoints.
    
    Limits users to 10 installation attempts per hour to prevent
    abuse and protect OAuth provider rate limits.
    
    Requirements: 18.7
    """
    
    # 10 installations per hour
    rate = '10/hour'
    scope = 'installation'
    
    def throttle_failure(self):
        """
        Called when throttle limit is exceeded.
        
        Logs the rate limit violation for monitoring.
        """
        # Get user from request
        if hasattr(self, 'request') and self.request.user.is_authenticated:
            user_id = str(self.request.user.id)
            
            # Get current count from cache
            cache_key = self.get_cache_key(self.request, self.request.user)
            history = cache.get(cache_key, [])
            current_count = len(history)
            
            # Log rate limit violation
            InstallationErrorLogger.log_rate_limit_violation(
                user_id=user_id,
                endpoint=self.request.path,
                limit_type='installation',
                current_count=current_count,
                max_allowed=10
            )
        
        return super().throttle_failure()


class APIRateThrottle(UserRateThrottle):
    """
    Rate throttle for general API endpoints.
    
    Limits users to 1000 API requests per hour to prevent abuse
    and ensure fair resource allocation.
    
    Requirements: 18.7
    """
    
    # 1000 requests per hour
    rate = '1000/hour'
    scope = 'api'
    
    def throttle_failure(self):
        """
        Called when throttle limit is exceeded.
        
        Logs the rate limit violation for monitoring.
        """
        # Get user from request
        if hasattr(self, 'request') and self.request.user.is_authenticated:
            user_id = str(self.request.user.id)
            
            # Get current count from cache
            cache_key = self.get_cache_key(self.request, self.request.user)
            history = cache.get(cache_key, [])
            current_count = len(history)
            
            # Log rate limit violation
            InstallationErrorLogger.log_rate_limit_violation(
                user_id=user_id,
                endpoint=self.request.path,
                limit_type='api',
                current_count=current_count,
                max_allowed=1000
            )
        
        return super().throttle_failure()


class BurstAPIRateThrottle(UserRateThrottle):
    """
    Burst rate throttle for API endpoints.
    
    Limits users to 100 requests per minute to prevent burst abuse
    while allowing normal usage patterns.
    """
    
    # 100 requests per minute
    rate = '100/min'
    scope = 'api_burst'
