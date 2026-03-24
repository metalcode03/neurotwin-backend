"""
URL configuration for automation app.

Registers all viewsets with DRF router and configures nested routes.
Requirements: 10.1-10.11
"""

from django.urls import path, include
from rest_framework.routers import DefaultRouter

from .views import (
    IntegrationTypeViewSet,
    InstallationViewSet,
    WorkflowViewSet,
)
from .views.oauth_callback import OAuthCallbackView, OAuthCallbackAPIView
from .views.twin_suggestion import TwinSuggestionViewSet

app_name = 'automation'

# Create router
router = DefaultRouter()

# Register viewsets
router.register(
    r'integrations/types',
    IntegrationTypeViewSet,
    basename='integration-type'
)

router.register(
    r'integrations',
    InstallationViewSet,
    basename='installation'
)

router.register(
    r'automations',
    WorkflowViewSet,
    basename='workflow'
)

router.register(
    r'twin-suggestions',
    TwinSuggestionViewSet,
    basename='twin-suggestion'
)

# URL patterns
urlpatterns = [
    # OAuth callback endpoints
    path('oauth/callback/', OAuthCallbackView.as_view(), name='oauth-callback'),
    path('oauth/callback/api/', OAuthCallbackAPIView.as_view(), name='oauth-callback-api'),
    
    # Include router URLs
    path('', include(router.urls)),
]
