"""
Admin interface for subscription management.
"""

from django.contrib import admin
from unfold.admin import ModelAdmin as UnfoldModelAdmin
from unfold.decorators import display

from neurotwin.admin_utils import format_currency

from .models import Subscription, SubscriptionHistory
from .payment_models import PaymentTransaction, WebhookLog


@admin.register(Subscription)
class SubscriptionAdmin(UnfoldModelAdmin):
    """Admin interface for Subscription model."""
    
    list_display = [
        'user',
        'tier',
        'display_is_active',
        'started_at',
        'expires_at',
        'is_lapsed',
    ]
    list_filter = ['tier', 'is_active', 'started_at']
    search_fields = ['user__email', 'user__first_name', 'user__last_name']
    readonly_fields = ['id', 'created_at', 'updated_at']
    date_hierarchy = 'started_at'

    @display(
        description="Active",
        label={
            True: "success",
            False: "danger",
        },
    )
    def display_is_active(self, obj):
        return obj.is_active


@admin.register(SubscriptionHistory)
class SubscriptionHistoryAdmin(UnfoldModelAdmin):
    """Admin interface for SubscriptionHistory model."""
    
    list_display = [
        'subscription',
        'from_tier',
        'to_tier',
        'reason',
        'changed_at',
    ]
    list_filter = ['from_tier', 'to_tier', 'reason', 'changed_at']
    search_fields = ['subscription__user__email']
    readonly_fields = ['id', 'changed_at']
    date_hierarchy = 'changed_at'


@admin.register(PaymentTransaction)
class PaymentTransactionAdmin(UnfoldModelAdmin):
    """Admin interface for PaymentTransaction model."""
    
    list_display = [
        'tx_ref',
        'user',
        'display_amount',
        'currency',
        'tier',
        'display_status',
        'signature_verified',
        'created_at',
    ]
    list_filter = [
        'status',
        'currency',
        'tier',
        'signature_verified',
        'created_at',
    ]
    search_fields = [
        'tx_ref',
        'flutterwave_tx_id',
        'user__email',
    ]
    readonly_fields = [
        'id',
        'created_at',
        'updated_at',
        'webhook_received_at',
        'processed_at',
    ]
    date_hierarchy = 'created_at'
    
    fieldsets = (
        ('Transaction Info', {
            'fields': (
                'id',
                'tx_ref',
                'flutterwave_tx_id',
                'status',
                'payment_status',
            )
        }),
        ('User & Subscription', {
            'fields': (
                'user',
                'subscription',
                'tier',
            )
        }),
        ('Payment Details', {
            'fields': (
                'amount',
                'currency',
            )
        }),
        ('Security', {
            'fields': (
                'signature_verified',
                'ip_address',
            )
        }),
        ('Processing', {
            'fields': (
                'webhook_received_at',
                'processed_at',
                'retry_count',
                'error_message',
            )
        }),
        ('Audit', {
            'fields': (
                'webhook_payload',
                'created_at',
                'updated_at',
            )
        }),
    )

    @display(
        description="Status",
        label={
            "pending": "warning",
            "processing": "info",
            "completed": "success",
            "failed": "danger",
            "duplicate": "warning",
        },
    )
    def display_status(self, obj):
        return obj.status

    @display(description="Amount")
    def display_amount(self, obj):
        return format_currency(float(obj.amount), symbol=f"{obj.currency} ")


@admin.register(WebhookLog)
class WebhookLogAdmin(UnfoldModelAdmin):
    """Admin interface for WebhookLog model."""
    
    list_display = [
        'event_type',
        'ip_address',
        'signature_valid',
        'processed',
        'response_status',
        'created_at',
    ]
    list_filter = [
        'event_type',
        'signature_valid',
        'processed',
        'response_status',
        'created_at',
    ]
    search_fields = [
        'ip_address',
        'event_type',
    ]
    readonly_fields = [
        'id',
        'created_at',
    ]
    date_hierarchy = 'created_at'
    
    fieldsets = (
        ('Event Info', {
            'fields': (
                'id',
                'event_type',
                'created_at',
            )
        }),
        ('Security', {
            'fields': (
                'ip_address',
                'signature_provided',
                'signature_valid',
            )
        }),
        ('Processing', {
            'fields': (
                'processed',
                'response_status',
                'error_message',
                'transaction',
            )
        }),
        ('Request Data', {
            'fields': (
                'payload',
                'headers',
            ),
            'classes': ('collapse',),
        }),
    )
