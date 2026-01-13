"""
Permissions API URL configuration.

Requirements: 10.1-10.7, 13.1
"""

from django.urls import path

from .views import PermissionListView, PermissionDetailView

app_name = 'permissions'

urlpatterns = [
    path('', PermissionListView.as_view(), name='list'),
    path('<str:integration>/<str:action_type>', PermissionDetailView.as_view(), name='detail'),
]
