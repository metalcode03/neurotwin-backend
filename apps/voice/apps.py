"""
Voice app configuration.
"""

from django.apps import AppConfig


class VoiceConfig(AppConfig):
    """Configuration for the voice app."""
    
    default_auto_field = 'django.db.models.BigAutoField'
    name = 'apps.voice'
    verbose_name = 'Voice Twin'
