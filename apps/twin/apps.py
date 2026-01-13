"""
Django app configuration for Twin app.
"""

from django.apps import AppConfig


class TwinConfig(AppConfig):
    """Configuration for the Twin Django app."""
    
    default_auto_field = 'django.db.models.BigAutoField'
    name = 'apps.twin'
    verbose_name = 'Twin Management'
