"""
Kill-switch service for Twin automations.

Provides functionality to disable all Twin automations globally.
Notifies user of kill-switch activation.

Requirements: Safety principles
"""

import logging
from typing import Optional
from uuid import UUID

from django.contrib.auth import get_user_model
from django.utils import timezone

from apps.twin.models import Twin
from apps.twin.services.audit import AuditLogService


User = get_user_model()
logger = logging.getLogger(__name__)


class KillSwitchService:
    """
    Service for managing Twin kill-switch.
    
    The kill-switch provides an emergency stop for all Twin automations.
    When activated, all Twin-initiated requests are blocked.
    
    Requirements: Safety principles
    """
    
    @staticmethod
    def activate_kill_switch(
        user: User,
        reason: Optional[str] = None,
        ip_address: Optional[str] = None,
        user_agent: Optional[str] = None
    ) -> Twin:
        """
        Activate kill-switch for a user's Twin.
        
        Disables all Twin automations and blocks Twin-initiated requests.
        
        Args:
            user: User whose Twin to disable
            reason: Optional reason for activation
            ip_address: IP address of the request
            user_agent: User agent string
            
        Returns:
            Updated Twin instance
        """
        try:
            twin = user.twin
        except Twin.DoesNotExist:
            logger.error(f'No Twin found for user {user.id}')
            raise ValueError('User does not have a Twin')
        
        # Activate kill-switch
        twin.kill_switch_active = True
        twin.save(update_fields=['kill_switch_active', 'updated_at'])
        
        logger.warning(
            f'Kill-switch activated for user {user.id} (Twin: {twin.id}). '
            f'Reason: {reason or "Not specified"}'
        )
        
        # Log to audit log
        AuditLogService.log_twin_action(
            user=user,
            resource_type='Twin',
            resource_id=str(twin.id),
            action='kill_switch_activated',
            result='success',
            details={
                'reason': reason or 'User-initiated',
                'timestamp': timezone.now().isoformat(),
            },
            cognitive_blend_value=twin.cognitive_blend,
            permission_flag=True,  # User explicitly activated
            ip_address=ip_address,
            user_agent=user_agent
        )
        
        # TODO: Send notification to user
        # This would integrate with notification service when available
        logger.info(f'Kill-switch notification sent to user {user.id}')
        
        return twin
    
    @staticmethod
    def deactivate_kill_switch(
        user: User,
        reason: Optional[str] = None,
        ip_address: Optional[str] = None,
        user_agent: Optional[str] = None
    ) -> Twin:
        """
        Deactivate kill-switch for a user's Twin.
        
        Re-enables Twin automations.
        
        Args:
            user: User whose Twin to enable
            reason: Optional reason for deactivation
            ip_address: IP address of the request
            user_agent: User agent string
            
        Returns:
            Updated Twin instance
        """
        try:
            twin = user.twin
        except Twin.DoesNotExist:
            logger.error(f'No Twin found for user {user.id}')
            raise ValueError('User does not have a Twin')
        
        # Deactivate kill-switch
        twin.kill_switch_active = False
        twin.save(update_fields=['kill_switch_active', 'updated_at'])
        
        logger.info(
            f'Kill-switch deactivated for user {user.id} (Twin: {twin.id}). '
            f'Reason: {reason or "Not specified"}'
        )
        
        # Log to audit log
        AuditLogService.log_twin_action(
            user=user,
            resource_type='Twin',
            resource_id=str(twin.id),
            action='kill_switch_deactivated',
            result='success',
            details={
                'reason': reason or 'User-initiated',
                'timestamp': timezone.now().isoformat(),
            },
            cognitive_blend_value=twin.cognitive_blend,
            permission_flag=True,  # User explicitly deactivated
            ip_address=ip_address,
            user_agent=user_agent
        )
        
        # TODO: Send notification to user
        logger.info(f'Kill-switch deactivation notification sent to user {user.id}')
        
        return twin
    
    @staticmethod
    def get_kill_switch_status(user: User) -> dict:
        """
        Get kill-switch status for a user's Twin.
        
        Args:
            user: User to check
            
        Returns:
            Dictionary with kill-switch status and details
        """
        try:
            twin = user.twin
            return {
                'active': twin.kill_switch_active,
                'twin_id': str(twin.id),
                'twin_active': twin.is_active,
                'cognitive_blend': twin.cognitive_blend,
                'last_updated': twin.updated_at.isoformat(),
            }
        except Twin.DoesNotExist:
            return {
                'active': False,
                'twin_id': None,
                'twin_active': False,
                'error': 'No Twin found for user',
            }
    
    @staticmethod
    def is_kill_switch_active(user: User) -> bool:
        """
        Check if kill-switch is active for a user.
        
        Args:
            user: User to check
            
        Returns:
            True if kill-switch is active, False otherwise
        """
        try:
            twin = user.twin
            return twin.kill_switch_active
        except Twin.DoesNotExist:
            return False
    
    @staticmethod
    def disable_all_twin_automations(user: User) -> int:
        """
        Disable all active workflows for a user.
        
        This is called when kill-switch is activated to ensure
        no workflows can execute.
        
        Args:
            user: User whose workflows to disable
            
        Returns:
            Number of workflows disabled
        """
        from apps.automation.models import Workflow
        
        # Get all active workflows
        active_workflows = Workflow.objects.filter(
            user=user,
            is_active=True
        )
        
        count = active_workflows.count()
        
        # Disable all workflows
        active_workflows.update(is_active=False)
        
        logger.info(
            f'Disabled {count} workflows for user {user.id} due to kill-switch'
        )
        
        return count
    
    @staticmethod
    def get_blocked_requests_count(user: User, since_hours: int = 24) -> int:
        """
        Get count of requests blocked by kill-switch.
        
        Args:
            user: User to check
            since_hours: Number of hours to look back
            
        Returns:
            Count of blocked requests
        """
        from datetime import timedelta
        from apps.twin.models import AuditLog
        
        since_time = timezone.now() - timedelta(hours=since_hours)
        
        blocked_count = AuditLog.objects.filter(
            user=user,
            event_type='twin_action',
            action='blocked',
            result='denied',
            details__reason='Kill-switch active',
            timestamp__gte=since_time
        ).count()
        
        return blocked_count
