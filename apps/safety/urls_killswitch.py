"""
Kill Switch API URL configuration.

Requirements: 12.1-12.6, 13.1
"""

from django.urls import path

from .views import (
    KillSwitchStatusView,
    KillSwitchActivateView,
    KillSwitchDeactivateView,
)

app_name = 'killswitch'

urlpatterns = [
    path('', KillSwitchStatusView.as_view(), name='status'),
    path('activate', KillSwitchActivateView.as_view(), name='activate'),
    path('deactivate', KillSwitchDeactivateView.as_view(), name='deactivate'),
]
