"""
Authentication strategy implementations for multi-auth integration support.

This package provides pluggable authentication strategies for OAuth 2.0,
Meta Business API, and API Key authentication.

Requirements: 4.1-8.7
"""

from .base import BaseAuthStrategy, AuthorizationResult, AuthenticationResult
from .oauth import OAuthStrategy
from .meta import MetaAuthStrategy
from .api_key import APIKeyStrategy
from .factory import AuthStrategyFactory

__all__ = [
    'BaseAuthStrategy',
    'AuthorizationResult',
    'AuthenticationResult',
    'OAuthStrategy',
    'MetaAuthStrategy',
    'APIKeyStrategy',
    'AuthStrategyFactory',
]
