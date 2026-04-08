"""
URL configuration for monitoring and alerting endpoints.

Requirements: 27.1-27.7
"""
from django.urls import path
from apps.automation.views.task_monitoring import (
    TaskStatisticsView,
    QueueStatusView,
    WorkerStatusView
)
from apps.automation.views.alerts import AlertStatusView

urlpatterns = [
    # Task statistics endpoint
    path(
        'tasks/stats/',
        TaskStatisticsView.as_view(),
        name='task-statistics'
    ),
    
    # Queue status endpoint
    path(
        'queues/status/',
        QueueStatusView.as_view(),
        name='queue-status'
    ),
    
    # Worker status endpoint
    path(
        'workers/status/',
        WorkerStatusView.as_view(),
        name='worker-status'
    ),
    
    # Alert status endpoint
    path(
        'alerts/status/',
        AlertStatusView.as_view(),
        name='alert-status'
    ),
]
