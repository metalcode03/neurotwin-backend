"""
Integration API URL configuration.

Requirements: 7.1-7.6, 13.1, 20.1-20.3, 23.1-23.7, 28.1-28.7
"""

from django.urls import path

from .views import (
    IntegrationListView,
    IntegrationConnectView,
    IntegrationDetailView,
    IntegrationPermissionsView,
    IntegrationDeleteView,
    DataExportView,
    DataDeletionView,
)

app_name = 'integrations'

urlpatterns = [
    # GDPR compliance endpoints
    path('export/', DataExportView.as_view(), name='export'),
    path('delete-all/', DataDeletionView.as_view(), name='delete-all'),
    
    # Integration management endpoints
    path('', IntegrationListView.as_view(), name='list'),
    path('<uuid:integration_id>/', IntegrationDetailView.as_view(), name='detail'),
    path('<uuid:integration_id>/delete/', IntegrationDeleteView.as_view(), name='delete'),
    
    # Legacy endpoints (to be deprecated)
    path('<str:integration_type>/connect', IntegrationConnectView.as_view(), name='connect'),
    path('<str:integration_id>/permissions', IntegrationPermissionsView.as_view(), name='permissions'),
]
