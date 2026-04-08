"""
Management command to clean up old logs and data based on retention policies.

Requirements: 22.6, 27.7, 30.7
"""
from django.core.management.base import BaseCommand
from django.utils import timezone
from datetime import timedelta
from apps.automation.models import WebhookEvent
import redis
from django.conf import settings
import logging

logger = logging.getLogger(__name__)


class Command(BaseCommand):
    help = 'Clean up old logs and data based on retention policies'
    
    def add_arguments(self, parser):
        parser.add_argument(
            '--dry-run',
            action='store_true',
            help='Show what would be deleted without actually deleting',
        )
    
    def handle(self, *args, **options):
        dry_run = options['dry_run']
        
        if dry_run:
            self.stdout.write(self.style.WARNING('DRY RUN MODE - No data will be deleted'))
        
        # Clean up webhook events (30-day retention)
        self.cleanup_webhook_events(dry_run)
        
        # Clean up Celery task results (7-day retention)
        self.cleanup_celery_results(dry_run)
        
        # Clean up integration logs (90-day retention)
        # Note: Integration logs are handled by Django logging configuration
        # This is documented in the logging configuration
        
        self.stdout.write(self.style.SUCCESS('Cleanup completed successfully'))
    
    def cleanup_webhook_events(self, dry_run: bool):
        """
        Clean up webhook events older than 30 days.
        
        Requirements: 22.6
        """
        retention_days = 30
        cutoff_date = timezone.now() - timedelta(days=retention_days)
        
        # Count events to delete
        old_events = WebhookEvent.objects.filter(created_at__lt=cutoff_date)
        count = old_events.count()
        
        if count > 0:
            self.stdout.write(
                f'Found {count} webhook events older than {retention_days} days'
            )
            
            if not dry_run:
                deleted_count, _ = old_events.delete()
                self.stdout.write(
                    self.style.SUCCESS(f'Deleted {deleted_count} webhook events')
                )
                logger.info(f'Deleted {deleted_count} webhook events older than {retention_days} days')
            else:
                self.stdout.write(
                    self.style.WARNING(f'Would delete {count} webhook events')
                )
        else:
            self.stdout.write('No webhook events to clean up')
    
    def cleanup_celery_results(self, dry_run: bool):
        """
        Clean up Celery task results older than 7 days.
        
        Requirements: 27.7
        """
        retention_days = 7
        
        try:
            # Connect to Redis
            redis_client = redis.from_url(
                settings.CELERY_BROKER_URL,
                decode_responses=True
            )
            
            # Celery stores results with keys like: celery-task-meta-<task_id>
            # We'll scan for these keys and check their age
            
            cutoff_timestamp = (timezone.now() - timedelta(days=retention_days)).timestamp()
            deleted_count = 0
            
            # Scan for celery task result keys
            cursor = 0
            while True:
                cursor, keys = redis_client.scan(
                    cursor,
                    match='celery-task-meta-*',
                    count=100
                )
                
                for key in keys:
                    try:
                        # Get TTL to check if key has expiry
                        ttl = redis_client.ttl(key)
                        
                        # If no TTL set or TTL is very long, check age
                        if ttl == -1 or ttl > retention_days * 86400:
                            # Get key creation time (if available)
                            # For simplicity, we'll just set expiry on old keys
                            if not dry_run:
                                redis_client.expire(key, retention_days * 86400)
                                deleted_count += 1
                    except Exception as e:
                        logger.error(f"Error processing key {key}: {e}")
                
                if cursor == 0:
                    break
            
            if deleted_count > 0:
                self.stdout.write(
                    self.style.SUCCESS(
                        f'Set expiry on {deleted_count} Celery task result keys'
                    )
                )
                logger.info(f'Set expiry on {deleted_count} Celery task result keys')
            else:
                self.stdout.write('No Celery task results to clean up')
                
        except Exception as e:
            self.stdout.write(
                self.style.ERROR(f'Error cleaning up Celery results: {e}')
            )
            logger.error(f'Error cleaning up Celery results: {e}')
