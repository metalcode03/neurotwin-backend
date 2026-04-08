"""
Health check service for system monitoring.

Requirements: 31.1-31.7
"""
from typing import Dict, Any, Tuple
from django.db import connection
from django.core.cache import cache
import redis
from celery import current_app
import logging

logger = logging.getLogger(__name__)


class HealthCheckService:
    """
    Service for checking system health status.
    
    Checks:
    - Database connectivity
    - Redis connectivity
    - Celery worker status
    
    Requirements: 31.1-31.7
    """
    
    @staticmethod
    def check_database() -> Tuple[bool, str]:
        """
        Check database connectivity.
        
        Returns:
            Tuple of (is_healthy, message)
        """
        try:
            with connection.cursor() as cursor:
                cursor.execute("SELECT 1")
                cursor.fetchone()
            return True, "Database connection healthy"
        except Exception as e:
            logger.error(f"Database health check failed: {e}")
            return False, f"Database connection failed: {str(e)}"
    
    @staticmethod
    def check_redis() -> Tuple[bool, str]:
        """
        Check Redis connectivity.
        
        Returns:
            Tuple of (is_healthy, message)
        """
        try:
            # Test cache backend (Redis)
            test_key = "health_check_test"
            test_value = "ok"
            cache.set(test_key, test_value, timeout=10)
            result = cache.get(test_key)
            cache.delete(test_key)
            
            if result == test_value:
                return True, "Redis connection healthy"
            else:
                return False, "Redis read/write test failed"
        except Exception as e:
            logger.error(f"Redis health check failed: {e}")
            return False, f"Redis connection failed: {str(e)}"
    
    @staticmethod
    def check_celery() -> Tuple[bool, str]:
        """
        Check Celery worker status.
        
        Returns:
            Tuple of (is_healthy, message)
        """
        try:
            # Get active workers
            inspect = current_app.control.inspect()
            active_workers = inspect.active()
            
            if active_workers:
                worker_count = len(active_workers)
                return True, f"Celery workers healthy ({worker_count} active)"
            else:
                return False, "No active Celery workers found"
        except Exception as e:
            logger.error(f"Celery health check failed: {e}")
            return False, f"Celery check failed: {str(e)}"
    
    @classmethod
    def get_overall_health(cls) -> Dict[str, Any]:
        """
        Get overall system health status.
        
        Returns:
            Dict with health status for each component and overall status
        """
        db_healthy, db_message = cls.check_database()
        redis_healthy, redis_message = cls.check_redis()
        celery_healthy, celery_message = cls.check_celery()
        
        # Determine overall status
        if db_healthy and redis_healthy and celery_healthy:
            overall_status = "healthy"
        elif db_healthy and redis_healthy:
            # Database and Redis are critical, Celery is degraded
            overall_status = "degraded"
        else:
            overall_status = "unhealthy"
        
        return {
            "status": overall_status,
            "components": {
                "database": {
                    "status": "healthy" if db_healthy else "unhealthy",
                    "message": db_message
                },
                "redis": {
                    "status": "healthy" if redis_healthy else "unhealthy",
                    "message": redis_message
                },
                "celery": {
                    "status": "healthy" if celery_healthy else "unhealthy",
                    "message": celery_message
                }
            }
        }
