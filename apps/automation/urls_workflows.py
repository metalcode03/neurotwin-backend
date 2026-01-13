"""
Workflow API URL configuration.

Requirements: 8.1-8.6, 13.1
"""

from django.urls import path

from .views import (
    WorkflowListView,
    WorkflowDetailView,
    WorkflowExecuteView,
)

app_name = 'workflows'

urlpatterns = [
    path('', WorkflowListView.as_view(), name='list'),
    path('<str:workflow_id>', WorkflowDetailView.as_view(), name='detail'),
    path('<str:workflow_id>/execute', WorkflowExecuteView.as_view(), name='execute'),
]
