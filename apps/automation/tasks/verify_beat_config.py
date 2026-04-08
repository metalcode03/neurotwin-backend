"""
Verification script for Celery Beat configuration.

Run this to verify that the token refresh task is properly configured.

Usage:
    python manage.py shell < apps/automation/tasks/verify_beat_config.py
"""

from django.conf import settings
from celery import current_app
import sys


def verify_beat_configuration():
    """Verify Celery Beat is properly configured for token refresh."""
    
    print("=" * 70)
    print("Celery Beat Configuration Verification")
    print("=" * 70)
    print()
    
    # Check if Beat scheduler is configured
    print("1. Checking Beat Scheduler Configuration...")
    beat_scheduler = getattr(settings, 'CELERY_BEAT_SCHEDULER', None)
    if beat_scheduler == 'django_celery_beat.schedulers:DatabaseScheduler':
        print("   ✓ Beat scheduler: django_celery_beat.schedulers:DatabaseScheduler")
    else:
        print(f"   ✗ Beat scheduler: {beat_scheduler}")
        print("   Expected: django_celery_beat.schedulers:DatabaseScheduler")
        return False
    print()
    
    # Check if Beat schedule is configured
    print("2. Checking Beat Schedule Configuration...")
    beat_schedule = getattr(settings, 'CELERY_BEAT_SCHEDULE', {})
    
    if 'refresh-expiring-tokens' in beat_schedule:
        print("   ✓ Token refresh task found in schedule")
        
        task_config = beat_schedule['refresh-expiring-tokens']
        print(f"   - Task: {task_config.get('task')}")
        print(f"   - Schedule: {task_config.get('schedule')}")
        print(f"   - Queue: {task_config.get('options', {}).get('queue')}")
        print(f"   - Expires: {task_config.get('options', {}).get('expires')}s")
    else:
        print("   ✗ Token refresh task NOT found in schedule")
        print("   Available tasks:", list(beat_schedule.keys()))
        return False
    print()
    
    # Check if task is registered
    print("3. Checking Task Registration...")
    registered_tasks = current_app.tasks.keys()
    
    if 'automation.refresh_expiring_tokens' in registered_tasks:
        print("   ✓ Task 'automation.refresh_expiring_tokens' is registered")
    else:
        print("   ✗ Task 'automation.refresh_expiring_tokens' is NOT registered")
        print("   Registered tasks:", [t for t in registered_tasks if 'automation' in t])
        return False
    print()
    
    # Check Redis connection
    print("4. Checking Redis Connection...")
    try:
        from django.core.cache import cache
        cache.set('celery_beat_test', 'ok', 10)
        result = cache.get('celery_beat_test')
        if result == 'ok':
            print("   ✓ Redis connection successful")
        else:
            print("   ✗ Redis connection failed (cache test failed)")
            return False
    except Exception as e:
        print(f"   ✗ Redis connection failed: {e}")
        return False
    print()
    
    # Check django-celery-beat installation
    print("5. Checking django-celery-beat Installation...")
    try:
        import django_celery_beat
        print(f"   ✓ django-celery-beat installed (version {django_celery_beat.__version__})")
    except ImportError:
        print("   ✗ django-celery-beat NOT installed")
        print("   Install with: uv add django-celery-beat")
        return False
    print()
    
    # Check if migrations are applied
    print("6. Checking Database Migrations...")
    try:
        from django_celery_beat.models import PeriodicTask
        count = PeriodicTask.objects.count()
        print(f"   ✓ django-celery-beat tables exist ({count} periodic tasks in DB)")
    except Exception as e:
        print(f"   ✗ django-celery-beat tables NOT found: {e}")
        print("   Run: python manage.py migrate django_celery_beat")
        return False
    print()
    
    # Summary
    print("=" * 70)
    print("✓ All checks passed! Celery Beat is properly configured.")
    print("=" * 70)
    print()
    print("Next steps:")
    print("1. Start Celery workers:")
    print("   celery -A neurotwin worker --loglevel=info")
    print()
    print("2. Start Celery Beat:")
    print("   python manage.py celery_beat --loglevel=info")
    print()
    print("3. Monitor task execution:")
    print("   celery -A neurotwin inspect scheduled")
    print()
    
    return True


if __name__ == '__main__':
    try:
        success = verify_beat_configuration()
        sys.exit(0 if success else 1)
    except Exception as e:
        print(f"\n✗ Verification failed with error: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)
