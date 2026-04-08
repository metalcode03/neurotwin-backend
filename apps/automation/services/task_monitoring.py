"""
Celery task monitoring service.

Requirements: 27.1-27.7
"""
from typing import Dict, Any, List
from datetime import datetime, timedelta
from django.utils import timezone
from celery import current_app
from celery.result import AsyncResult
import redis
import json


class TaskMonitoringService:
    """
    Service for monitoring Celery task execution statistics.
    
    Requirements: 27.1-27.7
    """
    
    def __init__(self, redis_client=None):
        """Initialize with Redis client for task statistics storage"""
        from django.conf import settings
        self.redis = redis_client or redis.from_url(
            settings.CELERY_BROKER_URL,
            decode_responses=True
        )
        self.stats_key_prefix = "celery:task:stats"
    
    def get_task_statistics(
        self,
        task_name: str = None,
        period: str = 'hour'
    ) -> Dict[str, Any]:
        """
        Get task execution statistics.
        
        Args:
            task_name: Optional task name to filter by
            period: Time period ('hour', 'day', 'week')
            
        Returns:
            Dictionary with task statistics
        """
        period_seconds = self._get_period_seconds(period)
        cutoff_time = timezone.now() - timedelta(seconds=period_seconds)
        
        if task_name:
            return self._get_task_stats(task_name, cutoff_time, period)
        else:
            return self._get_all_task_stats(cutoff_time, period)
    
    def _get_task_stats(
        self,
        task_name: str,
        cutoff_time: datetime,
        period: str
    ) -> Dict[str, Any]:
        """Get statistics for a specific task"""
        stats_key = f"{self.stats_key_prefix}:{task_name}:{period}"
        
        # Get stored statistics from Redis
        stats_data = self.redis.get(stats_key)
        if stats_data:
            stats = json.loads(stats_data)
        else:
            stats = {
                'task_name': task_name,
                'total_tasks': 0,
                'successful_tasks': 0,
                'failed_tasks': 0,
                'total_duration': 0.0,
                'average_duration': 0.0,
                'period': period,
                'last_updated': None
            }
        
        # Calculate average duration
        if stats['successful_tasks'] > 0:
            stats['average_duration'] = stats['total_duration'] / stats['successful_tasks']
        
        return stats
    
    def _get_all_task_stats(
        self,
        cutoff_time: datetime,
        period: str
    ) -> Dict[str, Any]:
        """Get statistics for all tasks"""
        # Get all registered tasks
        registered_tasks = list(current_app.tasks.keys())
        
        # Filter to only automation tasks
        automation_tasks = [
            t for t in registered_tasks 
            if t.startswith('apps.automation.tasks.')
        ]
        
        all_stats = []
        total_summary = {
            'total_tasks': 0,
            'successful_tasks': 0,
            'failed_tasks': 0,
            'total_duration': 0.0
        }
        
        for task_name in automation_tasks:
            task_stats = self._get_task_stats(task_name, cutoff_time, period)
            all_stats.append(task_stats)
            
            # Aggregate totals
            total_summary['total_tasks'] += task_stats['total_tasks']
            total_summary['successful_tasks'] += task_stats['successful_tasks']
            total_summary['failed_tasks'] += task_stats['failed_tasks']
            total_summary['total_duration'] += task_stats['total_duration']
        
        # Calculate overall average
        if total_summary['successful_tasks'] > 0:
            total_summary['average_duration'] = (
                total_summary['total_duration'] / total_summary['successful_tasks']
            )
        else:
            total_summary['average_duration'] = 0.0
        
        return {
            'period': period,
            'summary': total_summary,
            'tasks': all_stats,
            'timestamp': timezone.now().isoformat()
        }
    
    def record_task_execution(
        self,
        task_name: str,
        success: bool,
        duration: float
    ):
        """
        Record task execution for statistics.
        
        Args:
            task_name: Name of the task
            success: Whether task succeeded
            duration: Execution duration in seconds
        """
        for period in ['hour', 'day', 'week']:
            stats_key = f"{self.stats_key_prefix}:{task_name}:{period}"
            
            # Get current stats
            stats_data = self.redis.get(stats_key)
            if stats_data:
                stats = json.loads(stats_data)
            else:
                stats = {
                    'task_name': task_name,
                    'total_tasks': 0,
                    'successful_tasks': 0,
                    'failed_tasks': 0,
                    'total_duration': 0.0,
                    'average_duration': 0.0,
                    'period': period,
                    'last_updated': None
                }
            
            # Update stats
            stats['total_tasks'] += 1
            if success:
                stats['successful_tasks'] += 1
                stats['total_duration'] += duration
            else:
                stats['failed_tasks'] += 1
            
            stats['last_updated'] = timezone.now().isoformat()
            
            # Store back to Redis with expiry
            expiry = self._get_period_seconds(period) + 3600  # Add 1 hour buffer
            self.redis.setex(
                stats_key,
                expiry,
                json.dumps(stats)
            )
    
    def get_queue_lengths(self) -> Dict[str, int]:
        """
        Get current queue lengths for all Celery queues.
        
        Returns:
            Dictionary mapping queue names to message counts
        """
        queues = ['high_priority', 'incoming_messages', 'outgoing_messages', 'default']
        queue_lengths = {}
        
        for queue_name in queues:
            try:
                # Get queue length from Redis
                queue_key = f"celery:queue:{queue_name}"
                length = self.redis.llen(queue_key)
                queue_lengths[queue_name] = length
            except Exception as e:
                queue_lengths[queue_name] = -1  # Error indicator
        
        return queue_lengths
    
    def get_worker_status(self) -> Dict[str, Any]:
        """
        Get Celery worker status.
        
        Returns:
            Dictionary with worker information
        """
        inspect = current_app.control.inspect()
        
        # Get active workers
        active_workers = inspect.active()
        registered_tasks = inspect.registered()
        stats = inspect.stats()
        
        return {
            'active_workers': len(active_workers) if active_workers else 0,
            'workers': active_workers or {},
            'registered_tasks': registered_tasks or {},
            'stats': stats or {},
            'timestamp': timezone.now().isoformat()
        }
    
    def _get_period_seconds(self, period: str) -> int:
        """Convert period string to seconds"""
        periods = {
            'hour': 3600,
            'day': 86400,
            'week': 604800
        }
        return periods.get(period, 3600)
