"""
Installation recovery utility for handling OAuth and installation failures.

Provides error handling, retry logic, and support reference generation
for failed installation attempts.

Requirements: 15.1-15.6
"""

import logging
import secrets
from typing import Tuple, Optional, Dict, Any
from datetime import datetime

from django.utils import timezone

from apps.automation.models import InstallationSession, InstallationStatus


logger = logging.getLogger(__name__)


class InstallationRecovery:
    """
    Utility for handling installation failures and recovery.
    
    Provides methods for handling OAuth failures, token exchange failures,
    retry logic, and support reference generation.
    
    Requirements: 15.1-15.6
    """
    
    # Maximum retry attempts before generating support reference
    MAX_RETRY_ATTEMPTS = 3
    
    @staticmethod
    def handle_oauth_failure(
        session: InstallationSession,
        error_type: str,
        error_details: str,
        user_message: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        Handle OAuth authorization failure.
        
        Updates session status, logs error, and determines if retry is allowed.
        
        Args:
            session: InstallationSession instance
            error_type: Type of OAuth error (e.g., 'access_denied', 'invalid_request')
            error_details: Detailed error information for logging
            user_message: Optional user-friendly error message
            
        Returns:
            dict: Recovery information with keys:
                - can_retry: Whether retry is allowed
                - retry_count: Current retry count
                - support_reference: Support reference ID if max retries exceeded
                - error_message: User-friendly error message
                
        Requirements: 15.1-15.3
        """
        # Increment retry counter
        session.increment_retry()
        
        # Determine user-friendly message
        if user_message:
            friendly_message = user_message
        else:
            friendly_message = InstallationRecovery._get_oauth_error_message(error_type)
        
        # Update session with error details
        session.status = InstallationStatus.FAILED
        session.error_message = friendly_message
        session.completed_at = timezone.now()
        session.save(update_fields=[
            'status', 'error_message', 'completed_at', 'updated_at'
        ])
        
        # Log structured error
        logger.error(
            'OAuth authorization failed',
            extra={
                'user_id': str(session.user.id),
                'integration_type_id': str(session.integration_type.id),
                'integration_type': session.integration_type.name,
                'session_id': str(session.id),
                'error_type': error_type,
                'error_details': error_details,
                'retry_count': session.retry_count,
            }
        )
        
        # Build recovery response
        result = {
            'can_retry': session.can_retry,
            'retry_count': session.retry_count,
            'error_message': friendly_message,
        }
        
        # Generate support reference if max retries exceeded
        if not session.can_retry:
            support_ref = InstallationRecovery._generate_support_reference(session)
            result['support_reference'] = support_ref
            
            logger.error(
                f'Max retry attempts exceeded for session {session.id}. '
                f'Support reference: {support_ref}'
            )
        
        return result
    
    @staticmethod
    def handle_token_exchange_failure(
        session: InstallationSession,
        error_type: str,
        error_details: str,
        http_status: Optional[int] = None
    ) -> Dict[str, Any]:
        """
        Handle OAuth token exchange failure.
        
        Updates session status, logs error with HTTP details, and determines
        if retry is allowed.
        
        Args:
            session: InstallationSession instance
            error_type: Type of token exchange error (e.g., 'invalid_grant', 'network_error')
            error_details: Detailed error information for logging
            http_status: HTTP status code from token endpoint (if available)
            
        Returns:
            dict: Recovery information with keys:
                - can_retry: Whether retry is allowed
                - retry_count: Current retry count
                - support_reference: Support reference ID if max retries exceeded
                - error_message: User-friendly error message
                
        Requirements: 15.1-15.3
        """
        # Increment retry counter
        session.increment_retry()
        
        # Determine user-friendly message
        friendly_message = InstallationRecovery._get_token_error_message(
            error_type,
            http_status
        )
        
        # Update session with error details
        session.status = InstallationStatus.FAILED
        session.error_message = friendly_message
        session.completed_at = timezone.now()
        session.save(update_fields=[
            'status', 'error_message', 'completed_at', 'updated_at'
        ])
        
        # Log structured error
        logger.error(
            'OAuth token exchange failed',
            extra={
                'user_id': str(session.user.id),
                'integration_type_id': str(session.integration_type.id),
                'integration_type': session.integration_type.name,
                'session_id': str(session.id),
                'error_type': error_type,
                'error_details': error_details,
                'http_status': http_status,
                'retry_count': session.retry_count,
            }
        )
        
        # Build recovery response
        result = {
            'can_retry': session.can_retry,
            'retry_count': session.retry_count,
            'error_message': friendly_message,
        }
        
        # Generate support reference if max retries exceeded
        if not session.can_retry:
            support_ref = InstallationRecovery._generate_support_reference(session)
            result['support_reference'] = support_ref
            
            logger.error(
                f'Max retry attempts exceeded for session {session.id}. '
                f'Support reference: {support_ref}',
                extra={
                    'support_reference': support_ref,
                    'user_id': str(session.user.id),
                    'integration_type': session.integration_type.name,
                }
            )
        
        return result
    
    @staticmethod
    def _get_oauth_error_message(error_type: str) -> str:
        """
        Get user-friendly error message for OAuth errors.
        
        Args:
            error_type: OAuth error type
            
        Returns:
            str: User-friendly error message
        """
        error_messages = {
            'access_denied': (
                'Authorization was cancelled. '
                'Please try again and approve the requested permissions.'
            ),
            'invalid_request': (
                'Invalid authorization request. '
                'Please try again or contact support if the issue persists.'
            ),
            'unauthorized_client': (
                'This application is not authorized. '
                'Please contact support.'
            ),
            'unsupported_response_type': (
                'Authorization configuration error. '
                'Please contact support.'
            ),
            'invalid_scope': (
                'Invalid permissions requested. '
                'Please contact support.'
            ),
            'server_error': (
                'The authorization server encountered an error. '
                'Please try again in a few moments.'
            ),
            'temporarily_unavailable': (
                'The authorization server is temporarily unavailable. '
                'Please try again in a few moments.'
            ),
        }
        
        return error_messages.get(
            error_type,
            'Authorization failed. Please try again or contact support.'
        )
    
    @staticmethod
    def _get_token_error_message(
        error_type: str,
        http_status: Optional[int] = None
    ) -> str:
        """
        Get user-friendly error message for token exchange errors.
        
        Args:
            error_type: Token exchange error type
            http_status: HTTP status code (if available)
            
        Returns:
            str: User-friendly error message
        """
        error_messages = {
            'invalid_grant': (
                'Authorization code expired or invalid. '
                'Please try the installation again.'
            ),
            'invalid_client': (
                'Application credentials are invalid. '
                'Please contact support.'
            ),
            'invalid_request': (
                'Invalid token request. '
                'Please try again or contact support.'
            ),
            'unauthorized_client': (
                'This application is not authorized. '
                'Please contact support.'
            ),
            'unsupported_grant_type': (
                'Token exchange configuration error. '
                'Please contact support.'
            ),
            'network_error': (
                'Network connection failed. '
                'Please check your connection and try again.'
            ),
            'timeout': (
                'Request timed out. '
                'Please try again in a few moments.'
            ),
        }
        
        # Check for specific HTTP status codes
        if http_status:
            if http_status == 429:
                return (
                    'Rate limit exceeded. '
                    'Please wait a few minutes and try again.'
                )
            elif http_status >= 500:
                return (
                    'The service is temporarily unavailable. '
                    'Please try again in a few moments.'
                )
        
        return error_messages.get(
            error_type,
            'Token exchange failed. Please try again or contact support.'
        )
    
    @staticmethod
    def _generate_support_reference(session: InstallationSession) -> str:
        """
        Generate a unique support reference ID.
        
        Creates a reference ID that includes timestamp and random component
        for easy support ticket tracking.
        
        Args:
            session: InstallationSession instance
            
        Returns:
            str: Support reference ID (format: INST-YYYYMMDD-XXXXXX)
            
        Requirements: 15.5
        """
        # Generate timestamp component
        timestamp = datetime.now().strftime('%Y%m%d')
        
        # Generate random component (6 characters, uppercase alphanumeric)
        random_component = secrets.token_hex(3).upper()
        
        # Build reference ID
        support_ref = f'INST-{timestamp}-{random_component}'
        
        # Log support reference creation
        logger.info(
            f'Generated support reference {support_ref} for session {session.id}',
            extra={
                'support_reference': support_ref,
                'session_id': str(session.id),
                'user_id': str(session.user.id),
                'integration_type': session.integration_type.name,
                'retry_count': session.retry_count,
            }
        )
        
        return support_ref
    
    @staticmethod
    def can_retry_installation(session: InstallationSession) -> Tuple[bool, str]:
        """
        Check if installation can be retried.
        
        Validates retry eligibility based on retry count and session state.
        
        Args:
            session: InstallationSession instance
            
        Returns:
            tuple: (can_retry: bool, reason: str)
                - can_retry: Whether retry is allowed
                - reason: Explanation if retry not allowed
        """
        # Check if session is expired
        if session.is_expired:
            return False, 'Installation session has expired. Please start a new installation.'
        
        # Check retry count
        if not session.can_retry:
            return False, (
                f'Maximum retry attempts ({InstallationRecovery.MAX_RETRY_ATTEMPTS}) exceeded. '
                'Please contact support for assistance.'
            )
        
        # Check if session is already completed
        if session.status == InstallationStatus.COMPLETED:
            return False, 'Installation already completed successfully.'
        
        return True, 'Retry allowed'
    
    @staticmethod
    def reset_session_for_retry(session: InstallationSession) -> InstallationSession:
        """
        Reset session state for retry attempt.
        
        Resets status to DOWNLOADING and clears error message while
        preserving retry count.
        
        Args:
            session: InstallationSession instance
            
        Returns:
            InstallationSession: Updated session
            
        Raises:
            ValueError: If retry not allowed
        """
        can_retry, reason = InstallationRecovery.can_retry_installation(session)
        
        if not can_retry:
            raise ValueError(reason)
        
        # Reset session state
        session.status = InstallationStatus.DOWNLOADING
        session.progress = 0
        session.error_message = ''
        session.completed_at = None
        session.save(update_fields=[
            'status', 'progress', 'error_message', 'completed_at', 'updated_at'
        ])
        
        logger.info(
            f'Reset session {session.id} for retry attempt {session.retry_count + 1}',
            extra={
                'session_id': str(session.id),
                'user_id': str(session.user.id),
                'integration_type': session.integration_type.name,
                'retry_count': session.retry_count,
            }
        )
        
        return session
