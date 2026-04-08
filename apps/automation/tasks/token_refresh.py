"""
Background tasks for automatic token refresh.

Provides scheduled tasks to check and refresh expiring tokens
for Meta and OAuth integrations.

Requirements: 5.3, 6.5
"""

import logging
from datetime import timedelta
from typing import Dict, Any
from celery import shared_task
from django.utils import timezone
from django.db.models import Q
from apps.automation.models import Integration, AuthType


logger = logging.getLogger(__name__)


@shared_task(name='automation.refresh_expiring_tokens')
def refresh_expiring_tokens() -> Dict[str, Any]:
    """
    Background task to refresh tokens expiring within 24 hours.
    
    Queries integrations with tokens expiring soon and attempts to
    refresh them using the appropriate authentication strategy.
    
    This task should be scheduled to run periodically (e.g., every hour)
    using Celery Beat.
    
    Returns:
        Dictionary with refresh statistics
        
    Requirements: 5.3, 6.5
    
    Celery Beat Schedule Example:
    ```python
    CELERY_BEAT_SCHEDULE = {
        'refresh-expiring-tokens': {
            'task': 'automation.refresh_expiring_tokens',
            'schedule': crontab(minute=0),  # Every hour
        },
    }
    ```
    """
    from apps.automation.auth_strategies.factory import AuthStrategyFactory
    
    logger.info('Starting automatic token refresh task')
    
    # Find integrations with tokens expiring within 24 hours
    threshold = timezone.now() + timedelta(hours=24)
    
    expiring_integrations = Integration.objects.filter(
        status='active',
        token_expires_at__lte=threshold,
        token_expires_at__gt=timezone.now()
    ).select_related('integration_type', 'user')
    
    total_count = expiring_integrations.count()
    refreshed_count = 0
    failed_count = 0
    skipped_count = 0
    
    logger.info(f'Found {total_count} integrations with expiring tokens')
    
    for integration in expiring_integrations:
        try:
            # Skip API key integrations (they don't expire)
            if integration.integration_type.auth_type == AuthType.API_KEY:
                skipped_count += 1
                logger.debug(
                    f'Skipping API key integration {integration.id} (no expiration)'
                )
                continue
            
            # Skip OAuth integrations without refresh token
            if (integration.integration_type.auth_type == AuthType.OAUTH and 
                not integration.refresh_token_encrypted):
                skipped_count += 1
                logger.warning(
                    f'Skipping OAuth integration {integration.id} (no refresh token)'
                )
                continue
            
            logger.info(
                f'Attempting to refresh token for integration {integration.id} '
                f'(type: {integration.integration_type.auth_type}, '
                f'expires: {integration.token_expires_at})'
            )
            
            # Create strategy and refresh credentials
            strategy = AuthStrategyFactory.create_strategy(integration.integration_type)
            auth_result = strategy.refresh_credentials(integration)
            
            # Update integration with new token
            integration.access_token_encrypted = auth_result.access_token_encrypted
            if auth_result.refresh_token_encrypted:
                integration.refresh_token_encrypted = auth_result.refresh_token_encrypted
            integration.token_expires_at = auth_result.expires_at
            integration.last_successful_sync_at = timezone.now()
            
            # Reset health status on successful refresh
            if integration.consecutive_failures > 0:
                integration.consecutive_failures = 0
                integration.health_status = 'healthy'
            
            integration.save(update_fields=[
                'access_token_encrypted',
                'refresh_token_encrypted',
                'token_expires_at',
                'last_successful_sync_at',
                'consecutive_failures',
                'health_status',
                'updated_at'
            ])
            
            refreshed_count += 1
            logger.info(
                f'Successfully refreshed token for integration {integration.id} '
                f'(new expiry: {auth_result.expires_at})'
            )
            
        except Exception as e:
            failed_count += 1
            logger.error(
                f'Failed to refresh token for integration {integration.id}: {e}',
                exc_info=True
            )
            
            # Update integration health
            try:
                integration.consecutive_failures += 1
                previous_status = integration.health_status
                
                # Mark as degraded after 3 failures
                if integration.consecutive_failures >= 3:
                    integration.health_status = 'degraded'
                
                # Mark as disconnected after 10 failures
                if integration.consecutive_failures >= 10:
                    integration.health_status = 'disconnected'
                    integration.status = 'disconnected'
                    
                    # Notify user if status just changed to disconnected
                    if previous_status != 'disconnected':
                        from apps.automation.tasks.notification_tasks import notify_integration_disconnected
                        notify_integration_disconnected.delay(str(integration.id))
                
                integration.save(update_fields=[
                    'consecutive_failures',
                    'health_status',
                    'status',
                    'updated_at'
                ])
            except Exception as save_error:
                logger.error(
                    f'Failed to update integration {integration.id} health status: {save_error}'
                )
    
    result = {
        'total_checked': total_count,
        'refreshed': refreshed_count,
        'failed': failed_count,
        'skipped': skipped_count,
        'timestamp': timezone.now().isoformat()
    }
    
    logger.info(
        f'Token refresh task completed: {refreshed_count} refreshed, '
        f'{failed_count} failed, {skipped_count} skipped out of {total_count} total'
    )
    
    return result
