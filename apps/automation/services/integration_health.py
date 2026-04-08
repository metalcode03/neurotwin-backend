"""
Integration health monitoring service.

Requirements: 23.1-23.5
"""
from typing import Optional
from django.utils import timezone
from apps.automation.models import Integration
import logging

logger = logging.getLogger(__name__)


class IntegrationHealthService:
    """
    Service for monitoring and updating integration health status.
    
    Health status transitions:
    - healthy: 0-2 consecutive failures
    - degraded: 3-9 consecutive failures
    - disconnected: 10+ consecutive failures
    
    Requirements: 23.1-23.5
    """
    
    DEGRADED_THRESHOLD = 3
    DISCONNECTED_THRESHOLD = 10
    
    @classmethod
    def record_success(cls, integration: Integration) -> None:
        """
        Record a successful operation and reset failure count.
        
        Args:
            integration: Integration instance
        """
        integration.consecutive_failures = 0
        integration.health_status = 'healthy'
        integration.last_successful_sync_at = timezone.now()
        integration.save(update_fields=[
            'consecutive_failures',
            'health_status',
            'last_successful_sync_at',
            'updated_at'
        ])
        
        logger.info(
            f"Integration {integration.id} operation successful. "
            f"Health status: {integration.health_status}"
        )
    
    @classmethod
    def record_failure(
        cls,
        integration: Integration,
        error_message: Optional[str] = None
    ) -> None:
        """
        Record a failed operation and update health status.
        
        Args:
            integration: Integration instance
            error_message: Optional error message for logging
        """
        integration.consecutive_failures += 1
        
        # Update health status based on failure count
        previous_status = integration.health_status
        
        if integration.consecutive_failures >= cls.DISCONNECTED_THRESHOLD:
            integration.health_status = 'disconnected'
        elif integration.consecutive_failures >= cls.DEGRADED_THRESHOLD:
            integration.health_status = 'degraded'
        else:
            integration.health_status = 'healthy'
        
        integration.save(update_fields=[
            'consecutive_failures',
            'health_status',
            'updated_at'
        ])
        
        logger.warning(
            f"Integration {integration.id} operation failed. "
            f"Consecutive failures: {integration.consecutive_failures}, "
            f"Health status: {integration.health_status}. "
            f"Error: {error_message or 'Unknown'}"
        )
        
        # Log critical status changes
        if integration.health_status == 'disconnected':
            logger.error(
                f"Integration {integration.id} marked as DISCONNECTED "
                f"after {integration.consecutive_failures} consecutive failures"
            )
            
            # Notify user if status just changed to disconnected
            if previous_status != 'disconnected':
                from apps.automation.tasks.notification_tasks import notify_integration_disconnected
                notify_integration_disconnected.delay(str(integration.id))
                
        elif integration.health_status == 'degraded':
            logger.warning(
                f"Integration {integration.id} marked as DEGRADED "
                f"after {integration.consecutive_failures} consecutive failures"
            )
    
    @classmethod
    def get_health_metrics(cls, integration: Integration) -> dict:
        """
        Get health metrics for an integration.
        
        Args:
            integration: Integration instance
            
        Returns:
            Dict with health metrics
        """
        return {
            'health_status': integration.health_status,
            'consecutive_failures': integration.consecutive_failures,
            'last_successful_sync_at': integration.last_successful_sync_at,
            'is_healthy': integration.health_status == 'healthy',
            'is_degraded': integration.health_status == 'degraded',
            'is_disconnected': integration.health_status == 'disconnected',
        }
