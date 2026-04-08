"""
Structured logging service for integration events.

Requirements: 30.1-30.7
"""
import json
import logging
from typing import Optional, Dict, Any
from datetime import datetime
from django.utils import timezone

logger = logging.getLogger('automation.events')


class StructuredLogger:
    """
    Service for structured JSON logging of integration events.
    
    Logs include:
    - Authentication attempts
    - Webhook events
    - Message sends
    - Rate limit violations
    
    Requirements: 30.1-30.7
    """
    
    @staticmethod
    def _log_event(
        event_type: str,
        level: str,
        message: str,
        **kwargs
    ) -> None:
        """
        Log a structured event as JSON.
        
        Args:
            event_type: Type of event (auth, webhook, message, rate_limit)
            level: Log level (info, warning, error)
            message: Human-readable message
            **kwargs: Additional structured data
        """
        log_data = {
            'timestamp': timezone.now().isoformat(),
            'event_type': event_type,
            'message': message,
            **kwargs
        }
        
        log_message = json.dumps(log_data)
        
        if level == 'info':
            logger.info(log_message)
        elif level == 'warning':
            logger.warning(log_message)
        elif level == 'error':
            logger.error(log_message)
        else:
            logger.debug(log_message)
    
    @classmethod
    def log_authentication_attempt(
        cls,
        user_id: str,
        integration_type_id: str,
        auth_type: str,
        result: str,
        duration_ms: Optional[float] = None,
        error_message: Optional[str] = None
    ) -> None:
        """
        Log an authentication attempt.
        
        Args:
            user_id: User identifier
            integration_type_id: Integration type ID
            auth_type: Authentication type (oauth, meta, api_key)
            result: Result (success, failure)
            duration_ms: Duration in milliseconds
            error_message: Error message if failed
        """
        level = 'info' if result == 'success' else 'error'
        
        cls._log_event(
            event_type='authentication',
            level=level,
            message=f"Authentication {result} for {auth_type}",
            user_id=user_id,
            integration_type_id=integration_type_id,
            auth_type=auth_type,
            result=result,
            duration_ms=duration_ms,
            error_message=error_message
        )
    
    @classmethod
    def log_webhook_event(
        cls,
        integration_type: str,
        integration_id: Optional[str],
        event_type: str,
        processing_status: str,
        duration_ms: Optional[float] = None,
        error_message: Optional[str] = None
    ) -> None:
        """
        Log a webhook event.
        
        Args:
            integration_type: Integration type name
            integration_id: Integration ID (if identified)
            event_type: Type of webhook event
            processing_status: Status (pending, processing, processed, failed)
            duration_ms: Processing duration in milliseconds
            error_message: Error message if failed
        """
        level = 'info' if processing_status == 'processed' else 'warning'
        if processing_status == 'failed':
            level = 'error'
        
        cls._log_event(
            event_type='webhook',
            level=level,
            message=f"Webhook {event_type} {processing_status}",
            integration_type=integration_type,
            integration_id=integration_id,
            webhook_event_type=event_type,
            processing_status=processing_status,
            duration_ms=duration_ms,
            error_message=error_message
        )
    
    @classmethod
    def log_message_send(
        cls,
        integration_id: str,
        message_id: str,
        status: str,
        duration_ms: Optional[float] = None,
        retry_count: int = 0,
        error_message: Optional[str] = None
    ) -> None:
        """
        Log a message send attempt.
        
        Args:
            integration_id: Integration ID
            message_id: Message ID
            status: Status (sent, failed, pending)
            duration_ms: Send duration in milliseconds
            retry_count: Number of retries
            error_message: Error message if failed
        """
        level = 'info' if status == 'sent' else 'warning'
        if status == 'failed':
            level = 'error'
        
        cls._log_event(
            event_type='message_send',
            level=level,
            message=f"Message {status}",
            integration_id=integration_id,
            message_id=message_id,
            status=status,
            duration_ms=duration_ms,
            retry_count=retry_count,
            error_message=error_message
        )
    
    @classmethod
    def log_rate_limit_violation(
        cls,
        integration_id: str,
        limit_type: str,
        attempted_rate: int,
        limit: int,
        wait_seconds: int
    ) -> None:
        """
        Log a rate limit violation.
        
        Args:
            integration_id: Integration ID
            limit_type: Type of limit (per_integration, global)
            attempted_rate: Attempted request rate
            limit: Rate limit threshold
            wait_seconds: Seconds to wait before retry
        """
        cls._log_event(
            event_type='rate_limit_violation',
            level='warning',
            message=f"Rate limit exceeded for {limit_type}",
            integration_id=integration_id,
            limit_type=limit_type,
            attempted_rate=attempted_rate,
            limit=limit,
            wait_seconds=wait_seconds
        )
    
    @classmethod
    def log_integration_health_change(
        cls,
        integration_id: str,
        old_status: str,
        new_status: str,
        consecutive_failures: int
    ) -> None:
        """
        Log an integration health status change.
        
        Args:
            integration_id: Integration ID
            old_status: Previous health status
            new_status: New health status
            consecutive_failures: Number of consecutive failures
        """
        level = 'warning' if new_status == 'degraded' else 'error'
        if new_status == 'healthy':
            level = 'info'
        
        cls._log_event(
            event_type='health_status_change',
            level=level,
            message=f"Integration health changed from {old_status} to {new_status}",
            integration_id=integration_id,
            old_status=old_status,
            new_status=new_status,
            consecutive_failures=consecutive_failures
        )
    
    @classmethod
    def log_token_refresh(
        cls,
        integration_id: str,
        auth_type: str,
        result: str,
        error_message: Optional[str] = None
    ) -> None:
        """
        Log a token refresh attempt.
        
        Args:
            integration_id: Integration ID
            auth_type: Authentication type
            result: Result (success, failure)
            error_message: Error message if failed
        """
        level = 'info' if result == 'success' else 'error'
        
        cls._log_event(
            event_type='token_refresh',
            level=level,
            message=f"Token refresh {result}",
            integration_id=integration_id,
            auth_type=auth_type,
            result=result,
            error_message=error_message
        )
