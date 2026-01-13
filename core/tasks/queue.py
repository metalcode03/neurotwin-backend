"""
Task queue utilities for NeuroTwin platform.

Provides functions for enqueueing background tasks using Django-Q2.
Requirements: 14.5 - Memory writes shall be asynchronous
"""

import logging
from enum import Enum
from typing import Any, Callable, Optional, Dict
from datetime import datetime, timedelta

from django.conf import settings

logger = logging.getLogger(__name__)


class TaskPriority(Enum):
    """Priority levels for background tasks."""
    LOW = 'low'
    NORMAL = 'normal'
    HIGH = 'high'
    CRITICAL = 'critical'


def _get_queue_name(priority: TaskPriority) -> str:
    """Get the queue name for a given priority."""
    queue_mapping = {
        TaskPriority.LOW: 'low',
        TaskPriority.NORMAL: 'default',
        TaskPriority.HIGH: 'high',
        TaskPriority.CRITICAL: 'critical',
    }
    return queue_mapping.get(priority, 'default')


def enqueue_task(
    func: Callable,
    *args,
    priority: TaskPriority = TaskPriority.NORMAL,
    timeout: int = 300,
    retry: int = 3,
    group: Optional[str] = None,
    hook: Optional[Callable] = None,
    **kwargs
) -> Optional[str]:
    """
    Enqueue a task for background execution.
    
    Requirements: 14.5 - Async task execution
    
    Args:
        func: The function to execute
        *args: Positional arguments for the function
        priority: Task priority level
        timeout: Timeout in seconds
        retry: Number of retries on failure
        group: Optional task group name
        hook: Optional callback function on completion
        **kwargs: Keyword arguments for the function
        
    Returns:
        Task ID if enqueued successfully, None otherwise
    """
    try:
        from django_q.tasks import async_task as q_async_task
        
        task_id = q_async_task(
            func,
            *args,
            q_options={
                'timeout': timeout,
                'retry': retry,
                'group': group,
                'hook': hook,
                'queue': _get_queue_name(priority),
            },
            **kwargs
        )
        
        # Handle both callable and string function paths
        func_name = func if isinstance(func, str) else getattr(func, '__name__', str(func))
        logger.debug(f"Enqueued task {func_name} with ID {task_id}")
        return task_id
        
    except ImportError:
        # Django-Q not available, execute synchronously
        logger.warning("Django-Q not available, executing task synchronously")
        try:
            func(*args, **kwargs)
            return None
        except Exception as e:
            logger.error(f"Synchronous task execution failed: {e}")
            raise
    except Exception as e:
        logger.error(f"Failed to enqueue task: {e}")
        raise


def enqueue_memory_write(
    user_id: str,
    content: str,
    source: str,
    metadata: Optional[Dict[str, Any]] = None,
    priority: TaskPriority = TaskPriority.NORMAL,
) -> Optional[str]:
    """
    Enqueue a memory write operation for async execution.
    
    Requirements: 14.5 - Memory writes shall be asynchronous
    
    Args:
        user_id: The user's ID
        content: The content to store
        source: The source of the memory
        metadata: Optional metadata
        priority: Task priority
        
    Returns:
        Task ID if enqueued successfully
    """
    return enqueue_task(
        'core.tasks.handlers.handle_memory_write',
        user_id=user_id,
        content=content,
        source=source,
        metadata=metadata,
        priority=priority,
        group='memory_writes',
    )


def enqueue_embedding_generation(
    user_id: str,
    content: str,
    memory_id: str,
    priority: TaskPriority = TaskPriority.NORMAL,
) -> Optional[str]:
    """
    Enqueue embedding generation for async execution.
    
    Requirements: 14.5 - Embedding generation shall be asynchronous
    
    Args:
        user_id: The user's ID
        content: The content to generate embeddings for
        memory_id: The memory record ID
        priority: Task priority
        
    Returns:
        Task ID if enqueued successfully
    """
    return enqueue_task(
        'core.tasks.handlers.handle_embedding_generation',
        user_id=user_id,
        content=content,
        memory_id=memory_id,
        priority=priority,
        group='embeddings',
    )


def enqueue_email(
    to_email: str,
    subject: str,
    body: str,
    template: Optional[str] = None,
    context: Optional[Dict[str, Any]] = None,
    priority: TaskPriority = TaskPriority.NORMAL,
) -> Optional[str]:
    """
    Enqueue an email for async sending.
    
    Args:
        to_email: Recipient email address
        subject: Email subject
        body: Email body (plain text)
        template: Optional email template name
        context: Optional template context
        priority: Task priority
        
    Returns:
        Task ID if enqueued successfully
    """
    return enqueue_task(
        'core.tasks.handlers.handle_send_email',
        to_email=to_email,
        subject=subject,
        body=body,
        template=template,
        context=context,
        priority=priority,
        group='emails',
    )


def enqueue_learning_update(
    user_id: str,
    features: Dict[str, Any],
    priority: TaskPriority = TaskPriority.NORMAL,
) -> Optional[str]:
    """
    Enqueue a learning profile update for async execution.
    
    Requirements: 6.2 - Profile updates shall be asynchronous
    
    Args:
        user_id: The user's ID
        features: Extracted features for profile update
        priority: Task priority
        
    Returns:
        Task ID if enqueued successfully
    """
    return enqueue_task(
        'core.tasks.handlers.handle_learning_update',
        user_id=user_id,
        features=features,
        priority=priority,
        group='learning',
    )


def get_task_result(task_id: str, wait: int = 0) -> Optional[Any]:
    """
    Get the result of a completed task.
    
    Args:
        task_id: The task ID
        wait: Seconds to wait for completion (0 = don't wait)
        
    Returns:
        Task result if available, None otherwise
    """
    try:
        from django_q.tasks import result as q_result
        return q_result(task_id, wait=wait)
    except ImportError:
        logger.warning("Django-Q not available")
        return None
    except Exception as e:
        logger.error(f"Failed to get task result: {e}")
        return None


def schedule_task(
    func: Callable,
    *args,
    schedule_type: str = 'O',  # O=Once, I=Interval, C=Cron
    next_run: Optional[datetime] = None,
    minutes: Optional[int] = None,
    cron: Optional[str] = None,
    name: Optional[str] = None,
    **kwargs
) -> Optional[str]:
    """
    Schedule a task for future or recurring execution.
    
    Args:
        func: The function to execute
        *args: Positional arguments
        schedule_type: 'O' for once, 'I' for interval, 'C' for cron
        next_run: When to run (for once)
        minutes: Interval in minutes (for interval)
        cron: Cron expression (for cron)
        name: Optional schedule name
        **kwargs: Keyword arguments
        
    Returns:
        Schedule ID if created successfully
    """
    try:
        from django_q.models import Schedule
        
        schedule_kwargs = {
            'func': f"{func.__module__}.{func.__name__}",
            'args': args,
            'kwargs': kwargs,
            'schedule_type': schedule_type,
            'name': name or f"schedule_{func.__name__}",
        }
        
        if schedule_type == 'O' and next_run:
            schedule_kwargs['next_run'] = next_run
        elif schedule_type == 'I' and minutes:
            schedule_kwargs['minutes'] = minutes
        elif schedule_type == 'C' and cron:
            schedule_kwargs['cron'] = cron
        
        schedule = Schedule.objects.create(**schedule_kwargs)
        return str(schedule.id)
        
    except ImportError:
        logger.warning("Django-Q not available for scheduling")
        return None
    except Exception as e:
        logger.error(f"Failed to schedule task: {e}")
        return None
