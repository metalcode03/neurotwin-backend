"""
Django app configuration for automation app.
"""

from django.apps import AppConfig


class AutomationConfig(AppConfig):
    """Configuration for the automation app."""
    
    default_auto_field = 'django.db.models.BigAutoField'
    name = 'apps.automation'
    verbose_name = 'Automation Hub'
    
    def ready(self):
        """Import signal handlers when app is ready."""
        import apps.automation.signals  # noqa: F401
        
        # Register cache invalidation signals (Requirement 31.6)
        from apps.automation.signals import register_cache_invalidation_signals
        register_cache_invalidation_signals()
