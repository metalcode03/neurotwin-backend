"""
CSM API URL configuration.

Includes both CSM profile management and memory endpoints.
Requirements: 4.1-4.7, 5.1-5.6, 13.1
"""

from django.urls import path, include
from .views import (
    CSMProfileView,
    CSMPersonalityProfileView,
    CSMHistoryView,
    CSMVersionDetailView,
    CSMRollbackView,
)

app_name = 'csm'

urlpatterns = [
    # CSM Profile endpoints
    path('profile', CSMPersonalityProfileView.as_view(), name='personality-profile'),
    path('profile/raw', CSMProfileView.as_view(), name='profile-raw'),
    path('history', CSMHistoryView.as_view(), name='history'),
    path('history/<int:version>', CSMVersionDetailView.as_view(), name='version-detail'),
    path('rollback', CSMRollbackView.as_view(), name='rollback'),
    
    # Memory endpoints (nested under CSM)
    path('memories/', include('apps.memory.urls', namespace='memory')),
]
