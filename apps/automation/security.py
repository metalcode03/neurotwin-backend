"""
Security utilities for automation system.

Provides input sanitization, security event logging, and security helpers.
Requirements: 33.3, 33.6
"""

import logging
import re
from typing import Any, Dict, Optional
from html import escape
from django.utils.html import strip_tags
from django.core.exceptions import ValidationError


logger = logging.getLogger('automation.security')


class InputSanitizer:
    """
    Input sanitization utility.
    
    Sanitizes user input before storage and display to prevent XSS and injection attacks.
    Requirements: 33.3
    """
    
    # Patterns for potentially dangerous content
    SCRIPT_PATTERN = re.compile(r'<script[^>]*>.*?</script>', re.IGNORECASE | re.DOTALL)
    STYLE_PATTERN = re.compile(r'<style[^>]*>.*?</style>', re.IGNORECASE | re.DOTALL)
    IFRAME_PATTERN = re.compile(r'<iframe[^>]*>.*?</iframe>', re.IGNORECASE | re.DOTALL)
    OBJECT_PATTERN = re.compile(r'<object[^>]*>.*?</object>', re.IGNORECASE | re.DOTALL)
    EMBED_PATTERN = re.compile(r'<embed[^>]*>', re.IGNORECASE)
    
    # JavaScript event handlers
    EVENT_HANDLER_PATTERN = re.compile(r'\bon\w+\s*=', re.IGNORECASE)
    
    # SQL injection patterns
    SQL_KEYWORDS = ['SELECT', 'INSERT', 'UPDATE', 'DELETE', 'DROP', 'CREATE', 'ALTER', 'EXEC', 'UNION']
    
    @classmethod
    def sanitize_string(cls, value: str, strip_html: bool = True) -> str:
        """
        Sanitize a string value.
        
        Args:
            value: String to sanitize
            strip_html: Whether to strip HTML tags
            
        Returns:
            Sanitized string
        """
        if not isinstance(value, str):
            return value
        
        # Remove dangerous HTML elements
        value = cls.SCRIPT_PATTERN.sub('', value)
        value = cls.STYLE_PATTERN.sub('', value)
        value = cls.IFRAME_PATTERN.sub('', value)
        value = cls.OBJECT_PATTERN.sub('', value)
        value = cls.EMBED_PATTERN.sub('', value)
        
        # Remove event handlers
        value = cls.EVENT_HANDLER_PATTERN.sub('', value)
        
        # Strip HTML tags if requested
        if strip_html:
            value = strip_tags(value)
        
        # Escape HTML entities
        value = escape(value)
        
        return value.strip()
    
    @classmethod
    def sanitize_dict(cls, data: Dict[str, Any], strip_html: bool = True) -> Dict[str, Any]:
        """
        Recursively sanitize dictionary values.
        
        Args:
            data: Dictionary to sanitize
            strip_html: Whether to strip HTML tags
            
        Returns:
            Sanitized dictionary
        """
        if not isinstance(data, dict):
            return data
        
        sanitized = {}
        for key, value in data.items():
            if isinstance(value, str):
                sanitized[key] = cls.sanitize_string(value, strip_html)
            elif isinstance(value, dict):
                sanitized[key] = cls.sanitize_dict(value, strip_html)
            elif isinstance(value, list):
                sanitized[key] = cls.sanitize_list(value, strip_html)
            else:
                sanitized[key] = value
        
        return sanitized
    
    @classmethod
    def sanitize_list(cls, data: list, strip_html: bool = True) -> list:
        """
        Recursively sanitize list values.
        
        Args:
            data: List to sanitize
            strip_html: Whether to strip HTML tags
            
        Returns:
            Sanitized list
        """
        if not isinstance(data, list):
            return data
        
        sanitized = []
        for item in data:
            if isinstance(item, str):
                sanitized.append(cls.sanitize_string(item, strip_html))
            elif isinstance(item, dict):
                sanitized.append(cls.sanitize_dict(item, strip_html))
            elif isinstance(item, list):
                sanitized.append(cls.sanitize_list(item, strip_html))
            else:
                sanitized.append(item)
        
        return sanitized
    
    @classmethod
    def validate_no_sql_injection(cls, value: str) -> None:
        """
        Validate that string doesn't contain SQL injection patterns.
        
        Args:
            value: String to validate
            
        Raises:
            ValidationError: If SQL injection pattern detected
        """
        if not isinstance(value, str):
            return
        
        value_upper = value.upper()
        
        # Check for SQL keywords in suspicious contexts
        for keyword in cls.SQL_KEYWORDS:
            # Look for SQL keywords followed by common SQL syntax
            if re.search(rf'\b{keyword}\b.*\b(FROM|INTO|WHERE|SET|TABLE)\b', value_upper):
                logger.warning(
                    "Potential SQL injection attempt detected",
                    extra={
                        'value': value[:100],  # Log first 100 chars
                        'keyword': keyword
                    }
                )
                raise ValidationError(f"Invalid input: contains suspicious SQL pattern")


class SecurityEventLogger:
    """
    Security event logging utility.
    
    Logs all security-relevant events for audit.
    Requirements: 33.6
    """
    
    @staticmethod
    def log_authentication_attempt(
        user_id: Optional[str],
        username: str,
        success: bool,
        ip_address: str,
        user_agent: str,
        failure_reason: Optional[str] = None
    ) -> None:
        """
        Log authentication attempt.
        
        Args:
            user_id: User ID if authentication succeeded
            username: Username or email used
            success: Whether authentication succeeded
            ip_address: Client IP address
            user_agent: Client user agent
            failure_reason: Reason for failure if applicable
        """
        logger.info(
            f"Authentication {'succeeded' if success else 'failed'}: {username}",
            extra={
                'event_type': 'authentication_attempt',
                'user_id': user_id,
                'username': username,
                'success': success,
                'ip_address': ip_address,
                'user_agent': user_agent,
                'failure_reason': failure_reason,
            }
        )
    
    @staticmethod
    def log_webhook_signature_failure(
        integration_type: str,
        integration_id: Optional[str],
        ip_address: str,
        payload_hash: str
    ) -> None:
        """
        Log webhook signature verification failure.
        
        Args:
            integration_type: Type of integration
            integration_id: Integration ID if known
            ip_address: Client IP address
            payload_hash: Hash of payload for tracking
        """
        logger.warning(
            f"Webhook signature verification failed: {integration_type}",
            extra={
                'event_type': 'webhook_signature_failure',
                'integration_type': integration_type,
                'integration_id': integration_id,
                'ip_address': ip_address,
                'payload_hash': payload_hash,
            }
        )
    
    @staticmethod
    def log_rate_limit_violation(
        user_id: Optional[str],
        integration_id: Optional[str],
        limit_type: str,
        attempted_rate: int,
        limit: int,
        ip_address: str
    ) -> None:
        """
        Log rate limit violation.
        
        Args:
            user_id: User ID if authenticated
            integration_id: Integration ID if applicable
            limit_type: Type of rate limit (per_integration, global, auth)
            attempted_rate: Attempted request rate
            limit: Rate limit threshold
            ip_address: Client IP address
        """
        logger.warning(
            f"Rate limit violation: {limit_type}",
            extra={
                'event_type': 'rate_limit_violation',
                'user_id': user_id,
                'integration_id': integration_id,
                'limit_type': limit_type,
                'attempted_rate': attempted_rate,
                'limit': limit,
                'ip_address': ip_address,
            }
        )
    
    @staticmethod
    def log_integration_deletion(
        user_id: str,
        integration_id: str,
        integration_type: str,
        revocation_success: bool,
        ip_address: str
    ) -> None:
        """
        Log integration deletion.
        
        Args:
            user_id: User ID
            integration_id: Integration ID
            integration_type: Type of integration
            revocation_success: Whether credential revocation succeeded
            ip_address: Client IP address
        """
        logger.info(
            f"Integration deleted: {integration_type}",
            extra={
                'event_type': 'integration_deletion',
                'user_id': user_id,
                'integration_id': integration_id,
                'integration_type': integration_type,
                'revocation_success': revocation_success,
                'ip_address': ip_address,
            }
        )
    
    @staticmethod
    def log_csrf_failure(
        user_id: Optional[str],
        path: str,
        method: str,
        ip_address: str
    ) -> None:
        """
        Log CSRF token validation failure.
        
        Args:
            user_id: User ID if authenticated
            path: Request path
            method: HTTP method
            ip_address: Client IP address
        """
        logger.warning(
            f"CSRF validation failed: {method} {path}",
            extra={
                'event_type': 'csrf_failure',
                'user_id': user_id,
                'path': path,
                'method': method,
                'ip_address': ip_address,
            }
        )
    
    @staticmethod
    def log_permission_denied(
        user_id: str,
        resource_type: str,
        resource_id: str,
        action: str,
        ip_address: str
    ) -> None:
        """
        Log permission denied event.
        
        Args:
            user_id: User ID
            resource_type: Type of resource (integration, workflow, etc.)
            resource_id: Resource ID
            action: Attempted action
            ip_address: Client IP address
        """
        logger.warning(
            f"Permission denied: {action} on {resource_type}",
            extra={
                'event_type': 'permission_denied',
                'user_id': user_id,
                'resource_type': resource_type,
                'resource_id': resource_id,
                'action': action,
                'ip_address': ip_address,
            }
        )


def get_client_ip(request) -> str:
    """
    Get client IP address from request.
    
    Handles X-Forwarded-For header for proxied requests.
    
    Args:
        request: Django request object
        
    Returns:
        Client IP address
    """
    x_forwarded_for = request.META.get('HTTP_X_FORWARDED_FOR')
    if x_forwarded_for:
        ip = x_forwarded_for.split(',')[0].strip()
    else:
        ip = request.META.get('REMOTE_ADDR', 'unknown')
    return ip


def get_user_agent(request) -> str:
    """
    Get user agent from request.
    
    Args:
        request: Django request object
        
    Returns:
        User agent string
    """
    return request.META.get('HTTP_USER_AGENT', 'unknown')
