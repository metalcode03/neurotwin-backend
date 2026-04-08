"""
Automation utilities package.
"""

from .encryption import TokenEncryption
from .oauth_client import OAuthClient, OAuthError, OAuthTokenExchangeError, OAuthTokenRefreshError
from .oauth_state import OAuthStateManager
from .rate_limiter import RateLimiter
from .meta_installation_rate_limiter import MetaInstallationRateLimiter
from .circuit_breaker import CircuitBreaker, CircuitState, CircuitBreakerOpenException
from .circuit_breaker_registry import CircuitBreakerRegistry

__all__ = [
    'TokenEncryption',
    'OAuthClient',
    'OAuthError',
    'OAuthTokenExchangeError',
    'OAuthTokenRefreshError',
    'OAuthStateManager',
    'RateLimiter',
    'MetaInstallationRateLimiter',
    'CircuitBreaker',
    'CircuitState',
    'CircuitBreakerOpenException',
    'CircuitBreakerRegistry',
]
