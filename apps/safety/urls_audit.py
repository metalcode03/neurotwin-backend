"""
Audit API URL configuration.

Requirements: 11.1-11.5, 13.1
"""

from django.urls import path

from .views import AuditListView, AuditDetailView, AuditVerifyView

app_name = 'audit'

urlpatterns = [
    path('', AuditListView.as_view(), name='list'),
    path('<str:entry_id>', AuditDetailView.as_view(), name='detail'),
    path('<str:entry_id>/verify', AuditVerifyView.as_view(), name='verify'),
]
