"""
Django admin configuration for credits app.
"""

from django.contrib import admin
from django.utils.html import format_html
from .models import (
    UserCredits,
    CreditUsageLog,
    AIRequestLog,
    BrainRoutingConfig,
    CreditTopUp,
)


@admin.register(UserCredits)
class UserCreditsAdmin(admin.ModelAdmin):
    list_display = [
        'user',
        'remaining_credits',
        'monthly_credits',
        'used_credits',
        'purchased_credits',
        'last_reset_date',
        'created_at',
    ]
    list_filter = ['created_at', 'last_reset_date']
    search_fields = ['user__email', 'user__username']
    readonly_fields = ['created_at', 'updated_at']
    ordering = ['-remaining_credits']

    fieldsets = (
        ('User Information', {
            'fields': ('user',)
        }),
        ('Credit Balance', {
            'fields': ('monthly_credits', 'remaining_credits', 'used_credits', 'purchased_credits')
        }),
        ('Reset Information', {
            'fields': ('last_reset_date',)
        }),
        ('Timestamps', {
            'fields': ('created_at', 'updated_at'),
            'classes': ('collapse',)
        }),
    )


@admin.register(CreditUsageLog)
class CreditUsageLogAdmin(admin.ModelAdmin):
    list_display = [
        'user',
        'operation_type',
        'credits_consumed',
        'brain_mode',
        'model_used',
        'timestamp',
    ]
    list_filter = ['operation_type', 'brain_mode', 'timestamp']
    search_fields = ['user__email', 'user__username', 'model_used']
    readonly_fields = ['created_at', 'timestamp']
    ordering = ['-timestamp']

    fieldsets = (
        ('User & Operation', {
            'fields': ('user', 'operation_type', 'brain_mode')
        }),
        ('Credits & Model', {
            'fields': ('credits_consumed', 'model_used')
        }),
        ('Request Details', {
            'fields': ('request_id',)
        }),
        ('Timestamps', {
            'fields': ('timestamp', 'created_at')
        }),
    )


@admin.register(AIRequestLog)
class AIRequestLogAdmin(admin.ModelAdmin):
    list_display = [
        'user',
        'brain_mode',
        'model_used',
        'credits_consumed',
        'status',
        'timestamp',
    ]
    list_filter = ['brain_mode', 'model_used', 'status', 'timestamp']
    search_fields = ['user__email', 'user__username', 'id']
    readonly_fields = ['created_at', 'timestamp', 'id']
    ordering = ['-timestamp']

    fieldsets = (
        ('Request Information', {
            'fields': ('id', 'user', 'brain_mode', 'operation_type', 'model_used')
        }),
        ('Usage Details', {
            'fields': (
                'credits_consumed',
                'tokens_used',
                'prompt_length',
                'response_length',
            )
        }),
        ('Status & Timing', {
            'fields': (
                'status',
                'latency_ms',
                'timestamp',
                'created_at',
            )
        }),
        ('Error Information', {
            'fields': ('error_message', 'error_type'),
            'classes': ('collapse',)
        }),
        ('Cognitive Data', {
            'fields': ('cognitive_blend_value',),
            'classes': ('collapse',)
        }),
    )


@admin.register(BrainRoutingConfig)
class BrainRoutingConfigAdmin(admin.ModelAdmin):
    list_display = [
        'config_name',
        'is_active',
        'created_by',
        'updated_at',
    ]
    list_filter = ['is_active', 'created_at']
    search_fields = ['config_name', 'created_by__email']
    readonly_fields = ['created_at', 'updated_at']
    ordering = ['-updated_at']

    fieldsets = (
        ('Configuration', {
            'fields': ('config_name', 'is_active', 'created_by')
        }),
        ('Routing Rules', {
            'fields': ('routing_rules',),
            'description': 'JSON mapping of brain_mode -> operation_type -> model'
        }),
        ('Timestamps', {
            'fields': ('created_at', 'updated_at'),
            'classes': ('collapse',)
        }),
    )


@admin.register(CreditTopUp)
class CreditTopUpAdmin(admin.ModelAdmin):
    list_display = [
        'user',
        'amount',
        'payment_method',
        'status',
        'created_at',
    ]
    list_filter = ['payment_method', 'status', 'created_at']
    search_fields = ['user__email', 'user__username', 'transaction_id']
    readonly_fields = ['created_at', 'updated_at', 'id']
    ordering = ['-created_at']

    fieldsets = (
        ('User & Transaction', {
            'fields': ('id', 'user', 'transaction_id', 'amount')
        }),
        ('Payment Details', {
            'fields': ('payment_method', 'price_paid', 'status')
        }),
        ('Timestamps', {
            'fields': ('created_at', 'updated_at')
        }),
    )

    def get_readonly_fields(self, request, obj=None):
        """Make transaction_id readonly after creation."""
        if obj:  # Editing existing object
            return self.readonly_fields + ('transaction_id',)
        return self.readonly_fields
