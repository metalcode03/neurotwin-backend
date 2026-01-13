"""
Custom exception handling for NeuroTwin REST API.

Provides consistent error response format across all API endpoints.
Requirements: 13.4 - Appropriate HTTP status codes and descriptive error messages
"""

from typing import Any, Optional

from rest_framework.views import exception_handler
from rest_framework.response import Response
from rest_framework import status
from rest_framework.exceptions import (
    APIException,
    ValidationError,
    AuthenticationFailed,
    NotAuthenticated,
    PermissionDenied,
    NotFound,
    Throttled,
)

# JWT-related exceptions that should return 401
JWT_EXCEPTIONS = []

try:
    from jwt.exceptions import (
        InvalidTokenError,
        DecodeError,
        InvalidSignatureError,
        ExpiredSignatureError,
        InvalidAudienceError,
        InvalidIssuerError,
        InvalidIssuedAtError,
        ImmatureSignatureError,
        InvalidKeyError,
        InvalidAlgorithmError,
        MissingRequiredClaimError,
    )
    JWT_EXCEPTIONS.extend([
        InvalidTokenError,
        DecodeError,
        InvalidSignatureError,
        ExpiredSignatureError,
        InvalidAudienceError,
        InvalidIssuerError,
        InvalidIssuedAtError,
        ImmatureSignatureError,
        InvalidKeyError,
        InvalidAlgorithmError,
        MissingRequiredClaimError,
    ])
except ImportError:
    pass

try:
    from rest_framework_simplejwt.exceptions import (
        InvalidToken,
        TokenError,
        AuthenticationFailed as JWTAuthenticationFailed,
    )
    JWT_EXCEPTIONS.extend([InvalidToken, TokenError, JWTAuthenticationFailed])
except ImportError:
    pass

# Convert to tuple for isinstance check
JWT_EXCEPTION_CLASSES = tuple(JWT_EXCEPTIONS) if JWT_EXCEPTIONS else ()


def is_jwt_exception(exc: Exception) -> bool:
    """Check if exception is JWT-related."""
    if JWT_EXCEPTION_CLASSES and isinstance(exc, JWT_EXCEPTION_CLASSES):
        return True
    # Also check by exception name for edge cases
    exc_name = type(exc).__name__.lower()
    jwt_keywords = ['token', 'jwt', 'decode', 'signature', 'claim']
    return any(keyword in exc_name for keyword in jwt_keywords)


def custom_exception_handler(exc: Exception, context: dict) -> Optional[Response]:
    """
    Custom exception handler for consistent error response format.
    
    All error responses follow the format:
    {
        "success": false,
        "error": {
            "code": "ERROR_CODE",
            "message": "Human-readable error message",
            "details": {...}  # Optional additional details
        }
    }
    
    Requirements: 13.4
    """
    # Handle JWT-related exceptions as 401 Unauthorized
    if is_jwt_exception(exc):
        return Response(
            {
                "success": False,
                "error": {
                    "code": "INVALID_TOKEN",
                    "message": "Invalid or malformed authentication token",
                }
            },
            status=status.HTTP_401_UNAUTHORIZED
        )
    
    # Handle UnicodeDecodeError and similar encoding issues in auth context
    if isinstance(exc, (UnicodeDecodeError, UnicodeEncodeError, ValueError)):
        # Check if this is in an authentication context
        view = context.get('view')
        if view and hasattr(view, 'authentication_classes'):
            return Response(
                {
                    "success": False,
                    "error": {
                        "code": "INVALID_TOKEN",
                        "message": "Invalid or malformed authentication token",
                    }
                },
                status=status.HTTP_401_UNAUTHORIZED
            )
    
    # Call REST framework's default exception handler first
    response = exception_handler(exc, context)
    
    if response is None:
        # Unhandled exception - return 500
        return Response(
            {
                "success": False,
                "error": {
                    "code": "INTERNAL_ERROR",
                    "message": "An unexpected error occurred",
                }
            },
            status=status.HTTP_500_INTERNAL_SERVER_ERROR
        )
    
    # Format the error response consistently
    error_response = format_error_response(exc, response)
    response.data = error_response
    
    return response


def format_error_response(exc: Exception, response: Response) -> dict:
    """
    Format exception into consistent error response structure.
    
    Args:
        exc: The exception that was raised
        response: The initial response from DRF's exception handler
        
    Returns:
        Formatted error response dictionary
    """
    error_code = get_error_code(exc, response.status_code)
    error_message = get_error_message(exc, response)
    
    error_data = {
        "success": False,
        "error": {
            "code": error_code,
            "message": error_message,
        }
    }
    
    # Add details for validation errors
    if isinstance(exc, ValidationError):
        error_data["error"]["details"] = response.data
    
    # Add retry-after for throttled requests
    if isinstance(exc, Throttled):
        error_data["error"]["retry_after"] = exc.wait
    
    return error_data


def get_error_code(exc: Exception, status_code: int) -> str:
    """
    Get appropriate error code based on exception type.
    
    Args:
        exc: The exception that was raised
        status_code: HTTP status code
        
    Returns:
        Error code string
    """
    error_codes = {
        AuthenticationFailed: "AUTHENTICATION_FAILED",
        NotAuthenticated: "NOT_AUTHENTICATED",
        PermissionDenied: "PERMISSION_DENIED",
        NotFound: "NOT_FOUND",
        ValidationError: "VALIDATION_ERROR",
        Throttled: "RATE_LIMIT_EXCEEDED",
    }
    
    for exc_class, code in error_codes.items():
        if isinstance(exc, exc_class):
            return code
    
    # Default codes based on status
    status_codes = {
        400: "BAD_REQUEST",
        401: "UNAUTHORIZED",
        403: "FORBIDDEN",
        404: "NOT_FOUND",
        405: "METHOD_NOT_ALLOWED",
        409: "CONFLICT",
        429: "RATE_LIMIT_EXCEEDED",
        500: "INTERNAL_ERROR",
    }
    
    return status_codes.get(status_code, "ERROR")


def get_error_message(exc: Exception, response: Response) -> str:
    """
    Get human-readable error message from exception.
    
    Args:
        exc: The exception that was raised
        response: The initial response from DRF's exception handler
        
    Returns:
        Human-readable error message
    """
    if hasattr(exc, 'detail'):
        detail = exc.detail
        
        # Handle list of errors
        if isinstance(detail, list):
            return str(detail[0]) if detail else "An error occurred"
        
        # Handle dict of errors (validation errors)
        if isinstance(detail, dict):
            # Get first error message
            for field, errors in detail.items():
                if isinstance(errors, list) and errors:
                    return f"{field}: {errors[0]}"
                elif isinstance(errors, str):
                    return f"{field}: {errors}"
            return "Validation error"
        
        return str(detail)
    
    return str(exc) if str(exc) else "An error occurred"


# Custom API Exceptions

class BusinessLogicError(APIException):
    """Exception for business logic errors."""
    status_code = status.HTTP_400_BAD_REQUEST
    default_detail = "A business logic error occurred"
    default_code = "BUSINESS_ERROR"


class ResourceConflictError(APIException):
    """Exception for resource conflicts (e.g., duplicate entries)."""
    status_code = status.HTTP_409_CONFLICT
    default_detail = "Resource conflict"
    default_code = "CONFLICT"


class FeatureNotAvailableError(APIException):
    """Exception when a feature is not available for user's subscription tier."""
    status_code = status.HTTP_403_FORBIDDEN
    default_detail = "This feature is not available for your subscription tier"
    default_code = "FEATURE_NOT_AVAILABLE"


class KillSwitchActiveError(APIException):
    """Exception when kill switch is active and action is blocked."""
    status_code = status.HTTP_403_FORBIDDEN
    default_detail = "Kill switch is active. All automations are halted."
    default_code = "KILL_SWITCH_ACTIVE"


class PermissionRequiredError(APIException):
    """Exception when explicit permission is required for an action."""
    status_code = status.HTTP_403_FORBIDDEN
    default_detail = "Explicit permission required for this action"
    default_code = "PERMISSION_REQUIRED"
