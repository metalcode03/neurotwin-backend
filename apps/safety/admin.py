"""
Admin configuration for the safety app.
"""

from django.contrib import admin
from unfold.admin import ModelAdmin as UnfoldModelAdmin

from .models import PermissionScope, PermissionHistory


@admin.register(PermissionScope)
class PermissionScopeAdmin(UnfoldModelAdmin):
    """Admin configuration for PermissionScope model."""
    
    list_display = [
        'user',
        'integration',
        'action_type',
        'is_granted',
        'requires_approval',
        'updated_at',
    ]
    list_filter = [
        'integration',
        'action_type',
        'is_granted',
        'requires_approval',
    ]
    search_fields = ['user__email', 'integration', 'action_type']
    readonly_fields = ['id', 'created_at', 'updated_at']
    ordering = ['user', 'integration', 'action_type']


@admin.register(PermissionHistory)
class PermissionHistoryAdmin(UnfoldModelAdmin):
    """Admin configuration for PermissionHistory model."""
    
    list_display = [
        'permission_scope',
        'previous_is_granted',
        'new_is_granted',
        'changed_at',
        'reason',
    ]
    list_filter = ['new_is_granted', 'changed_at']
    search_fields = ['permission_scope__user__email', 'reason']
    readonly_fields = ['id', 'changed_at']
    ordering = ['-changed_at']
