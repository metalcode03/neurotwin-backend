"""
Transaction handling utilities for NeuroTwin platform.

Provides decorators and context managers for ensuring atomic database operations.
Requirements: 14.3 - Use transactions to ensure data integrity

This module provides:
- atomic_operation: Decorator for wrapping functions in database transactions
- ensure_atomic: Context manager for atomic blocks
- TransactionManager: Class for managing complex multi-step transactions
"""

import functools
import logging
from contextlib import contextmanager
from typing import Callable, TypeVar, ParamSpec, Optional, Any

from django.db import transaction, DatabaseError, IntegrityError
from django.db.transaction import get_connection

logger = logging.getLogger(__name__)

P = ParamSpec('P')
T = TypeVar('T')


class TransactionError(Exception):
    """Base exception for transaction-related errors."""
    pass


class RetryableTransactionError(TransactionError):
    """Exception indicating a transaction that can be retried."""
    pass


def atomic_operation(
    using: Optional[str] = None,
    savepoint: bool = True,
    durable: bool = False,
    max_retries: int = 0,
    retry_on: tuple = (DatabaseError,),
) -> Callable[[Callable[P, T]], Callable[P, T]]:
    """
    Decorator for wrapping functions in database transactions.
    
    Ensures all database operations within the decorated function are
    executed atomically - either all succeed or all are rolled back.
    
    Requirements: 14.3 - Use transactions to ensure data integrity
    
    Args:
        using: Database alias to use (default: 'default')
        savepoint: Whether to use savepoints for nested transactions
        durable: If True, ensures the outermost atomic block commits
        max_retries: Number of times to retry on transient errors
        retry_on: Tuple of exception types that trigger retry
        
    Returns:
        Decorated function that executes within a transaction
        
    Example:
        @atomic_operation()
        def create_user_with_profile(user_data, profile_data):
            user = User.objects.create(**user_data)
            Profile.objects.create(user=user, **profile_data)
            return user
    """
    def decorator(func: Callable[P, T]) -> Callable[P, T]:
        @functools.wraps(func)
        def wrapper(*args: P.args, **kwargs: P.kwargs) -> T:
            last_exception = None
            
            for attempt in range(max_retries + 1):
                try:
                    with transaction.atomic(using=using, savepoint=savepoint, durable=durable):
                        return func(*args, **kwargs)
                except retry_on as e:
                    last_exception = e
                    if attempt < max_retries:
                        logger.warning(
                            f"Transaction failed (attempt {attempt + 1}/{max_retries + 1}): {e}. Retrying..."
                        )
                        continue
                    raise
            
            # Should not reach here, but just in case
            if last_exception:
                raise last_exception
            raise TransactionError("Transaction failed with no exception")
        
        return wrapper
    return decorator


@contextmanager
def ensure_atomic(
    using: Optional[str] = None,
    savepoint: bool = True,
    durable: bool = False,
):
    """
    Context manager for ensuring atomic database operations.
    
    Requirements: 14.3 - Use transactions to ensure data integrity
    
    Args:
        using: Database alias to use
        savepoint: Whether to use savepoints for nested transactions
        durable: If True, ensures the outermost atomic block commits
        
    Yields:
        None
        
    Example:
        with ensure_atomic():
            user = User.objects.create(email='test@example.com')
            Profile.objects.create(user=user)
    """
    with transaction.atomic(using=using, savepoint=savepoint, durable=durable):
        yield


class TransactionManager:
    """
    Manager for complex multi-step transactions with rollback support.
    
    Provides a way to manage transactions that span multiple operations
    with the ability to track and rollback individual steps.
    
    Requirements: 14.3 - Use transactions to ensure data integrity
    
    Example:
        manager = TransactionManager()
        
        with manager.begin():
            manager.add_step('create_user', lambda: User.objects.create(...))
            manager.add_step('create_profile', lambda: Profile.objects.create(...))
            manager.execute_all()
    """
    
    def __init__(self, using: Optional[str] = None):
        """
        Initialize the transaction manager.
        
        Args:
            using: Database alias to use
        """
        self._using = using
        self._steps: list[tuple[str, Callable, Optional[Callable]]] = []
        self._results: dict[str, Any] = {}
        self._executed_steps: list[str] = []
        self._in_transaction = False
    
    def add_step(
        self,
        name: str,
        operation: Callable[[], Any],
        rollback: Optional[Callable[[Any], None]] = None,
    ) -> 'TransactionManager':
        """
        Add a step to the transaction.
        
        Args:
            name: Unique name for this step
            operation: Callable that performs the operation
            rollback: Optional callable to rollback this step (receives operation result)
            
        Returns:
            Self for method chaining
        """
        self._steps.append((name, operation, rollback))
        return self
    
    def execute_step(self, name: str) -> Any:
        """
        Execute a specific step by name.
        
        Args:
            name: Name of the step to execute
            
        Returns:
            Result of the operation
            
        Raises:
            ValueError: If step not found
            TransactionError: If not in a transaction
        """
        if not self._in_transaction:
            raise TransactionError("Must be within a transaction context")
        
        for step_name, operation, _ in self._steps:
            if step_name == name:
                result = operation()
                self._results[name] = result
                self._executed_steps.append(name)
                return result
        
        raise ValueError(f"Step '{name}' not found")
    
    def execute_all(self) -> dict[str, Any]:
        """
        Execute all steps in order.
        
        Returns:
            Dictionary mapping step names to their results
            
        Raises:
            TransactionError: If not in a transaction or if any step fails
        """
        if not self._in_transaction:
            raise TransactionError("Must be within a transaction context")
        
        for name, operation, _ in self._steps:
            if name not in self._executed_steps:
                result = operation()
                self._results[name] = result
                self._executed_steps.append(name)
        
        return self._results.copy()
    
    def get_result(self, name: str) -> Any:
        """
        Get the result of a previously executed step.
        
        Args:
            name: Name of the step
            
        Returns:
            Result of the step
            
        Raises:
            KeyError: If step hasn't been executed
        """
        return self._results[name]
    
    @contextmanager
    def begin(self, savepoint: bool = True):
        """
        Begin a transaction context.
        
        Args:
            savepoint: Whether to use savepoints
            
        Yields:
            Self for accessing results
        """
        self._in_transaction = True
        self._results.clear()
        self._executed_steps.clear()
        
        try:
            with transaction.atomic(using=self._using, savepoint=savepoint):
                yield self
        except Exception:
            # Transaction will be rolled back automatically
            self._in_transaction = False
            raise
        finally:
            self._in_transaction = False
    
    def clear(self):
        """Clear all steps and results."""
        self._steps.clear()
        self._results.clear()
        self._executed_steps.clear()


def is_in_transaction(using: Optional[str] = None) -> bool:
    """
    Check if currently inside a database transaction.
    
    Args:
        using: Database alias to check
        
    Returns:
        True if inside a transaction
    """
    connection = get_connection(using)
    return connection.in_atomic_block


def get_transaction_depth(using: Optional[str] = None) -> int:
    """
    Get the current transaction nesting depth.
    
    Args:
        using: Database alias to check
        
    Returns:
        Number of nested atomic blocks
    """
    connection = get_connection(using)
    return len(connection.savepoint_ids)
