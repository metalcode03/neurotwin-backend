"""
Installation service for integration installation workflows.

Manages the two-phase installation process:
- Phase 1: Create session and prepare OAuth
- Phase 2: Complete OAuth flow and create Integration

Requirements: 4.1-4.11, 5.4-5.6, 11.1-11.7, 18.4-18.7
"""

import secrets
import logging
from datetime import timedelta
from typing import Optional, Dict, Any
from urllib.parse import urlencode

import httpx
from django.conf import settings
from django.core.cache import cache
from django.db import transaction
from django.utils import timezone

from apps.automation.models import (
    InstallationSession,
    InstallationStatus,
    Integration,
    IntegrationTypeModel,
)
from apps.automation.cache import MarketplaceCache
from apps.automation.utils.encryption import TokenEncryption
from apps.automation.utils.oauth_client import OAuthClient, OAuthTokenExchangeError
from apps.automation.utils.oauth_state import OAuthStateManager
from apps.automation.utils.recovery import InstallationRecovery
from apps.automation.utils.error_logging import InstallationErrorLogger


logger = logging.getLogger(__name__)


class InstallationRateLimitExceeded(Exception):
    """Raised when user exceeds installation rate limit."""
    pass


class OAuthStateValidationError(Exception):
    """Raised when OAuth state validation fails."""
    pass


class InstallationService:
    """
    Service for managing integration installation workflows.
    
    Handles two-phase installation:
    1. Downloading phase: Create session, generate OAuth state
    2. OAuth setup phase: Exchange code for tokens, create Integration
    
    Requirements: 4.1-4.11, 5.4-5.6, 11.1-11.7, 18.4-18.7
    """
    
    # Rate limiting: 10 installations per hour per user
    RATE_LIMIT_MAX = 10
    RATE_LIMIT_WINDOW = 3600  # 1 hour in seconds
    
    @staticmethod
    def _get_rate_limit_key(user_id: str) -> str:
        """Get cache key for rate limiting."""
        return f'installation_rate_limit:{user_id}'
    
    @staticmethod
    def _check_rate_limit(user) -> bool:
        """
        Check if user has exceeded installation rate limit.
        
        Args:
            user: User instance
            
        Returns:
            bool: True if within limit, False if exceeded
            
        Requirements: 18.7
        """
        cache_key = InstallationService._get_rate_limit_key(str(user.id))
        
        # Get current count from cache
        current_count = cache.get(cache_key, 0)
        
        if current_count >= InstallationService.RATE_LIMIT_MAX:
            logger.warning(
                f'Rate limit exceeded for user {user.id}: '
                f'{current_count} installations in last hour'
            )
            return False
        
        # Increment counter with expiry
        cache.set(
            cache_key,
            current_count + 1,
            InstallationService.RATE_LIMIT_WINDOW
        )
        
        return True
    
    @staticmethod
    def _get_oauth_config_cached(integration_type: IntegrationTypeModel) -> Dict[str, Any]:
        """
        Get OAuth configuration with caching.
        
        Args:
            integration_type: IntegrationType instance
            
        Returns:
            dict: OAuth configuration
            
        Requirements: 17.3
        """
        # Try to get from cache
        cached_config = MarketplaceCache.get_oauth_config(str(integration_type.id))
        
        if cached_config is not None:
            return cached_config
        
        # Get from database
        oauth_config = integration_type.oauth_config
        
        # Cache the result
        MarketplaceCache.cache_oauth_config(str(integration_type.id), oauth_config)
        
        return oauth_config
    
    @staticmethod
    def start_installation(
        user,
        integration_type_id: str
    ) -> InstallationSession:
        """
        Start Phase 1 of installation: Create session.
        
        Creates an InstallationSession with status="downloading" and
        generates a cryptographically random OAuth state for CSRF protection.
        
        Args:
            user: User instance
            integration_type_id: UUID of IntegrationType to install
            
        Returns:
            InstallationSession: Created session
            
        Raises:
            InstallationRateLimitExceeded: If user exceeded rate limit
            IntegrationTypeModel.DoesNotExist: If integration type not found
            
        Requirements: 4.1-4.2, 11.1, 18.7
        """
        # Check rate limit
        if not InstallationService._check_rate_limit(user):
            raise InstallationRateLimitExceeded(
                'Installation rate limit exceeded. '
                'Maximum 10 installations per hour.'
            )
        
        # Get integration type
        integration_type = IntegrationTypeModel.objects.get(
            id=integration_type_id,
            is_active=True
        )
        
        # Create session with generated OAuth state
        session = OAuthStateManager.create_session_with_state(
            user=user,
            integration_type=integration_type
        )
        
        logger.info(
            f'Started installation session {session.id} for user {user.id}, '
            f'integration type {integration_type.name}'
        )
        
        return session

    @staticmethod
    def get_oauth_authorization_url(session_id: str) -> str:
        """
        Get OAuth authorization URL for Phase 2.
        
        Builds the OAuth authorization URL with client_id, scopes, state,
        and redirect_uri. Updates session status to "oauth_setup".
        
        Args:
            session_id: UUID of InstallationSession
            
        Returns:
            str: OAuth authorization URL
            
        Raises:
            InstallationSession.DoesNotExist: If session not found
            ValueError: If OAuth config is invalid or URLs are not HTTPS
            
        Requirements: 4.4, 2.3, 11.3
        """
        # Get session
        session = InstallationSession.objects.select_related(
            'integration_type'
        ).get(id=session_id)
        
        integration_type = session.integration_type
        
        # Get redirect URI from settings
        redirect_uri = getattr(
            settings,
            'OAUTH_REDIRECT_URI',
            f'{settings.FRONTEND_URL}/oauth/callback'
        )
        
        # Build OAuth client using utility
        oauth_client = OAuthClient.from_integration_type(
            integration_type=integration_type,
            redirect_uri=redirect_uri
        )
        
        # Build authorization URL with state
        oauth_url = oauth_client.build_authorization_url(
            state=session.oauth_state,
            session_id=str(session.id)  # Include session_id in URL for callback
        )
        
        # Update session status to oauth_setup
        session.status = InstallationStatus.OAUTH_SETUP
        session.progress = 50  # Halfway through installation
        session.save(update_fields=['status', 'progress', 'updated_at'])
        
        logger.info(
            f'Generated OAuth URL for session {session.id}, '
            f'integration type {integration_type.name}'
        )
        
        return oauth_url

    @staticmethod
    async def complete_oauth_flow(
        session_id: str,
        authorization_code: str,
        state: str
    ) -> Integration:
        """
        Complete OAuth flow and create Integration (async).
        
        Validates OAuth state, exchanges authorization code for tokens,
        encrypts and stores tokens, creates Integration record, and
        triggers automation template instantiation.
        
        Args:
            session_id: UUID of InstallationSession
            authorization_code: OAuth authorization code from callback
            state: OAuth state parameter for validation
            
        Returns:
            Integration: Created integration instance
            
        Raises:
            OAuthStateValidationError: If state validation fails
            InstallationSession.DoesNotExist: If session not found
            OAuthTokenExchangeError: If token exchange fails
            
        Requirements: 4.5-4.9, 18.4
        """
        # Get session with related data
        session = await InstallationSession.objects.select_related(
            'integration_type', 'user'
        ).aget(id=session_id)
        
        # Validate OAuth state using OAuthStateManager (CSRF protection - Requirement 18.4)
        is_valid, error_message = OAuthStateManager.validate_state(session, state)
        
        if not is_valid:
            logger.error(
                f'OAuth state validation failed for session {session.id}: {error_message}'
            )
            
            session.status = InstallationStatus.FAILED
            session.error_message = error_message
            await session.asave(update_fields=['status', 'error_message', 'updated_at'])
            
            raise OAuthStateValidationError(error_message)
        
        integration_type = session.integration_type
        
        # Get redirect URI
        redirect_uri = getattr(
            settings,
            'OAUTH_REDIRECT_URI',
            f'{settings.FRONTEND_URL}/oauth/callback'
        )
        
        # Build OAuth client using utility
        oauth_client = OAuthClient.from_integration_type(
            integration_type=integration_type,
            redirect_uri=redirect_uri
        )
        
        # Exchange authorization code for tokens using OAuthClient
        try:
            token_data = await oauth_client.exchange_code_for_tokens(
                authorization_code=authorization_code
            )
                
        except OAuthTokenExchangeError as e:
            logger.error(
                f'OAuth token exchange failed for session {session.id}: {str(e)}'
            )
            
            session.status = InstallationStatus.FAILED
            session.error_message = f'OAuth token exchange failed: {str(e)}'
            await session.asave(update_fields=['status', 'error_message', 'updated_at'])
            
            raise
        
        # Extract tokens
        access_token = token_data.get('access_token')
        refresh_token = token_data.get('refresh_token')
        expires_in = token_data.get('expires_in')
        
        if not access_token:
            raise ValueError('OAuth response missing access_token')
        
        # Calculate token expiration
        token_expires_at = None
        if expires_in:
            token_expires_at = timezone.now() + timedelta(seconds=expires_in)
        
        # Create Integration record with encrypted tokens (atomic transaction)
        async with transaction.atomic():
            # Create integration
            integration = Integration(
                user=session.user,
                integration_type=integration_type,
                scopes=integration_type.oauth_scopes,
                permissions=integration_type.default_permissions.copy(),
                token_expires_at=token_expires_at,
                is_active=True
            )
            
            # Encrypt and set tokens
            integration.oauth_token = access_token
            if refresh_token:
                integration.refresh_token = refresh_token
            
            await integration.asave()
            
            # Update session to completed
            session.status = InstallationStatus.COMPLETED
            session.progress = 100
            session.completed_at = timezone.now()
            await session.asave(
                update_fields=['status', 'progress', 'completed_at', 'updated_at']
            )
        
        logger.info(
            f'Completed OAuth flow for session {session.id}, '
            f'created integration {integration.id}'
        )
        
        # Trigger template instantiation (async, non-blocking)
        # Import here to avoid circular dependency
        from .automation_template import AutomationTemplateService
        
        try:
            await AutomationTemplateService.instantiate_templates_for_user(
                session.user,
                integration
            )
        except Exception as e:
            # Log error but don't fail the installation
            logger.error(
                f'Failed to instantiate templates for integration {integration.id}: {str(e)}'
            )
        
        return integration

    @staticmethod
    def get_installation_progress(session_id: str) -> Dict[str, Any]:
        """
        Get current installation progress.
        
        Returns session status and progress for polling endpoint.
        
        Args:
            session_id: UUID of InstallationSession
            
        Returns:
            dict: Progress information with keys:
                - phase: Current installation phase (downloading, oauth_setup, completed, failed)
                - progress: Progress percentage (0-100)
                - message: Human-readable status message
                - error_message: Error details if failed (optional)
                - can_retry: Whether retry is allowed (optional)
                
        Raises:
            InstallationSession.DoesNotExist: If session not found
            
        Requirements: 11.2-11.5
        """
        session = InstallationSession.objects.select_related(
            'integration_type'
        ).get(id=session_id)
        
        # Build status message based on phase
        status_messages = {
            InstallationStatus.DOWNLOADING: f'Downloading {session.integration_type.name}...',
            InstallationStatus.OAUTH_SETUP: f'Setting up {session.integration_type.name}...',
            InstallationStatus.COMPLETED: f'{session.integration_type.name} installed successfully!',
            InstallationStatus.FAILED: f'Installation failed: {session.error_message}',
        }
        
        result = {
            'phase': session.status,
            'progress': session.progress,
            'message': status_messages.get(session.status, 'Processing...'),
        }
        
        # Add error details if failed
        if session.status == InstallationStatus.FAILED:
            result['error_message'] = session.error_message
            result['can_retry'] = session.can_retry
            result['retry_count'] = session.retry_count
        
        # Add completion timestamp if complete
        if session.completed_at:
            result['completed_at'] = session.completed_at.isoformat()
        
        return result

    @staticmethod
    def uninstall_integration(
        user,
        integration_id: str,
        force: bool = False
    ) -> Dict[str, Any]:
        """
        Uninstall an integration.
        
        Checks for dependent workflows, disables them, deletes the Integration
        record (which cascades to encrypted tokens), and logs the uninstallation.
        
        Args:
            user: User instance
            integration_id: UUID of Integration to uninstall
            force: If True, skip confirmation check for dependent workflows
            
        Returns:
            dict: Uninstallation result with keys:
                - success: Whether uninstallation succeeded
                - disabled_workflows: Number of workflows disabled
                - requires_confirmation: Whether user confirmation is needed
                - dependent_workflows: List of workflow names that depend on this integration
                
        Raises:
            Integration.DoesNotExist: If integration not found
            ValueError: If confirmation required but force=False
            
        Requirements: 5.4-5.6, 18.5-18.6
        """
        from apps.automation.models import Workflow
        
        # Get integration with related data
        integration = Integration.objects.select_related(
            'integration_type'
        ).get(
            id=integration_id,
            user=user
        )
        
        integration_type_id = str(integration.integration_type.id)
        
        # Find workflows that depend on this integration
        dependent_workflows = Workflow.objects.filter(
            user=user,
            is_active=True
        )
        
        # Filter workflows that use this integration type in their steps
        workflows_to_disable = []
        workflow_names = []
        
        for workflow in dependent_workflows:
            integration_types_used = workflow.get_integration_types_used()
            if integration_type_id in integration_types_used:
                workflows_to_disable.append(workflow)
                workflow_names.append(workflow.name)
        
        # Check if confirmation is required (Requirement 5.6)
        requires_confirmation = len(workflows_to_disable) > 0
        
        if requires_confirmation and not force:
            logger.info(
                f'Uninstallation of integration {integration_id} requires confirmation: '
                f'{len(workflows_to_disable)} dependent workflows'
            )
            
            return {
                'success': False,
                'requires_confirmation': True,
                'dependent_workflows': workflow_names,
                'disabled_workflows': 0,
            }
        
        # Proceed with uninstallation
        disabled_count = 0
        
        with transaction.atomic():
            # Disable dependent workflows (Requirement 5.5)
            for workflow in workflows_to_disable:
                workflow.is_active = False
                workflow.save(update_fields=['is_active', 'updated_at'])
                disabled_count += 1
            
            # Revoke OAuth tokens with provider (best effort)
            try:
                InstallationService._revoke_oauth_tokens(integration)
            except Exception as e:
                # Log error but don't fail uninstallation
                logger.error(
                    f'Failed to revoke OAuth tokens for integration {integration_id}: {str(e)}'
                )
            
            # Delete Integration record (cascades to encrypted tokens)
            integration.delete()
        
        # Log uninstallation in audit log (Requirement 18.6)
        logger.info(
            f'Uninstalled integration {integration_id} for user {user.id}, '
            f'integration type {integration.integration_type.name}, '
            f'disabled {disabled_count} workflows'
        )
        
        # TODO: Add to audit log table when implemented
        # AuditLog.objects.create(
        #     user=user,
        #     event_type='integration_uninstalled',
        #     resource_type='integration',
        #     resource_id=integration_id,
        #     details={
        #         'integration_type': integration.integration_type.name,
        #         'disabled_workflows': disabled_count,
        #     }
        # )
        
        return {
            'success': True,
            'disabled_workflows': disabled_count,
            'requires_confirmation': False,
            'dependent_workflows': workflow_names,
        }
    
    @staticmethod
    def _revoke_oauth_tokens(integration: Integration) -> None:
        """
        Revoke OAuth tokens with the provider.
        
        Makes a best-effort attempt to revoke tokens. Failures are logged
        but don't prevent uninstallation.
        
        Args:
            integration: Integration instance with tokens to revoke
            
        Requirements: 18.5
        """
        oauth_config = integration.integration_type.oauth_config
        revoke_url = oauth_config.get('revoke_url')
        
        if not revoke_url:
            # Not all providers support token revocation
            logger.debug(
                f'No revoke_url configured for {integration.integration_type.name}, '
                'skipping token revocation'
            )
            return
        
        # Get access token
        access_token = integration.oauth_token
        if not access_token:
            logger.debug('No access token to revoke')
            return
        
        # Attempt to revoke token
        try:
            import httpx
            
            with httpx.Client() as client:
                response = client.post(
                    revoke_url,
                    data={'token': access_token},
                    headers={'Content-Type': 'application/x-www-form-urlencoded'},
                    timeout=10.0
                )
                
                if response.status_code in [200, 204]:
                    logger.info(
                        f'Successfully revoked OAuth token for integration {integration.id}'
                    )
                else:
                    logger.warning(
                        f'Token revocation returned status {response.status_code} '
                        f'for integration {integration.id}'
                    )
                    
        except Exception as e:
            logger.error(
                f'Failed to revoke OAuth token for integration {integration.id}: {str(e)}'
            )
            # Don't raise - this is best effort

    @staticmethod
    def handle_oauth_callback_error(
        session_id: str,
        error_type: str,
        error_description: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        Handle OAuth callback error (e.g., user cancelled authorization).
        
        Uses InstallationRecovery to handle the error, update session,
        and determine retry eligibility.
        
        Args:
            session_id: UUID of InstallationSession
            error_type: OAuth error type from callback (e.g., 'access_denied')
            error_description: Optional error description from provider
            
        Returns:
            dict: Recovery information from InstallationRecovery
            
        Requirements: 15.1-15.5
        """
        # Get session
        session = InstallationSession.objects.select_related(
            'integration_type', 'user'
        ).get(id=session_id)
        
        # Build error details
        error_details = error_description or f'OAuth error: {error_type}'
        
        # Use recovery utility to handle error
        recovery_info = InstallationRecovery.handle_oauth_failure(
            session=session,
            error_type=error_type,
            error_details=error_details
        )
        
        # Log with structured logger
        InstallationErrorLogger.log_oauth_error(
            user_id=str(session.user.id),
            integration_type_id=str(session.integration_type.id),
            integration_type_name=session.integration_type.name,
            error_type=error_type,
            error_details=error_details,
            session_id=str(session.id),
            retry_count=session.retry_count
        )
        
        return recovery_info
    
    @staticmethod
    def retry_installation(session_id: str) -> InstallationSession:
        """
        Retry a failed installation.
        
        Validates retry eligibility and resets session state for retry.
        
        Args:
            session_id: UUID of InstallationSession to retry
            
        Returns:
            InstallationSession: Reset session ready for retry
            
        Raises:
            ValueError: If retry not allowed
            
        Requirements: 15.2-15.3
        """
        # Get session
        session = InstallationSession.objects.select_related(
            'integration_type', 'user'
        ).get(id=session_id)
        
        # Use recovery utility to reset session
        reset_session = InstallationRecovery.reset_session_for_retry(session)
        
        logger.info(
            f'Retrying installation for session {session.id}, '
            f'attempt {session.retry_count + 1}'
        )
        
        return reset_session
