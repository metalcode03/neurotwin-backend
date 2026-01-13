"""
Django admin configuration for automation app.
"""

from django.contrib import admin

from .models import Integration


@admin.register(Integration)
class IntegrationAdmin(admin.ModelAdmin):
    """Admin configuration for Integration model."""
    
    list_display = [
        'user',
        'type',
        'is_active',
        'token_expires_at',
        'created_at',
    ]
    list_filter = ['type', 'is_active']
    search_fields = ['user__email', 'type']
    readonly_fields = ['id', 'created_at', 'updated_at']
    ordering = ['-created_at']
