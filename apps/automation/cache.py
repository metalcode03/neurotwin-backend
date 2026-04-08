"""
Caching utilities for automation models.

Requirements: 31.6 - Cache Integration and IntegrationTypeModel with 5-minute TTL
"""

from typing import Optional, Any
from django.core.cache import cache
from django.db.models import Model
import logging

logger = logging.getLogger(__name__)

# Cache TTL: 5 minutes (Requirement 31.6)
CACHE_TTL = 300


class ModelCache:
    """
    Generic model caching utility with automatic invalidation.
    
    Requirements: 31.6
    """
    
    @staticmethod
    def get_cache_key(model_class: type[Model], pk: Any) -> str:
        """
        Generate cache key for a model instance.
        
        Args:
            model_class: Model class
            pk: Primary key value
            
        Returns:
            Cache key string
        """
        model_name = model_class._meta.label_lower.replace('.', '_')
        return f"model_cache:{model_name}:{pk}"
    
    @staticmethod
    def get_list_cache_key(model_class: type[Model], filter_key: str = "all") -> str:
        """
        Generate cache key for a list of model instances.
        
        Args:
            model_class: Model class
            filter_key: Filter identifier (e.g., "active", "user_123")
            
        Returns:
            Cache key string
        """
        model_name = model_class._meta.label_lower.replace('.', '_')
        return f"model_cache:{model_name}:list:{filter_key}"
    
    @classmethod
    def get(cls, model_class: type[Model], pk: Any) -> Optional[Model]:
        """
        Get model instance from cache.
        
        Args:
            model_class: Model class
            pk: Primary key value
            
        Returns:
            Model instance or None if not cached
        """
        cache_key = cls.get_cache_key(model_class, pk)
        instance = cache.get(cache_key)
        
        if instance:
            logger.debug(f"Cache hit: {cache_key}")
        else:
            logger.debug(f"Cache miss: {cache_key}")
        
        return instance
    
    @classmethod
    def set(cls, instance: Model, ttl: int = CACHE_TTL) -> None:
        """
        Store model instance in cache.
        
        Args:
            instance: Model instance to cache
            ttl: Time to live in seconds (default: 5 minutes)
        """
        cache_key = cls.get_cache_key(instance.__class__, instance.pk)
        cache.set(cache_key, instance, ttl)
        logger.debug(f"Cached: {cache_key} (TTL: {ttl}s)")
    
    @classmethod
    def delete(cls, model_class: type[Model], pk: Any) -> None:
        """
        Remove model instance from cache.
        
        Args:
            model_class: Model class
            pk: Primary key value
        """
        cache_key = cls.get_cache_key(model_class, pk)
        cache.delete(cache_key)
        logger.debug(f"Cache invalidated: {cache_key}")
    
    @classmethod
    def get_or_fetch(cls, model_class: type[Model], pk: Any, ttl: int = CACHE_TTL) -> Optional[Model]:
        """
        Get model instance from cache or fetch from database.
        
        Args:
            model_class: Model class
            pk: Primary key value
            ttl: Time to live in seconds (default: 5 minutes)
            
        Returns:
            Model instance or None if not found
        """
        # Try cache first
        instance = cls.get(model_class, pk)
        
        if instance is None:
            # Fetch from database
            try:
                instance = model_class.objects.get(pk=pk)
                cls.set(instance, ttl)
            except model_class.DoesNotExist:
                logger.debug(f"Model not found: {model_class.__name__} pk={pk}")
                return None
        
        return instance
    
    @classmethod
    def invalidate_list(cls, model_class: type[Model], filter_key: str = "all") -> None:
        """
        Invalidate cached list of model instances.
        
        Args:
            model_class: Model class
            filter_key: Filter identifier
        """
        cache_key = cls.get_list_cache_key(model_class, filter_key)
        cache.delete(cache_key)
        logger.debug(f"List cache invalidated: {cache_key}")


class IntegrationCache:
    """
    Specialized caching for Integration model.
    
    Requirements: 31.6 - Cache with 5-minute TTL, invalidate on updates
    """
    
    @staticmethod
    def get_by_id(integration_id: int) -> Optional[Any]:
        """
        Get Integration by ID from cache or database.
        
        Args:
            integration_id: Integration primary key
            
        Returns:
            Integration instance or None
        """
        from apps.automation.models import Integration
        return ModelCache.get_or_fetch(Integration, integration_id)
    
    @staticmethod
    def get_by_user(user_id: int) -> Optional[list]:
        """
        Get user's integrations from cache.
        
        Args:
            user_id: User primary key
            
        Returns:
            List of Integration instances or None if not cached
        """
        from apps.automation.models import Integration
        cache_key = ModelCache.get_list_cache_key(Integration, f"user_{user_id}")
        return cache.get(cache_key)
    
    @staticmethod
    def set_user_integrations(user_id: int, integrations: list, ttl: int = CACHE_TTL) -> None:
        """
        Cache user's integrations.
        
        Args:
            user_id: User primary key
            integrations: List of Integration instances
            ttl: Time to live in seconds
        """
        from apps.automation.models import Integration
        cache_key = ModelCache.get_list_cache_key(Integration, f"user_{user_id}")
        cache.set(cache_key, integrations, ttl)
        logger.debug(f"Cached user integrations: user_id={user_id}")
    
    @staticmethod
    def invalidate(integration_id: int, user_id: Optional[int] = None) -> None:
        """
        Invalidate Integration cache.
        
        Args:
            integration_id: Integration primary key
            user_id: Optional user ID to invalidate user's integration list
        """
        from apps.automation.models import Integration
        
        # Invalidate single instance cache
        ModelCache.delete(Integration, integration_id)
        
        # Invalidate user's integration list if provided
        if user_id:
            ModelCache.invalidate_list(Integration, f"user_{user_id}")
        
        logger.info(f"Integration cache invalidated: id={integration_id}, user_id={user_id}")


class IntegrationTypeCache:
    """
    Specialized caching for IntegrationTypeModel.
    
    Requirements: 31.6 - Cache with 5-minute TTL, invalidate on updates
    """
    
    @staticmethod
    def get_by_id(integration_type_id: int) -> Optional[Any]:
        """
        Get IntegrationTypeModel by ID from cache or database.
        
        Args:
            integration_type_id: IntegrationTypeModel primary key
            
        Returns:
            IntegrationTypeModel instance or None
        """
        from apps.automation.models import IntegrationTypeModel
        return ModelCache.get_or_fetch(IntegrationTypeModel, integration_type_id)
    
    @staticmethod
    def get_all_active() -> Optional[list]:
        """
        Get all active integration types from cache.
        
        Returns:
            List of IntegrationTypeModel instances or None if not cached
        """
        from apps.automation.models import IntegrationTypeModel
        cache_key = ModelCache.get_list_cache_key(IntegrationTypeModel, "active")
        return cache.get(cache_key)
    
    @staticmethod
    def set_all_active(integration_types: list, ttl: int = CACHE_TTL) -> None:
        """
        Cache all active integration types.
        
        Args:
            integration_types: List of IntegrationTypeModel instances
            ttl: Time to live in seconds
        """
        from apps.automation.models import IntegrationTypeModel
        cache_key = ModelCache.get_list_cache_key(IntegrationTypeModel, "active")
        cache.set(cache_key, integration_types, ttl)
        logger.debug("Cached active integration types")
    
    @staticmethod
    def invalidate(integration_type_id: int) -> None:
        """
        Invalidate IntegrationTypeModel cache.
        
        Args:
            integration_type_id: IntegrationTypeModel primary key
        """
        from apps.automation.models import IntegrationTypeModel
        
        # Invalidate single instance cache
        ModelCache.delete(IntegrationTypeModel, integration_type_id)
        
        # Invalidate active list cache
        ModelCache.invalidate_list(IntegrationTypeModel, "active")
        
        logger.info(f"IntegrationTypeModel cache invalidated: id={integration_type_id}")
    
    @staticmethod
    def invalidate_all() -> None:
        """Invalidate all IntegrationTypeModel caches."""
        from apps.automation.models import IntegrationTypeModel
        ModelCache.invalidate_list(IntegrationTypeModel, "active")
        logger.info("All IntegrationTypeModel caches invalidated")


def invalidate_integration_cache(sender, instance, **kwargs):
    """
    Signal handler to invalidate Integration cache on save/delete.
    
    Usage:
        from django.db.models.signals import post_save, post_delete
        post_save.connect(invalidate_integration_cache, sender=Integration)
        post_delete.connect(invalidate_integration_cache, sender=Integration)
    """
    IntegrationCache.invalidate(
        integration_id=instance.pk,
        user_id=instance.user_id if hasattr(instance, 'user_id') else None
    )


def invalidate_integration_type_cache(sender, instance, **kwargs):
    """
    Signal handler to invalidate IntegrationTypeModel cache on save/delete.
    
    Usage:
        from django.db.models.signals import post_save, post_delete
        post_save.connect(invalidate_integration_type_cache, sender=IntegrationTypeModel)
        post_delete.connect(invalidate_integration_type_cache, sender=IntegrationTypeModel)
    """
    IntegrationTypeCache.invalidate(integration_type_id=instance.pk)



class MarketplaceCache:
    """
    Specialized caching for marketplace operations.
    
    Requirements: 13.1-13.6, 17.1-17.5
    """
    
    # Cache keys
    KEY_CATEGORIES = "marketplace:categories"
    KEY_ACTIVE_TYPES = "marketplace:active_types"
    KEY_USER_INSTALLED_PREFIX = "marketplace:user_installed:"
    
    # Cache TTLs
    TTL_CATEGORIES = 300  # 5 minutes
    TTL_ACTIVE_TYPES = 300  # 5 minutes
    TTL_USER_INSTALLED = 300  # 5 minutes
    
    @classmethod
    def get_user_installed(cls, user_id: int) -> Optional[set]:
        """
        Get user's installed integration type IDs from cache.
        
        Args:
            user_id: User primary key
            
        Returns:
            Set of integration type IDs (as strings) or None if not cached
        """
        cache_key = f"{cls.KEY_USER_INSTALLED_PREFIX}{user_id}"
        return cache.get(cache_key)
    
    @classmethod
    def cache_user_installed(cls, user_id: int, integration_type_ids: set, ttl: int = TTL_USER_INSTALLED) -> None:
        """
        Cache user's installed integration type IDs.
        
        Args:
            user_id: User primary key
            integration_type_ids: Set of integration type IDs (as strings)
            ttl: Time to live in seconds
        """
        cache_key = f"{cls.KEY_USER_INSTALLED_PREFIX}{user_id}"
        cache.set(cache_key, integration_type_ids, ttl)
        logger.debug(f"Cached user installed integrations: user_id={user_id}")
    
    @classmethod
    def invalidate_user_installed(cls, user_id: int) -> None:
        """
        Invalidate user's installed integrations cache.
        
        Args:
            user_id: User primary key
        """
        cache_key = f"{cls.KEY_USER_INSTALLED_PREFIX}{user_id}"
        cache.delete(cache_key)
        logger.debug(f"User installed cache invalidated: user_id={user_id}")
    
    @classmethod
    def invalidate_active_types(cls) -> None:
        """Invalidate active integration types cache."""
        cache.delete(cls.KEY_ACTIVE_TYPES)
        cache.delete(cls.KEY_CATEGORIES)
        logger.debug("Active integration types cache invalidated")
