"""
Retryable Celery task base class with exponential backoff.

Provides automatic retry logic for transient failures with exponential
backoff, error classification, and comprehensive logging.

Requirements: 13.1-13.7
"""

import logging
from typing import Type, Tuple
from celery import Task
from celery.exceptions import Retry
import httpx


logger = logging.getLogger(__name__)


class RetryableTask(Task):
    """
    Base Celery task with exponential backoff retry.
    
    Automatically retries tasks on transient failures with exponential
    backoff. Classifies errors as transient (retry) or permanent (fail).
    
    Configuration:
    - max_retries: 5 attempts
    - Backoff: 1s, 2s, 4s, 8s, 16s (exponential with jitter)
    - Transient errors: network timeout, 429 rate limit, 5xx server errors
    - Permanent errors: 401 unauthorized, 403 forbidden, 400 bad request
    
    Requirements: 13.1-13.7
    """
    
    # Transient exceptions that should trigger retry
    autoretry_for = (
        httpx.TimeoutException,
        httpx.NetworkError,
        httpx.ConnectTimeout,
        httpx.ReadTimeout,
        httpx.WriteTimeout,
        httpx.PoolTimeout,
        httpx.ConnectError,
        httpx.RemoteProtocolError,
    )
    
    # Retry configuration
    retry_kwargs = {
        'max_retries': 5,
        'countdown': 1  # Initial delay in seconds
    }
    
    # Enable exponential backoff
    retry_backoff = True
    retry_backoff_max = 16  # Max 16 seconds between retries
    retry_jitter = True  # Add randomness to prevent thundering herd
    
    def should_retry(self, exc: Exception) -> bool:
        """
        Determine if exception is retryable.
        
        Classifies errors as transient (should retry) or permanent
        (should not retry) based on error type and HTTP status codes.
        
        Args:
            exc: Exception that occurred during task execution
            
        Returns:
            True if error is transient and should be retried
            
        Requirements: 13.5, 13.6
        """
        # Network and timeout errors - always retry
        if isinstance(exc, (
            httpx.TimeoutException,
            httpx.NetworkError,
            httpx.ConnectTimeout,
            httpx.ReadTimeout,
            httpx.WriteTimeout,
            httpx.PoolTimeout,
            httpx.ConnectError,
            httpx.RemoteProtocolError,
        )):
            logger.info(
                f"Transient network error detected: {type(exc).__name__}",
                extra={'exception': str(exc)}
            )
            return True
        
        # HTTP status errors - classify by status code
        if isinstance(exc, httpx.HTTPStatusError):
            status_code = exc.response.status_code
            
            # Rate limit (429) - retry
            if status_code == 429:
                logger.info(
                    f"Rate limit error (429) detected, will retry",
                    extra={'status_code': status_code}
                )
                return True
            
            # Server errors (5xx) - retry
            if 500 <= status_code < 600:
                logger.info(
                    f"Server error ({status_code}) detected, will retry",
                    extra={'status_code': status_code}
                )
                return True
            
            # Client errors (4xx except 429) - don't retry
            if 400 <= status_code < 500:
                logger.warning(
                    f"Client error ({status_code}) detected, will not retry",
                    extra={'status_code': status_code}
                )
                return False
        
        # Unknown error - don't retry by default
        logger.warning(
            f"Unknown error type: {type(exc).__name__}, will not retry",
            extra={'exception': str(exc)}
        )
        return False
    
    def on_retry(self, exc, task_id, args, kwargs, einfo):
        """
        Log retry attempts with context.
        
        Called automatically by Celery when a task is retried.
        Logs retry attempt number, exception details, and task context.
        
        Args:
            exc: Exception that triggered the retry
            task_id: Unique task identifier
            args: Task positional arguments
            kwargs: Task keyword arguments
            einfo: Exception info object
            
        Requirements: 13.7
        """
        retry_count = self.request.retries
        max_retries = self.max_retries
        
        # Calculate next retry delay (exponential backoff)
        if self.retry_backoff:
            next_delay = min(
                2 ** retry_count,  # Exponential: 1, 2, 4, 8, 16
                self.retry_backoff_max
            )
        else:
            next_delay = self.retry_kwargs.get('countdown', 1)
        
        logger.warning(
            f"Task {self.name} retry {retry_count}/{max_retries} "
            f"(next attempt in {next_delay}s)",
            extra={
                'task_id': task_id,
                'task_name': self.name,
                'retry_count': retry_count,
                'max_retries': max_retries,
                'next_delay_seconds': next_delay,
                'exception_type': type(exc).__name__,
                'exception_message': str(exc),
                'args': args,
                'kwargs': kwargs
            }
        )
    
    def on_failure(self, exc, task_id, args, kwargs, einfo):
        """
        Log task failure after all retries exhausted.
        
        Called automatically by Celery when a task fails permanently
        after exhausting all retry attempts.
        
        Args:
            exc: Exception that caused the failure
            task_id: Unique task identifier
            args: Task positional arguments
            kwargs: Task keyword arguments
            einfo: Exception info object
        """
        logger.error(
            f"Task {self.name} failed permanently after {self.request.retries} retries",
            extra={
                'task_id': task_id,
                'task_name': self.name,
                'retry_count': self.request.retries,
                'exception_type': type(exc).__name__,
                'exception_message': str(exc),
                'args': args,
                'kwargs': kwargs,
                'traceback': str(einfo)
            }
        )
    
    def on_success(self, retval, task_id, args, kwargs):
        """
        Log successful task completion.
        
        Called automatically by Celery when a task completes successfully.
        
        Args:
            retval: Return value of the task
            task_id: Unique task identifier
            args: Task positional arguments
            kwargs: Task keyword arguments
        """
        if self.request.retries > 0:
            logger.info(
                f"Task {self.name} succeeded after {self.request.retries} retries",
                extra={
                    'task_id': task_id,
                    'task_name': self.name,
                    'retry_count': self.request.retries,
                    'args': args,
                    'kwargs': kwargs
                }
            )
        else:
            logger.debug(
                f"Task {self.name} completed successfully",
                extra={
                    'task_id': task_id,
                    'task_name': self.name,
                    'args': args,
                    'kwargs': kwargs
                }
            )


class TransientError(Exception):
    """
    Exception indicating a transient error that should be retried.
    
    Use this exception to explicitly mark errors as transient when
    the automatic classification in should_retry() is insufficient.
    """
    pass


class PermanentError(Exception):
    """
    Exception indicating a permanent error that should not be retried.
    
    Use this exception to explicitly mark errors as permanent when
    the automatic classification in should_retry() is insufficient.
    """
    pass
