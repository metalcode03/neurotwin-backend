"""
Admin URL routing for credit system monitoring and configuration.

Requirements: 13.1, 11.5
"""

from django.urls import path, include
from rest_framework.routers import DefaultRouter

from apps.credits.admin_views import (
    AdminAIRequestViewSet,
    AdminBrainConfigViewSet,
    HealthCheckViewSet
)

app_name = 'credits_admin'

# Create router for admin viewsets
router = DefaultRouter()
router.register(r'ai-requests', AdminAIRequestViewSet, basename='ai-requests')
router.register(r'brain-config', AdminBrainConfigViewSet, basename='brain-config')
router.register(r'health', HealthCheckViewSet, basename='health')

urlpatterns = router.urls
