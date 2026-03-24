"""
Custom exception handlers for DRF API views.

Provides custom error responses with proper HTTP status codes
and headers for rate limiting and other errors.

Requirements: 18.7
"""

from rest_framework.views import exception_handler
from rest_framework.response import Response
from rest_framework import status


def custom_exception_handler(exc, context):
    """
    Custom exception handler for DRF views.
    
    Adds Retry-After header for rate limit errors (HTTP 429)
    and provides consistent error response format.
    
    Args:
        exc: Exception instance
        context: Context dict with view and request
        
    Returns:
        Response: DRF Response with error details
        
    Requirements: 18.7
    """
    # Call DRF's default exception handler first
    response = exception_handler(exc, context)
    
    if response is not None:
        # Add Retry-After header for rate limit errors
        if response.status_code == status.HTTP_429_TOO_MANY_REQUESTS:
            # Get throttle wait time from exception
            if hasattr(exc, 'wait'):
                # Convert to seconds (rounded up)
                retry_after = int(exc.wait) + 1
                response['Retry-After'] = str(retry_after)
            else:
                # Default to 1 hour if wait time not available
                response['Retry-After'] = '3600'
            
            # Enhance error message
            if 'detail' in response.data:
                original_detail = response.data['detail']
                response.data = {
                    'error': 'rate_limit_exceeded',
                    'message': str(original_detail),
                    'retry_after_seconds': response['Retry-After'],
                }
        
        # Add error type for other errors
        elif response.status_code >= 400:
            if isinstance(response.data, dict) and 'detail' in response.data:
                error_detail = response.data['detail']
                response.data = {
                    'error': get_error_type(response.status_code),
                    'message': str(error_detail),
                }
    
    return response


def get_error_type(status_code: int) -> str:
    """
    Get error type string from HTTP status code.
    
    Args:
        status_code: HTTP status code
        
    Returns:
        str: Error type identifier
    """
    error_types = {
        400: 'bad_request',
        401: 'unauthorized',
        403: 'forbidden',
        404: 'not_found',
        405: 'method_not_allowed',
        409: 'conflict',
        422: 'validation_error',
        429: 'rate_limit_exceeded',
        500: 'internal_server_error',
        502: 'bad_gateway',
        503: 'service_unavailable',
        504: 'gateway_timeout',
    }
    
    return error_types.get(status_code, 'error')
