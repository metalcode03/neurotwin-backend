"""
Custom exception handler for automation system.

Provides consistent error response formatting and logging.
Requirements: 29.1-29.7
"""

import logging
from typing import Any, Dict, Optional

from django.core.exceptions import ValidationError, PermissionDenied
from django.http import Http404
from rest_framework import status
from rest_framework.response import Response
from rest_framework.views import exception_handler as drf_exception_handler

from .exceptions import AutomationException


logger = logging.getLogger(__name__)


def automation_exception_handler(exc: Exception, context: Dict[str, Any]) -> Optional[Response]:
    """
    Custom exception handler for automation system.
    
    Formats error responses consistently with error_code and details fields.
    Maps exceptions to appropriate HTTP status codes.
    Logs all errors with context.
    
    Requirements: 29.1-29.7
    
    Args:
        exc: The exception that was raised
        context: Context dictionary containing request and view information
        
    Returns:
        Response object with formatted error, or None to use default handler
    """
    
    # Get request information for logging
    request = context.get('request')
    view = context.get('view')
    
    request_info = {}
    if request:
        request_info = {
            'method': request.method,
            'path': request.path,
            'user': str(request.user) if hasattr(request, 'user') else 'anonymous',
        }
    
    # Handle custom automation exceptions
    if isinstance(exc, AutomationException):
        error_response = {
            'error': {
                'code': exc.error_code,
                'message': exc.message,
                'details': exc.details
            }
        }
        
        # Log error with context
        logger.error(
            f"Automation error: {exc.error_code}",
            extra={
                'error_code': exc.error_code,
                'message': exc.message,
                'details': exc.details,
                'status_code': exc.status_code,
                **request_info
            },
            exc_info=True
        )
        
        return Response(
            error_response,
            status=exc.status_code
        )
    
    # Handle Django validation errors
    if isinstance(exc, ValidationError):
        error_response = {
            'error': {
                'code': 'VALIDATION_ERROR',
                'message': 'Validation failed',
                'details': {
                    'errors': exc.message_dict if hasattr(exc, 'message_dict') else {'non_field_errors': exc.messages}
                }
            }
        }
        
        logger.warning(
            "Validation error",
            extra={
                'error_code': 'VALIDATION_ERROR',
                'errors': exc.message_dict if hasattr(exc, 'message_dict') else exc.messages,
                **request_info
            }
        )
        
        return Response(error_response, status=status.HTTP_400_BAD_REQUEST)
    
    # Handle Django permission denied
    if isinstance(exc, PermissionDenied):
        error_response = {
            'error': {
                'code': 'PERMISSION_DENIED',
                'message': str(exc) or 'You do not have permission to perform this action',
                'details': {}
            }
        }
        
        logger.warning(
            "Permission denied",
            extra={
                'error_code': 'PERMISSION_DENIED',
                'message': str(exc),
                **request_info
            }
        )
        
        return Response(error_response, status=status.HTTP_403_FORBIDDEN)
    
    # Handle Django 404
    if isinstance(exc, Http404):
        error_response = {
            'error': {
                'code': 'NOT_FOUND',
                'message': str(exc) or 'Resource not found',
                'details': {}
            }
        }
        
        logger.info(
            "Resource not found",
            extra={
                'error_code': 'NOT_FOUND',
                **request_info
            }
        )
        
        return Response(error_response, status=status.HTTP_404_NOT_FOUND)
    
    # Use DRF's default exception handler for other cases
    response = drf_exception_handler(exc, context)
    
    if response is not None:
        # Format DRF exceptions consistently
        if isinstance(response.data, dict):
            # Check if already formatted
            if 'error' not in response.data:
                error_response = {
                    'error': {
                        'code': 'API_ERROR',
                        'message': 'An error occurred',
                        'details': response.data
                    }
                }
                response.data = error_response
        
        # Log DRF exceptions
        logger.error(
            f"DRF exception: {exc.__class__.__name__}",
            extra={
                'error_code': 'API_ERROR',
                'exception_type': exc.__class__.__name__,
                'status_code': response.status_code,
                **request_info
            },
            exc_info=True
        )
        
        return response
    
    # Handle unexpected exceptions
    logger.exception(
        f"Unexpected exception: {exc.__class__.__name__}",
        extra={
            'error_code': 'INTERNAL_ERROR',
            'exception_type': exc.__class__.__name__,
            **request_info
        }
    )
    
    error_response = {
        'error': {
            'code': 'INTERNAL_ERROR',
            'message': 'An unexpected error occurred',
            'details': {}
        }
    }
    
    return Response(
        error_response,
        status=status.HTTP_500_INTERNAL_SERVER_ERROR
    )


def format_error_response(
    error_code: str,
    message: str,
    details: Optional[Dict[str, Any]] = None,
    status_code: int = 400
) -> Response:
    """
    Helper function to format error responses consistently.
    
    Args:
        error_code: Machine-readable error code
        message: Human-readable error message
        details: Additional error details
        status_code: HTTP status code
        
    Returns:
        Response object with formatted error
    """
    return Response(
        {
            'error': {
                'code': error_code,
                'message': message,
                'details': details or {}
            }
        },
        status=status_code
    )
