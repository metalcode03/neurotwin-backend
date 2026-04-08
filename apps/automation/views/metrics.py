"""
Prometheus metrics endpoint.

Requirements: 30.6
"""
from django.http import HttpResponse
from django.views import View
from prometheus_client import generate_latest, CONTENT_TYPE_LATEST


class MetricsView(View):
    """
    Prometheus metrics endpoint.
    
    GET /api/v1/metrics/
    
    Returns Prometheus-formatted metrics.
    
    Requirements: 30.6
    """
    
    def get(self, request):
        """
        Return Prometheus metrics.
        
        Returns:
            Prometheus-formatted metrics
        """
        metrics = generate_latest()
        return HttpResponse(
            metrics,
            content_type=CONTENT_TYPE_LATEST
        )
