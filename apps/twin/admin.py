"""
Django admin configuration for Twin app.
"""

from django.contrib import admin
from .models import Twin, OnboardingProgress, AuditLog


@admin.register(Twin)
class TwinAdmin(admin.ModelAdmin):
    """Admin configuration for Twin model."""
    
    list_display = [
        'id', 'user', 'model', 'cognitive_blend', 
        'is_active', 'kill_switch_active', 'created_at'
    ]
    list_filter = ['model', 'is_active', 'kill_switch_active']
    search_fields = ['user__email']
    readonly_fields = ['id', 'created_at', 'updated_at']
    
    fieldsets = [
        ('Basic Info', {
            'fields': ['id', 'user', 'model']
        }),
        ('Cognitive Settings', {
            'fields': ['cognitive_blend', 'csm_profile']
        }),
        ('Status', {
            'fields': ['is_active', 'kill_switch_active']
        }),
        ('Timestamps', {
            'fields': ['created_at', 'updated_at'],
            'classes': ['collapse']
        }),
    ]


@admin.register(OnboardingProgress)
class OnboardingProgressAdmin(admin.ModelAdmin):
    """Admin configuration for OnboardingProgress model."""
    
    list_display = [
        'id', 'user', 'selected_model', 'is_complete', 'started_at'
    ]
    list_filter = ['is_complete', 'selected_model']
    search_fields = ['user__email']
    readonly_fields = ['id', 'started_at', 'updated_at']



@admin.register(AuditLog)
class AuditLogAdmin(admin.ModelAdmin):
    """
    Admin configuration for AuditLog model.
    
    Provides filtering, searching, and viewing of audit logs
    in chronological order.
    
    Requirements: 8.2
    """
    
    list_display = [
        'timestamp',
        'event_type',
        'user',
        'resource_type',
        'action',
        'result',
        'initiated_by_twin',
        'requires_attention',
    ]
    
    list_filter = [
        'event_type',
        'action',
        'result',
        'initiated_by_twin',
        'timestamp',
        'resource_type',
    ]
    
    search_fields = [
        'user__email',
        'resource_type',
        'resource_id',
        'details',
    ]
    
    readonly_fields = [
        'id',
        'timestamp',
        'event_type',
        'user',
        'resource_type',
        'resource_id',
        'action',
        'result',
        'details',
        'initiated_by_twin',
        'cognitive_blend_value',
        'permission_flag',
        'ip_address',
        'user_agent',
        'is_twin_action',
        'requires_attention',
    ]
    
    fieldsets = [
        ('Event Information', {
            'fields': [
                'id',
                'timestamp',
                'event_type',
                'user',
            ]
        }),
        ('Resource Details', {
            'fields': [
                'resource_type',
                'resource_id',
                'action',
                'result',
            ]
        }),
        ('Twin Context', {
            'fields': [
                'initiated_by_twin',
                'cognitive_blend_value',
                'permission_flag',
                'is_twin_action',
                'requires_attention',
            ]
        }),
        ('Additional Details', {
            'fields': [
                'details',
            ]
        }),
        ('Request Context', {
            'fields': [
                'ip_address',
                'user_agent',
            ],
            'classes': ['collapse']
        }),
    ]
    
    # Ordering by most recent first
    ordering = ['-timestamp']
    
    # Disable add/edit/delete permissions (audit logs are immutable)
    def has_add_permission(self, request):
        """Audit logs cannot be manually created."""
        return False
    
    def has_change_permission(self, request, obj=None):
        """Audit logs cannot be modified."""
        return False
    
    def has_delete_permission(self, request, obj=None):
        """Audit logs cannot be deleted."""
        return False
    
    # Custom display methods
    def requires_attention(self, obj):
        """Display whether this log requires attention."""
        return obj.requires_attention
    requires_attention.boolean = True
    requires_attention.short_description = 'Needs Attention'
    
    # Pagination
    list_per_page = 50
    
    # Date hierarchy for easy navigation
    date_hierarchy = 'timestamp'
