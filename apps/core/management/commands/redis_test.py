"""
Django management command to test and manage Redis connection.

Usage:
    python manage.py redis_test
    python manage.py redis_test --stats
    python manage.py redis_test --clear
"""

from django.core.management.base import BaseCommand
from django.core.cache import cache
from apps.core.redis_utils import (
    test_redis_connection,
    get_cache_stats,
    get_cache_size,
    clear_all_cache,
)


class Command(BaseCommand):
    help = 'Test Redis connection and display cache statistics'

    def add_arguments(self, parser):
        parser.add_argument(
            '--stats',
            action='store_true',
            help='Display cache statistics',
        )
        parser.add_argument(
            '--clear',
            action='store_true',
            help='Clear all cache (use with caution)',
        )
        parser.add_argument(
            '--test',
            action='store_true',
            help='Run connection test',
        )

    def handle(self, *args, **options):
        if options['clear']:
            self.stdout.write(self.style.WARNING('⚠️  Clearing all cache...'))
            clear_all_cache()
            self.stdout.write(self.style.SUCCESS('✓ Cache cleared'))
            return

        if options['stats']:
            self.display_stats()
            return

        if options['test'] or not any([options['stats'], options['clear']]):
            self.test_connection()

    def test_connection(self):
        """Test Redis connection."""
        self.stdout.write('Testing Redis connection...')
        
        if test_redis_connection():
            self.stdout.write(self.style.SUCCESS('✓ Redis connection successful'))
            
            # Test basic operations
            self.stdout.write('\nTesting cache operations...')
            
            # Set
            cache.set('test_key', 'test_value', timeout=60)
            self.stdout.write(self.style.SUCCESS('✓ SET operation successful'))
            
            # Get
            value = cache.get('test_key')
            if value == 'test_value':
                self.stdout.write(self.style.SUCCESS('✓ GET operation successful'))
            else:
                self.stdout.write(self.style.ERROR('✗ GET operation failed'))
            
            # Delete
            cache.delete('test_key')
            value = cache.get('test_key')
            if value is None:
                self.stdout.write(self.style.SUCCESS('✓ DELETE operation successful'))
            else:
                self.stdout.write(self.style.ERROR('✗ DELETE operation failed'))
            
            self.stdout.write(self.style.SUCCESS('\n✓ All tests passed'))
        else:
            self.stdout.write(self.style.ERROR('✗ Redis connection failed'))
            self.stdout.write('\nTroubleshooting:')
            self.stdout.write('1. Check REDIS_HOST in .env')
            self.stdout.write('2. Verify security group allows port 6379')
            self.stdout.write('3. Check VPC/subnet configuration')
            self.stdout.write('4. Verify SSL/TLS settings')

    def display_stats(self):
        """Display cache statistics."""
        self.stdout.write('Cache Statistics:')
        self.stdout.write('=' * 50)
        
        stats = get_cache_stats()
        if stats:
            self.stdout.write(f"Connected Clients: {stats.get('connected_clients', 'N/A')}")
            self.stdout.write(f"Memory Used: {stats.get('used_memory_human', 'N/A')}")
            self.stdout.write(f"Total Commands: {stats.get('total_commands_processed', 'N/A')}")
            self.stdout.write(f"Cache Hits: {stats.get('keyspace_hits', 'N/A')}")
            self.stdout.write(f"Cache Misses: {stats.get('keyspace_misses', 'N/A')}")
            self.stdout.write(f"Hit Rate: {stats.get('hit_rate', 'N/A')}%")
        else:
            self.stdout.write(self.style.ERROR('Failed to retrieve statistics'))
        
        # Display cache size
        size = get_cache_size()
        self.stdout.write(f"\nTotal Keys: {size}")
        
        self.stdout.write('=' * 50)
