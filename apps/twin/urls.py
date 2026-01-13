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
]
