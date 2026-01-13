"""
Integration API URL configuration.

Requirements: 7.1-7.6, 13.1
"""

from django.urls import path

from .views import (
    IntegrationListView,
    IntegrationConnectView,
    IntegrationDetailView,
    IntegrationPermissionsView,
)

app_name = 'integrations'

urlpatterns = [
    path('', IntegrationListView.as_view(), name='list'),
    path('<str:integration_type>/connect', IntegrationConnectView.as_view(), name='connect'),
    path('<str:integration_id>', IntegrationDetailView.as_view(), name='detail'),
    path('<str:integration_id>/permissions', IntegrationPermissionsView.as_view(), name='permissions'),
]
