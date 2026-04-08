"""
API views for credit management endpoints.

Requirements: 1.10, 4.5, 10.3-10.8, 13.1, 13.2
"""

import logging
from rest_framework import viewsets, status
from rest_framework.decorators import action
from rest_framework.response import Response
from rest_framework.permissions import IsAuthenticated
from rest_framework.pagination import PageNumberPagination

from apps.credits.services import CreditManager
from apps.credits.throttling import CreditRateThrottle
from apps.credits.serializers import (
    CreditBalanceSerializer,
    CreditEstimateRequestSerializer,
    CreditEstimateSerializer,
    CreditUsageHistoryRequestSerializer,
    CreditUsageHistorySerializer,
    CreditUsageLogSerializer,
    CreditUsageSummaryRequestSerializer,
    CreditUsageSummarySerializer,
)


logger = logging.getLogger(__name__)


class CreditPagination(PageNumberPagination):
    """Custom pagination for credit usage history."""
    page_size = 20
    page_size_query_param = 'page_size'
    max_page_size = 100


class CreditViewSet(viewsets.ViewSet):
    """
    ViewSet for credit management operations.
    
    Requirements: 1.10, 4.5, 10.3-10.8, 13.1, 13.2
    """
    permission_classes = [IsAuthenticated]
    throttle_classes = [CreditRateThrottle]
    
    @action(detail=False, methods=['get'], url_path='balance')
    def balance(self, request):
        """
        Get user's current credit balance.
        
        Requirements: 1.10, 4.5
        
        Returns:
            - monthly_credits: Monthly allocation
            - remaining_credits: Current available credits
            - used_credits: Credits consumed this period
            - purchased_credits: Additional purchased credits
            - last_reset_date: Last reset date
            - next_reset_date: Next reset date
            - days_until_reset: Days until next reset
            - usage_percentage: Percentage of credits used
        """
        try:
            balance_data = CreditManager.get_balance(request.user.id)
            serializer = CreditBalanceSerializer(balance_data)
            
            logger.info(f"Retrieved credit balance for user {request.user.id}")
            return Response(serializer.data, status=status.HTTP_200_OK)
            
        except ValueError as e:
            logger.error(f"Error retrieving balance for user {request.user.id}: {str(e)}")
            return Response(
                {'error': 'Credit balance not found'},
                status=status.HTTP_404_NOT_FOUND
            )
        except Exception as e:
            logger.exception(f"Unexpected error retrieving balance for user {request.user.id}")
            return Response(
                {'error': 'Internal server error'},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )
    
    @action(detail=False, methods=['get'], url_path='estimate')
    def estimate(self, request):
        """
        Estimate credit cost for a request.
        
        Requirements: 4.5
        
        Query Parameters:
            - operation_type (required): Type of operation
            - brain_mode (required): Brain intelligence level
            - estimated_tokens (optional): Estimated token count (default 500)
        
        Returns:
            - estimated_cost: Estimated credit cost
            - operation_type: Type of operation
            - brain_mode: Brain mode
            - estimated_tokens: Token count used
            - sufficient_credits: Whether user has enough credits
            - remaining_credits: User's remaining balance
        """
        # Validate request parameters
        request_serializer = CreditEstimateRequestSerializer(data=request.query_params)
        if not request_serializer.is_valid():
            return Response(
                request_serializer.errors,
                status=status.HTTP_400_BAD_REQUEST
            )
        
        validated_data = request_serializer.validated_data
        operation_type = validated_data['operation_type']
        brain_mode = validated_data['brain_mode']
        estimated_tokens = validated_data.get('estimated_tokens', 500)
        
        try:
            # Calculate estimated cost
            estimated_cost = CreditManager.estimate_cost(
                operation_type=operation_type,
                brain_mode=brain_mode,
                estimated_tokens=estimated_tokens
            )
            
            # Check if user has sufficient credits
            sufficient_credits = CreditManager.check_sufficient_credits(
                user_id=request.user.id,
                estimated_cost=estimated_cost
            )
            
            # Get remaining credits
            balance_data = CreditManager.get_balance(request.user.id)
            remaining_credits = balance_data['remaining_credits']
            
            response_data = {
                'estimated_cost': estimated_cost,
                'operation_type': operation_type,
                'brain_mode': brain_mode,
                'estimated_tokens': estimated_tokens,
                'sufficient_credits': sufficient_credits,
                'remaining_credits': remaining_credits,
            }
            
            serializer = CreditEstimateSerializer(response_data)
            
            logger.info(
                f"Estimated cost for user {request.user.id}: "
                f"{estimated_cost} credits (operation={operation_type}, brain={brain_mode})"
            )
            
            return Response(serializer.data, status=status.HTTP_200_OK)
            
        except Exception as e:
            logger.exception(f"Error estimating cost for user {request.user.id}")
            return Response(
                {'error': 'Internal server error'},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )
    
    @action(detail=False, methods=['get'], url_path='usage')
    def usage(self, request):
        """
        Get paginated credit usage history with filtering.
        
        Requirements: 10.3, 10.4, 10.5, 10.6
        
        Query Parameters:
            - page (optional): Page number (default 1)
            - page_size (optional): Records per page (default 20, max 100)
            - start_date (optional): Filter from date (ISO 8601)
            - end_date (optional): Filter to date (ISO 8601)
            - operation_type (optional): Filter by operation type
            - brain_mode (optional): Filter by brain mode
        
        Returns:
            - count: Total number of records
            - next: URL to next page
            - previous: URL to previous page
            - results: List of usage log records
            - summary: Summary statistics (total_consumed, average_per_request, count)
        """
        # Validate request parameters
        request_serializer = CreditUsageHistoryRequestSerializer(data=request.query_params)
        if not request_serializer.is_valid():
            return Response(
                request_serializer.errors,
                status=status.HTTP_400_BAD_REQUEST
            )
        
        validated_data = request_serializer.validated_data
        page = validated_data.get('page', 1)
        page_size = validated_data.get('page_size', 20)
        
        # Build filters dict
        filters = {}
        if 'start_date' in validated_data:
            filters['start_date'] = validated_data['start_date'].isoformat()
        if 'end_date' in validated_data:
            filters['end_date'] = validated_data['end_date'].isoformat()
        if 'operation_type' in validated_data:
            filters['operation_type'] = validated_data['operation_type']
        if 'brain_mode' in validated_data:
            filters['brain_mode'] = validated_data['brain_mode']
        
        try:
            # Get usage history from service
            usage_logs, summary_stats = CreditManager.get_usage_history(
                user_id=request.user.id,
                filters=filters,
                page=page,
                page_size=page_size
            )
            
            # Serialize usage logs
            logs_serializer = CreditUsageLogSerializer(usage_logs, many=True)
            
            # Build pagination URLs
            base_url = request.build_absolute_uri(request.path)
            query_params = request.query_params.copy()
            
            next_url = None
            if len(usage_logs) == page_size:
                query_params['page'] = page + 1
                next_url = f"{base_url}?{query_params.urlencode()}"
            
            previous_url = None
            if page > 1:
                query_params['page'] = page - 1
                previous_url = f"{base_url}?{query_params.urlencode()}"
            
            response_data = {
                'count': summary_stats['count'],
                'next': next_url,
                'previous': previous_url,
                'results': logs_serializer.data,
                'summary': {
                    'total_credits_consumed': summary_stats['total_consumed'],
                    'average_per_request': summary_stats['average_per_request'],
                    'date_range': {
                        'start': filters.get('start_date'),
                        'end': filters.get('end_date'),
                    }
                }
            }
            
            logger.info(
                f"Retrieved {len(usage_logs)} usage logs for user {request.user.id} "
                f"(page {page})"
            )
            
            return Response(response_data, status=status.HTTP_200_OK)
            
        except Exception as e:
            logger.exception(f"Error retrieving usage history for user {request.user.id}")
            return Response(
                {'error': 'Internal server error'},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )
    
    @action(detail=False, methods=['get'], url_path='usage/summary')
    def usage_summary(self, request):
        """
        Get aggregated usage summary for specified period.
        
        Requirements: 10.7, 10.8
        
        Query Parameters:
            - days (optional): Number of days to include (default 30, max 365)
        
        Returns:
            - period: start_date, end_date, days
            - total_credits_consumed: Total credits in period
            - daily_breakdown: List of {date, credits, requests}
            - by_operation_type: Dict of operation_type -> credits
            - by_brain_mode: Dict of brain_mode -> credits
        """
        # Validate request parameters
        request_serializer = CreditUsageSummaryRequestSerializer(data=request.query_params)
        if not request_serializer.is_valid():
            return Response(
                request_serializer.errors,
                status=status.HTTP_400_BAD_REQUEST
            )
        
        validated_data = request_serializer.validated_data
        days = validated_data.get('days', 30)
        
        try:
            # Get usage summary from service
            summary_data = CreditManager.get_usage_summary(
                user_id=request.user.id,
                days=days
            )
            
            serializer = CreditUsageSummarySerializer(summary_data)
            
            logger.info(
                f"Retrieved usage summary for user {request.user.id} "
                f"({days} days, {summary_data['total_credits_consumed']} credits)"
            )
            
            return Response(serializer.data, status=status.HTTP_200_OK)
            
        except Exception as e:
            logger.exception(f"Error retrieving usage summary for user {request.user.id}")
            return Response(
                {'error': 'Internal server error'},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )
