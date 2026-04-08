"""
Authentication metrics service for monitoring and alerting.

Provides methods for logging authentication attempts and analyzing
authentication performance and reliability.

Requirements: 23.2, 23.3, 23.4, 23.5, 23.6
"""

import logging
from datetime import timedelta
from typing import Dict, List, Optional
from django.utils import timezone
from django.db.models import Avg, Count, Q
from apps.automation.models import (
    AuthenticationAuditLog,
    AuthenticationAction,
    AuthType
)


logger = logging.getLogger(__name__)


class AuthenticationMetrics:
    """
    Service for tracking and analyzing authentication metrics.
    
    Provides methods for logging authentication attempts, calculating
    success rates, monitoring performance, and detecting anomalies.
    
    Requirements: 23.2-23.6
    """
    
    # Alert threshold for failure rate
    FAILURE_RATE_THRESHOLD = 0.10  # 10%
    
    @staticmethod
    def log_authentication_attempt(
        action: str,
        auth_type: str,
        success: bool,
        user=None,
        integration_type=None,
        duration_ms: int = None,
        error_code: str = '',
        error_message: str = '',
        ip_address: str = None,
        user_agent: str = '',
        metadata: dict = None
    ) -> AuthenticationAuditLog:
        """
        Log an authentication attempt to the audit log.
        
        Args:
            action: Authentication action (install_start, install_complete, etc.)
            auth_type: Authentication type (oauth, meta, api_key)
            success: Whether the action succeeded
            user: User who initiated the action (optional)
            integration_type: Integration type being authenticated (optional)
            duration_ms: Duration in milliseconds (optional)
            error_code: Error code if failed (optional)
            error_message: Error message if failed (optional)
            ip_address: IP address of the request (optional)
            user_agent: User agent string (optional)
            metadata: Additional context (optional)
            
        Returns:
            Created AuthenticationAuditLog instance
            
        Requirements: 23.2
        """
        log_entry = AuthenticationAuditLog.log_authentication_attempt(
            action=action,
            auth_type=auth_type,
            success=success,
            user=user,
            integration_type=integration_type,
            duration_ms=duration_ms,
            error_code=error_code,
            error_message=error_message,
            ip_address=ip_address,
            user_agent=user_agent,
            metadata=metadata
        )
        
        logger.info(
            f'Authentication attempt logged: {action} - {auth_type} - '
            f'{"Success" if success else "Failed"}'
        )
        
        # Check if failure rate alert should be triggered
        if not success:
            AuthenticationMetrics.check_failure_rate_alert(auth_type)
        
        return log_entry
    
    @staticmethod
    def get_success_rate_by_auth_type(
        auth_type: str,
        days: int = 7
    ) -> float:
        """
        Calculate success rate for an authentication type.
        
        Args:
            auth_type: Authentication type to analyze (oauth, meta, api_key)
            days: Number of days to look back (default: 7)
            
        Returns:
            Success rate as percentage (0-100)
            
        Requirements: 23.3
        """
        cutoff = timezone.now() - timedelta(days=days)
        
        logs = AuthenticationAuditLog.objects.filter(
            auth_type=auth_type,
            created_at__gte=cutoff
        )
        
        total = logs.count()
        if total == 0:
            return 100.0
        
        successful = logs.filter(success=True).count()
        success_rate = (successful / total) * 100
        
        logger.debug(
            f'Success rate for {auth_type} (last {days} days): '
            f'{success_rate:.2f}% ({successful}/{total})'
        )
        
        return success_rate
    
    @staticmethod
    def get_average_duration_by_auth_type(
        auth_type: str,
        days: int = 7
    ) -> float:
        """
        Calculate average duration for an authentication type.
        
        Args:
            auth_type: Authentication type to analyze (oauth, meta, api_key)
            days: Number of days to look back (default: 7)
            
        Returns:
            Average duration in milliseconds
            
        Requirements: 23.4
        """
        cutoff = timezone.now() - timedelta(days=days)
        
        result = AuthenticationAuditLog.objects.filter(
            auth_type=auth_type,
            created_at__gte=cutoff,
            duration_ms__isnull=False
        ).aggregate(avg_duration=Avg('duration_ms'))
        
        avg_duration = result['avg_duration'] or 0.0
        
        logger.debug(
            f'Average duration for {auth_type} (last {days} days): '
            f'{avg_duration:.2f}ms'
        )
        
        return avg_duration
    
    @staticmethod
    def check_failure_rate_alert(auth_type: str, hours: int = 1) -> bool:
        """
        Check if failure rate exceeds threshold and trigger alert.
        
        Args:
            auth_type: Authentication type to check
            hours: Number of hours to look back (default: 1)
            
        Returns:
            True if alert was triggered, False otherwise
            
        Requirements: 23.5, 23.6
        """
        cutoff = timezone.now() - timedelta(hours=hours)
        
        logs = AuthenticationAuditLog.objects.filter(
            auth_type=auth_type,
            created_at__gte=cutoff
        )
        
        total = logs.count()
        if total < 10:  # Need at least 10 attempts for meaningful analysis
            return False
        
        failed = logs.filter(success=False).count()
        failure_rate = failed / total
        
        if failure_rate > AuthenticationMetrics.FAILURE_RATE_THRESHOLD:
            logger.warning(
                f'ALERT: High failure rate for {auth_type} authentication: '
                f'{failure_rate * 100:.2f}% ({failed}/{total} failed in last {hours}h)'
            )
            
            # TODO: Send alert notification to administrators
            # This could be integrated with monitoring systems like:
            # - Email notifications
            # - Slack/Discord webhooks
            # - PagerDuty/Opsgenie
            # - CloudWatch/Datadog alerts
            
            return True
        
        return False
    
    @staticmethod
    def get_metrics_summary(days: int = 7) -> Dict[str, Dict]:
        """
        Get comprehensive metrics summary for all authentication types.
        
        Args:
            days: Number of days to look back (default: 7)
            
        Returns:
            Dictionary with metrics for each auth type
            
        Requirements: 23.3, 23.4
        """
        summary = {}
        
        for auth_type_choice in AuthType.choices:
            auth_type = auth_type_choice[0]
            
            success_rate = AuthenticationMetrics.get_success_rate_by_auth_type(
                auth_type, days
            )
            avg_duration = AuthenticationMetrics.get_average_duration_by_auth_type(
                auth_type, days
            )
            
            # Get total attempts
            cutoff = timezone.now() - timedelta(days=days)
            total_attempts = AuthenticationAuditLog.objects.filter(
                auth_type=auth_type,
                created_at__gte=cutoff
            ).count()
            
            summary[auth_type] = {
                'success_rate': success_rate,
                'average_duration_ms': avg_duration,
                'total_attempts': total_attempts,
                'auth_type_display': auth_type_choice[1]
            }
        
        return summary
    
    @staticmethod
    def get_failure_breakdown_by_error_code(
        auth_type: str,
        days: int = 7
    ) -> List[Dict]:
        """
        Get breakdown of failures by error code.
        
        Args:
            auth_type: Authentication type to analyze
            days: Number of days to look back (default: 7)
            
        Returns:
            List of dictionaries with error_code and count
        """
        cutoff = timezone.now() - timedelta(days=days)
        
        failures = AuthenticationAuditLog.objects.filter(
            auth_type=auth_type,
            success=False,
            created_at__gte=cutoff
        ).values('error_code').annotate(
            count=Count('id')
        ).order_by('-count')
        
        return list(failures)
    
    @staticmethod
    def get_authentication_timeline(
        auth_type: Optional[str] = None,
        days: int = 7,
        interval_hours: int = 1
    ) -> List[Dict]:
        """
        Get authentication attempts over time.
        
        Args:
            auth_type: Authentication type to filter (optional)
            days: Number of days to look back (default: 7)
            interval_hours: Grouping interval in hours (default: 1)
            
        Returns:
            List of dictionaries with timestamp, total, successful, failed
        """
        from django.db.models.functions import TruncHour
        
        cutoff = timezone.now() - timedelta(days=days)
        
        query = AuthenticationAuditLog.objects.filter(created_at__gte=cutoff)
        if auth_type:
            query = query.filter(auth_type=auth_type)
        
        timeline = query.annotate(
            hour=TruncHour('created_at')
        ).values('hour').annotate(
            total=Count('id'),
            successful=Count('id', filter=Q(success=True)),
            failed=Count('id', filter=Q(success=False))
        ).order_by('hour')
        
        return list(timeline)
    
    @staticmethod
    def get_top_failing_integrations(days: int = 7, limit: int = 10) -> List[Dict]:
        """
        Get integration types with highest failure rates.
        
        Args:
            days: Number of days to look back (default: 7)
            limit: Maximum number of results (default: 10)
            
        Returns:
            List of dictionaries with integration_type, failure_rate, total_attempts
        """
        cutoff = timezone.now() - timedelta(days=days)
        
        # Get all integration types with attempts
        integration_stats = AuthenticationAuditLog.objects.filter(
            created_at__gte=cutoff,
            integration_type__isnull=False
        ).values(
            'integration_type__id',
            'integration_type__name'
        ).annotate(
            total=Count('id'),
            failed=Count('id', filter=Q(success=False))
        )
        
        # Calculate failure rates
        results = []
        for stat in integration_stats:
            if stat['total'] > 0:
                failure_rate = (stat['failed'] / stat['total']) * 100
                results.append({
                    'integration_type_id': stat['integration_type__id'],
                    'integration_type_name': stat['integration_type__name'],
                    'failure_rate': failure_rate,
                    'total_attempts': stat['total'],
                    'failed_attempts': stat['failed']
                })
        
        # Sort by failure rate descending
        results.sort(key=lambda x: x['failure_rate'], reverse=True)
        
        return results[:limit]
