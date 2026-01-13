"""
Memory app configuration.
"""

from django.apps import AppConfig


class MemoryConfig(AppConfig):
    """Configuration for the Memory app."""
    
    default_auto_field = 'django.db.models.BigAutoField'
    name = 'apps.memory'
    verbose_name = 'Memory'
