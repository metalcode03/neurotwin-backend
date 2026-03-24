"""
Token refresh service for managing OAuth token lifecycle.

Handles automatic token refresh before expiration and marks
integrations as disconnected when refresh fails.

Requirements: 15.7
"""

import logging
from datetime import timedelta
from typing import Optional

from django.utils import timezone
from django.db import transaction

from apps.automation.models import Integration
from apps.automation.utils.oauth_client import OAuthClient, OAuthTokenRefreshError
from apps.automation.utils.encryption import TokenEncryption


logger = logging.getLogger(__name__)


class TokenRefreshService:
    """
    Service for refreshing OAuth tokens before expiration.
    
    Checks token expiration and attempts refresh before workflow execution.
    Marks integrations as disconnected if refresh fails.
    
    Requirements: 15.7
    - Check token_expires_at before workflow execution
    - Attempt refresh before marking integration as disconnected
    - Log refresh attempts and failures
    """
    
    # Refresh tokens when they expire within this window
    REFRESH_WINDOW_MINUTES = 5
    
    @staticmethod
    async def refresh_if_expired(integration: Integration) -> bool:
        """
        Check if token is expired and refresh if needed.
        
        Args:
            integration: Integration instance to check and refresh
            
        Returns:
            bool: True if token is valid (either not expired or successfully refreshed),
                  False if refresh failed
                  
        Requirements: 15.7
        """
        # Check if token needs refresh
        if not TokenRefreshService._needs_refresh(integration):
            logger.debug(
                f"Integration {integration.id} token is still valid, "
                f"expires at {integration.token_expires_at}"
            )
            return True
        
        logger.info(
            f"Integration {integration.id} token expired or expiring soon, "
            f"attempting refresh"
        )
        
        # Attempt refresh
        try:
            await TokenRefreshService._refresh_token(integration)
            return True
        except Exception as e:
            logger.error(
                f"Failed to refresh token for integration {integration.id}: {str(e)}"
            )
            
            # Mark integration as disconnected
            TokenRefreshService._mark_disconnected(integration, str(e))
            return False
    
    @staticmethod
    def _needs_refresh(integration: Integration) -> bool:
        """
        Check if integration token needs refresh.
        
        Args:
            integration: Integration instance
            
        Returns:
            bool: True if token is expired or expiring soon
        """
        # If no expiry time set, assume it needs refresh
        if not integration.token_expires_at:
            return True
        
        # Check if token is expired or expiring within refresh window
        refresh_threshold = timezone.now() + timedelta(
            minutes=TokenRefreshService.REFRESH_WINDOW_MINUTES
        )
        
        return integration.token_expires_at <= refresh_threshold
    
    @staticmethod
    async def _refresh_token(integration: Integration) -> None:
        """
        Refresh OAuth token for integration.
        
        Args:
            integration: Integration instance
            
        Raises:
            OAuthTokenRefreshError: If refresh fails
        """
        # Get refresh token
        refresh_token = integration.refresh_token
        
        if not refresh_token:
            raise OAuthTokenRefreshError(
                "No refresh token available for integration"
            )
        
        # Build OAuth client
        oauth_client = OAuthClient.from_integration_type(
            integration.integration_type,
            redirect_uri='https://placeholder.com/callback'  # Not used for refresh
        )
        
        # Attempt token refresh
        try:
            token_data = await oauth_client.refresh_token(refresh_token)
        except OAuthTokenRefreshError as e:
            logger.error(
                f"OAuth provider rejected token refresh for integration {integration.id}: {str(e)}"
            )
            raise
        
        # Update integration with new tokens
        with transaction.atomic():
            # Encrypt and store new access token
            access_token = token_data.get('access_token')
            if access_token:
                encrypted_token = TokenEncryption.encrypt(access_token)
                integration.oauth_token_encrypted = encrypted_token
            
            # Update refresh token if provider issued a new one
            new_refresh_token = token_data.get('refresh_token')
            if new_refresh_token:
                encrypted_refresh = TokenEncryption.encrypt(new_refresh_token)
                integration.refresh_token_encrypted = encrypted_refresh
            
            # Update expiration time
            expires_in = token_data.get('expires_in')
            if expires_in:
                integration.token_expires_at = timezone.now() + timedelta(
                    seconds=expires_in
                )
            
            integration.save(update_fields=[
                'oauth_token_encrypted',
                'refresh_token_encrypted',
                'token_expires_at',
                'updated_at'
            ])
        
        logger.info(
            f"Successfully refreshed token for integration {integration.id}, "
            f"new expiry: {integration.token_expires_at}"
        )
    
    @staticmethod
    def _mark_disconnected(integration: Integration, error_message: str) -> None:
        """
        Mark integration as disconnected after failed refresh.
        
        Args:
            integration: Integration instance
            error_message: Error message from refresh attempt
        """
        with transaction.atomic():
            integration.is_active = False
            integration.save(update_fields=['is_active', 'updated_at'])
        
        logger.warning(
            f"Marked integration {integration.id} as disconnected due to "
            f"token refresh failure: {error_message}"
        )
        
        # TODO: Notify user about disconnected integration
        # This could be done via email, push notification, or in-app notification
    
    @staticmethod
    async def refresh_integration_by_id(integration_id: str) -> bool:
        """
        Refresh integration token by ID.
        
        Convenience method for refreshing a specific integration.
        
        Args:
            integration_id: UUID of integration
            
        Returns:
            bool: True if refresh succeeded or not needed, False if failed
        """
        try:
            integration = Integration.objects.select_related(
                'integration_type'
            ).get(id=integration_id)
        except Integration.DoesNotExist:
            logger.error(f"Integration {integration_id} not found")
            return False
        
        return await TokenRefreshService.refresh_if_expired(integration)
    
    @staticmethod
    async def refresh_all_expiring_tokens(batch_size: int = 50) -> dict:
        """
        Refresh all tokens that are expiring soon.
        
        This method can be called periodically (e.g., via cron job or Celery task)
        to proactively refresh tokens before they expire.
        
        Args:
            batch_size: Number of integrations to process in one batch
            
        Returns:
            dict: Statistics about refresh operation
                - total: Total integrations checked
                - refreshed: Number successfully refreshed
                - failed: Number that failed refresh
                - skipped: Number that didn't need refresh
        """
        stats = {
            'total': 0,
            'refreshed': 0,
            'failed': 0,
            'skipped': 0
        }
        
        # Find integrations with tokens expiring soon
        refresh_threshold = timezone.now() + timedelta(
            minutes=TokenRefreshService.REFRESH_WINDOW_MINUTES
        )
        
        integrations = Integration.objects.select_related(
            'integration_type'
        ).filter(
            is_active=True,
            token_expires_at__lte=refresh_threshold
        )[:batch_size]
        
        logger.info(
            f"Found {integrations.count()} integrations with expiring tokens"
        )
        
        for integration in integrations:
            stats['total'] += 1
            
            try:
                if TokenRefreshService._needs_refresh(integration):
                    await TokenRefreshService._refresh_token(integration)
                    stats['refreshed'] += 1
                else:
                    stats['skipped'] += 1
            except Exception as e:
                logger.error(
                    f"Failed to refresh integration {integration.id}: {str(e)}"
                )
                stats['failed'] += 1
                TokenRefreshService._mark_disconnected(integration, str(e))
        
        logger.info(
            f"Token refresh batch complete: {stats['refreshed']} refreshed, "
            f"{stats['failed']} failed, {stats['skipped']} skipped"
        )
        
        return stats
