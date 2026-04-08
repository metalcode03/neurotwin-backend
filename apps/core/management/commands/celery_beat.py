"""
Django management command to start Celery Beat scheduler.

Requirements: 11.1-11.7

Usage:
    python manage.py celery_beat [--loglevel LEVEL]
"""
import sys
import subprocess
from django.core.management.base import BaseCommand


class Command(BaseCommand):
    help = 'Start Celery Beat scheduler for periodic tasks'

    def add_arguments(self, parser):
        parser.add_argument(
            '--loglevel',
            type=str,
            default='info',
            choices=['debug', 'info', 'warning', 'error', 'critical'],
            help='Logging level (default: info)',
        )

    def handle(self, *args, **options):
        loglevel = options['loglevel']

        self.stdout.write(self.style.SUCCESS('Starting Celery Beat scheduler...'))
        self.stdout.write(f'Log level: {loglevel}')

        # Build Celery Beat command
        cmd = [
            'celery',
            '-A', 'neurotwin',
            'beat',
            '--loglevel', loglevel,
            '--scheduler', 'django_celery_beat.schedulers:DatabaseScheduler',
        ]

        self.stdout.write(self.style.WARNING(f'\nCommand: {" ".join(cmd)}\n'))
        self.stdout.write(self.style.SUCCESS('Beat scheduler is running. Press Ctrl+C to stop.\n'))

        try:
            # Run Celery Beat
            subprocess.run(cmd, check=True)
        except KeyboardInterrupt:
            self.stdout.write(self.style.WARNING('\nStopping Celery Beat...'))
            sys.exit(0)
        except subprocess.CalledProcessError as e:
            self.stdout.write(self.style.ERROR(f'\nCelery Beat failed with exit code {e.returncode}'))
            sys.exit(e.returncode)
        except FileNotFoundError:
            self.stdout.write(self.style.ERROR(
                '\nCelery is not installed or not in PATH. '
                'Install it with: uv add celery'
            ))
            sys.exit(1)
