"""
Admin configuration for CSM app.
"""

from django.contrib import admin
from unfold.admin import ModelAdmin as UnfoldModelAdmin

from .models import CSMProfile, CSMChangeLog


@admin.register(CSMProfile)
class CSMProfileAdmin(UnfoldModelAdmin):
    """Admin for CSM profiles."""
    
    list_display = ['id', 'user', 'version', 'is_current', 'created_at', 'updated_at']
    list_filter = ['is_current', 'created_at']
    search_fields = ['user__email']
    readonly_fields = ['id', 'created_at', 'updated_at']
    ordering = ['-created_at']


@admin.register(CSMChangeLog)
class CSMChangeLogAdmin(UnfoldModelAdmin):
    """Admin for CSM change logs."""
    
    list_display = ['id', 'profile', 'from_version', 'to_version', 'change_type', 'changed_at']
    list_filter = ['change_type', 'changed_at']
    readonly_fields = ['id', 'changed_at']
    ordering = ['-changed_at']
