"""
Admin configuration for subscription models.
"""

from django.contrib import admin
from .models import Subscription, SubscriptionHistory


@admin.register(Subscription)
class SubscriptionAdmin(admin.ModelAdmin):
    list_display = ['user', 'tier', 'is_active', 'started_at', 'expires_at']
    list_filter = ['tier', 'is_active']
    search_fields = ['user__email']
    readonly_fields = ['id', 'created_at', 'updated_at']


@admin.register(SubscriptionHistory)
class SubscriptionHistoryAdmin(admin.ModelAdmin):
    list_display = ['subscription', 'from_tier', 'to_tier', 'reason', 'changed_at']
    list_filter = ['from_tier', 'to_tier', 'reason']
    readonly_fields = ['id', 'changed_at']
