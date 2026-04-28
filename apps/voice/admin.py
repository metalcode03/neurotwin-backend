"""
Admin configuration for voice app.
"""

from django.contrib import admin
from unfold.admin import ModelAdmin as UnfoldModelAdmin

from .models import VoiceProfile, CallRecord, VoiceApprovalHistory


@admin.register(VoiceProfile)
class VoiceProfileAdmin(UnfoldModelAdmin):
    """Admin for VoiceProfile model."""
    
    list_display = [
        'user', 'phone_number', 'is_enabled', 
        'is_approved', 'approval_expires_at', 'created_at'
    ]
    list_filter = ['is_enabled', 'is_approved']
    search_fields = ['user__email', 'phone_number']
    readonly_fields = ['id', 'created_at', 'updated_at']
    
    fieldsets = [
        (None, {
            'fields': ['id', 'user']
        }),
        ('Phone Configuration', {
            'fields': ['phone_number', 'twilio_phone_sid', 'is_enabled']
        }),
        ('Voice Clone', {
            'fields': ['voice_clone_id', 'voice_clone_name']
        }),
        ('Approval', {
            'fields': ['is_approved', 'approval_expires_at']
        }),
        ('Timestamps', {
            'fields': ['created_at', 'updated_at']
        }),
    ]


@admin.register(CallRecord)
class CallRecordAdmin(UnfoldModelAdmin):
    """Admin for CallRecord model."""
    
    list_display = [
        'user', 'direction', 'phone_number', 'status',
        'duration_seconds', 'was_terminated', 'created_at'
    ]
    list_filter = ['direction', 'status', 'was_terminated']
    search_fields = ['user__email', 'phone_number', 'twilio_call_sid']
    readonly_fields = ['id', 'created_at', 'updated_at']
    
    fieldsets = [
        (None, {
            'fields': ['id', 'user', 'voice_profile']
        }),
        ('Call Details', {
            'fields': [
                'twilio_call_sid', 'direction', 'phone_number',
                'status', 'cognitive_blend'
            ]
        }),
        ('Content', {
            'fields': ['transcript', 'script']
        }),
        ('Metrics', {
            'fields': ['duration_seconds', 'started_at', 'ended_at']
        }),
        ('Termination', {
            'fields': ['was_terminated', 'termination_reason']
        }),
        ('Timestamps', {
            'fields': ['created_at', 'updated_at']
        }),
    ]


@admin.register(VoiceApprovalHistory)
class VoiceApprovalHistoryAdmin(UnfoldModelAdmin):
    """Admin for VoiceApprovalHistory model."""
    
    list_display = ['voice_profile', 'action', 'duration_minutes', 'timestamp']
    list_filter = ['action']
    search_fields = ['voice_profile__user__email']
    readonly_fields = ['id', 'timestamp']
