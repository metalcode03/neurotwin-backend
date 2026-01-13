"""
Task decorators for NeuroTwin platform.

Provides decorators for marking functions as background tasks.
Requirements: 14.5 - Memory writes shall be asynchronous
"""

import functools
import logging
from typing import Callable, TypeVar, ParamSpec, Optional

from .queue import enqueue_task, TaskPriority

logger = logging.getLogger(__name__)

P = ParamSpec('P')
T = TypeVar('T')


def async_task(
    priority: TaskPriority = TaskPriority.NORMAL,
    timeout: int = 300,
    retry: int = 3,
    group: Optional[str] = None,
) -> Callable[[Callable[P, T]], Callable[P, Optional[str]]]:
    """
    Decorator to mark a function for async execution.
    
    When the decorated function is called, it will be enqueued
    for background execution instead of running synchronously.
    
    Requirements: 14.5 - Async task execution
    
    Args:
        priority: Task priority level
        timeout: Timeout in seconds
        retry: Number of retries on failure
        group: Optional task group name
        
    Returns:
        Decorated function that enqueues the task
        
    Example:
        @async_task(priority=TaskPriority.HIGH)
        def send_notification(user_id: str, message: str):
            # This will run in the background
            pass
            
        # Calling the function enqueues it
        task_id = send_notification(user_id='123', message='Hello')
    """
    def decorator(func: Callable[P, T]) -> Callable[P, Optional[str]]:
        @functools.wraps(func)
        def wrapper(*args: P.args, **kwargs: P.kwargs) -> Optional[str]:
            return enqueue_task(
                func,
                *args,
                priority=priority,
                timeout=timeout,
                retry=retry,
                group=group,
                **kwargs
            )
        
        # Store original function for direct execution if needed
        wrapper._original = func
        wrapper._is_async_task = True
        
        return wrapper
    return decorator


def background_task(
    priority: TaskPriority = TaskPriority.NORMAL,
    timeout: int = 300,
    retry: int = 3,
    group: Optional[str] = None,
    run_sync_if_unavailable: bool = True,
) -> Callable[[Callable[P, T]], Callable[P, T]]:
    """
    Decorator that attempts async execution but falls back to sync.
    
    Unlike @async_task, this decorator will execute the function
    synchronously if the task queue is unavailable.
    
    Requirements: 14.5 - Async task execution with fallback
    
    Args:
        priority: Task priority level
        timeout: Timeout in seconds
        retry: Number of retries on failure
        group: Optional task group name
        run_sync_if_unavailable: If True, run synchronously when queue unavailable
        
    Returns:
        Decorated function
        
    Example:
        @background_task(run_sync_if_unavailable=True)
        def process_data(data: dict):
            # Will run async if possible, sync otherwise
            pass
    """
    def decorator(func: Callable[P, T]) -> Callable[P, T]:
        @functools.wraps(func)
        def wrapper(*args: P.args, **kwargs: P.kwargs) -> T:
            try:
                task_id = enqueue_task(
                    func,
                    *args,
                    priority=priority,
                    timeout=timeout,
                    retry=retry,
                    group=group,
                    **kwargs
                )
                
                if task_id:
                    logger.debug(f"Task {func.__name__} enqueued with ID {task_id}")
                    # Return None since task is running async
                    return None
                    
            except Exception as e:
                if run_sync_if_unavailable:
                    logger.warning(
                        f"Failed to enqueue {func.__name__}, running synchronously: {e}"
                    )
                else:
                    raise
            
            # Fallback to synchronous execution
            if run_sync_if_unavailable:
                return func(*args, **kwargs)
            
            return None
        
        # Store original function for direct execution if needed
        wrapper._original = func
        wrapper._is_background_task = True
        
        return wrapper
    return decorator


def run_sync(func: Callable[P, T]) -> Callable[P, T]:
    """
    Get the synchronous version of an async/background task.
    
    Args:
        func: The decorated function
        
    Returns:
        The original synchronous function
        
    Example:
        @async_task()
        def my_task():
            pass
            
        # Run synchronously for testing
        run_sync(my_task)()
    """
    if hasattr(func, '_original'):
        return func._original
    return func
