"""
Health check API endpoint.

Requirements: 31.1-31.7
"""
from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework import status
from rest_framework.permissions import AllowAny
from apps.automation.services.health_check import HealthCheckService
import logging

logger = logging.getLogger(__name__)


class HealthCheckView(APIView):
    """
    Health check endpoint for monitoring system status.
    
    GET /api/v1/health/
    
    Returns overall health status and component-level health.
    
    Requirements: 31.1-31.7
    """
    permission_classes = [AllowAny]  # Health checks should be accessible without auth
    
    def get(self, request):
        """
        Get system health status.
        
        Returns:
            200: System is healthy
            503: System is degraded or unhealthy
        """
        health_data = HealthCheckService.get_overall_health()
        
        # Return 503 if system is unhealthy
        if health_data["status"] == "unhealthy":
            return Response(health_data, status=status.HTTP_503_SERVICE_UNAVAILABLE)
        
        # Return 200 for healthy or degraded
        return Response(health_data, status=status.HTTP_200_OK)
