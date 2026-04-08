"""
NeuroTwin Django project initialization.

This ensures Celery app is loaded when Django starts.
"""

# Import Celery app to ensure it's loaded
from .celery import app as celery_app

__all__ = ('celery_app',)
