"""
Authentication error handler service.

Provides user-friendly error messages and recovery instructions
for authentication failures across different auth types.

Requirements: 17.1, 17.2, 17.3, 17.4, 17.5, 17.6
"""

import logging
from typing import Dict, Optional, Tuple
from django.utils import timezone
from apps.automation.models import InstallationSession, InstallationStatus


logger = logging.getLogger(__name__)


class AuthErrorHandler:
    """
    Service for handling authentication errors with user-friendly messages.
    
    Provides error handling, recovery instructions, and session management
    for authentication failures across OAuth, Meta, and API Key flows.
    
    Requirements: 17.1-17.6
    """
    
    # OAuth error codes and messages
    OAUTH_ERRORS = {
        'access_denied': {
            'message': 'You denied access to the integration.',
            'troubleshooting': [
                'Click "Retry" to start the authorization process again',
                'Make sure to click "Allow" or "Authorize" when prompted',
                'Check that you have the necessary permissions in your account'
            ],
            'recoverable': True
        },
        'invalid_grant': {
            'message': 'The authorization code is invalid or has expired.',
            'troubleshooting': [
                'Authorization codes expire after 10 minutes',
                'Click "Retry" to get a new authorization code',
                'Make sure your system clock is accurate'
            ],
            'recoverable': True
        },
        'invalid_client': {
            'message': 'The integration configuration is invalid.',
            'troubleshooting': [
                'This is a configuration issue on our end',
                'Please contact support with error reference ID',
                'Our team will fix the integration configuration'
            ],
            'recoverable': False
        },
        'invalid_scope': {
            'message': 'The requested permissions are not available.',
            'troubleshooting': [
                'The integration requires permissions that are not available in your account',
                'Contact support to adjust the required permissions',
                'Check if your account type supports this integration'
            ],
            'recoverable': False
        },
        'server_error': {
            'message': 'The authorization server encountered an error.',
            'troubleshooting': [
                'This is a temporary issue with the provider',
                'Wait a few minutes and click "Retry"',
                'If the problem persists, contact support'
            ],
            'recoverable': True
        },
        'temporarily_unavailable': {
            'message': 'The authorization server is temporarily unavailable.',
            'troubleshooting': [
                'The provider is experiencing temporary issues',
                'Wait 5-10 minutes and click "Retry"',
                'Check the provider\'s status page for updates'
            ],
            'recoverable': True
        },
        'network_error': {
            'message': 'Unable to connect to the authorization server.',
            'troubleshooting': [
                'Check your internet connection',
                'Try disabling VPN or proxy if enabled',
                'Wait a moment and click "Retry"'
            ],
            'recoverable': True
        },
        'timeout': {
            'message': 'The authorization request timed out.',
            'troubleshooting': [
                'The provider took too long to respond',
                'Check your internet connection',
                'Click "Retry" to try again'
            ],
            'recoverable': True
        }
    }
    
    # Meta-specific error codes and messages
    META_ERRORS = {
        'invalid_verification': {
            'message': 'Meta Business verification failed.',
            'troubleshooting': [
                'Make sure you have a Meta Business account',
                'Verify that your business is verified on Meta',
                'Check that you have admin access to the business account',
                'Click "Retry" to start the verification process again'
            ],
            'recoverable': True
        },
        'missing_permissions': {
            'message': 'Required Meta permissions were not granted.',
            'troubleshooting': [
                'The integration requires specific permissions to function',
                'Click "Retry" and make sure to grant all requested permissions',
                'Check Meta Business Manager for permission settings'
            ],
            'recoverable': True
        },
        'invalid_phone_number': {
            'message': 'No valid WhatsApp Business phone number found.',
            'troubleshooting': [
                'Make sure you have a WhatsApp Business account set up',
                'Verify your phone number in WhatsApp Business Manager',
                'Check that the phone number is active and verified',
                'Click "Retry" after setting up your phone number'
            ],
            'recoverable': True
        },
        'token_exchange_failed': {
            'message': 'Failed to exchange Meta authorization code for access token.',
            'troubleshooting': [
                'This is usually a temporary issue',
                'Wait a few minutes and click "Retry"',
                'If the problem persists, contact support'
            ],
            'recoverable': True
        },
        'business_not_found': {
            'message': 'Meta Business account not found.',
            'troubleshooting': [
                'Make sure you have a Meta Business account',
                'Create a business account at business.facebook.com',
                'Verify that you have admin access to the business',
                'Click "Retry" after setting up your business account'
            ],
            'recoverable': True
        },
        'rate_limit_exceeded': {
            'message': 'Meta API rate limit exceeded.',
            'troubleshooting': [
                'Too many requests to Meta API in a short time',
                'Wait 15-30 minutes before trying again',
                'This is a temporary limitation from Meta'
            ],
            'recoverable': True
        }
    }
    
    # API Key error codes and messages
    API_KEY_ERRORS = {
        'invalid_api_key': {
            'message': 'The API key is invalid.',
            'troubleshooting': [
                'Double-check that you copied the entire API key',
                'Make sure there are no extra spaces or characters',
                'Verify the API key is active in your provider account',
                'Generate a new API key if needed and try again'
            ],
            'recoverable': True
        },
        'api_key_expired': {
            'message': 'The API key has expired.',
            'troubleshooting': [
                'Generate a new API key from your provider account',
                'Copy the new key and click "Retry"',
                'Consider setting up key rotation reminders'
            ],
            'recoverable': True
        },
        'insufficient_permissions': {
            'message': 'The API key does not have sufficient permissions.',
            'troubleshooting': [
                'Check the required permissions for this integration',
                'Generate a new API key with the correct permissions',
                'Verify the key has access to the required resources'
            ],
            'recoverable': True
        },
        'validation_failed': {
            'message': 'Unable to validate the API key.',
            'troubleshooting': [
                'The provider API is not responding',
                'Check your internet connection',
                'Wait a few minutes and click "Retry"',
                'Verify the provider service is operational'
            ],
            'recoverable': True
        },
        'invalid_format': {
            'message': 'The API key format is incorrect.',
            'troubleshooting': [
                'Check the expected format for this integration',
                'Make sure you copied the complete key',
                'Remove any extra spaces or line breaks',
                'Verify you\'re using the correct type of key'
            ],
            'recoverable': True
        }
    }
    
    @staticmethod
    def handle_oauth_error(
        error_code: str,
        session: InstallationSession,
        error_description: str = ''
    ) -> Dict:
        """
        Handle OAuth authentication error with user-friendly message.
        
        Args:
            error_code: OAuth error code
            session: Installation session
            error_description: Optional error description from provider
            
        Returns:
            Dictionary with user_message, troubleshooting, can_retry
            
        Requirements: 17.1, 17.4, 17.5
        """
        error_info = AuthErrorHandler.OAUTH_ERRORS.get(
            error_code,
            {
                'message': f'OAuth authentication failed: {error_code}',
                'troubleshooting': [
                    'An unexpected error occurred',
                    'Click "Retry" to try again',
                    'Contact support if the problem persists'
                ],
                'recoverable': True
            }
        )
        
        # Update session status
        session.status = InstallationStatus.FAILED
        session.error_message = f"{error_info['message']} {error_description}".strip()
        session.completed_at = timezone.now()
        session.save()
        
        logger.warning(
            f'OAuth error for session {session.id}: {error_code} - {error_description}'
        )
        
        return {
            'user_message': error_info['message'],
            'troubleshooting': error_info['troubleshooting'],
            'can_retry': error_info['recoverable'] and session.can_retry,
            'retry_count': session.retry_count,
            'max_retries': 3,
            'error_code': error_code,
            'session_id': str(session.id)
        }
    
    @staticmethod
    def handle_meta_error(
        error_code: str,
        session: InstallationSession,
        error_details: str = ''
    ) -> Dict:
        """
        Handle Meta authentication error with troubleshooting steps.
        
        Args:
            error_code: Meta error code
            session: Installation session
            error_details: Optional error details from Meta API
            
        Returns:
            Dictionary with user_message, troubleshooting, can_retry
            
        Requirements: 17.2, 17.4, 17.5
        """
        error_info = AuthErrorHandler.META_ERRORS.get(
            error_code,
            {
                'message': f'Meta authentication failed: {error_code}',
                'troubleshooting': [
                    'An unexpected error occurred with Meta',
                    'Check Meta Business Manager for any issues',
                    'Click "Retry" to try again',
                    'Contact support if the problem persists'
                ],
                'recoverable': True
            }
        )
        
        # Update session status
        session.status = InstallationStatus.FAILED
        session.error_message = f"{error_info['message']} {error_details}".strip()
        session.completed_at = timezone.now()
        session.save()
        
        logger.warning(
            f'Meta error for session {session.id}: {error_code} - {error_details}'
        )
        
        return {
            'user_message': error_info['message'],
            'troubleshooting': error_info['troubleshooting'],
            'can_retry': error_info['recoverable'] and session.can_retry,
            'retry_count': session.retry_count,
            'max_retries': 3,
            'error_code': error_code,
            'session_id': str(session.id),
            'meta_help_url': 'https://business.facebook.com/help'
        }
    
    @staticmethod
    def handle_api_key_error(
        error_code: str,
        session: InstallationSession,
        error_message: str = ''
    ) -> Dict:
        """
        Handle API key authentication error with retry instructions.
        
        Args:
            error_code: API key error code
            session: Installation session
            error_message: Optional error message
            
        Returns:
            Dictionary with user_message, troubleshooting, can_retry
            
        Requirements: 17.3, 17.4, 17.5
        """
        error_info = AuthErrorHandler.API_KEY_ERRORS.get(
            error_code,
            {
                'message': f'API key validation failed: {error_code}',
                'troubleshooting': [
                    'Verify your API key is correct',
                    'Check that the key is active',
                    'Click "Retry" to enter the key again',
                    'Contact support if you need help'
                ],
                'recoverable': True
            }
        )
        
        # Update session status
        session.status = InstallationStatus.FAILED
        session.error_message = f"{error_info['message']} {error_message}".strip()
        session.completed_at = timezone.now()
        session.save()
        
        logger.warning(
            f'API key error for session {session.id}: {error_code} - {error_message}'
        )
        
        return {
            'user_message': error_info['message'],
            'troubleshooting': error_info['troubleshooting'],
            'can_retry': error_info['recoverable'] and session.can_retry,
            'retry_count': session.retry_count,
            'max_retries': 3,
            'error_code': error_code,
            'session_id': str(session.id)
        }
    
    @staticmethod
    def provide_retry_capability(session: InstallationSession) -> Tuple[bool, str]:
        """
        Check if retry is allowed and provide retry URL.
        
        Args:
            session: Installation session
            
        Returns:
            Tuple of (can_retry, retry_url)
            
        Requirements: 17.5, 17.6
        """
        if not session.can_retry:
            return False, ''
        
        # Increment retry counter
        session.increment_retry()
        
        # Reset session status for retry
        session.status = InstallationStatus.DOWNLOADING
        session.progress = 0
        session.error_message = ''
        session.save()
        
        # Generate retry URL based on auth type
        retry_url = f'/api/v1/integrations/install/?integration_type_id={session.integration_type_id}'
        
        logger.info(
            f'Retry enabled for session {session.id} (attempt {session.retry_count}/3)'
        )
        
        return True, retry_url
    
    @staticmethod
    def get_support_reference(session: InstallationSession) -> str:
        """
        Generate support reference ID for error reporting.
        
        Args:
            session: Installation session
            
        Returns:
            Support reference ID string
        """
        return f"AUTH-{session.id.hex[:8].upper()}-{session.created_at.strftime('%Y%m%d')}"
    
    @staticmethod
    def should_contact_support(session: InstallationSession) -> bool:
        """
        Determine if user should contact support.
        
        Args:
            session: Installation session
            
        Returns:
            True if user should contact support
            
        Requirements: 17.5
        """
        # Contact support if:
        # 1. Max retries exceeded
        # 2. Non-recoverable error
        # 3. Session is expired
        
        if session.retry_count >= 3:
            return True
        
        if session.is_expired:
            return True
        
        # Check if error is non-recoverable
        error_code = session.error_message.split(':')[0] if session.error_message else ''
        
        oauth_error = AuthErrorHandler.OAUTH_ERRORS.get(error_code, {})
        meta_error = AuthErrorHandler.META_ERRORS.get(error_code, {})
        api_key_error = AuthErrorHandler.API_KEY_ERRORS.get(error_code, {})
        
        if not oauth_error.get('recoverable', True):
            return True
        if not meta_error.get('recoverable', True):
            return True
        if not api_key_error.get('recoverable', True):
            return True
        
        return False
