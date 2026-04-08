"""
Prometheus metrics endpoint for credit system monitoring.

Exposes metrics in Prometheus text format for scraping.
Requires authentication or IP whitelist for production.

Requirements: 23.1
"""

from django.http import HttpResponse
from django.views import View
from prometheus_client import generate_latest, CONTENT_TYPE_LATEST


class MetricsView(View):
    """
    Expose Prometheus metrics endpoint.
    
    Returns metrics in Prometheus text format.
    
    Requirements: 23.1
    
    Security:
    - In production, this endpoint should be protected by:
      - IP whitelist (only allow monitoring servers)
      - Basic authentication
      - Network-level firewall rules
    
    Example nginx config for IP whitelist:
    ```
    location /metrics {
        allow 10.0.0.0/8;  # Internal monitoring network
        deny all;
        proxy_pass http://django;
    }
    ```
    """
    
    def get(self, request):
        """
        Return Prometheus metrics in text format.
        
        Returns:
            HttpResponse with metrics in Prometheus format
        """
        metrics = generate_latest()
        return HttpResponse(
            metrics,
            content_type=CONTENT_TYPE_LATEST
        )
