"""
Django admin configuration for Twin app.
"""

from django.contrib import admin
from .models import Twin, OnboardingProgress


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
