"""
Signal handlers for automation app.

Requirements: 31.6 - Invalidate cache on updates
"""

from django.db.models.signals import post_save, post_delete
from django.dispatch import receiver
import logging

logger = logging.getLogger('automation.events')


# Import will be done when models are created
# from apps.automation.models import Integration, IntegrationTypeModel
# from apps.automation.cache import invalidate_integration_cache, invalidate_integration_type_cache


def register_cache_invalidation_signals():
    """
    Register signal handlers for cache invalidation.
    
    This function should be called in apps.py ready() method.
    Requirements: 31.6
    """
    try:
        from apps.automation.models import Integration, IntegrationTypeModel
        from apps.automation.cache import (
            invalidate_integration_cache,
            invalidate_integration_type_cache
        )
        
        # Register Integration cache invalidation
        post_save.connect(invalidate_integration_cache, sender=Integration)
        post_delete.connect(invalidate_integration_cache, sender=Integration)
        
        # Register IntegrationTypeModel cache invalidation
        post_save.connect(invalidate_integration_type_cache, sender=IntegrationTypeModel)
        post_delete.connect(invalidate_integration_type_cache, sender=IntegrationTypeModel)
        
        logger.info("Cache invalidation signals registered successfully")
    except ImportError as e:
        logger.warning(f"Could not register cache invalidation signals: {e}")


# Example signal handlers for other automation events

@receiver(post_save, sender='automation.WebhookEvent')
def log_webhook_event(sender, instance, created, **kwargs):
    """
    Log webhook event creation.
    
    Requirements: 30.2 - Log all webhook events
    """
    if created:
        logger.info(
            "Webhook event created",
            extra={
                'event_id': instance.pk,
                'integration_type': instance.integration_type_id,
                'status': instance.status,
                'timestamp': instance.created_at.isoformat(),
            }
        )


@receiver(post_save, sender='automation.Message')
def log_message_status_change(sender, instance, created, **kwargs):
    """
    Log message status changes.
    
    Requirements: 30.3 - Log all message sends
    """
    if not created:
        logger.info(
            "Message status updated",
            extra={
                'message_id': instance.pk,
                'integration_id': instance.conversation.integration_id if hasattr(instance, 'conversation') else None,
                'status': instance.status,
                'retry_count': instance.retry_count if hasattr(instance, 'retry_count') else 0,
                'timestamp': instance.updated_at.isoformat(),
            }
        )
