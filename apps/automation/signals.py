"""
Signal handlers for cache invalidation.

Automatically invalidates caches when models are saved or deleted.

Requirements: 17.4, 17.5
"""

from django.db.models.signals import post_save, post_delete
from django.dispatch import receiver

from .models import IntegrationTypeModel, Integration
from .cache import MarketplaceCache


@receiver(post_save, sender=IntegrationTypeModel)
def invalidate_integration_type_cache_on_save(sender, instance, created, **kwargs):
    """
    Invalidate integration type caches when IntegrationType is saved.
    
    Requirements: 17.1, 17.3, 17.4
    
    Args:
        sender: The model class (IntegrationTypeModel)
        instance: The actual instance being saved
        created: Boolean indicating if this is a new record
        **kwargs: Additional keyword arguments
    """
    # Invalidate active types listing cache
    MarketplaceCache.invalidate_active_types()
    
    # Invalidate OAuth config cache for this specific integration type
    MarketplaceCache.invalidate_oauth_config(str(instance.id))


@receiver(post_delete, sender=IntegrationTypeModel)
def invalidate_integration_type_cache_on_delete(sender, instance, **kwargs):
    """
    Invalidate integration type caches when IntegrationType is deleted.
    
    Requirements: 17.1, 17.3, 17.4
    
    Args:
        sender: The model class (IntegrationTypeModel)
        instance: The actual instance being deleted
        **kwargs: Additional keyword arguments
    """
    # Invalidate active types listing cache
    MarketplaceCache.invalidate_active_types()
    
    # Invalidate OAuth config cache for this specific integration type
    MarketplaceCache.invalidate_oauth_config(str(instance.id))


@receiver(post_save, sender=Integration)
def invalidate_user_installed_cache_on_save(sender, instance, created, **kwargs):
    """
    Invalidate user installation cache when Integration is saved.
    
    Requirements: 17.2, 17.4
    
    Args:
        sender: The model class (Integration)
        instance: The actual instance being saved
        created: Boolean indicating if this is a new record
        **kwargs: Additional keyword arguments
    """
    # Invalidate user's installed integrations cache
    MarketplaceCache.invalidate_user_installed(instance.user.id)


@receiver(post_delete, sender=Integration)
def invalidate_user_installed_cache_on_delete(sender, instance, **kwargs):
    """
    Invalidate user installation cache when Integration is deleted.
    
    Requirements: 17.2, 17.4
    
    Args:
        sender: The model class (Integration)
        instance: The actual instance being deleted
        **kwargs: Additional keyword arguments
    """
    # Invalidate user's installed integrations cache
    MarketplaceCache.invalidate_user_installed(instance.user.id)
