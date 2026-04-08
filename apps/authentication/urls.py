"""
Authentication API URL configuration.

Requirements: 1.1-1.7, 13.1
"""

from django.urls import path
from .views import (
    RegisterView,
    VerifyEmailView,
    LoginView,
    RefreshTokenView,
    PasswordResetRequestView,
    PasswordResetView,
    OAuthView,
    OAuthCallbackView,
    LogoutView,
    LogoutAllView,
    CurrentUserView,
    UserSettingsView,
)

app_name = 'auth'

urlpatterns = [
    # Registration and verification
    path('register', RegisterView.as_view(), name='register'),
    path('verify', VerifyEmailView.as_view(), name='verify'),
    
    # Login and token management
    path('login', LoginView.as_view(), name='login'),
    path('refresh', RefreshTokenView.as_view(), name='refresh'),
    path('logout', LogoutView.as_view(), name='logout'),
    path('logout-all', LogoutAllView.as_view(), name='logout-all'),
    
    # Current user
    path('me', CurrentUserView.as_view(), name='current-user'),
    
    # Password reset
    path('password-reset', PasswordResetRequestView.as_view(), name='password-reset'),
    path('password-reset/confirm', PasswordResetView.as_view(), name='password-reset-confirm'),
    
    # OAuth
    path('oauth/<str:provider>', OAuthView.as_view(), name='oauth'),
    path('oauth/<str:provider>/callback', OAuthCallbackView.as_view(), name='oauth-callback'),
]
