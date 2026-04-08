"""
User-friendly error messages for automation system.

Provides clear, actionable error messages for different failure scenarios.
Requirements: 29.1-29.7
"""

from typing import Dict, Any, Optional


class ErrorMessages:
    """
    Centralized error message templates for user-friendly feedback.
    
    Requirements: 29.1-29.7
    """
    
    # OAuth Authorization Failures
    OAUTH_AUTHORIZATION_FAILED = (
        "Authorization failed. Please try connecting again. "
        "If the problem persists, check that you granted all required permissions."
    )
    
    OAUTH_ACCESS_DENIED = (
        "You denied access to the integration. "
        "To connect this service, you'll need to grant the requested permissions."
    )
    
    OAUTH_INVALID_GRANT = (
        "The authorization code has expired or is invalid. "
        "Please start the connection process again."
    )
    
    OAUTH_TOKEN_EXPIRED = (
        "Your connection has expired. Please reconnect to continue using this integration."
    )
    
    OAUTH_INVALID_CLIENT = (
        "There's a configuration issue with this integration. "
        "Please contact support for assistance."
    )
    
    # Meta Authentication Failures
    META_AUTH_FAILED = (
        "WhatsApp Business connection failed. Please try again."
    )
    
    META_NO_BUSINESS_ACCOUNT = (
        "No Meta Business account found. "
        "To connect WhatsApp Business, you need:\n"
        "1. A Meta Business account\n"
        "2. A WhatsApp Business account\n"
        "3. At least one phone number configured"
    )
    
    META_NO_WABA = (
        "No WhatsApp Business Account found in your Meta Business account. "
        "Please set up WhatsApp Business first at business.facebook.com"
    )
    
    META_NO_PHONE_NUMBER = (
        "No phone numbers found in your WhatsApp Business Account. "
        "Please add a phone number in your Meta Business Manager."
    )
    
    META_PERMISSIONS_INSUFFICIENT = (
        "Insufficient permissions granted. "
        "Please ensure you grant all requested permissions for WhatsApp Business integration."
    )
    
    META_TOKEN_REFRESH_FAILED = (
        "Failed to refresh your WhatsApp connection. "
        "Please reconnect your WhatsApp Business account."
    )
    
    # API Key Validation Failures
    API_KEY_INVALID = (
        "Invalid API key. Please verify your API key and try again. "
        "You can find your API key in your account settings on the provider's platform."
    )
    
    API_KEY_EXPIRED = (
        "Your API key has expired. Please generate a new API key and update your connection."
    )
    
    API_KEY_INSUFFICIENT_PERMISSIONS = (
        "Your API key doesn't have the required permissions. "
        "Please ensure your API key has access to the necessary resources."
    )
    
    API_KEY_VALIDATION_FAILED = (
        "Unable to validate your API key. "
        "Please check that the key is correct and that the service is accessible."
    )
    
    # Rate Limit Exceeded
    RATE_LIMIT_EXCEEDED = (
        "Rate limit exceeded. Please try again in {retry_after} seconds."
    )
    
    RATE_LIMIT_EXCEEDED_GENERIC = (
        "You've sent too many messages. Please wait a moment and try again."
    )
    
    RATE_LIMIT_INTEGRATION_QUOTA = (
        "You've reached the message limit for this integration ({limit} messages per minute). "
        "Please wait {retry_after} seconds before sending more messages."
    )
    
    RATE_LIMIT_GLOBAL_QUOTA = (
        "Platform message limit reached. Please try again in {retry_after} seconds."
    )
    
    # Message Sending Failures
    MESSAGE_SEND_FAILED = (
        "Failed to send message. Please try again."
    )
    
    MESSAGE_SEND_FAILED_RETRYABLE = (
        "Failed to send message due to a temporary issue. "
        "We'll automatically retry sending this message."
    )
    
    MESSAGE_SEND_FAILED_PERMANENT = (
        "Unable to send message. {reason}"
    )
    
    MESSAGE_RECIPIENT_INVALID = (
        "The recipient is invalid or unreachable. Please check the contact information."
    )
    
    MESSAGE_CONTENT_INVALID = (
        "Message content is invalid. Please check your message and try again."
    )
    
    MESSAGE_TOO_LONG = (
        "Message is too long. Please shorten your message and try again. "
        "Maximum length: {max_length} characters."
    )
    
    # Integration Status Errors
    INTEGRATION_NOT_FOUND = (
        "Integration not found. It may have been removed or you don't have access to it."
    )
    
    INTEGRATION_DISCONNECTED = (
        "This integration is disconnected. Please reconnect to continue using it."
    )
    
    INTEGRATION_DEGRADED = (
        "This integration is experiencing issues. Some features may not work correctly. "
        "We're working to restore full functionality."
    )
    
    INTEGRATION_UNAUTHORIZED = (
        "You don't have permission to access this integration."
    )
    
    # Session Errors
    SESSION_EXPIRED = (
        "Your installation session has expired. Please start the connection process again."
    )
    
    SESSION_INVALID = (
        "Invalid session. Please start the connection process again."
    )
    
    # Webhook Errors
    WEBHOOK_SIGNATURE_INVALID = (
        "Invalid webhook signature. This request cannot be processed."
    )
    
    WEBHOOK_PROCESSING_FAILED = (
        "Failed to process incoming message. We'll retry automatically."
    )
    
    # Configuration Errors
    CONFIGURATION_INVALID = (
        "Integration configuration is invalid. Please check your settings."
    )
    
    CONFIGURATION_MISSING_FIELDS = (
        "Required configuration fields are missing: {fields}"
    )
    
    # Generic Errors
    INTERNAL_ERROR = (
        "An unexpected error occurred. Please try again. "
        "If the problem persists, contact support."
    )
    
    SERVICE_UNAVAILABLE = (
        "The service is temporarily unavailable. Please try again in a few moments."
    )
    
    NETWORK_ERROR = (
        "Network error. Please check your connection and try again."
    )
    
    @staticmethod
    def get_oauth_error_message(error_code: str, error_description: Optional[str] = None) -> str:
        """
        Get user-friendly message for OAuth error.
        
        Args:
            error_code: OAuth error code from provider
            error_description: Optional error description from provider
            
        Returns:
            User-friendly error message
        """
        oauth_errors = {
            'access_denied': ErrorMessages.OAUTH_ACCESS_DENIED,
            'invalid_grant': ErrorMessages.OAUTH_INVALID_GRANT,
            'invalid_client': ErrorMessages.OAUTH_INVALID_CLIENT,
            'unauthorized_client': ErrorMessages.OAUTH_INVALID_CLIENT,
            'unsupported_grant_type': ErrorMessages.OAUTH_INVALID_CLIENT,
        }
        
        message = oauth_errors.get(error_code, ErrorMessages.OAUTH_AUTHORIZATION_FAILED)
        
        if error_description:
            message += f"\n\nTechnical details: {error_description}"
        
        return message
    
    @staticmethod
    def get_meta_error_message(error_code: Optional[int] = None, error_message: Optional[str] = None) -> str:
        """
        Get user-friendly message for Meta API error.
        
        Args:
            error_code: Meta API error code
            error_message: Error message from Meta
            
        Returns:
            User-friendly error message with troubleshooting steps
        """
        # Meta error code mappings
        meta_errors = {
            190: ErrorMessages.META_TOKEN_REFRESH_FAILED,  # Invalid OAuth token
            200: ErrorMessages.META_PERMISSIONS_INSUFFICIENT,  # Permission error
            368: ErrorMessages.META_NO_BUSINESS_ACCOUNT,  # Business account issue
        }
        
        if error_code and error_code in meta_errors:
            message = meta_errors[error_code]
        else:
            message = ErrorMessages.META_AUTH_FAILED
        
        # Add troubleshooting steps
        troubleshooting = (
            "\n\nTroubleshooting steps:\n"
            "1. Verify your Meta Business account is active\n"
            "2. Check that WhatsApp Business is properly configured\n"
            "3. Ensure you have admin access to the Business account\n"
            "4. Try disconnecting and reconnecting"
        )
        
        message += troubleshooting
        
        if error_message:
            message += f"\n\nTechnical details: {error_message}"
        
        return message
    
    @staticmethod
    def get_api_key_error_message(status_code: Optional[int] = None) -> str:
        """
        Get user-friendly message for API key validation error.
        
        Args:
            status_code: HTTP status code from validation attempt
            
        Returns:
            User-friendly error message
        """
        if status_code == 401:
            return ErrorMessages.API_KEY_INVALID
        elif status_code == 403:
            return ErrorMessages.API_KEY_INSUFFICIENT_PERMISSIONS
        elif status_code == 404:
            return ErrorMessages.API_KEY_VALIDATION_FAILED
        else:
            return ErrorMessages.API_KEY_INVALID
    
    @staticmethod
    def get_rate_limit_message(retry_after: Optional[int] = None, limit: Optional[int] = None) -> str:
        """
        Get user-friendly rate limit exceeded message.
        
        Args:
            retry_after: Seconds until rate limit resets
            limit: Rate limit threshold
            
        Returns:
            User-friendly error message with retry information
        """
        if retry_after and limit:
            return ErrorMessages.RATE_LIMIT_INTEGRATION_QUOTA.format(
                limit=limit,
                retry_after=retry_after
            )
        elif retry_after:
            return ErrorMessages.RATE_LIMIT_EXCEEDED.format(retry_after=retry_after)
        else:
            return ErrorMessages.RATE_LIMIT_EXCEEDED_GENERIC
    
    @staticmethod
    def get_message_send_error(
        is_retryable: bool = False,
        reason: Optional[str] = None,
        status_code: Optional[int] = None
    ) -> str:
        """
        Get user-friendly message sending error.
        
        Args:
            is_retryable: Whether the error is transient and retryable
            reason: Specific failure reason
            status_code: HTTP status code from delivery attempt
            
        Returns:
            User-friendly error message with retry option if applicable
        """
        if is_retryable:
            return ErrorMessages.MESSAGE_SEND_FAILED_RETRYABLE
        
        if status_code == 400:
            return ErrorMessages.MESSAGE_CONTENT_INVALID
        elif status_code == 404:
            return ErrorMessages.MESSAGE_RECIPIENT_INVALID
        elif reason:
            return ErrorMessages.MESSAGE_SEND_FAILED_PERMANENT.format(reason=reason)
        else:
            return ErrorMessages.MESSAGE_SEND_FAILED


def format_error_with_retry(message: str, retry_available: bool = True) -> Dict[str, Any]:
    """
    Format error message with retry option.
    
    Args:
        message: Error message
        retry_available: Whether retry is available
        
    Returns:
        Formatted error details with retry flag
    """
    return {
        'message': message,
        'retry_available': retry_available,
        'support_contact': 'support@neurotwin.ai'
    }
