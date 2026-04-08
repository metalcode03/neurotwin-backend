"""
Celery tasks for log and data cleanup.

Requirements: 22.6, 27.7, 30.7
"""
from celery import shared_task
from django.core.management import call_command
import logging

logger = logging.getLogger(__name__)


@shared_task(
    name='automation.cleanup_old_logs',
    bind=True,
    max_retries=3,
    default_retry_delay=300  # 5 minutes
)
def cleanup_old_logs(self):
    """
    Celery task to clean up old logs and data based on retention policies.
    
    Retention policies:
    - Webhook events: 30 days (Requirements: 22.6)
    - Celery task results: 7 days (Requirements: 27.7)
    - Integration logs: 90 days (Requirements: 30.7)
    
    Scheduled to run daily at 2:00 AM via Celery Beat.
    """
    try:
        logger.info("Starting scheduled log cleanup task")
        
        # Call the management command
        call_command('cleanup_old_logs')
        
        logger.info("Log cleanup task completed successfully")
        return {
            'status': 'success',
            'message': 'Log cleanup completed successfully'
        }
        
    except Exception as e:
        logger.error(f"Error during log cleanup: {e}", exc_info=True)
        
        # Retry on failure
        try:
            self.retry(exc=e)
        except self.MaxRetriesExceededError:
            logger.error("Max retries exceeded for log cleanup task")
            return {
                'status': 'failed',
                'message': f'Log cleanup failed after max retries: {str(e)}'
            }
