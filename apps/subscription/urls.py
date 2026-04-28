"""
Subscription API URL configuration.

Requirements: 3.1-3.7, 13.1
"""

from django.urls import path
from .views import (
    SubscriptionView,
    SubscriptionUpgradeView,
    SubscriptionDowngradeView,
    SubscriptionHistoryView,
    FeatureAccessView,
)
from .webhooks import FlutterwaveWebhookView

app_name = 'subscription'

urlpatterns = [
    path('', SubscriptionView.as_view(), name='subscription'),
    path('upgrade', SubscriptionUpgradeView.as_view(), name='upgrade'),
    path('downgrade', SubscriptionDowngradeView.as_view(), name='downgrade'),
    path('history', SubscriptionHistoryView.as_view(), name='history'),
    path('features/<str:feature>', FeatureAccessView.as_view(), name='feature-access'),
    path('webhook/flutterwave', FlutterwaveWebhookView.as_view(), name='flutterwave-webhook'),
]
