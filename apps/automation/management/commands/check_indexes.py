"""
Management command to check database indexes.

Usage:
    python manage.py check_indexes
    python manage.py check_indexes --unused
    python manage.py check_indexes --missing

Requirements: 31.7 - Verify all indexes from model definitions are created
"""

from django.core.management.base import BaseCommand
from django.db import connection
from django.apps import apps
import sys


class Command(BaseCommand):
    help = 'Check database indexes for automation models'

    def add_arguments(self, parser):
        parser.add_argument(
            '--unused',
            action='store_true',
            help='Show unused indexes',
        )
        parser.add_argument(
            '--missing',
            action='store_true',
            help='Show missing indexes from model definitions',
        )
        parser.add_argument(
            '--sizes',
            action='store_true',
            help='Show index sizes',
        )

    def handle(self, *args, **options):
        self.stdout.write(self.style.SUCCESS('Checking database indexes...\n'))

        if options['unused']:
            self.check_unused_indexes()
        elif options['missing']:
            self.check_missing_indexes()
        elif options['sizes']:
            self.show_index_sizes()
        else:
            self.show_all_indexes()

    def show_all_indexes(self):
        """Show all indexes for automation models."""
        with connection.cursor() as cursor:
            cursor.execute("""
                SELECT
                    t.tablename,
                    i.indexname,
                    array_agg(a.attname ORDER BY a.attnum) as columns,
                    idx_scan,
                    pg_size_pretty(pg_relation_size(i.indexrelid)) as size
                FROM pg_indexes i
                JOIN pg_stat_user_indexes s ON i.indexname = s.indexname
                JOIN pg_class c ON c.relname = i.tablename
                JOIN pg_index ix ON ix.indexrelid = s.indexrelid
                JOIN pg_attribute a ON a.attrelid = c.oid AND a.attnum = ANY(ix.indkey)
                WHERE i.schemaname = 'public'
                    AND i.tablename LIKE 'automation_%'
                GROUP BY t.tablename, i.indexname, idx_scan, i.indexrelid
                ORDER BY t.tablename, i.indexname;
            """)

            results = cursor.fetchall()

            if not results:
                self.stdout.write(self.style.WARNING('No indexes found for automation models.'))
                return

            current_table = None
            for table, index, columns, scans, size in results:
                if table != current_table:
                    self.stdout.write(f'\n{self.style.SUCCESS(table)}')
                    current_table = table

                columns_str = ', '.join(columns) if columns else 'N/A'
                scans_str = f'{scans:,}' if scans else '0'
                self.stdout.write(f'  {index}')
                self.stdout.write(f'    Columns: {columns_str}')
                self.stdout.write(f'    Scans: {scans_str}')
                self.stdout.write(f'    Size: {size}')

    def check_unused_indexes(self):
        """Check for unused indexes."""
        with connection.cursor() as cursor:
            cursor.execute("""
                SELECT
                    schemaname,
                    tablename,
                    indexname,
                    pg_size_pretty(pg_relation_size(indexrelid)) as size
                FROM pg_stat_user_indexes
                WHERE idx_scan = 0
                    AND indexname NOT LIKE 'pg_toast%'
                    AND schemaname = 'public'
                    AND tablename LIKE 'automation_%'
                ORDER BY pg_relation_size(indexrelid) DESC;
            """)

            results = cursor.fetchall()

            if not results:
                self.stdout.write(self.style.SUCCESS('No unused indexes found!'))
                return

            self.stdout.write(self.style.WARNING(f'Found {len(results)} unused indexes:\n'))

            for schema, table, index, size in results:
                self.stdout.write(f'  {table}.{index} ({size})')

            self.stdout.write(self.style.WARNING(
                '\nConsider removing unused indexes to improve write performance.'
            ))

    def check_missing_indexes(self):
        """Check for missing indexes defined in models."""
        automation_app = apps.get_app_config('automation')
        models = automation_app.get_models()

        self.stdout.write('Checking for missing indexes...\n')

        missing_count = 0

        for model in models:
            table_name = model._meta.db_table

            # Get indexes defined in model
            model_indexes = getattr(model._meta, 'indexes', [])

            if not model_indexes:
                continue

            self.stdout.write(f'\n{self.style.SUCCESS(model.__name__)} ({table_name})')

            # Get actual indexes from database
            with connection.cursor() as cursor:
                cursor.execute("""
                    SELECT indexname
                    FROM pg_indexes
                    WHERE schemaname = 'public'
                        AND tablename = %s;
                """, [table_name])

                db_indexes = {row[0] for row in cursor.fetchall()}

            # Check each model index
            for index in model_indexes:
                index_name = index.name

                if index_name in db_indexes:
                    self.stdout.write(f'  ✓ {index_name}')
                else:
                    self.stdout.write(self.style.ERROR(f'  ✗ {index_name} (MISSING)'))
                    missing_count += 1

        if missing_count > 0:
            self.stdout.write(self.style.ERROR(
                f'\n{missing_count} indexes are missing. Run migrations to create them.'
            ))
            sys.exit(1)
        else:
            self.stdout.write(self.style.SUCCESS('\nAll model indexes are present!'))

    def show_index_sizes(self):
        """Show index sizes for automation models."""
        with connection.cursor() as cursor:
            cursor.execute("""
                SELECT
                    tablename,
                    indexname,
                    pg_size_pretty(pg_relation_size(indexrelid)) AS index_size,
                    pg_relation_size(indexrelid) AS size_bytes
                FROM pg_stat_user_indexes
                WHERE schemaname = 'public'
                    AND tablename LIKE 'automation_%'
                ORDER BY pg_relation_size(indexrelid) DESC;
            """)

            results = cursor.fetchall()

            if not results:
                self.stdout.write(self.style.WARNING('No indexes found.'))
                return

            self.stdout.write(self.style.SUCCESS('Index sizes:\n'))

            total_size = 0
            for table, index, size, size_bytes in results:
                self.stdout.write(f'  {table}.{index}: {size}')
                total_size += size_bytes

            # Convert total size to human readable
            if total_size < 1024:
                total_str = f'{total_size} bytes'
            elif total_size < 1024 * 1024:
                total_str = f'{total_size / 1024:.2f} KB'
            elif total_size < 1024 * 1024 * 1024:
                total_str = f'{total_size / (1024 * 1024):.2f} MB'
            else:
                total_str = f'{total_size / (1024 * 1024 * 1024):.2f} GB'

            self.stdout.write(f'\nTotal index size: {total_str}')
