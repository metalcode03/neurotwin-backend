"""
Example usage of error handling system.

This file demonstrates how to use the custom exceptions and error messages
in views, services, and other components.

Requirements: 29.1-29.7
"""

from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework import status

from .error_helpers import (
    raise_oauth_error,
    raise_meta_error,
    raise_api_key_error,
    raise_rate_limit_error,
    raise_message_send_error,
    raise_integration_not_found,
    raise_integration_disconnected,
    raise_session_expired,
)
from .exceptions import (
    AuthenticationFailedException,
    RateLimitExceededException,
    MessageDeliveryFailedException,
)


class ExampleOAuthCallbackView(APIView):
    """
    Example: OAuth callback handling with error messages.
    """
    
    def get(self, request):
        code = request.query_params.get('code')
        error = request.query_params.get('error')
        error_description = request.query_params.get('error_description')
        
        # Handle OAuth errors
        if error:
            # This will raise AuthenticationFailedException with user-friendly message
            raise_oauth_error(
                error_code=error,
                error_description=error_description,
                provider='google'
            )
        
        # Process successful OAuth callback
        # ... authentication logic ...
        
        return Response({'status': 'success'})


class ExampleMetaCallbackView(APIView):
    """
    Example: Meta authentication with error handling.
    """
    
    def post(self, request):
        try:
            # Attempt Meta authentication
            # ... authentication logic ...
            pass
        except Exception as e:
            # Check for specific Meta error codes
            if hasattr(e, 'response') and hasattr(e.response, 'json'):
                error_data = e.response.json()
                error_code = error_data.get('error', {}).get('code')
                error_message = error_data.get('error', {}).get('message')
                
                # Raise with troubleshooting steps
                raise_meta_error(
                    error_code=error_code,
                    error_message=error_message
                )
            
            # Re-raise if not a Meta-specific error
            raise
        
        return Response({'status': 'success'})


class ExampleAPIKeyValidationView(APIView):
    """
    Example: API key validation with error messages.
    """
    
    def post(self, request):
        api_key = request.data.get('api_key')
        
        try:
            # Validate API key
            # ... validation logic ...
            pass
        except Exception as e:
            # Get status code from validation attempt
            status_code = getattr(e, 'status_code', None)
            
            # Raise with instructions
            raise_api_key_error(status_code=status_code)
        
        return Response({'status': 'success'})


class ExampleSendMessageView(APIView):
    """
    Example: Message sending with rate limiting and error handling.
    """
    
    def post(self, request, conversation_id):
        # Check rate limit
        rate_limit_status = self._check_rate_limit(request.user)
        
        if not rate_limit_status['allowed']:
            # Raise rate limit error with retry information
            raise_rate_limit_error(
                retry_after=rate_limit_status['retry_after'],
                limit=rate_limit_status['limit'],
                current=rate_limit_status['current']
            )
        
        # Attempt to send message
        try:
            # ... message sending logic ...
            pass
        except Exception as e:
            # Determine if error is retryable
            is_retryable = self._is_retryable_error(e)
            status_code = getattr(e, 'status_code', None)
            
            # Raise with retry option
            raise_message_send_error(
                is_retryable=is_retryable,
                reason=str(e),
                status_code=status_code
            )
        
        return Response({'status': 'sent'})
    
    def _check_rate_limit(self, user):
        """Mock rate limit check"""
        return {
            'allowed': True,
            'retry_after': None,
            'limit': 20,
            'current': 5
        }
    
    def _is_retryable_error(self, error):
        """Determine if error is transient"""
        # Check for transient error indicators
        if hasattr(error, 'status_code'):
            # 429 (rate limit), 5xx (server errors) are retryable
            return error.status_code in [429, 500, 502, 503, 504]
        
        # Network errors are retryable
        if 'timeout' in str(error).lower() or 'network' in str(error).lower():
            return True
        
        return False


class ExampleIntegrationDetailView(APIView):
    """
    Example: Integration access with error handling.
    """
    
    def get(self, request, integration_id):
        # Check if integration exists
        integration = self._get_integration(integration_id)
        
        if not integration:
            # Raise not found error
            raise_integration_not_found(integration_id=integration_id)
        
        # Check if integration is disconnected
        if integration.status == 'disconnected':
            # Raise disconnected error
            raise_integration_disconnected(integration_id=integration_id)
        
        # Return integration details
        return Response({'integration': integration})
    
    def _get_integration(self, integration_id):
        """Mock integration retrieval"""
        return None  # Simulating not found


class ExampleInstallationCompleteView(APIView):
    """
    Example: Installation completion with session validation.
    """
    
    def post(self, request):
        session_id = request.data.get('session_id')
        
        # Get installation session
        session = self._get_session(session_id)
        
        if not session:
            # Raise session expired error
            raise_session_expired(session_id=session_id)
        
        # Complete installation
        # ... installation logic ...
        
        return Response({'status': 'completed'})
    
    def _get_session(self, session_id):
        """Mock session retrieval"""
        return None  # Simulating expired session


# Example: Using exceptions directly in services

class ExampleIntegrationService:
    """
    Example: Service layer error handling.
    """
    
    @staticmethod
    def send_message(integration, message_content):
        """
        Send message through integration.
        
        Raises:
            RateLimitExceededException: If rate limit exceeded
            MessageDeliveryFailedException: If delivery fails
            IntegrationDisconnectedException: If integration disconnected
        """
        # Check integration status
        if integration.status == 'disconnected':
            raise_integration_disconnected(integration_id=str(integration.id))
        
        # Check rate limit
        if not ExampleIntegrationService._check_rate_limit(integration):
            raise_rate_limit_error(
                retry_after=60,
                limit=20,
                current=20
            )
        
        # Attempt delivery
        try:
            # ... actual delivery logic ...
            pass
        except Exception as e:
            # Handle delivery failure
            is_retryable = 'timeout' in str(e).lower()
            raise_message_send_error(
                is_retryable=is_retryable,
                reason=str(e)
            )
    
    @staticmethod
    def _check_rate_limit(integration):
        """Mock rate limit check"""
        return True
