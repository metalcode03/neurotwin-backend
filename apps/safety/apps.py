"""
Safety app configuration.
"""

from django.apps import AppConfig


class SafetyConfig(AppConfig):
    """Configuration for the safety app."""
    
    default_auto_field = 'django.db.models.BigAutoField'
    name = 'apps.safety'
    verbose_name = 'Safety'
