"""
Alerting service for monitoring integration health and performance.

Requirements: 27.1-27.7
"""
from typing import Dict, Any, List
from datetime import datetime, timedelta
from django.utils import timezone
from django.conf import settings
import redis
import json
import logging

logger = logging.getLogger(__name__)


class AlertRule:
    """Base class for alert rules"""
    
    def __init__(self, name: str, threshold: Any, description: str):
        self.name = name
        self.threshold = threshold
        self.description = description
    
    def check(self) -> Dict[str, Any]:
        """
        Check if alert condition is met.
        
        Returns:
            Dictionary with alert status and details
        """
        raise NotImplementedError


class RateLimitViolationAlert(AlertRule):
    """
    Alert on high rate limit violations.
    
    Requirements: 27.1-27.7
    Threshold: >100 violations per hour
    """
    
    def __init__(self, redis_client):
        super().__init__(
            name='rate_limit_violations',
            threshold=100,
            description='Alert when rate limit violations exceed 100 per hour'
        )
        self.redis = redis_client
    
    def check(self) -> Dict[str, Any]:
        """Check rate limit violations in the last hour"""
        violations_key = 'alerts:rate_limit_violations:hour'
        
        try:
            # Get violations count from Redis
            violations_data = self.redis.get(violations_key)
            violations_count = int(violations_data) if violations_data else 0
            
            is_triggered = violations_count > self.threshold
            
            return {
                'name': self.name,
                'triggered': is_triggered,
                'current_value': violations_count,
                'threshold': self.threshold,
                'description': self.description,
                'severity': 'warning' if is_triggered else 'ok',
                'timestamp': timezone.now().isoformat()
            }
        except Exception as e:
            logger.error(f"Error checking rate limit violations: {e}")
            return {
                'name': self.name,
                'triggered': False,
                'error': str(e)
            }


class MessageDeliveryFailureAlert(AlertRule):
    """
    Alert on message delivery failures.
    
    Requirements: 27.1-27.7
    Threshold: >5% failure rate
    """
    
    def __init__(self, redis_client):
        super().__init__(
            name='message_delivery_failures',
            threshold=5.0,  # 5% failure rate
            description='Alert when message delivery failure rate exceeds 5%'
        )
        self.redis = redis_client
    
    def check(self) -> Dict[str, Any]:
        """Check message delivery failure rate in the last hour"""
        stats_key = 'alerts:message_delivery:hour'
        
        try:
            # Get delivery stats from Redis
            stats_data = self.redis.get(stats_key)
            if stats_data:
                stats = json.loads(stats_data)
                total = stats.get('total', 0)
                failed = stats.get('failed', 0)
                
                if total > 0:
                    failure_rate = (failed / total) * 100
                else:
                    failure_rate = 0.0
            else:
                failure_rate = 0.0
                total = 0
                failed = 0
            
            is_triggered = failure_rate > self.threshold
            
            return {
                'name': self.name,
                'triggered': is_triggered,
                'current_value': round(failure_rate, 2),
                'threshold': self.threshold,
                'total_messages': total,
                'failed_messages': failed,
                'description': self.description,
                'severity': 'critical' if is_triggered else 'ok',
                'timestamp': timezone.now().isoformat()
            }
        except Exception as e:
            logger.error(f"Error checking message delivery failures: {e}")
            return {
                'name': self.name,
                'triggered': False,
                'error': str(e)
            }


class TokenRefreshFailureAlert(AlertRule):
    """
    Alert on token refresh failures.
    
    Requirements: 27.1-27.7
    """
    
    def __init__(self, redis_client):
        super().__init__(
            name='token_refresh_failures',
            threshold=3,  # 3 failures in last hour
            description='Alert when token refresh failures exceed 3 per hour'
        )
        self.redis = redis_client
    
    def check(self) -> Dict[str, Any]:
        """Check token refresh failures in the last hour"""
        failures_key = 'alerts:token_refresh_failures:hour'
        
        try:
            # Get failures count from Redis
            failures_data = self.redis.get(failures_key)
            failures_count = int(failures_data) if failures_data else 0
            
            is_triggered = failures_count > self.threshold
            
            return {
                'name': self.name,
                'triggered': is_triggered,
                'current_value': failures_count,
                'threshold': self.threshold,
                'description': self.description,
                'severity': 'warning' if is_triggered else 'ok',
                'timestamp': timezone.now().isoformat()
            }
        except Exception as e:
            logger.error(f"Error checking token refresh failures: {e}")
            return {
                'name': self.name,
                'triggered': False,
                'error': str(e)
            }


class WebhookProcessingDelayAlert(AlertRule):
    """
    Alert on webhook processing delays.
    
    Requirements: 27.1-27.7
    Threshold: >10 seconds average processing time
    """
    
    def __init__(self, redis_client):
        super().__init__(
            name='webhook_processing_delay',
            threshold=10.0,  # 10 seconds
            description='Alert when webhook processing time exceeds 10 seconds'
        )
        self.redis = redis_client
    
    def check(self) -> Dict[str, Any]:
        """Check webhook processing delays in the last hour"""
        stats_key = 'alerts:webhook_processing:hour'
        
        try:
            # Get processing stats from Redis
            stats_data = self.redis.get(stats_key)
            if stats_data:
                stats = json.loads(stats_data)
                total_time = stats.get('total_time', 0.0)
                count = stats.get('count', 0)
                
                if count > 0:
                    avg_time = total_time / count
                else:
                    avg_time = 0.0
            else:
                avg_time = 0.0
                count = 0
            
            is_triggered = avg_time > self.threshold
            
            return {
                'name': self.name,
                'triggered': is_triggered,
                'current_value': round(avg_time, 2),
                'threshold': self.threshold,
                'webhook_count': count,
                'description': self.description,
                'severity': 'warning' if is_triggered else 'ok',
                'timestamp': timezone.now().isoformat()
            }
        except Exception as e:
            logger.error(f"Error checking webhook processing delays: {e}")
            return {
                'name': self.name,
                'triggered': False,
                'error': str(e)
            }


class QueueBacklogAlert(AlertRule):
    """
    Alert on Celery queue backlog.
    
    Requirements: 27.1-27.7
    Threshold: >1000 messages in queue
    """
    
    def __init__(self, redis_client):
        super().__init__(
            name='queue_backlog',
            threshold=1000,
            description='Alert when Celery queue backlog exceeds 1000 messages'
        )
        self.redis = redis_client
    
    def check(self) -> Dict[str, Any]:
        """Check queue backlog"""
        queues = ['high_priority', 'incoming_messages', 'outgoing_messages', 'default']
        
        try:
            queue_lengths = {}
            total_backlog = 0
            
            for queue_name in queues:
                queue_key = f"celery:queue:{queue_name}"
                length = self.redis.llen(queue_key)
                queue_lengths[queue_name] = length
                total_backlog += length
            
            is_triggered = total_backlog > self.threshold
            
            # Find queues exceeding individual threshold
            problem_queues = [
                {'queue': q, 'length': l}
                for q, l in queue_lengths.items()
                if l > 500  # Individual queue threshold
            ]
            
            return {
                'name': self.name,
                'triggered': is_triggered,
                'current_value': total_backlog,
                'threshold': self.threshold,
                'queue_lengths': queue_lengths,
                'problem_queues': problem_queues,
                'description': self.description,
                'severity': 'critical' if is_triggered else 'ok',
                'timestamp': timezone.now().isoformat()
            }
        except Exception as e:
            logger.error(f"Error checking queue backlog: {e}")
            return {
                'name': self.name,
                'triggered': False,
                'error': str(e)
            }


class IntegrationHealthAlert(AlertRule):
    """
    Alert on integration health degradation.
    
    Requirements: 27.1-27.7
    """
    
    def __init__(self):
        super().__init__(
            name='integration_health_degradation',
            threshold=5,  # 5 or more degraded/disconnected integrations
            description='Alert when 5 or more integrations are degraded or disconnected'
        )
    
    def check(self) -> Dict[str, Any]:
        """Check integration health status"""
        from apps.automation.models import Integration
        
        try:
            # Count integrations by health status
            degraded_count = Integration.objects.filter(
                health_status='degraded'
            ).count()
            
            disconnected_count = Integration.objects.filter(
                health_status='disconnected'
            ).count()
            
            total_unhealthy = degraded_count + disconnected_count
            is_triggered = total_unhealthy >= self.threshold
            
            return {
                'name': self.name,
                'triggered': is_triggered,
                'current_value': total_unhealthy,
                'threshold': self.threshold,
                'degraded_count': degraded_count,
                'disconnected_count': disconnected_count,
                'description': self.description,
                'severity': 'warning' if is_triggered else 'ok',
                'timestamp': timezone.now().isoformat()
            }
        except Exception as e:
            logger.error(f"Error checking integration health: {e}")
            return {
                'name': self.name,
                'triggered': False,
                'error': str(e)
            }


class AlertingService:
    """
    Service for checking alert rules and managing alerts.
    
    Requirements: 27.1-27.7
    """
    
    def __init__(self, redis_client=None):
        """Initialize with Redis client"""
        self.redis = redis_client or redis.from_url(
            settings.CELERY_BROKER_URL,
            decode_responses=True
        )
        
        # Initialize alert rules
        self.alert_rules = [
            RateLimitViolationAlert(self.redis),
            MessageDeliveryFailureAlert(self.redis),
            TokenRefreshFailureAlert(self.redis),
            WebhookProcessingDelayAlert(self.redis),
            QueueBacklogAlert(self.redis),
            IntegrationHealthAlert(),
        ]
    
    def check_all_alerts(self) -> Dict[str, Any]:
        """
        Check all alert rules.
        
        Returns:
            Dictionary with alert status for all rules
        """
        alerts = []
        triggered_count = 0
        
        for rule in self.alert_rules:
            alert_status = rule.check()
            alerts.append(alert_status)
            
            if alert_status.get('triggered', False):
                triggered_count += 1
                # Log triggered alerts
                logger.warning(
                    f"Alert triggered: {alert_status['name']} - "
                    f"{alert_status.get('description', 'No description')}"
                )
        
        return {
            'alerts': alerts,
            'triggered_count': triggered_count,
            'total_rules': len(self.alert_rules),
            'timestamp': timezone.now().isoformat()
        }
    
    def record_rate_limit_violation(self):
        """Record a rate limit violation for alerting"""
        violations_key = 'alerts:rate_limit_violations:hour'
        self.redis.incr(violations_key)
        self.redis.expire(violations_key, 3600)  # 1 hour expiry
    
    def record_message_delivery(self, success: bool):
        """Record message delivery result for alerting"""
        stats_key = 'alerts:message_delivery:hour'
        
        # Get current stats
        stats_data = self.redis.get(stats_key)
        if stats_data:
            stats = json.loads(stats_data)
        else:
            stats = {'total': 0, 'failed': 0}
        
        # Update stats
        stats['total'] += 1
        if not success:
            stats['failed'] += 1
        
        # Store back to Redis
        self.redis.setex(stats_key, 3600, json.dumps(stats))
    
    def record_token_refresh_failure(self):
        """Record a token refresh failure for alerting"""
        failures_key = 'alerts:token_refresh_failures:hour'
        self.redis.incr(failures_key)
        self.redis.expire(failures_key, 3600)  # 1 hour expiry
    
    def record_webhook_processing(self, processing_time: float):
        """Record webhook processing time for alerting"""
        stats_key = 'alerts:webhook_processing:hour'
        
        # Get current stats
        stats_data = self.redis.get(stats_key)
        if stats_data:
            stats = json.loads(stats_data)
        else:
            stats = {'total_time': 0.0, 'count': 0}
        
        # Update stats
        stats['total_time'] += processing_time
        stats['count'] += 1
        
        # Store back to Redis
        self.redis.setex(stats_key, 3600, json.dumps(stats))
