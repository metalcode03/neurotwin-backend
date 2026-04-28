"""
Django admin configuration for the Learning app.
"""

from django.contrib import admin
from unfold.admin import ModelAdmin as UnfoldModelAdmin

from .models import LearningEvent


@admin.register(LearningEvent)
class LearningEventAdmin(UnfoldModelAdmin):
    """Admin configuration for LearningEvent model."""
    
    list_display = [
        'id',
        'user',
        'action_type',
        'action_category',
        'is_processed',
        'is_profile_updated',
        'feedback',
        'created_at',
    ]
    list_filter = [
        'action_category',
        'is_processed',
        'is_profile_updated',
        'feedback',
        'created_at',
    ]
    search_fields = [
        'user__email',
        'action_type',
        'action_content',
    ]
    readonly_fields = [
        'id',
        'created_at',
        'processed_at',
        'feedback_applied_at',
    ]
    ordering = ['-created_at']
    
    fieldsets = [
        ('Event Info', {
            'fields': ['id', 'user', 'created_at']
        }),
        ('Action Details', {
            'fields': [
                'action_type',
                'action_category',
                'action_content',
                'action_context',
            ]
        }),
        ('Feature Extraction', {
            'fields': [
                'features',
                'is_processed',
                'processed_at',
                'processing_error',
            ]
        }),
        ('Profile Updates', {
            'fields': [
                'profile_updates',
                'csm_version_before',
                'csm_version_after',
                'is_profile_updated',
            ]
        }),
        ('Feedback', {
            'fields': [
                'feedback',
                'feedback_content',
                'feedback_applied_at',
            ]
        }),
    ]
