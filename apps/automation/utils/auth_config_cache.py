"""
AuthConfigCache utility for caching authentication configurations.

Provides caching for auth_config with 5-minute TTL to reduce database queries
and improve performance for authentication operations.

Requirements: 22.5
"""

import logging
from typing import Optional, Dict, Any

from django.core.cache import cache


logger = logging.getLogger(__name__)


class AuthConfigCache:
    """
    Cache utility for authentication configurations.
    
    Caches auth_config from IntegrationTypeModel to reduce database queries
    during authentication flows. Uses 5-minute TTL as specified in requirements.
    
    Requirements: 22.5
    """
    
    # Cache key pattern
    KEY_AUTH_CONFIG = 'auth_config:{integration_type_id}'
    
    # Cache TTL (in seconds)
    TTL_AUTH_CONFIG = 300  # 5 minutes
    
    @classmethod
    def _get_cache_key(cls, integration_type_id: str) -> str:
        """
        Get cache key for auth configuration.
        
        Args:
            integration_type_id: UUID of integration type
            
        Returns:
            Cache key string
        """
        return cls.KEY_AUTH_CONFIG.format(integration_type_id=integration_type_id)
    
    @classmethod
    def get_auth_config(cls, integration_type_id: str) -> Optional[Dict[str, Any]]:
        """
        Get cached authentication configuration.
        
        Retrieves auth_config from cache if available. Returns None if not cached,
        allowing caller to fetch from database and cache the result.
        
        Args:
            integration_type_id: UUID of integration type
            
        Returns:
            Authentication configuration dictionary or None if not cached
            
        Requirements: 22.5
        """
        cache_key = cls._get_cache_key(integration_type_id)
        auth_config = cache.get(cache_key)
        
        if auth_config is not None:
            logger.debug(
                f'Cache hit for auth_config: integration_type_id={integration_type_id}'
            )
        else:
            logger.debug(
                f'Cache miss for auth_config: integration_type_id={integration_type_id}'
            )
        
        return auth_config
    
    @classmethod
    def set_auth_config(
        cls,
        integration_type_id: str,
        auth_config: Dict[str, Any]
    ) -> None:
        """
        Cache authentication configuration.
        
        Stores auth_config in cache with 5-minute TTL. Should be called after
        fetching auth_config from database.
        
        Args:
            integration_type_id: UUID of integration type
            auth_config: Authentication configuration dictionary to cache
            
        Requirements: 22.5
        """
        cache_key = cls._get_cache_key(integration_type_id)
        
        cache.set(
            cache_key,
            auth_config,
            cls.TTL_AUTH_CONFIG
        )
        
        logger.debug(
            f'Cached auth_config: integration_type_id={integration_type_id}, '
            f'ttl={cls.TTL_AUTH_CONFIG}s'
        )
    
    @classmethod
    def invalidate(cls, integration_type_id: str) -> None:
        """
        Invalidate cached authentication configuration.
        
        Removes auth_config from cache. Should be called when IntegrationTypeModel
        auth_config is updated to ensure fresh data is fetched.
        
        Args:
            integration_type_id: UUID of integration type
            
        Requirements: 22.5
        """
        cache_key = cls._get_cache_key(integration_type_id)
        cache.delete(cache_key)
        
        logger.info(
            f'Invalidated auth_config cache: integration_type_id={integration_type_id}'
        )
    
    @classmethod
    def invalidate_all(cls) -> None:
        """
        Invalidate all cached authentication configurations.
        
        Note: This is a best-effort operation. Django's cache backend may not
        support pattern-based deletion, so this clears the entire cache.
        Use sparingly.
        """
        try:
            cache.clear()
            logger.info('Cleared all auth_config cache entries')
        except Exception as e:
            logger.error(f'Failed to clear auth_config cache: {str(e)}')
