"""
User settings API URL configuration.

Requirements: 15.7, 15.8
"""

from django.urls import path
from .views import (
    UserSettingsView,
    UserProfileView,
    UserProfileImageView,
    ChangePasswordView,
)

app_name = 'users'

urlpatterns = [
    path('profile', UserProfileView.as_view(), name='profile'),
    path('profile/image', UserProfileImageView.as_view(), name='profile-image'),
    path('change-password', ChangePasswordView.as_view(), name='change-password'),
    path('settings', UserSettingsView.as_view(), name='settings'),
]
