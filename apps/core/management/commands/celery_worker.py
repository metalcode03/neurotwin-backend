"""
Django management command to start Celery workers.

Requirements: 11.1-11.7

Usage:
    python manage.py celery_worker [--queue QUEUE] [--concurrency N] [--loglevel LEVEL]
"""
import sys
import shlex
import subprocess
from django.core.management.base import BaseCommand
from django.conf import settings


class Command(BaseCommand):
    help = 'Start Celery worker with specified configuration'

    def add_arguments(self, parser):
        parser.add_argument(
            '--queue',
            type=str,
            default='default,incoming_messages,outgoing_messages,high_priority',
            help='Comma-separated list of queues to consume from (default: all queues)',
        )
        parser.add_argument(
            '--concurrency',
            type=int,
            default=4,
            help='Number of concurrent worker processes (default: 4)',
        )
        parser.add_argument(
            '--loglevel',
            type=str,
            default='info',
            choices=['debug', 'info', 'warning', 'error', 'critical'],
            help='Logging level (default: info)',
        )
        parser.add_argument(
            '--autoscale',
            type=str,
            default=None,
            help='Enable autoscaling: MAX,MIN (e.g., 10,3)',
        )
        parser.add_argument(
            '--pool',
            type=str,
            default='prefork',
            choices=['prefork', 'solo', 'eventlet', 'gevent'],
            help='Pool implementation (default: prefork)',
        )

    def handle(self, *args, **options):
        queue = options['queue']
        concurrency = options['concurrency']
        loglevel = options['loglevel']
        autoscale = options['autoscale']
        pool = options['pool']

        self.stdout.write(self.style.SUCCESS('Starting Celery worker...'))
        self.stdout.write(f'Queues: {queue}')
        self.stdout.write(f'Concurrency: {concurrency}')
        self.stdout.write(f'Log level: {loglevel}')
        self.stdout.write(f'Pool: {pool}')

        # Build Celery worker command
        cmd = [
            'celery',
            '-A', 'neurotwin',
            'worker',
            '--queues', queue,
            '--loglevel', loglevel,
            '--pool', pool,
        ]

        # Add concurrency or autoscale
        if autoscale:
            cmd.extend(['--autoscale', autoscale])
        else:
            cmd.extend(['--concurrency', str(concurrency)])

        # Add additional worker options
        cmd.extend([
            '--without-gossip',  # Disable gossip for better performance
            '--without-mingle',  # Disable mingle for faster startup
            '--without-heartbeat',  # Disable heartbeat for simpler setup
        ])

        self.stdout.write(self.style.WARNING(f'\nCommand: {" ".join(cmd)}\n'))
        self.stdout.write(self.style.SUCCESS('Worker is running. Press Ctrl+C to stop.\n'))

        try:
            # Run Celery worker
            subprocess.run(cmd, check=True)
        except KeyboardInterrupt:
            self.stdout.write(self.style.WARNING('\nStopping Celery worker...'))
            sys.exit(0)
        except subprocess.CalledProcessError as e:
            self.stdout.write(self.style.ERROR(f'\nCelery worker failed with exit code {e.returncode}'))
            sys.exit(e.returncode)
        except FileNotFoundError:
            self.stdout.write(self.style.ERROR(
                '\nCelery is not installed or not in PATH. '
                'Install it with: uv add celery'
            ))
            sys.exit(1)
