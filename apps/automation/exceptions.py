"""
Custom exceptions for the automation/integration system.

Requirements: 29.1-29.7
"""

from typing import Optional, Dict, Any


class AutomationException(Exception):
    """Base exception for automation system errors."""
    
    def __init__(
        self,
        message: str,
        error_code: str,
        details: Optional[Dict[str, Any]] = None,
        status_code: int = 500
    ):
        self.message = message
        self.error_code = error_code
        self.details = details or {}
        self.status_code = status_code
        super().__init__(self.message)


class AuthenticationFailedException(AutomationException):
    """
    Raised when authentication with an external provider fails.
    
    Requirements: 29.1-29.7
    """
    
    def __init__(
        self,
        message: str = "Authentication failed",
        details: Optional[Dict[str, Any]] = None,
        provider: Optional[str] = None
    ):
        error_code = "AUTH_FAILED"
        if provider:
            error_code = f"AUTH_FAILED_{provider.upper()}"
        
        super().__init__(
            message=message,
            error_code=error_code,
            details=details or {},
            status_code=401
        )


class RateLimitExceededException(AutomationException):
    """
    Raised when rate limit is exceeded.
    
    Requirements: 29.1-29.7
    """
    
    def __init__(
        self,
        message: str = "Rate limit exceeded",
        retry_after: Optional[int] = None,
        limit: Optional[int] = None,
        current: Optional[int] = None,
        details: Optional[Dict[str, Any]] = None
    ):
        error_details = details or {}
        if retry_after is not None:
            error_details['retry_after'] = retry_after
        if limit is not None:
            error_details['limit'] = limit
        if current is not None:
            error_details['current'] = current
        
        super().__init__(
            message=message,
            error_code="RATE_LIMIT_EXCEEDED",
            details=error_details,
            status_code=429
        )


class MetaInstallationRateLimitExceeded(RateLimitExceededException):
    """
    Raised when Meta installation rate limit is exceeded.
    
    Requirements: 14.1-14.7
    """
    
    def __init__(
        self,
        message: str = "Meta installation rate limit exceeded",
        retry_after: Optional[int] = None,
        details: Optional[Dict[str, Any]] = None
    ):
        super().__init__(
            message=message,
            retry_after=retry_after,
            limit=5,  # 5 installations per minute
            details=details
        )


class WebhookSignatureInvalidException(AutomationException):
    """
    Raised when webhook signature verification fails.
    
    Requirements: 29.1-29.7
    """
    
    def __init__(
        self,
        message: str = "Invalid webhook signature",
        details: Optional[Dict[str, Any]] = None
    ):
        super().__init__(
            message=message,
            error_code="WEBHOOK_SIGNATURE_INVALID",
            details=details or {},
            status_code=401
        )


class IntegrationNotFoundException(AutomationException):
    """
    Raised when a requested integration is not found.
    
    Requirements: 29.1-29.7
    """
    
    def __init__(
        self,
        message: str = "Integration not found",
        integration_id: Optional[str] = None,
        details: Optional[Dict[str, Any]] = None
    ):
        error_details = details or {}
        if integration_id:
            error_details['integration_id'] = integration_id
        
        super().__init__(
            message=message,
            error_code="INTEGRATION_NOT_FOUND",
            details=error_details,
            status_code=404
        )


class IntegrationDisconnectedException(AutomationException):
    """
    Raised when attempting to use a disconnected integration.
    
    Requirements: 29.1-29.7
    """
    
    def __init__(
        self,
        message: str = "Integration is disconnected",
        integration_id: Optional[str] = None,
        details: Optional[Dict[str, Any]] = None
    ):
        error_details = details or {}
        if integration_id:
            error_details['integration_id'] = integration_id
        
        super().__init__(
            message=message,
            error_code="INTEGRATION_DISCONNECTED",
            details=error_details,
            status_code=400
        )


class MessageDeliveryFailedException(AutomationException):
    """
    Raised when message delivery fails.
    
    Requirements: 29.1-29.7
    """
    
    def __init__(
        self,
        message: str = "Message delivery failed",
        is_retryable: bool = False,
        details: Optional[Dict[str, Any]] = None
    ):
        error_details = details or {}
        error_details['is_retryable'] = is_retryable
        
        super().__init__(
            message=message,
            error_code="MESSAGE_DELIVERY_FAILED",
            details=error_details,
            status_code=500 if is_retryable else 400
        )


class InvalidConfigurationException(AutomationException):
    """
    Raised when integration configuration is invalid.
    
    Requirements: 29.1-29.7
    """
    
    def __init__(
        self,
        message: str = "Invalid configuration",
        field_errors: Optional[Dict[str, str]] = None,
        details: Optional[Dict[str, Any]] = None
    ):
        error_details = details or {}
        if field_errors:
            error_details['field_errors'] = field_errors
        
        super().__init__(
            message=message,
            error_code="INVALID_CONFIGURATION",
            details=error_details,
            status_code=400
        )


class SessionExpiredException(AutomationException):
    """
    Raised when an installation session has expired.
    
    Requirements: 29.1-29.7
    """
    
    def __init__(
        self,
        message: str = "Installation session expired",
        session_id: Optional[str] = None,
        details: Optional[Dict[str, Any]] = None
    ):
        error_details = details or {}
        if session_id:
            error_details['session_id'] = session_id
        
        super().__init__(
            message=message,
            error_code="SESSION_EXPIRED",
            details=error_details,
            status_code=400
        )
