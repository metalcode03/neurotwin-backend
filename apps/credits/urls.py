"""
URL routing for credit management API endpoints.

Requirements: 13.1
"""

from django.urls import path, include
from rest_framework.routers import DefaultRouter
from apps.credits.views import CreditViewSet

app_name = 'credits'

# Create router and register viewsets
router = DefaultRouter()
router.register(r'', CreditViewSet, basename='credits')

urlpatterns = [
    path('', include(router.urls)),
]
