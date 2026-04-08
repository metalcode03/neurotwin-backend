"""
Webhook URL Configuration

URL patterns for webhook endpoints (Meta, future providers).

Requirements: 10.1-10.7
"""

from django.urls import path
from apps.automation.views.webhooks import meta_webhook

app_name = 'webhooks'

urlpatterns = [
    # Meta webhook endpoint (GET for verification, POST for events)
    path('meta/', meta_webhook, name='meta_webhook'),
]
