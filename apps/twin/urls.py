"""
Twin API URL configuration.

Requirements: 2.1-2.6, 13.1
"""

from django.urls import path
from .views import (
    OnboardingStartView,
    OnboardingCompleteView,
    OnboardingProgressView,
    TwinView,
    CognitiveBlendView,
    TwinDeactivateView,
    TwinReactivateView,
    KillSwitchActivateView,
    KillSwitchDeactivateView,
    KillSwitchStatusView,
)

app_name = 'twin'

urlpatterns = [
    # Onboarding
    path('onboarding/start', OnboardingStartView.as_view(), name='onboarding-start'),
    path('onboarding/complete', OnboardingCompleteView.as_view(), name='onboarding-complete'),
    path('onboarding/progress', OnboardingProgressView.as_view(), name='onboarding-progress'),
    
    # Twin management
    path('', TwinView.as_view(), name='twin'),
    path('blend', CognitiveBlendView.as_view(), name='blend'),
    path('deactivate', TwinDeactivateView.as_view(), name='deactivate'),
    path('reactivate', TwinReactivateView.as_view(), name='reactivate'),
    
    # Kill-switch
    path('kill-switch/activate', KillSwitchActivateView.as_view(), name='kill-switch-activate'),
    path('kill-switch/deactivate', KillSwitchDeactivateView.as_view(), name='kill-switch-deactivate'),
    path('kill-switch/status', KillSwitchStatusView.as_view(), name='kill-switch-status'),
]
