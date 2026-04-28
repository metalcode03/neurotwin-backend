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
import uuid
from django.conf import settings
from django.utils import timezone
from apps.subscription.models import Subscription, SubscriptionTier, SubscriptionHistory
from apps.credits.models import UserCredits, CreditTopUp
from apps.credits.payment_service import FlutterwaveService
from apps.credits.serializers import (
    CreditBalanceSerializer,
    CreditEstimateRequestSerializer,
    CreditEstimateSerializer,
    CreditUsageHistoryRequestSerializer,
    CreditUsageHistorySerializer,
    CreditUsageLogSerializer,
    CreditUsageSummaryRequestSerializer,
    CreditUsageSummarySerializer,
    PaymentInitiateSerializer,
    PaymentVerifySerializer,
    PaymentResponseSerializer,
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

    @action(detail=False, methods=['post'], url_path='payment/initiate')
    def initiate_payment(self, request):
        """Initiate payment for subscription tier upgrade."""
        serializer = PaymentInitiateSerializer(data=request.data)
        if not serializer.is_valid():
            logger.error(f"Payment initiation validation failed: {serializer.errors}")
            return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)
            
        tier = serializer.validated_data.get('tier')
        if not tier:
            return Response({'error': 'tier is required for upgrade'}, status=status.HTTP_400_BAD_REQUEST)
            
        tier_info = settings.SUBSCRIPTION_PRICING.get(tier)
        if not tier_info:
            return Response({'error': 'Invalid tier'}, status=status.HTTP_400_BAD_REQUEST)
        
        if not settings.FLUTTERWAVE_PUBLIC_KEY:
            logger.error("FLUTTERWAVE_PUBLIC_KEY not configured")
            return Response({'error': 'Payment gateway not configured'}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)
            
        tx_ref = f"tx-upg-{uuid.uuid4().hex}"
        amount = tier_info['price']
        
        response_data = {
            'tx_ref': tx_ref,
            'amount': amount,
            'currency': 'USD',
            'public_key': settings.FLUTTERWAVE_PUBLIC_KEY,
            'customer_email': request.user.email,
            'customer_name': request.user.display_name or request.user.email,
        }
        
        logger.info(f"Payment initiated for user {request.user.id}, tier {tier}, tx_ref {tx_ref}")
        return Response(response_data, status=status.HTTP_200_OK)

    @action(detail=False, methods=['post'], url_path='payment/verify-upgrade')
    def verify_upgrade_payment(self, request):
        """Verify payment and apply tier upgrade."""
        serializer = PaymentVerifySerializer(data=request.data)
        if not serializer.is_valid():
            logger.error(f"Payment verification validation failed: {serializer.errors}")
            return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)
            
        transaction_id = serializer.validated_data['transaction_id']
        tier = serializer.validated_data.get('tier')
        
        if not tier:
            return Response({'error': 'tier is required'}, status=status.HTTP_400_BAD_REQUEST)
        
        try:
            logger.info(f"Verifying payment for user {request.user.id}, transaction {transaction_id}")
            payment_data = FlutterwaveService.verify_transaction(transaction_id)
            
            tier_info = settings.SUBSCRIPTION_PRICING.get(tier)
            if not tier_info:
                return Response({'error': 'Invalid tier'}, status=status.HTTP_400_BAD_REQUEST)
            
            # Check payment amount
            paid_amount = float(payment_data.get('amount', 0))
            required_amount = float(tier_info['price'])
            
            logger.info(f"Payment verification: paid={paid_amount}, required={required_amount}")
            
            if paid_amount < required_amount:
                logger.error(f"Insufficient payment: {paid_amount} < {required_amount}")
                return Response({'error': 'Insufficient payment amount'}, status=status.HTTP_400_BAD_REQUEST)
            
            # Check payment status
            payment_status = payment_data.get('status')
            if payment_status != 'successful':
                logger.error(f"Payment not successful: {payment_status}")
                return Response({'error': f'Payment status: {payment_status}'}, status=status.HTTP_400_BAD_REQUEST)
                
            # Update Subscription
            sub, _ = Subscription.objects.get_or_create(user=request.user)
            old_tier = sub.tier
            sub.previous_tier = old_tier
            sub.tier_changed_at = timezone.now()
            sub.tier = tier
            sub.save()
            
            logger.info(f"Subscription updated: {old_tier} -> {tier}")
            
            # Log History
            SubscriptionHistory.objects.create(
                subscription=sub,
                from_tier=old_tier,
                to_tier=tier,
                reason='upgrade'
            )
            
            # Update Credits
            creds, _ = UserCredits.objects.get_or_create(user=request.user, defaults={
                'monthly_credits': 50,
                'remaining_credits': 50,
                'last_reset_date': timezone.now().date()
            })
            creds.monthly_credits = tier_info['credits']
            creds.remaining_credits = tier_info['credits']
            creds.save()
            
            logger.info(f"Credits updated: {tier_info['credits']}")
            
            return Response({
                'status': 'success',
                'tier': tier,
                'remaining_credits': creds.remaining_credits
            }, status=status.HTTP_200_OK)
            
        except PaymentVerificationError as e:
            logger.error(f"Payment verification error: {str(e)}")
            return Response({'error': str(e)}, status=status.HTTP_400_BAD_REQUEST)
        except Exception as e:
            logger.exception("Unexpected error during payment verification")
            return Response({'error': 'Internal server error'}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)

    @action(detail=False, methods=['post'], url_path='payment/initiate-topup')
    def initiate_topup(self, request):
        """Initiate payment for credit top-up."""
        serializer = PaymentInitiateSerializer(data=request.data)
        if not serializer.is_valid():
            return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)
            
        sub = request.user.subscription
        if not sub or sub.tier == SubscriptionTier.FREE:
            return Response({'error': 'Must be on a paid tier to purchase top-up credits.'}, status=status.HTTP_400_BAD_REQUEST)
            
        package = serializer.validated_data.get('topup_package')
        if not package:
            return Response({'error': 'topup_package is required'}, status=status.HTTP_400_BAD_REQUEST)
            
        package_info = settings.TOPUP_PACKAGES.get(package)
        if not package_info:
            return Response({'error': 'Invalid topup package'}, status=status.HTTP_400_BAD_REQUEST)
            
        tx_ref = f"tx-top-{uuid.uuid4().hex}"
        
        CreditTopUp.objects.create(
            user=request.user,
            amount=package_info['credits'],
            price_paid=package_info['price'],
            payment_method='flutterwave',
            transaction_id=tx_ref,
            status='pending'
        )
        
        response_data = {
            'tx_ref': tx_ref,
            'amount': package_info['price'],
            'currency': 'USD',
            'public_key': settings.FLUTTERWAVE_PUBLIC_KEY,
            'customer_email': request.user.email,
            'customer_name': request.user.display_name or request.user.email,
        }
        return Response(PaymentResponseSerializer(response_data).data)

    @action(detail=False, methods=['post'], url_path='payment/verify-topup')
    def verify_topup_payment(self, request):
        """Verify credit top-up payment."""
        serializer = PaymentVerifySerializer(data=request.data)
        if not serializer.is_valid():
            return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)
            
        transaction_id = serializer.validated_data['transaction_id']
        # The internal db tx_ref can be extracted via FlutterwaveService... wait we might not need tx_ref here if verified returns it, or we rely on the amount.
        
        try:
            payment_data = FlutterwaveService.verify_transaction(transaction_id)
            tx_ref = payment_data.get('tx_ref')
            
            topup = CreditTopUp.objects.filter(transaction_id=tx_ref, status='pending').first()
            if not topup:
                return Response({'error': 'Pending topup not found'}, status=status.HTTP_400_BAD_REQUEST)
                
            if payment_data['amount'] < float(topup.price_paid):
                 return Response({'error': 'Insufficient payment amount'}, status=status.HTTP_400_BAD_REQUEST)
                 
            topup.status = 'completed'
            topup.save()
            
            creds = request.user.credits
            creds.purchased_credits += topup.amount
            creds.remaining_credits += topup.amount
            creds.save()
            
            return Response({'status': 'success', 'remaining_credits': creds.remaining_credits})
        except Exception as e:
            logger.exception("Top-up verification failed")
            return Response({'error': str(e)}, status=status.HTTP_400_BAD_REQUEST)

