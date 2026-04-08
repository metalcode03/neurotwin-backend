"""
Installation service for integration installation workflows.

Manages the two-phase installation process:
- Phase 1: Create session and prepare authentication
- Phase 2: Complete authentication flow and create Integration

Supports multiple authentication strategies: OAuth, Meta, API Key.

Requirements: 4.1-4.11, 5.4-5.6, 8.1-8.8, 11.1-11.7, 18.4-18.7
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
from apps.automation.exceptions import MetaInstallationRateLimitExceeded
from apps.automation.cache import MarketplaceCache
from apps.automation.services.auth_strategy_factory import AuthStrategyFactory
from apps.automation.utils.encryption import TokenEncryption
from apps.automation.utils.oauth_client import OAuthClient, OAuthTokenExchangeError
from apps.automation.utils.oauth_state import OAuthStateManager
from apps.automation.utils.recovery import InstallationRecovery
from apps.automation.utils.error_logging import InstallationErrorLogger
from apps.automation.utils.auth_config_cache import AuthConfigCache
from apps.automation.utils.meta_installation_rate_limiter import MetaInstallationRateLimiter
from apps.automation.selectors import (
    IntegrationTypeSelector,
    InstallationSessionSelector,
)


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
    
    Handles two-phase installation for all authentication types:
    1. Downloading phase: Create session, generate state
    2. Authentication phase: Complete auth flow, create Integration
    
    Supports OAuth, Meta, and API Key authentication strategies.
    
    Requirements: 4.1-4.11, 5.4-5.6, 8.1-8.8, 11.1-11.7, 18.4-18.7
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
        
        Uses AuthConfigCache for 5-minute TTL caching to reduce database queries.
        
        Args:
            integration_type: IntegrationType instance
            
        Returns:
            dict: OAuth configuration
            
        Requirements: 17.3, 22.5
        """
        # Try to get from AuthConfigCache first
        cached_config = AuthConfigCache.get_auth_config(str(integration_type.id))
        
        if cached_config is not None:
            return cached_config
        
        # Get from database
        auth_config = integration_type.auth_config
        
        # Cache the result with 5-minute TTL
        AuthConfigCache.set_auth_config(str(integration_type.id), auth_config)
        
        return auth_config
    
    @staticmethod
    def start_installation(
        user,
        integration_type_id: str
    ) -> Dict[str, Any]:
        """
        Start Phase 1 of installation: Create session and get authorization URL.
        
        Creates an InstallationSession and uses AuthStrategyFactory to get
        the appropriate authorization URL (or None for API key flow).
        
        Args:
            user: User instance
            integration_type_id: UUID of IntegrationType to install
            
        Returns:
            dict: Installation start information with keys:
                - session_id: UUID of created session
                - authorization_url: URL for redirect (None for API key)
                - requires_redirect: Whether redirect is needed
                - requires_api_key: Whether API key input is needed
                - auth_type: Authentication type identifier
            
        Raises:
            InstallationRateLimitExceeded: If user exceeded rate limit
            MetaInstallationRateLimitExceeded: If Meta installation rate limit exceeded
            IntegrationTypeModel.DoesNotExist: If integration type not found
            ValidationError: If auth configuration is invalid
            
        Requirements: 4.1-4.2, 8.1, 8.2, 8.3, 11.1, 14.1-14.7, 18.7
        """
        # Check rate limit
        if not InstallationService._check_rate_limit(user):
            raise InstallationRateLimitExceeded(
                'Installation rate limit exceeded. '
                'Maximum 10 installations per hour.'
            )
        
        # Get integration type using optimized selector
        integration_type = IntegrationTypeSelector.get_type_by_id(integration_type_id)
        
        if not integration_type:
            raise IntegrationTypeModel.DoesNotExist(
                f'Integration type {integration_type_id} not found or inactive'
            )
        
        # Check Meta installation rate limit (Requirements 14.1-14.7)
        if integration_type.auth_type == 'meta':
            meta_rate_limiter = MetaInstallationRateLimiter()
            is_admin = user.is_staff or user.is_superuser
            
            allowed, wait_seconds = meta_rate_limiter.check_installation_limit(
                user_id=str(user.id),
                is_admin=is_admin
            )
            
            if not allowed:
                logger.warning(
                    f'Meta installation rate limit exceeded for user {user.id}. '
                    f'Wait {wait_seconds} seconds.'
                )
                raise MetaInstallationRateLimitExceeded(
                    message=f'High demand for WhatsApp connections. '
                            f'Please try again in {wait_seconds} seconds.',
                    retry_after=wait_seconds
                )
        
        # Create session with generated state
        session = OAuthStateManager.create_session_with_state(
            user=user,
            integration_type=integration_type
        )
        
        # Create strategy using factory (Requirement 8.1)
        strategy = AuthStrategyFactory.create_strategy(integration_type)
        
        # Get redirect URI from settings
        redirect_uri = InstallationService._get_callback_url(integration_type)
        
        # Get authorization URL (None for API key) (Requirement 8.2, 8.3)
        authorization_url = strategy.get_authorization_url(
            state=session.oauth_state,
            redirect_uri=redirect_uri
        )
        
        # Update session status based on auth type
        if authorization_url:
            session.status = InstallationStatus.OAUTH_SETUP
            session.progress = 50
        else:
            # API key flow - no redirect needed
            session.progress = 30
        session.save(update_fields=['status', 'progress', 'updated_at'])
        
        logger.info(
            f'Started installation session {session.id} for user {user.id}, '
            f'integration type {integration_type.name}, auth_type={integration_type.auth_type}'
        )
        
        return {
            'session_id': str(session.id),
            'authorization_url': authorization_url,
            'requires_redirect': authorization_url is not None,
            'requires_api_key': authorization_url is None,
            'auth_type': integration_type.auth_type
        }
    
    @staticmethod
    def _get_callback_url(integration_type: IntegrationTypeModel) -> str:
        """
        Get callback URL based on auth type.
        
        Args:
            integration_type: IntegrationTypeModel instance
            
        Returns:
            Callback URL string
        """
        # Use Meta-specific callback for Meta auth
        if integration_type.auth_type == 'meta':
            return getattr(
                settings,
                'META_CALLBACK_URI',
                f'{settings.FRONTEND_URL}/oauth/callback/meta'
            )
        
        # Default OAuth callback
        return getattr(
            settings,
            'OAUTH_REDIRECT_URI',
            f'{settings.FRONTEND_URL}/oauth/callback'
        )

    @staticmethod
    def get_authorization_url(session_id: str) -> str:
        """
        Get authorization URL for Phase 2 (renamed from get_oauth_authorization_url).
        
        Builds the authorization URL using the appropriate strategy.
        Updates session status to "oauth_setup".
        
        Args:
            session_id: UUID of InstallationSession
            
        Returns:
            str: Authorization URL
            
        Raises:
            InstallationSession.DoesNotExist: If session not found
            ValueError: If auth config is invalid or URLs are not HTTPS
            
        Requirements: 4.4, 2.3, 8.2, 11.3
        """
        # Get session using optimized selector
        session = InstallationSessionSelector.get_session_by_id(session_id)
        
        if not session:
            raise InstallationSession.DoesNotExist(
                f'Installation session {session_id} not found'
            )
        
        integration_type = session.integration_type
        
        # Create strategy using factory
        strategy = AuthStrategyFactory.create_strategy(integration_type)
        
        # Get redirect URI
        redirect_uri = InstallationService._get_callback_url(integration_type)
        
        # Get authorization URL
        authorization_url = strategy.get_authorization_url(
            state=session.oauth_state,
            redirect_uri=redirect_uri
        )
        
        if not authorization_url:
            raise ValueError(
                f"No authorization URL for auth_type={integration_type.auth_type}. "
                "Use API key completion endpoint instead."
            )
        
        # Update session status to oauth_setup
        session.status = InstallationStatus.OAUTH_SETUP
        session.progress = 50  # Halfway through installation
        session.save(update_fields=['status', 'progress', 'updated_at'])
        
        logger.info(
            f'Generated authorization URL for session {session.id}, '
            f'integration type {integration_type.name}, auth_type={integration_type.auth_type}'
        )
        
        return authorization_url
    
    @staticmethod
    def get_oauth_authorization_url(session_id: str) -> str:
        """
        Backward compatibility wrapper for get_authorization_url.
        
        DEPRECATED: Use get_authorization_url instead.
        
        Args:
            session_id: UUID of InstallationSession
            
        Returns:
            str: Authorization URL
        """
        logger.warning(
            'get_oauth_authorization_url is deprecated. Use get_authorization_url instead.'
        )
        return InstallationService.get_authorization_url(session_id)

    @staticmethod
    async def complete_authentication_flow(
        session_id: str,
        authorization_code: str,
        state: str,
        **kwargs
    ) -> Integration:
        """
        Complete authentication flow and create Integration (async).
        
        Renamed from complete_oauth_flow. Uses AuthStrategyFactory to handle
        all authentication types (OAuth, Meta, API Key).
        
        Validates state, completes authentication using strategy,
        encrypts and stores tokens/credentials, creates Integration record,
        and stores auth-type-specific data (e.g., Meta fields).
        
        Args:
            session_id: UUID of InstallationSession
            authorization_code: Authorization code from callback (or API key for API key auth)
            state: State parameter for validation
            **kwargs: Additional auth-type-specific parameters
            
        Returns:
            Integration: Created integration instance
            
        Raises:
            OAuthStateValidationError: If state validation fails
            InstallationSession.DoesNotExist: If session not found
            ValidationError: If authentication fails
            
        Requirements: 4.5-4.9, 8.4, 8.5, 8.6, 8.7, 18.4
        """
        # Get session with related data using optimized selector
        session = InstallationSessionSelector.get_session_by_id(session_id)
        
        if not session:
            raise InstallationSession.DoesNotExist(
                f'Installation session {session_id} not found'
            )
        
        # Validate state using OAuthStateManager (CSRF protection - Requirement 18.4)
        is_valid, error_message = OAuthStateManager.validate_state(session, state)
        
        if not is_valid:
            logger.error(
                f'State validation failed for session {session.id}: {error_message}'
            )
            
            session.status = InstallationStatus.FAILED
            session.error_message = error_message
            await session.asave(update_fields=['status', 'error_message', 'updated_at'])
            
            raise OAuthStateValidationError(error_message)
        
        integration_type = session.integration_type
        
        # Create strategy using factory (Requirement 8.4)
        strategy = AuthStrategyFactory.create_strategy(integration_type)
        
        # Get redirect URI
        redirect_uri = InstallationService._get_callback_url(integration_type)
        
        # Complete authentication using strategy (Requirement 8.5)
        try:
            auth_data = await strategy.complete_authentication(
                authorization_code=authorization_code,
                state=state,
                redirect_uri=redirect_uri,
                **kwargs
            )
                
        except Exception as e:
            logger.error(
                f'Authentication failed for session {session.id}: {str(e)}'
            )
            
            session.status = InstallationStatus.FAILED
            session.error_message = f'Authentication failed: {str(e)}'
            await session.asave(update_fields=['status', 'error_message', 'updated_at'])
            
            raise
        
        # Extract common fields
        access_token_encrypted = auth_data.get('access_token_encrypted')
        refresh_token_encrypted = auth_data.get('refresh_token_encrypted')
        expires_at = auth_data.get('expires_at')
        scopes = auth_data.get('scopes', [])
        
        # Extract Meta-specific fields (Requirement 8.7)
        meta_business_id = auth_data.get('meta_business_id')
        meta_waba_id = auth_data.get('meta_waba_id')
        meta_phone_number_id = auth_data.get('meta_phone_number_id')
        meta_config = auth_data.get('meta_config', {})
        
        if not access_token_encrypted:
            raise ValueError('Authentication response missing access_token_encrypted')
        
        # Create Integration record with encrypted tokens (atomic transaction)
        async with transaction.atomic():
            # Create integration
            integration = Integration(
                user=session.user,
                integration_type=integration_type,
                oauth_token_encrypted=access_token_encrypted,
                refresh_token_encrypted=refresh_token_encrypted,
                scopes=scopes,
                permissions=integration_type.default_permissions.copy(),
                token_expires_at=expires_at,
                is_active=True
            )
            
            # Store Meta-specific fields if present (Requirement 8.7)
            if meta_business_id:
                integration.meta_business_id = meta_business_id
            if meta_waba_id:
                integration.meta_waba_id = meta_waba_id
            if meta_phone_number_id:
                integration.meta_phone_number_id = meta_phone_number_id
            if meta_config:
                integration.meta_config = meta_config
            
            await integration.asave()
            
            # Update session to completed
            session.status = InstallationStatus.COMPLETED
            session.progress = 100
            session.completed_at = timezone.now()
            await session.asave(
                update_fields=['status', 'progress', 'completed_at', 'updated_at']
            )
        
        logger.info(
            f'Completed authentication flow for session {session.id}, '
            f'created integration {integration.id}, auth_type={integration_type.auth_type}'
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
    async def complete_oauth_flow(
        session_id: str,
        authorization_code: str,
        state: str
    ) -> Integration:
        """
        Backward compatibility wrapper for complete_authentication_flow.
        
        DEPRECATED: Use complete_authentication_flow instead.
        
        Args:
            session_id: UUID of InstallationSession
            authorization_code: Authorization code from callback
            state: State parameter for validation
            
        Returns:
            Integration: Created integration instance
        """
        logger.warning(
            'complete_oauth_flow is deprecated. Use complete_authentication_flow instead.'
        )
        return await InstallationService.complete_authentication_flow(
            session_id=session_id,
            authorization_code=authorization_code,
            state=state
        )

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
        # Get session using optimized selector
        session = InstallationSessionSelector.get_session_by_id(session_id)
        
        if not session:
            raise InstallationSession.DoesNotExist(
                f'Installation session {session_id} not found'
            )
        
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
        
        Checks for dependent workflows, disables them, revokes credentials
        using the appropriate strategy, deletes the Integration record,
        and logs the uninstallation.
        
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
            
        Requirements: 5.4-5.6, 8.6, 18.5-18.6
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
            
            # Revoke credentials using strategy (Requirement 8.6)
            try:
                InstallationService._revoke_credentials_with_strategy(integration)
            except Exception as e:
                # Log error but don't fail uninstallation
                logger.error(
                    f'Failed to revoke credentials for integration {integration_id}: {str(e)}'
                )
            
            # Delete Integration record (cascades to encrypted tokens)
            integration.delete()
        
        # Log uninstallation in audit log (Requirement 18.6)
        logger.info(
            f'Uninstalled integration {integration_id} for user {user.id}, '
            f'integration type {integration.integration_type.name}, '
            f'auth_type={integration.integration_type.auth_type}, '
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
        #         'auth_type': integration.integration_type.auth_type,
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
    def _revoke_credentials_with_strategy(integration: Integration) -> None:
        """
        Revoke credentials using the appropriate authentication strategy.
        
        Uses AuthStrategyFactory to get the correct strategy and revoke
        credentials with the provider.
        
        Args:
            integration: Integration instance with credentials to revoke
            
        Requirements: 8.6, 18.5
        """
        try:
            # Create strategy using factory
            strategy = AuthStrategyFactory.create_strategy(integration.integration_type)
            
            # Revoke credentials (async operation, run synchronously here)
            import asyncio
            
            try:
                # Try to get running event loop
                loop = asyncio.get_running_loop()
                # If we're already in an async context, create a task
                asyncio.create_task(strategy.revoke_credentials(integration))
            except RuntimeError:
                # No running loop, create new one
                asyncio.run(strategy.revoke_credentials(integration))
            
            logger.info(
                f'Successfully revoked credentials for integration {integration.id}, '
                f'auth_type={integration.integration_type.auth_type}'
            )
            
        except Exception as e:
            logger.error(
                f'Failed to revoke credentials for integration {integration.id}: {str(e)}'
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
        # Get session using optimized selector
        session = InstallationSessionSelector.get_session_by_id(session_id)
        
        if not session:
            raise InstallationSession.DoesNotExist(
                f'Installation session {session_id} not found'
            )
        
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
        # Get session using optimized selector
        session = InstallationSessionSelector.get_session_by_id(session_id)
        
        if not session:
            raise InstallationSession.DoesNotExist(
                f'Installation session {session_id} not found'
            )
        
        # Use recovery utility to reset session
        reset_session = InstallationRecovery.reset_session_for_retry(session)
        
        logger.info(
            f'Retrying installation for session {session.id}, '
            f'attempt {session.retry_count + 1}'
        )
        
        return reset_session
