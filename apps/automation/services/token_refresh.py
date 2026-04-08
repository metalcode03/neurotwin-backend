"""
Token refresh service for managing OAuth token lifecycle.

Handles automatic token refresh before expiration using appropriate
authentication strategies and marks integrations as disconnected when
refresh fails.

Requirements: 5.3, 6.5
"""

import logging
from datetime import timedelta
from typing import Optional

from django.utils import timezone
from django.db import transaction

from apps.automation.models import Integration, AuthType
from apps.automation.services.auth_strategy_factory import AuthStrategyFactory


logger = logging.getLogger(__name__)


class IntegrationRefreshService:
    """
    Service for refreshing integration credentials before expiration.
    
    Uses appropriate authentication strategy to refresh tokens and
    handles refresh failures gracefully.
    
    Requirements: 5.3, 6.5
    """
    
    # Refresh tokens when they expire within this window
    REFRESH_WINDOW_HOURS = 24
    
    def refresh_integration(self, integration: Integration) -> bool:
        """
        Refresh integration credentials using appropriate strategy.
        
        Args:
            integration: Integration instance to refresh
            
        Returns:
            bool: True if refresh succeeded, False if failed
            
        Requirements: 5.3, 6.5
        """
        try:
            # Get authentication strategy for this integration type
            strategy = AuthStrategyFactory.create_strategy(
                integration.integration_type
            )
            
            # Attempt credential refresh
            result = strategy.refresh_credentials(integration)
            
            # Update integration with new credentials
            with transaction.atomic():
                # Update access token
                if result.access_token:
                    integration.oauth_token = result.access_token
                
                # Update refresh token if provided
                if result.refresh_token:
                    integration.refresh_token = result.refresh_token
                
                # Update expiration time
                if result.expires_at:
                    integration.token_expires_at = result.expires_at
                
                # Update metadata if provided
                if result.metadata:
                    integration.user_config.update(result.metadata)
                
                # Reset health status
                integration.health_status = 'healthy'
                integration.consecutive_failures = 0
                integration.last_successful_sync_at = timezone.now()
                integration.status = 'active'
                
                integration.save(update_fields=[
                    'access_token_encrypted',
                    'refresh_token_encrypted',
                    'token_expires_at',
                    'user_config',
                    'health_status',
                    'consecutive_failures',
                    'last_successful_sync_at',
                    'status',
                    'updated_at'
                ])
            
            logger.info(
                f"Successfully refreshed integration {integration.id}",
                extra={
                    'integration_id': str(integration.id),
                    'integration_type': integration.integration_type.type,
                    'new_expiry': str(integration.token_expires_at)
                }
            )
            
            return True
            
        except Exception as e:
            logger.error(
                f"Failed to refresh integration {integration.id}: {str(e)}",
                extra={
                    'integration_id': str(integration.id),
                    'integration_type': integration.integration_type.type,
                    'error': str(e)
                }
            )
            
            # Handle refresh failure
            self._handle_refresh_failure(integration, str(e))
            return False
    
    def _handle_refresh_failure(
        self,
        integration: Integration,
        error_message: str
    ) -> None:
        """
        Handle integration refresh failure.
        
        Updates health status and marks as disconnected after
        multiple consecutive failures.
        
        Args:
            integration: Integration that failed to refresh
            error_message: Error message from refresh attempt
            
        Requirements: 5.3, 6.5, 23.1-23.5
        """
        with transaction.atomic():
            # Increment failure counter
            integration.consecutive_failures += 1
            previous_status = integration.health_status
            
            # Update health status based on failure count
            if integration.consecutive_failures >= 10:
                integration.health_status = 'disconnected'
                integration.status = 'disconnected'
                integration.is_active = False
                
                # Notify user if status just changed to disconnected
                if previous_status != 'disconnected':
                    from apps.automation.tasks.notification_tasks import notify_integration_disconnected
                    notify_integration_disconnected.delay(str(integration.id))
                    
            elif integration.consecutive_failures >= 3:
                integration.health_status = 'degraded'
            
            integration.save(update_fields=[
                'consecutive_failures',
                'health_status',
                'status',
                'is_active',
                'updated_at'
            ])
        
        logger.warning(
            f"Integration {integration.id} health status: {integration.health_status}",
            extra={
                'integration_id': str(integration.id),
                'consecutive_failures': integration.consecutive_failures,
                'health_status': integration.health_status,
                'error': error_message
            }
        )
    
    def needs_refresh(self, integration: Integration) -> bool:
        """
        Check if integration credentials need refresh.
        
        Args:
            integration: Integration instance
            
        Returns:
            bool: True if credentials are expired or expiring soon
            
        Requirements: 5.3
        """
        # API keys don't expire
        if integration.integration_type.auth_type == AuthType.API_KEY:
            return False
        
        # If no expiry time set, assume it needs refresh
        if not integration.token_expires_at:
            return True
        
        # Check if token is expired or expiring within refresh window
        refresh_threshold = timezone.now() + timedelta(
            hours=self.REFRESH_WINDOW_HOURS
        )
        
        return integration.token_expires_at <= refresh_threshold
    
    def refresh_expiring_integrations(self, batch_size: int = 50) -> dict:
        """
        Refresh all integrations with credentials expiring soon.
        
        This method can be called periodically (e.g., via Celery task)
        to proactively refresh credentials before they expire.
        
        Args:
            batch_size: Number of integrations to process in one batch
            
        Returns:
            dict: Statistics about refresh operation
                - total: Total integrations checked
                - refreshed: Number successfully refreshed
                - failed: Number that failed refresh
                - skipped: Number that didn't need refresh
                
        Requirements: 5.3, 6.5
        """
        stats = {
            'total': 0,
            'refreshed': 0,
            'failed': 0,
            'skipped': 0
        }
        
        # Find integrations with tokens expiring soon
        refresh_threshold = timezone.now() + timedelta(
            hours=self.REFRESH_WINDOW_HOURS
        )
        
        integrations = Integration.objects.select_related(
            'integration_type'
        ).filter(
            is_active=True,
            token_expires_at__lte=refresh_threshold,
            token_expires_at__gt=timezone.now()
        ).exclude(
            integration_type__auth_type=AuthType.API_KEY
        )[:batch_size]
        
        logger.info(
            f"Found {integrations.count()} integrations with expiring credentials"
        )
        
        for integration in integrations:
            stats['total'] += 1
            
            try:
                if self.needs_refresh(integration):
                    success = self.refresh_integration(integration)
                    if success:
                        stats['refreshed'] += 1
                    else:
                        stats['failed'] += 1
                else:
                    stats['skipped'] += 1
            except Exception as e:
                logger.error(
                    f"Failed to refresh integration {integration.id}: {str(e)}"
                )
                stats['failed'] += 1
                self._handle_refresh_failure(integration, str(e))
        
        logger.info(
            f"Credential refresh batch complete: {stats['refreshed']} refreshed, "
            f"{stats['failed']} failed, {stats['skipped']} skipped"
        )
        
        return stats
