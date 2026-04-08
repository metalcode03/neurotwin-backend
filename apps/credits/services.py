"""
Credit management service for NeuroTwin platform.

Handles credit balance operations, cost calculations, monthly resets,
and usage tracking with Redis caching for performance.

Requirements: 1.1, 1.10, 2.1-2.5, 3.1-3.11, 4.1, 4.2, 4.4, 9.8, 10.1-10.8, 20.1, 20.3, 20.4
"""

import logging
import time
from datetime import date, datetime, timedelta
from typing import Dict, List, Optional, Tuple
from decimal import Decimal

from django.core.cache import cache
from django.db import transaction
from django.db.models import Sum, Avg, Count, Q
from django.utils import timezone

from apps.credits.models import UserCredits, CreditUsageLog
from apps.credits.constants import (
    BASE_COSTS,
    BRAIN_MULTIPLIERS,
    CREDIT_BALANCE_CACHE_TTL,
)
from apps.credits.exceptions import InsufficientCreditsError
from apps.credits.metrics import (
    credit_checks_total,
    credit_deductions_total,
    credit_resets_total,
    credit_check_latency_seconds,
    credit_deduction_latency_seconds,
)


logger = logging.getLogger(__name__)


class CreditManager:
    """
    Manages credit balance operations, cost calculations, and usage tracking.
    
    Requirements: 1.1, 1.10, 2.1-2.5, 3.1-3.11, 4.1, 4.2, 4.4, 9.8, 10.1-10.8, 20.1, 20.3, 20.4
    """
    
    @staticmethod
    def _get_cache_key(user_id: int) -> str:
        """Generate cache key for user credit balance."""
        return f"credit_balance:{user_id}"
    
    @staticmethod
    def get_balance(user_id: int) -> Dict:
        """
        Retrieve user's credit balance with Redis caching.
        
        Requirements: 1.1, 1.10, 20.1
        
        Cache strategy:
        - Cache key: credit_balance:{user_id}
        - TTL: 60 seconds
        - Fallback to database on cache miss
        - Populate cache after database read
        
        Args:
            user_id: ID of the user
            
        Returns:
            Dict with balance information:
            - monthly_credits: Monthly allocation
            - remaining_credits: Current available credits
            - used_credits: Credits consumed this period
            - purchased_credits: Additional purchased credits
            - last_reset_date: Last reset date
            - next_reset_date: Next reset date
            - days_until_reset: Days until next reset
            - usage_percentage: Percentage of credits used
        """
        start_time = time.time()
        cache_key = CreditManager._get_cache_key(user_id)
        
        # Try to get from cache
        cached_balance = cache.get(cache_key)
        if cached_balance is not None:
            latency = time.time() - start_time
            credit_check_latency_seconds.labels(cache_hit='true').observe(latency)
            credit_checks_total.labels(user_tier='unknown', result='success').inc()
            logger.debug(f"Cache hit for user {user_id} credit balance")
            return cached_balance
        
        # Cache miss - fetch from database
        logger.debug(f"Cache miss for user {user_id} credit balance")
        try:
            user_credits = UserCredits.objects.select_related('user').get(user_id=user_id)
            user_tier = getattr(user_credits.user, 'subscription_tier', 'unknown')
        except UserCredits.DoesNotExist:
            latency = time.time() - start_time
            credit_check_latency_seconds.labels(cache_hit='false').observe(latency)
            credit_checks_total.labels(user_tier='unknown', result='not_found').inc()
            logger.error(f"UserCredits not found for user {user_id}")
            raise ValueError(f"UserCredits not found for user {user_id}")
        
        # Calculate next reset date (first day of next month)
        last_reset = user_credits.last_reset_date
        if last_reset.month == 12:
            next_reset = date(last_reset.year + 1, 1, 1)
        else:
            next_reset = date(last_reset.year, last_reset.month + 1, 1)
        
        # Calculate days until reset
        days_until_reset = (next_reset - date.today()).days
        
        # Calculate usage percentage
        total_credits = user_credits.monthly_credits + user_credits.purchased_credits
        usage_percentage = (
            (user_credits.used_credits / total_credits * 100)
            if total_credits > 0 else 0
        )
        
        balance_data = {
            'monthly_credits': user_credits.monthly_credits,
            'remaining_credits': user_credits.remaining_credits,
            'used_credits': user_credits.used_credits,
            'purchased_credits': user_credits.purchased_credits,
            'last_reset_date': last_reset.isoformat(),
            'next_reset_date': next_reset.isoformat(),
            'days_until_reset': max(0, days_until_reset),
            'usage_percentage': round(usage_percentage, 2),
        }
        
        # Store in cache
        cache.set(cache_key, balance_data, CREDIT_BALANCE_CACHE_TTL)
        logger.debug(f"Cached balance for user {user_id}")
        
        latency = time.time() - start_time
        credit_check_latency_seconds.labels(cache_hit='false').observe(latency)
        credit_checks_total.labels(user_tier=user_tier, result='success').inc()
        
        return balance_data
    
    @staticmethod
    def estimate_cost(
        operation_type: str,
        brain_mode: str,
        estimated_tokens: int = 500
    ) -> int:
        """
        Calculate estimated credit cost for a request.
        
        Requirements: 3.1-3.11
        
        Formula: base_cost × (tokens/1000) × brain_multiplier
        Minimum cost: 1 credit
        
        Args:
            operation_type: Type of operation (simple_response, long_response, etc.)
            brain_mode: Brain mode (brain, brain_pro, brain_gen)
            estimated_tokens: Estimated token count (default 500)
            
        Returns:
            Estimated credit cost (minimum 1)
        """
        # Get base cost for operation type
        base_cost = BASE_COSTS.get(operation_type, 1)
        
        # Get brain multiplier
        brain_multiplier = BRAIN_MULTIPLIERS.get(brain_mode, 1.0)
        
        # Calculate token multiplier
        token_multiplier = estimated_tokens / 1000
        
        # Calculate final cost
        calculated_cost = base_cost * token_multiplier * brain_multiplier
        
        # Return rounded cost with minimum of 1
        final_cost = max(1, round(calculated_cost))
        
        logger.debug(
            f"Estimated cost: {final_cost} credits "
            f"(operation={operation_type}, brain={brain_mode}, tokens={estimated_tokens})"
        )
        
        return final_cost
    
    @staticmethod
    def check_sufficient_credits(user_id: int, estimated_cost: int) -> bool:
        """
        Check if user has sufficient credits for a request.
        
        Requirements: 4.1, 4.2, 4.4
        
        Args:
            user_id: ID of the user
            estimated_cost: Estimated credit cost
            
        Returns:
            True if user has sufficient credits, False otherwise
        """
        balance = CreditManager.get_balance(user_id)
        remaining = balance['remaining_credits']
        
        sufficient = remaining >= estimated_cost
        
        logger.debug(
            f"Credit check for user {user_id}: "
            f"required={estimated_cost}, remaining={remaining}, sufficient={sufficient}"
        )
        
        return sufficient

    
    @staticmethod
    def deduct_credits(
        user_id: int,
        amount: int,
        metadata: Dict
    ) -> CreditUsageLog:
        """
        Deduct credits from user's balance with atomic transaction.
        
        Requirements: 3.1, 9.8, 20.3, 20.4
        
        Uses SELECT FOR UPDATE to prevent race conditions.
        Invalidates Redis cache immediately after deduction.
        Creates CreditUsageLog record for audit trail.
        
        Args:
            user_id: ID of the user
            amount: Number of credits to deduct
            metadata: Dict with operation_type, brain_mode, model_used, request_id
            
        Returns:
            CreditUsageLog record
            
        Raises:
            InsufficientCreditsError: If user has insufficient credits
        """
        start_time = time.time()
        
        with transaction.atomic():
            # Lock the user credits row to prevent race conditions
            user_credits = UserCredits.objects.select_for_update().select_related('user').get(user_id=user_id)
            user_tier = getattr(user_credits.user, 'subscription_tier', 'unknown')
            brain_mode = metadata.get('brain_mode', 'brain')
            operation_type = metadata.get('operation_type', 'unknown')
            
            # Check if sufficient credits
            if user_credits.remaining_credits < amount:
                logger.warning(
                    f"Insufficient credits for user {user_id}: "
                    f"required={amount}, remaining={user_credits.remaining_credits}"
                )
                raise InsufficientCreditsError(
                    remaining_credits=user_credits.remaining_credits,
                    required_credits=amount
                )
            
            # Deduct credits
            user_credits.remaining_credits -= amount
            user_credits.used_credits += amount
            user_credits.save(update_fields=['remaining_credits', 'used_credits', 'updated_at'])
            
            # Create usage log
            usage_log = CreditUsageLog.objects.create(
                user_id=user_id,
                credits_consumed=amount,
                operation_type=operation_type,
                brain_mode=brain_mode,
                model_used=metadata.get('model_used', 'unknown'),
                request_id=metadata.get('request_id'),
            )
            
            logger.info(
                f"Deducted {amount} credits from user {user_id}. "
                f"Remaining: {user_credits.remaining_credits}"
            )
            
            # Record metrics
            credit_deductions_total.labels(
                user_tier=user_tier,
                brain_mode=brain_mode,
                operation_type=operation_type
            ).inc()
        
        # Invalidate cache immediately after successful deduction
        cache_key = CreditManager._get_cache_key(user_id)
        cache.delete(cache_key)
        logger.debug(f"Invalidated cache for user {user_id}")
        
        latency = time.time() - start_time
        credit_deduction_latency_seconds.observe(latency)
        
        return usage_log
    
    @staticmethod
    def check_and_reset_if_needed(user_id: int) -> bool:
        """
        Check if monthly reset is needed and perform reset if conditions met.
        
        Requirements: 2.1-2.5
        
        Reset conditions:
        - Current date is first day of month
        - last_reset_date is in previous month
        
        Reset actions:
        - Set remaining_credits = monthly_credits
        - Set used_credits = 0
        - Update last_reset_date to current date
        - Create reset log entry
        - Invalidate cache
        
        Args:
            user_id: ID of the user
            
        Returns:
            True if reset was performed, False otherwise
        """
        today = date.today()
        
        # Only check on first day of month
        if today.day != 1:
            return False
        
        with transaction.atomic():
            user_credits = UserCredits.objects.select_for_update().select_related('user').get(user_id=user_id)
            user_tier = getattr(user_credits.user, 'subscription_tier', 'unknown')
            
            # Check if last reset was in previous month
            last_reset = user_credits.last_reset_date
            
            # If last reset is in current month, no reset needed
            if last_reset.year == today.year and last_reset.month == today.month:
                logger.debug(f"No reset needed for user {user_id} - already reset this month")
                return False
            
            # Perform reset
            previous_balance = user_credits.remaining_credits
            previous_used = user_credits.used_credits
            
            user_credits.remaining_credits = user_credits.monthly_credits
            user_credits.used_credits = 0
            user_credits.last_reset_date = today
            user_credits.save(
                update_fields=['remaining_credits', 'used_credits', 'last_reset_date', 'updated_at']
            )
            
            # Create reset log entry
            CreditUsageLog.objects.create(
                user_id=user_id,
                credits_consumed=-previous_balance,  # Negative to indicate reset
                operation_type='monthly_reset',
                brain_mode='system',
                model_used='system',
                request_id=None,
            )
            
            logger.info(
                f"Monthly reset for user {user_id}: "
                f"previous_balance={previous_balance}, "
                f"previous_used={previous_used}, "
                f"new_balance={user_credits.remaining_credits}"
            )
            
            # Record metrics
            credit_resets_total.labels(user_tier=user_tier).inc()
        
        # Invalidate cache
        cache_key = CreditManager._get_cache_key(user_id)
        cache.delete(cache_key)
        logger.debug(f"Invalidated cache for user {user_id} after reset")
        
        return True
    
    @staticmethod
    def get_usage_history(
        user_id: int,
        filters: Optional[Dict] = None,
        page: int = 1,
        page_size: int = 20
    ) -> Tuple[List[CreditUsageLog], Dict]:
        """
        Retrieve paginated credit usage history with filtering.
        
        Requirements: 10.1-10.6, 20.3
        
        Supported filters:
        - start_date: Filter from date (ISO 8601)
        - end_date: Filter to date (ISO 8601)
        - operation_type: Filter by operation type
        - brain_mode: Filter by brain mode
        
        Args:
            user_id: ID of the user
            filters: Optional dict with filter parameters
            page: Page number (1-indexed)
            page_size: Number of records per page
            
        Returns:
            Tuple of (usage_logs, summary_stats)
            - usage_logs: List of CreditUsageLog records
            - summary_stats: Dict with total_consumed, average_per_request, count
        """
        filters = filters or {}
        
        # Build query with optimization: only fetch needed fields
        queryset = CreditUsageLog.objects.filter(user_id=user_id).only(
            'id', 'timestamp', 'credits_consumed', 'operation_type',
            'brain_mode', 'model_used', 'request_id', 'created_at'
        )
        
        # Apply filters
        if 'start_date' in filters:
            start_date = datetime.fromisoformat(filters['start_date'])
            queryset = queryset.filter(timestamp__gte=start_date)
        
        if 'end_date' in filters:
            end_date = datetime.fromisoformat(filters['end_date'])
            queryset = queryset.filter(timestamp__lte=end_date)
        
        if 'operation_type' in filters:
            queryset = queryset.filter(operation_type=filters['operation_type'])
        
        if 'brain_mode' in filters:
            queryset = queryset.filter(brain_mode=filters['brain_mode'])
        
        # Exclude system operations (resets) from user-facing history
        queryset = queryset.exclude(operation_type='monthly_reset')
        
        # Calculate summary statistics
        stats = queryset.aggregate(
            total_consumed=Sum('credits_consumed'),
            average_per_request=Avg('credits_consumed'),
            count=Count('id')
        )
        
        summary_stats = {
            'total_consumed': stats['total_consumed'] or 0,
            'average_per_request': round(stats['average_per_request'] or 0, 2),
            'count': stats['count'] or 0,
        }
        
        # Apply pagination
        offset = (page - 1) * page_size
        usage_logs = list(queryset[offset:offset + page_size])
        
        logger.debug(
            f"Retrieved {len(usage_logs)} usage logs for user {user_id} "
            f"(page {page}, total {summary_stats['count']})"
        )
        
        return usage_logs, summary_stats
    
    @staticmethod
    def get_usage_summary(user_id: int, days: int = 30) -> Dict:
        """
        Get aggregated usage summary for specified period.
        
        Requirements: 10.7, 10.8
        
        Returns daily breakdown and category breakdowns by operation_type and brain_mode.
        
        Args:
            user_id: ID of the user
            days: Number of days to include (default 30)
            
        Returns:
            Dict with:
            - period: start_date, end_date, days
            - total_credits_consumed: Total credits in period
            - daily_breakdown: List of {date, credits, requests}
            - by_operation_type: Dict of operation_type -> credits
            - by_brain_mode: Dict of brain_mode -> credits
        """
        end_date = timezone.now()
        start_date = end_date - timedelta(days=days)
        
        # Get all usage logs in period (exclude resets)
        queryset = CreditUsageLog.objects.filter(
            user_id=user_id,
            timestamp__gte=start_date,
            timestamp__lte=end_date
        ).exclude(operation_type='monthly_reset')
        
        # Calculate total
        total_consumed = queryset.aggregate(
            total=Sum('credits_consumed')
        )['total'] or 0
        
        # Daily breakdown
        daily_data = {}
        for log in queryset:
            log_date = log.timestamp.date().isoformat()
            if log_date not in daily_data:
                daily_data[log_date] = {'credits': 0, 'requests': 0}
            daily_data[log_date]['credits'] += log.credits_consumed
            daily_data[log_date]['requests'] += 1
        
        daily_breakdown = [
            {'date': date_str, 'credits': data['credits'], 'requests': data['requests']}
            for date_str, data in sorted(daily_data.items())
        ]
        
        # Breakdown by operation type
        by_operation = queryset.values('operation_type').annotate(
            total=Sum('credits_consumed')
        )
        by_operation_type = {
            item['operation_type']: item['total']
            for item in by_operation
        }
        
        # Breakdown by brain mode
        by_brain = queryset.values('brain_mode').annotate(
            total=Sum('credits_consumed')
        )
        by_brain_mode = {
            item['brain_mode']: item['total']
            for item in by_brain
        }
        
        summary = {
            'period': {
                'start_date': start_date.date().isoformat(),
                'end_date': end_date.date().isoformat(),
                'days': days,
            },
            'total_credits_consumed': total_consumed,
            'daily_breakdown': daily_breakdown,
            'by_operation_type': by_operation_type,
            'by_brain_mode': by_brain_mode,
        }
        
        logger.debug(
            f"Generated usage summary for user {user_id}: "
            f"{total_consumed} credits over {days} days"
        )
        
        return summary
