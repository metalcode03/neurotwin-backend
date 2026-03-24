"""
Cache utilities for app marketplace.

Provides cache key management and invalidation utilities
for integration types, user installations, and OAuth configurations.

Requirements: 17.5
"""

from typing import Optional, Set, List
from django.core.cache import cache


class MarketplaceCache:
    """Cache management for marketplace data."""
    
    # Cache key patterns
    KEY_ACTIVE_TYPES = 'marketplace:active_types'
    KEY_USER_INSTALLED = 'user:{user_id}:installed_types'
    KEY_OAUTH_CONFIG = 'oauth_config:{integration_type_id}'
    KEY_CATEGORIES = 'marketplace:categories_with_counts'
    
    # Cache TTLs (in seconds)
    TTL_ACTIVE_TYPES = 300  # 5 minutes
    TTL_USER_INSTALLED = 60  # 1 minute
    TTL_OAUTH_CONFIG = 600  # 10 minutes
    TTL_CATEGORIES = 300  # 5 minutes
    
    @classmethod
    def get_active_types_key(cls) -> str:
        """Get cache key for active integration types."""
        return cls.KEY_ACTIVE_TYPES
    
    @classmethod
    def get_user_installed_key(cls, user_id: int) -> str:
        """Get cache key for user's installed integration types."""
        return cls.KEY_USER_INSTALLED.format(user_id=user_id)
    
    @classmethod
    def get_oauth_config_key(cls, integration_type_id: str) -> str:
        """Get cache key for OAuth configuration."""
        return cls.KEY_OAUTH_CONFIG.format(integration_type_id=integration_type_id)
    
    @classmethod
    def invalidate_active_types(cls):
        """
        Invalidate cache for active integration types.
        
        Should be called when IntegrationType records are created/updated/deleted.
        Requirements: 17.1
        """
        cache.delete(cls.get_active_types_key())
        cache.delete(cls.KEY_CATEGORIES)
    
    @classmethod
    def invalidate_user_installed(cls, user_id: int):
        """
        Invalidate cache for user's installed integrations.
        
        Should be called when Integration records are created/deleted.
        Requirements: 17.2
        
        Args:
            user_id: ID of the user whose cache should be invalidated
        """
        cache.delete(cls.get_user_installed_key(user_id))
    
    @classmethod
    def invalidate_oauth_config(cls, integration_type_id: str):
        """
        Invalidate cache for OAuth configuration.
        
        Should be called when IntegrationType OAuth config is updated.
        Requirements: 17.3
        
        Args:
            integration_type_id: UUID of the integration type
        """
        cache.delete(cls.get_oauth_config_key(integration_type_id))
    
    @classmethod
    def cache_active_types(cls, integration_type_ids: List[str]):
        """
        Cache active integration type IDs.
        
        Requirements: 17.1
        
        Args:
            integration_type_ids: List of integration type UUIDs
        """
        cache.set(
            cls.get_active_types_key(),
            integration_type_ids,
            cls.TTL_ACTIVE_TYPES
        )
    
    @classmethod
    def get_active_types(cls) -> Optional[List[str]]:
        """
        Get cached active integration type IDs.
        
        Requirements: 17.1
        
        Returns:
            List of integration type UUIDs or None if not cached
        """
        return cache.get(cls.get_active_types_key())
    
    @classmethod
    def cache_user_installed(cls, user_id: int, integration_type_ids: Set[str]):
        """
        Cache user's installed integration type IDs.
        
        Requirements: 17.2
        
        Args:
            user_id: User ID
            integration_type_ids: Set of integration type UUIDs
        """
        cache.set(
            cls.get_user_installed_key(user_id),
            integration_type_ids,
            cls.TTL_USER_INSTALLED
        )
    
    @classmethod
    def get_user_installed(cls, user_id: int) -> Optional[Set[str]]:
        """
        Get cached user's installed integration type IDs.
        
        Requirements: 17.2
        
        Returns:
            Set of integration type UUIDs or None if not cached
        """
        return cache.get(cls.get_user_installed_key(user_id))
    
    @classmethod
    def cache_oauth_config(cls, integration_type_id: str, oauth_config: dict):
        """
        Cache OAuth configuration for an integration type.
        
        Requirements: 17.3
        
        Args:
            integration_type_id: UUID of the integration type
            oauth_config: OAuth configuration dictionary
        """
        cache.set(
            cls.get_oauth_config_key(integration_type_id),
            oauth_config,
            cls.TTL_OAUTH_CONFIG
        )
    
    @classmethod
    def get_oauth_config(cls, integration_type_id: str) -> Optional[dict]:
        """
        Get cached OAuth configuration.
        
        Requirements: 17.3
        
        Returns:
            OAuth configuration dictionary or None if not cached
        """
        return cache.get(cls.get_oauth_config_key(integration_type_id))
