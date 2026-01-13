"""
CSM app configuration.
"""

from django.apps import AppConfig


class CsmConfig(AppConfig):
    """Configuration for the CSM app."""
    
    default_auto_field = 'django.db.models.BigAutoField'
    name = 'apps.csm'
    verbose_name = 'Cognitive Signature Model'
