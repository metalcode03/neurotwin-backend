"""
Integration health monitoring API views.

Provides health status and metrics for integrations.
Requirements: 23.6
"""

from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework import status
from rest_framework.permissions import IsAuthenticated
from django.shortcuts import get_object_or_404

from apps.automation.models import Integration, Message, MessageStatus
from apps.automation.utils.rate_limiter import RateLimiter
from django.utils import timezone
from datetime import timedelta


class IntegrationHealthView(APIView):
    """
    Get health status and metrics for an integration.
    
    GET /api/v1/integrations/{id}/health/
    
    Requirements: 23.6
    """
    
    permission_classes = [IsAuthenticated]
    
    def get(self, request, integration_id):
        """
        Return integration health metrics.
        
        Includes:
        - health_status (healthy, degraded, disconnected)
        - last_successful_sync_at
        - recent_error_count (last 24 hours)
        - rate_limit_status (current usage and remaining quota)
        """
        # Get integration and verify ownership
        integration = get_object_or_404(
            Integration.objects.select_related('integration_type'),
            id=integration_id,
            user=request.user
        )
        
        # Calculate recent error count (last 24 hours)
        recent_error_count = self._get_recent_error_count(integration)
        
        # Get rate limit status
        rate_limit_status = self._get_rate_limit_status(integration)
        
        # Build response
        health_data = {
            'integration_id': str(integration.id),
            'integration_name': integration.integration_type.name,
            'health_status': integration.health_status,
            'status': integration.status,
            'last_successful_sync_at': integration.last_successful_sync_at,
            'consecutive_failures': integration.consecutive_failures,
            'recent_error_count': recent_error_count,
            'rate_limit_status': rate_limit_status,
            'token_expires_at': integration.token_expires_at,
            'is_token_expired': integration.is_token_expired if hasattr(integration, 'is_token_expired') else False,
        }
        
        return Response(health_data, status=status.HTTP_200_OK)
    
    def _get_recent_error_count(self, integration: Integration) -> int:
        """
        Count failed messages in the last 24 hours.
        
        Args:
            integration: Integration instance
            
        Returns:
            Number of failed messages
        """
        cutoff_time = timezone.now() - timedelta(hours=24)
        
        error_count = Message.objects.filter(
            conversation__integration=integration,
            status=MessageStatus.FAILED,
            created_at__gte=cutoff_time
        ).count()
        
        return error_count
    
    def _get_rate_limit_status(self, integration: Integration) -> dict:
        """
        Get current rate limit status for integration.
        
        Args:
            integration: Integration instance
            
        Returns:
            Dictionary with rate limit metrics
        """
        rate_limiter = RateLimiter()
        
        # Get rate limit config from integration type
        rate_limit_config = integration.integration_type.rate_limit_config or {}
        messages_per_minute = rate_limit_config.get('messages_per_minute', 20)
        
        # Get current status
        rate_status = rate_limiter.get_rate_limit_status(
            integration_id=str(integration.id),
            limit_per_minute=messages_per_minute
        )
        
        return rate_status
