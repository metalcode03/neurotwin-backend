"""
Security middleware for automation system.

Provides input sanitization and security logging.
Requirements: 33.3, 33.4, 33.6
"""

import json
import logging
from typing import Callable
from django.http import HttpRequest, HttpResponse, JsonResponse, QueryDict
from django.utils.deprecation import MiddlewareMixin
from django.views.decorators.csrf import csrf_exempt
from django.middleware.csrf import CsrfViewMiddleware

from ..security import InputSanitizer, SecurityEventLogger, get_client_ip


logger = logging.getLogger('automation.security')


class InputSanitizationMiddleware(MiddlewareMixin):
    """
    Middleware to sanitize all user input before processing.
    
    Sanitizes POST, PUT, PATCH request data to prevent XSS and injection attacks.
    Requirements: 33.3
    """
    
    # Paths to exclude from sanitization (e.g., webhook endpoints that need raw data)
    EXCLUDED_PATHS = [
        '/api/v1/webhooks/',
    ]
    
    def process_request(self, request: HttpRequest) -> None:
        """
        Sanitize request data before view processing.
        
        Args:
            request: Django request object
        """
        # Skip sanitization for excluded paths
        if any(request.path.startswith(path) for path in self.EXCLUDED_PATHS):
            return None
        
        # Only sanitize state-changing methods
        if request.method not in ['POST', 'PUT', 'PATCH']:
            return None
        
        # Sanitize JSON request body
        if request.content_type == 'application/json' and request.body:
            try:
                data = json.loads(request.body)
                if isinstance(data, dict):
                    sanitized_data = InputSanitizer.sanitize_dict(data)
                    # Replace request body with sanitized data
                    request._body = json.dumps(sanitized_data).encode('utf-8')
                elif isinstance(data, list):
                    sanitized_data = InputSanitizer.sanitize_list(data)
                    request._body = json.dumps(sanitized_data).encode('utf-8')
            except (json.JSONDecodeError, UnicodeDecodeError):
                # Let the view handle invalid JSON
                pass
        
        # Sanitize POST data, but NEVER touch the CSRF token —
        # replacing the QueryDict with a plain dict causes all values to be
        # wrapped in lists, which breaks Django's CSRF length check.
        if request.POST:
            # Keys that must be passed through unchanged
            PROTECTED_KEYS = {'csrfmiddlewaretoken'}

            mutable_post = request.POST.copy()   # copy() returns a mutable QueryDict
            for key in list(mutable_post.keys()):
                if key in PROTECTED_KEYS:
                    continue
                raw_values = mutable_post.getlist(key)
                sanitized_values = [
                    InputSanitizer.sanitize_string(v) if isinstance(v, str) else v
                    for v in raw_values
                ]
                mutable_post.setlist(key, sanitized_values)

            request.POST = mutable_post

        return None


class CSRFLoggingMiddleware(CsrfViewMiddleware):
    """
    CSRF middleware with security event logging.
    
    Extends Django's CSRF middleware to log validation failures.
    Requirements: 33.4, 33.6
    """
    
    def process_view(self, request, callback, callback_args, callback_kwargs):
        """
        Process view and log CSRF failures.
        
        Args:
            request: Django request object
            callback: View function
            callback_args: View args
            callback_kwargs: View kwargs
            
        Returns:
            Response or None
        """
        # Check if view is exempt from CSRF
        if getattr(callback, 'csrf_exempt', False):
            return None
        
        # Call parent CSRF check
        response = super().process_view(request, callback, callback_args, callback_kwargs)
        
        # If CSRF check failed, log the event
        if response is not None and response.status_code == 403:
            SecurityEventLogger.log_csrf_failure(
                user_id=str(request.user.id) if hasattr(request, 'user') and request.user.is_authenticated else None,
                path=request.path,
                method=request.method,
                ip_address=get_client_ip(request)
            )
        
        return response


class SecurityHeadersMiddleware(MiddlewareMixin):
    """
    Middleware to add security headers to responses.
    
    Requirements: 33.1, 33.2
    """
    
    def process_response(self, request: HttpRequest, response: HttpResponse) -> HttpResponse:
        """
        Add security headers to response.
        
        Args:
            request: Django request object
            response: Django response object
            
        Returns:
            Response with security headers
        """
        # Prevent clickjacking
        response['X-Frame-Options'] = 'DENY'
        
        # Prevent MIME type sniffing
        response['X-Content-Type-Options'] = 'nosniff'
        
        # Enable XSS protection
        response['X-XSS-Protection'] = '1; mode=block'
        
        # Enforce HTTPS
        if not request.is_secure():
            response['Strict-Transport-Security'] = 'max-age=31536000; includeSubDomains'
        
        # Content Security Policy
        response['Content-Security-Policy'] = (
            "default-src 'self'; "
            "script-src 'self' 'unsafe-inline' 'unsafe-eval'; "
            "style-src 'self' 'unsafe-inline'; "
            "img-src 'self' data: https:; "
            "font-src 'self' data:; "
            "connect-src 'self' https:; "
            "frame-ancestors 'none';"
        )
        
        # Referrer Policy
        response['Referrer-Policy'] = 'strict-origin-when-cross-origin'
        
        # Permissions Policy
        response['Permissions-Policy'] = (
            "geolocation=(), "
            "microphone=(), "
            "camera=(), "
            "payment=(), "
            "usb=(), "
            "magnetometer=(), "
            "gyroscope=(), "
            "accelerometer=()"
        )
        
        return response
