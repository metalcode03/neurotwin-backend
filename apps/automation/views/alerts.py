"""
Alerting API endpoints.

Requirements: 27.1-27.7
"""
from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework import status
from rest_framework.permissions import IsAdminUser
from drf_spectacular.utils import extend_schema

from apps.automation.services.alerting import AlertingService


class AlertStatusView(APIView):
    """
    Get current alert status for all monitoring rules.
    
    Requirements: 27.1-27.7
    """
    permission_classes = [IsAdminUser]
    
    @extend_schema(
        summary="Get alert status",
        description="Returns current status of all configured alert rules",
        responses={
            200: {
                'description': 'Alert status',
                'content': {
                    'application/json': {
                        'example': {
                            'alerts': [
                                {
                                    'name': 'rate_limit_violations',
                                    'triggered': True,
                                    'current_value': 150,
                                    'threshold': 100,
                                    'severity': 'warning',
                                    'description': 'Alert when rate limit violations exceed 100 per hour'
                                }
                            ],
                            'triggered_count': 1,
                            'total_rules': 6
                        }
                    }
                }
            }
        }
    )
    def get(self, request):
        """Get alert status"""
        alerting_service = AlertingService()
        alert_status = alerting_service.check_all_alerts()
        
        return Response(alert_status, status=status.HTTP_200_OK)
