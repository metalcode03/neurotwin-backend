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
from .views.meta_callback import MetaCallbackView, MetaCallbackAPIView
from .views.api_key_complete import APIKeyCompleteView
from .views.twin_suggestion import TwinSuggestionViewSet
from .views.health_check import HealthCheckView
from .views.metrics import MetricsView
from .views.circuit_breaker_status import CircuitBreakerStatusView

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
    # Health check endpoint
    path('health/', HealthCheckView.as_view(), name='health-check'),
    
    # Metrics endpoint
    path('metrics/', MetricsView.as_view(), name='metrics'),
    
    # Circuit breaker status endpoint (admin only)
    path('admin/circuit-breakers/', CircuitBreakerStatusView.as_view(), name='circuit-breaker-status'),
    
    # Monitoring endpoints (admin only)
    path('admin/', include('apps.automation.urls_monitoring')),
    
    # OAuth callback endpoints
    path('oauth/callback/', OAuthCallbackView.as_view(), name='oauth-callback'),
    path('oauth/callback/api/', OAuthCallbackAPIView.as_view(), name='oauth-callback-api'),
    
    # Meta callback endpoints
    path('meta/callback/', MetaCallbackView.as_view(), name='meta-callback'),
    path('meta/callback/api/', MetaCallbackAPIView.as_view(), name='meta-callback-api'),
    
    # API key completion endpoint
    path('api-key/complete/', APIKeyCompleteView.as_view(), name='api-key-complete'),
    
    # Webhook endpoints
    path('webhooks/', include('apps.automation.urls_webhooks')),
    
    # Conversation and message endpoints
    path('', include('apps.automation.urls_conversations')),
    
    # Include router URLs
    path('', include(router.urls)),
]
