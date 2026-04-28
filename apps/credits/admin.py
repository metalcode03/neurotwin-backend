"""
Django admin configuration for credits app.
"""

from django.contrib import admin
from unfold.admin import ModelAdmin as UnfoldModelAdmin
from unfold.decorators import display

from neurotwin.admin_utils import format_credits

from .models import (
    UserCredits,
    CreditUsageLog,
    AIRequestLog,
    BrainRoutingConfig,
    CreditTopUp,
)


@admin.register(UserCredits)
class UserCreditsAdmin(UnfoldModelAdmin):
    list_display = [
        'user',
        'display_remaining_credits',
        'display_monthly_credits',
        'display_used_credits',
        'display_purchased_credits',
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

    @display(description="Remaining")
    def display_remaining_credits(self, obj):
        return format_credits(obj.remaining_credits)

    @display(description="Monthly")
    def display_monthly_credits(self, obj):
        return format_credits(obj.monthly_credits)

    @display(description="Used")
    def display_used_credits(self, obj):
        return format_credits(obj.used_credits)

    @display(description="Purchased")
    def display_purchased_credits(self, obj):
        return format_credits(obj.purchased_credits)


@admin.register(CreditUsageLog)
class CreditUsageLogAdmin(UnfoldModelAdmin):
    list_display = [
        'user',
        'operation_type',
        'display_credits_consumed',
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

    @display(description="Credits")
    def display_credits_consumed(self, obj):
        return format_credits(obj.credits_consumed)


@admin.register(AIRequestLog)
class AIRequestLogAdmin(UnfoldModelAdmin):
    list_display = [
        'user',
        'brain_mode',
        'model_used',
        'display_credits_consumed',
        'display_status',
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

    @display(
        description="Status",
        label={
            "success": "success",
            "failed": "danger",
            "insufficient_credits": "warning",
            "model_error": "danger",
        },
    )
    def display_status(self, obj):
        return obj.status

    @display(description="Credits")
    def display_credits_consumed(self, obj):
        if obj.credits_consumed is not None:
            return format_credits(obj.credits_consumed)
        return "-"


@admin.register(BrainRoutingConfig)
class BrainRoutingConfigAdmin(UnfoldModelAdmin):
    list_display = [
        'config_name',
        'display_is_active',
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

    @display(
        description="Active",
        label={
            True: "success",
            False: "danger",
        },
    )
    def display_is_active(self, obj):
        return obj.is_active


@admin.register(CreditTopUp)
class CreditTopUpAdmin(UnfoldModelAdmin):
    list_display = [
        'user',
        'display_amount',
        'payment_method',
        'display_status',
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

    @display(
        description="Status",
        label={
            "pending": "warning",
            "completed": "success",
            "failed": "danger",
            "refunded": "info",
        },
    )
    def display_status(self, obj):
        return obj.status

    @display(description="Amount")
    def display_amount(self, obj):
        return format_credits(obj.amount)
