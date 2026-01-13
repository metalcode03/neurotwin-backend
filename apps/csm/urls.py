"""
CSM API URL configuration.

Requirements: 4.1-4.7, 13.1
"""

from django.urls import path
from .views import (
    CSMProfileView,
    CSMHistoryView,
    CSMVersionDetailView,
    CSMRollbackView,
)

app_name = 'csm'

urlpatterns = [
    path('profile', CSMProfileView.as_view(), name='profile'),
    path('history', CSMHistoryView.as_view(), name='history'),
    path('history/<int:version>', CSMVersionDetailView.as_view(), name='version-detail'),
    path('rollback', CSMRollbackView.as_view(), name='rollback'),
]
