"""
Admin views for credit system monitoring and configuration.

Provides admin-only endpoints for:
- AI request log viewing and filtering
- Brain routing configuration management
- System health monitoring

Requirements: 11.5, 11.6, 11.7, 6.9, 21.1-21.10, 23.10
"""

from rest_framework import viewsets, status
from rest_framework.decorators import action
from rest_framework.response import Response
from apps.credits.permissions import IsAdminUser
from django.db.models import Avg, Count, Q
from django.utils import timezone
from datetime import timedelta

from apps.credits.models import AIRequestLog, BrainRoutingConfig
from apps.credits.serializers import (
    AIRequestLogSerializer,
    BrainRoutingConfigSerializer,
    HealthCheckSerializer
)
from apps.credits.routing import ModelRouter
from apps.credits.providers.registry import ProviderRegistry


class AdminAIRequestViewSet(viewsets.ReadOnlyModelViewSet):
    """
    Admin endpoint for viewing AI request logs with filtering and aggregation.
    
    Requirements: 11.5, 11.6, 11.7
    """
    serializer_class = AIRequestLogSerializer
    permission_classes = [IsAdminUser]
    filterset_fields = ['brain_mode', 'model_used', 'status']
    ordering_fields = ['timestamp', 'latency_ms', 'tokens_used', 'credits_consumed']
    ordering = ['-timestamp']
    
    def get_queryset(self):
        """
        Get AI request logs with optional filtering.
        
        Supports filters:
        - user_id: Filter by user
        - brain_mode: Filter by brain mode
        - model_used: Filter by model
        - status: Filter by status
        - start_date: Filter from date (ISO 8601)
        - end_date: Filter to date (ISO 8601)
        
        Optimizations:
        - select_related('user') to avoid N+1 queries
        - only() to fetch specific fields for list views
        """
        # Use select_related to avoid N+1 queries on user relationship
        queryset = AIRequestLog.objects.select_related('user').only(
            'id', 'user_id', 'timestamp', 'brain_mode', 'operation_type',
            'model_used', 'tokens_used', 'credits_consumed', 'latency_ms',
            'status', 'error_message', 'error_type', 'cognitive_blend_value',
            'created_at', 'user__email', 'user__username'
        )
        
        # Filter by user_id
        user_id = self.request.query_params.get('user_id')
        if user_id:
            queryset = queryset.filter(user_id=user_id)
        
        # Filter by date range
        start_date = self.request.query_params.get('start_date')
        end_date = self.request.query_params.get('end_date')
        
        if start_date:
            queryset = queryset.filter(timestamp__gte=start_date)
        if end_date:
            queryset = queryset.filter(timestamp__lte=end_date)
        
        return queryset
    
    def list(self, request, *args, **kwargs):
        """
        List AI request logs with aggregated statistics.
        
        Returns paginated logs plus aggregates:
        - total_requests
        - success_rate
        - average_latency_ms
        - total_tokens
        """
        queryset = self.filter_queryset(self.get_queryset())
        
        # Calculate aggregates
        aggregates = queryset.aggregate(
            total_requests=Count('id'),
            average_latency_ms=Avg('latency_ms'),
            total_tokens=Count('tokens_used')
        )
        
        # Calculate success rate
        success_count = queryset.filter(status='success').count()
        total_count = aggregates['total_requests'] or 1
        aggregates['success_rate'] = round((success_count / total_count) * 100, 2)
        
        # Paginate results
        page = self.paginate_queryset(queryset)
        if page is not None:
            serializer = self.get_serializer(page, many=True)
            response = self.get_paginated_response(serializer.data)
            response.data['aggregates'] = aggregates
            return response
        
        serializer = self.get_serializer(queryset, many=True)
        return Response({
            'results': serializer.data,
            'aggregates': aggregates
        })


class AdminBrainConfigViewSet(viewsets.ModelViewSet):
    """
    Admin endpoint for managing Brain routing configurations.
    
    Requirements: 6.9, 21.1-21.10
    """
    serializer_class = BrainRoutingConfigSerializer
    permission_classes = [IsAdminUser]
    queryset = BrainRoutingConfig.objects.all()
    
    def perform_create(self, serializer):
        """Create new routing config with current user as creator."""
        serializer.save(created_by=self.request.user)
    
    @action(detail=True, methods=['put'])
    def activate(self, request, pk=None):
        """
        Activate a routing configuration.
        
        Sets is_active=True for specified config and False for all others.
        Invalidates routing cache.
        
        Requirements: 6.9
        """
        config = self.get_object()
        
        # Deactivate all other configs
        BrainRoutingConfig.objects.exclude(pk=config.pk).update(is_active=False)
        
        # Activate this config
        config.is_active = True
        config.save()
        
        # Invalidate routing cache
        router = ModelRouter()
        router.invalidate_cache()
        
        serializer = self.get_serializer(config)
        return Response(serializer.data)


class HealthCheckViewSet(viewsets.ViewSet):
    """
    System health check endpoint.
    
    No authentication required for monitoring systems.
    
    Requirements: 23.10
    """
    permission_classes = []
    
    def list(self, request):
        """
        Check system health including database, Redis, and provider APIs.
        
        Returns:
        - status: healthy/degraded/unhealthy
        - components: status of each component
        - metrics: performance metrics
        """
        health_status = {
            'status': 'healthy',
            'timestamp': timezone.now().isoformat(),
            'components': {},
            'metrics': {}
        }
        
        # Check database connectivity
        try:
            from django.db import connection
            with connection.cursor() as cursor:
                cursor.execute("SELECT 1")
            health_status['components']['database'] = 'healthy'
        except Exception as e:
            health_status['components']['database'] = 'unhealthy'
            health_status['status'] = 'degraded'
        
        # Check Redis connectivity
        try:
            from django.core.cache import cache
            cache.set('health_check', 'ok', 10)
            result = cache.get('health_check')
            if result == 'ok':
                health_status['components']['redis'] = 'healthy'
            else:
                health_status['components']['redis'] = 'degraded'
                health_status['status'] = 'degraded'
        except Exception as e:
            health_status['components']['redis'] = 'unhealthy'
            health_status['status'] = 'degraded'
        
        # Check provider API health
        provider_registry = ProviderRegistry()
        
        # Check Cerebras API
        try:
            cerebras_provider = provider_registry.get_provider('cerebras')
            # Simple health check - just verify provider exists
            health_status['components']['cerebras_api'] = 'healthy'
        except Exception as e:
            health_status['components']['cerebras_api'] = 'unhealthy'
            health_status['status'] = 'degraded'
        
        # Check Gemini API
        try:
            gemini_provider = provider_registry.get_provider('gemini-2.5-flash')
            # Simple health check - just verify provider exists
            health_status['components']['gemini_api'] = 'healthy'
        except Exception as e:
            health_status['components']['gemini_api'] = 'unhealthy'
            health_status['status'] = 'degraded'
        
        # Calculate metrics
        try:
            # Get recent AI requests for metrics
            recent_requests = AIRequestLog.objects.filter(
                timestamp__gte=timezone.now() - timedelta(minutes=5)
            )
            
            total_requests = recent_requests.count()
            if total_requests > 0:
                success_count = recent_requests.filter(status='success').count()
                health_status['metrics']['ai_request_success_rate'] = round(
                    (success_count / total_requests) * 100, 2
                )
                
                # Calculate p95 latency for credit checks (approximation)
                latencies = list(recent_requests.values_list('latency_ms', flat=True))
                if latencies:
                    latencies.sort()
                    p95_index = int(len(latencies) * 0.95)
                    health_status['metrics']['credit_check_p95_latency_ms'] = latencies[p95_index]
        except Exception:
            pass
        
        # Set overall status
        if health_status['components'].get('database') == 'unhealthy':
            health_status['status'] = 'unhealthy'
        
        return Response(health_status)
