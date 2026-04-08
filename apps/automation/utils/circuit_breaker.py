"""
Circuit Breaker Pattern Implementation

Provides fault tolerance for external API calls by preventing cascading failures.
Implements state transitions: closed → open → half_open

Requirements: 32.3-32.4
"""

import time
import logging
from enum import Enum
from typing import Callable, Any, Optional
from dataclasses import dataclass
from threading import Lock

logger = logging.getLogger(__name__)


class CircuitState(Enum):
    """Circuit breaker states"""
    CLOSED = "closed"  # Normal operation, requests pass through
    OPEN = "open"  # Circuit is open, requests fail immediately
    HALF_OPEN = "half_open"  # Testing if service recovered


@dataclass
class CircuitBreakerConfig:
    """Configuration for circuit breaker"""
    failure_threshold: int = 5  # Number of failures before opening circuit
    timeout: int = 60  # Seconds to wait before attempting recovery (open → half_open)
    success_threshold: int = 2  # Successful calls needed in half_open to close circuit


class CircuitBreakerOpenException(Exception):
    """Raised when circuit breaker is open"""
    pass


class CircuitBreaker:
    """
    Circuit breaker for external API calls.
    
    Tracks failures and implements state transitions to prevent cascading failures.
    
    States:
    - CLOSED: Normal operation, all requests pass through
    - OPEN: Too many failures, requests fail immediately without calling external API
    - HALF_OPEN: Testing recovery, limited requests allowed
    
    Requirements: 32.3-32.4
    """
    
    def __init__(
        self,
        name: str,
        failure_threshold: int = 5,
        timeout: int = 60,
        success_threshold: int = 2
    ):
        """
        Initialize circuit breaker.
        
        Args:
            name: Identifier for this circuit breaker (for logging)
            failure_threshold: Number of failures before opening circuit
            timeout: Seconds to wait before attempting recovery
            success_threshold: Successful calls needed in half_open to close
        """
        self.name = name
        self.config = CircuitBreakerConfig(
            failure_threshold=failure_threshold,
            timeout=timeout,
            success_threshold=success_threshold
        )
        
        self._state = CircuitState.CLOSED
        self._failure_count = 0
        self._success_count = 0
        self._last_failure_time: Optional[float] = None
        self._lock = Lock()
    
    @property
    def state(self) -> CircuitState:
        """Get current circuit state"""
        return self._state
    
    @property
    def failure_count(self) -> int:
        """Get current failure count"""
        return self._failure_count
    
    def call(self, func: Callable, *args, **kwargs) -> Any:
        """
        Execute function with circuit breaker protection.
        
        Args:
            func: Function to execute
            *args: Positional arguments for func
            **kwargs: Keyword arguments for func
            
        Returns:
            Result of func execution
            
        Raises:
            CircuitBreakerOpenException: If circuit is open
            Exception: Any exception raised by func
        """
        with self._lock:
            # Check if we should transition from OPEN to HALF_OPEN
            if self._state == CircuitState.OPEN:
                if self._should_attempt_reset():
                    self._transition_to_half_open()
                else:
                    logger.warning(
                        f"Circuit breaker '{self.name}' is OPEN. "
                        f"Failing fast without calling external API."
                    )
                    raise CircuitBreakerOpenException(
                        f"Circuit breaker '{self.name}' is open. "
                        f"Service unavailable. Retry after {self._time_until_retry():.0f} seconds."
                    )
        
        # Execute the function
        try:
            result = func(*args, **kwargs)
            self._on_success()
            return result
        except Exception as e:
            self._on_failure(e)
            raise
    
    def _should_attempt_reset(self) -> bool:
        """Check if enough time has passed to attempt recovery"""
        if self._last_failure_time is None:
            return True
        
        elapsed = time.time() - self._last_failure_time
        return elapsed >= self.config.timeout
    
    def _time_until_retry(self) -> float:
        """Calculate seconds until retry is allowed"""
        if self._last_failure_time is None:
            return 0.0
        
        elapsed = time.time() - self._last_failure_time
        remaining = self.config.timeout - elapsed
        return max(0.0, remaining)
    
    def _on_success(self):
        """Handle successful call"""
        with self._lock:
            if self._state == CircuitState.HALF_OPEN:
                self._success_count += 1
                logger.info(
                    f"Circuit breaker '{self.name}' success in HALF_OPEN state. "
                    f"Success count: {self._success_count}/{self.config.success_threshold}"
                )
                
                if self._success_count >= self.config.success_threshold:
                    self._transition_to_closed()
            
            elif self._state == CircuitState.CLOSED:
                # Reset failure count on success
                if self._failure_count > 0:
                    logger.info(
                        f"Circuit breaker '{self.name}' success. "
                        f"Resetting failure count from {self._failure_count} to 0."
                    )
                    self._failure_count = 0
    
    def _on_failure(self, exception: Exception):
        """Handle failed call"""
        with self._lock:
            self._failure_count += 1
            self._last_failure_time = time.time()
            
            logger.warning(
                f"Circuit breaker '{self.name}' failure. "
                f"Failure count: {self._failure_count}/{self.config.failure_threshold}. "
                f"Exception: {type(exception).__name__}: {str(exception)}"
            )
            
            if self._state == CircuitState.HALF_OPEN:
                # Any failure in half_open immediately opens circuit
                self._transition_to_open()
            
            elif self._state == CircuitState.CLOSED:
                if self._failure_count >= self.config.failure_threshold:
                    self._transition_to_open()
    
    def _transition_to_open(self):
        """Transition to OPEN state"""
        self._state = CircuitState.OPEN
        self._success_count = 0
        logger.error(
            f"Circuit breaker '{self.name}' transitioned to OPEN. "
            f"Failure threshold ({self.config.failure_threshold}) exceeded. "
            f"Will retry after {self.config.timeout} seconds."
        )
    
    def _transition_to_half_open(self):
        """Transition to HALF_OPEN state"""
        self._state = CircuitState.HALF_OPEN
        self._success_count = 0
        self._failure_count = 0
        logger.info(
            f"Circuit breaker '{self.name}' transitioned to HALF_OPEN. "
            f"Testing service recovery."
        )
    
    def _transition_to_closed(self):
        """Transition to CLOSED state"""
        self._state = CircuitState.CLOSED
        self._failure_count = 0
        self._success_count = 0
        logger.info(
            f"Circuit breaker '{self.name}' transitioned to CLOSED. "
            f"Service recovered successfully."
        )
    
    def reset(self):
        """Manually reset circuit breaker to CLOSED state"""
        with self._lock:
            self._state = CircuitState.CLOSED
            self._failure_count = 0
            self._success_count = 0
            self._last_failure_time = None
            logger.info(f"Circuit breaker '{self.name}' manually reset to CLOSED.")
    
    def get_status(self) -> dict:
        """Get current circuit breaker status"""
        with self._lock:
            return {
                'name': self.name,
                'state': self._state.value,
                'failure_count': self._failure_count,
                'success_count': self._success_count,
                'failure_threshold': self.config.failure_threshold,
                'timeout': self.config.timeout,
                'last_failure_time': self._last_failure_time,
                'time_until_retry': self._time_until_retry() if self._state == CircuitState.OPEN else 0
            }
