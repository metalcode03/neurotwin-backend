"""
Django app configuration for the Learning app.
"""

from django.apps import AppConfig


class LearningConfig(AppConfig):
    """Configuration for the Learning app."""
    
    default_auto_field = 'django.db.models.BigAutoField'
    name = 'apps.learning'
    verbose_name = 'Learning Loop'
