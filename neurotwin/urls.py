"""
URL configuration for neurotwin project.

Requirements: 13.1, 13.6 - REST conventions and API versioning
"""
from django.contrib import admin
from django.urls import path, include
from drf_spectacular.views import (
    SpectacularAPIView,
    SpectacularSwaggerView,
    SpectacularRedocView,
)
from apps.credits.metrics_views import MetricsView

urlpatterns = [
    path('admin/', admin.site.urls),
    
    # Prometheus metrics endpoint
    # Note: In production, protect this endpoint with IP whitelist or authentication
    path('metrics', MetricsView.as_view(), name='metrics'),
    
    # API Documentation
    path('api/schema/', SpectacularAPIView.as_view(), name='schema'),
    path('docs/', SpectacularSwaggerView.as_view(url_name='schema'), name='swagger-ui'),
    path('redoc/', SpectacularRedocView.as_view(url_name='schema'), name='redoc'),
    
    # API endpoints with versioning
    path('api/', include('core.api.urls', namespace='api')),
]
