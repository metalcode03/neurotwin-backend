"""
Circuit Breaker Status View

Provides monitoring endpoint for circuit breaker states.
Admin-only endpoint for observability.

Requirements: 32.3-32.4
"""

import logging
from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework.permissions import IsAdminUser
from rest_framework import status

from ..utils.circuit_breaker_registry import CircuitBreakerRegistry

logger = logging.getLogger(__name__)


class CircuitBreakerStatusView(APIView):
    """
    Get status of all circuit breakers.
    
    Admin-only endpoint for monitoring circuit breaker states
    and identifying services experiencing failures.
    
    GET /api/v1/admin/circuit-breakers/
    
    Returns:
        {
            "circuit_breakers": {
                "oauth_provider_name": {
                    "name": "OAuth-provider_name",
                    "state": "closed|open|half_open",
                    "failure_count": 0,
                    "success_count": 0,
                    "failure_threshold": 5,
                    "timeout": 60,
                    "last_failure_time": 1234567890.0,
                    "time_until_retry": 0
                },
                ...
            }
        }
    
    Requirements: 32.3-32.4
    """
    
    permission_classes = [IsAdminUser]
    
    def get(self, request):
        """Get status of all circuit breakers"""
        try:
            breaker_status = CircuitBreakerRegistry.get_breaker_status()
            
            logger.info(
                f"Circuit breaker status requested by admin user {request.user.id}"
            )
            
            return Response({
                'circuit_breakers': breaker_status
            }, status=status.HTTP_200_OK)
            
        except Exception as e:
            logger.error(f"Failed to get circuit breaker status: {str(e)}")
            return Response({
                'error': 'Failed to retrieve circuit breaker status'
            }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)
    
    def post(self, request):
        """Reset all circuit breakers (admin action)"""
        try:
            CircuitBreakerRegistry.reset_all()
            
            logger.warning(
                f"All circuit breakers reset by admin user {request.user.id}"
            )
            
            return Response({
                'message': 'All circuit breakers have been reset to CLOSED state'
            }, status=status.HTTP_200_OK)
            
        except Exception as e:
            logger.error(f"Failed to reset circuit breakers: {str(e)}")
            return Response({
                'error': 'Failed to reset circuit breakers'
            }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)
