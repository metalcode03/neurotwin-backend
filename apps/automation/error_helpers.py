"""
Helper functions for raising exceptions with user-friendly messages.

Requirements: 29.1-29.7
"""

from typing import Optional, Dict, Any

from .exceptions import (
    AuthenticationFailedException,
    RateLimitExceededException,
    MessageDeliveryFailedException,
    IntegrationNotFoundException,
    IntegrationDisconnectedException,
    SessionExpiredException,
    InvalidConfigurationException,
)
from .error_messages import ErrorMessages


def raise_oauth_error(
    error_code: str,
    error_description: Optional[str] = None,
    provider: Optional[str] = None
) -> None:
    """
    Raise OAuth authentication error with user-friendly message.
    
    Args:
        error_code: OAuth error code from provider
        error_description: Optional error description from provider
        provider: OAuth provider name (e.g., 'google', 'slack')
    """
    message = ErrorMessages.get_oauth_error_message(error_code, error_description)
    
    details = {
        'error_code': error_code,
        'provider': provider,
    }
    if error_description:
        details['error_description'] = error_description
    
    raise AuthenticationFailedException(
        message=message,
        details=details,
        provider=provider
    )


def raise_meta_error(
    error_code: Optional[int] = None,
    error_message: Optional[str] = None
) -> None:
    """
    Raise Meta authentication error with troubleshooting steps.
    
    Args:
        error_code: Meta API error code
        error_message: Error message from Meta
    """
    message = ErrorMessages.get_meta_error_message(error_code, error_message)
    
    details = {}
    if error_code:
        details['meta_error_code'] = error_code
    if error_message:
        details['meta_error_message'] = error_message
    
    raise AuthenticationFailedException(
        message=message,
        details=details,
        provider='meta'
    )


def raise_api_key_error(status_code: Optional[int] = None) -> None:
    """
    Raise API key validation error with instructions.
    
    Args:
        status_code: HTTP status code from validation attempt
    """
    message = ErrorMessages.get_api_key_error_message(status_code)
    
    details = {}
    if status_code:
        details['validation_status_code'] = status_code
    
    raise AuthenticationFailedException(
        message=message,
        details=details,
        provider='api_key'
    )


def raise_rate_limit_error(
    retry_after: Optional[int] = None,
    limit: Optional[int] = None,
    current: Optional[int] = None
) -> None:
    """
    Raise rate limit exceeded error with retry information.
    
    Args:
        retry_after: Seconds until rate limit resets
        limit: Rate limit threshold
        current: Current usage count
    """
    message = ErrorMessages.get_rate_limit_message(retry_after, limit)
    
    raise RateLimitExceededException(
        message=message,
        retry_after=retry_after,
        limit=limit,
        current=current
    )


def raise_message_send_error(
    is_retryable: bool = False,
    reason: Optional[str] = None,
    status_code: Optional[int] = None
) -> None:
    """
    Raise message delivery error with retry option.
    
    Args:
        is_retryable: Whether the error is transient and retryable
        reason: Specific failure reason
        status_code: HTTP status code from delivery attempt
    """
    message = ErrorMessages.get_message_send_error(is_retryable, reason, status_code)
    
    details = {}
    if reason:
        details['reason'] = reason
    if status_code:
        details['status_code'] = status_code
    
    raise MessageDeliveryFailedException(
        message=message,
        is_retryable=is_retryable,
        details=details
    )


def raise_integration_not_found(integration_id: Optional[str] = None) -> None:
    """
    Raise integration not found error.
    
    Args:
        integration_id: Integration identifier
    """
    raise IntegrationNotFoundException(
        message=ErrorMessages.INTEGRATION_NOT_FOUND,
        integration_id=integration_id
    )


def raise_integration_disconnected(integration_id: Optional[str] = None) -> None:
    """
    Raise integration disconnected error.
    
    Args:
        integration_id: Integration identifier
    """
    raise IntegrationDisconnectedException(
        message=ErrorMessages.INTEGRATION_DISCONNECTED,
        integration_id=integration_id
    )


def raise_session_expired(session_id: Optional[str] = None) -> None:
    """
    Raise session expired error.
    
    Args:
        session_id: Session identifier
    """
    raise SessionExpiredException(
        message=ErrorMessages.SESSION_EXPIRED,
        session_id=session_id
    )


def raise_configuration_error(
    field_errors: Optional[Dict[str, str]] = None,
    message: Optional[str] = None
) -> None:
    """
    Raise configuration validation error.
    
    Args:
        field_errors: Dictionary of field-level errors
        message: Optional custom message
    """
    raise InvalidConfigurationException(
        message=message or ErrorMessages.CONFIGURATION_INVALID,
        field_errors=field_errors
    )
