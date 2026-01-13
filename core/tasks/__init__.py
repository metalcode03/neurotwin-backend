"""
Async task queue infrastructure for NeuroTwin platform.

Provides background task execution for:
- Memory writes (embedding generation and storage)
- Email sending
- Learning loop processing
- Integration token refresh

Requirements: 14.5 - Memory writes shall be asynchronous
"""

from .queue import (
    enqueue_task,
    enqueue_memory_write,
    enqueue_embedding_generation,
    enqueue_email,
    enqueue_learning_update,
    get_task_result,
    TaskPriority,
)
from .decorators import async_task, background_task

__all__ = [
    'enqueue_task',
    'enqueue_memory_write',
    'enqueue_embedding_generation',
    'enqueue_email',
    'enqueue_learning_update',
    'get_task_result',
    'TaskPriority',
    'async_task',
    'background_task',
]
