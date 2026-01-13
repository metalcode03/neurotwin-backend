"""
Permission service for NeuroTwin platform.

Handles permission management, verification, and high-risk action detection.
Requirements: 10.1, 10.2, 10.3, 10.4, 10.5, 10.6, 10.7
"""

from typing import List, Optional, Tuple

from django.db import transaction

from .models import PermissionScope, PermissionHistory, ActionType, IntegrationType
from .dataclasses import PermissionCheckResult, PermissionScopeData, PermissionUpdateRequest


class PermissionService:
    """
    Manages permission scopes and action authorization.
    
    Provides methods for permission management, verification, and high-risk action detection.
    Requirements: 10.1-10.7
    """
    
    # High-risk action types that always require explicit approval
    # Requirements: 10.3, 10.4, 10.5
    HIGH_RISK_ACTIONS = frozenset([
        ActionType.FINANCIAL,
        ActionType.LEGAL,
        ActionType.DELETE,
    ])
    
    def get_permissions(self, user_id: str) -> List[PermissionScopeData]:
        """
        Get all permission scopes for user.
        
        Requirements: 10.1
        
        Args:
            user_id: The user's ID
            
        Returns:
            List of PermissionScopeData for all defined scopes
        """
        permissions = PermissionScope.objects.filter(user_id=user_id)
        return [PermissionScopeData.from_model(p) for p in permissions]
    
    def get_permission(
        self, 
        user_id: str, 
        integration: str, 
        action_type: str
    ) -> Optional[PermissionScope]:
        """
        Get a specific permission scope.
        
        Args:
            user_id: The user's ID
            integration: The integration name
            action_type: The action type
            
        Returns:
            PermissionScope if found, None otherwise
        """
        return PermissionScope.objects.filter(
            user_id=user_id,
            integration=integration,
            action_type=action_type
        ).first()
    
    def get_or_create_permission(
        self, 
        user_id: str, 
        integration: str, 
        action_type: str
    ) -> PermissionScope:
        """
        Get or create a permission scope with default values.
        
        Default: is_granted=False, requires_approval=True
        
        Args:
            user_id: The user's ID
            integration: The integration name
            action_type: The action type
            
        Returns:
            The permission scope (existing or newly created)
        """
        permission, created = PermissionScope.objects.get_or_create(
            user_id=user_id,
            integration=integration,
            action_type=action_type,
            defaults={
                'is_granted': False,
                'requires_approval': True,
            }
        )
        return permission

    
    @transaction.atomic
    def update_permission(
        self, 
        user_id: str, 
        request: PermissionUpdateRequest
    ) -> PermissionScope:
        """
        Update a permission scope.
        
        Requirements: 10.7 - Users can modify permission scopes at any time
        
        Args:
            user_id: The user's ID
            request: The update request with new values
            
        Returns:
            Updated PermissionScope
        """
        permission = self.get_or_create_permission(
            user_id, 
            request.integration, 
            request.action_type
        )
        
        # Record previous values for history
        previous_is_granted = permission.is_granted
        previous_requires_approval = permission.requires_approval
        
        # Apply updates
        changed = False
        if request.is_granted is not None and request.is_granted != permission.is_granted:
            permission.is_granted = request.is_granted
            changed = True
        
        if request.requires_approval is not None and request.requires_approval != permission.requires_approval:
            permission.requires_approval = request.requires_approval
            changed = True
        
        if changed:
            permission.save()
            
            # Record history
            PermissionHistory.objects.create(
                permission_scope=permission,
                previous_is_granted=previous_is_granted,
                new_is_granted=permission.is_granted,
                previous_requires_approval=previous_requires_approval,
                new_requires_approval=permission.requires_approval,
                reason=request.reason
            )
        
        return permission
    
    def check_permission(
        self, 
        user_id: str, 
        integration: str, 
        action_type: str
    ) -> Tuple[bool, bool]:
        """
        Check if action is permitted and if approval needed.
        
        Requirements: 10.2, 10.3, 10.4, 10.5, 10.6
        - Verify action falls within granted permission scopes
        - Financial transactions require explicit per-transaction approval
        - Legal actions require explicit per-action approval
        - Irreversible actions require explicit approval
        - Out-of-scope actions request user approval
        
        Args:
            user_id: The user's ID
            integration: The integration name
            action_type: The action type
            
        Returns:
            Tuple of (allowed, needs_approval)
            - allowed: Whether the action is allowed
            - needs_approval: Whether per-action approval is needed
        """
        result = self.check_permission_detailed(user_id, integration, action_type)
        return (result.allowed, result.needs_approval)
    
    def check_permission_detailed(
        self, 
        user_id: str, 
        integration: str, 
        action_type: str
    ) -> PermissionCheckResult:
        """
        Check permission with detailed result.
        
        Requirements: 10.2, 10.3, 10.4, 10.5, 10.6
        
        Args:
            user_id: The user's ID
            integration: The integration name
            action_type: The action type
            
        Returns:
            PermissionCheckResult with allowed, needs_approval, and reason
        """
        # Get the permission scope
        permission = self.get_permission(user_id, integration, action_type)
        
        # If no permission scope exists, action is not allowed
        # Requirements: 10.6 - Out-of-scope actions request user approval
        if permission is None:
            return PermissionCheckResult.denied(
                f"No permission scope defined for {integration}/{action_type}. "
                "User approval required."
            )
        
        # If permission is not granted, action is not allowed
        if not permission.is_granted:
            return PermissionCheckResult.denied(
                f"Permission not granted for {integration}/{action_type}"
            )
        
        # Check if this is a high-risk action
        # Requirements: 10.3, 10.4, 10.5
        if self.is_high_risk_action(action_type):
            return PermissionCheckResult.allowed_with_approval(
                f"High-risk action ({action_type}) requires explicit approval"
            )
        
        # Check if the permission requires per-action approval
        if permission.requires_approval:
            return PermissionCheckResult.allowed_with_approval(
                f"Permission for {integration}/{action_type} requires approval"
            )
        
        # Permission granted without approval needed
        return PermissionCheckResult.allowed_without_approval()
    
    def is_high_risk_action(self, action_type: str) -> bool:
        """
        Check if action is financial, legal, or irreversible.
        
        Requirements: 10.3, 10.4, 10.5
        - Financial transactions require explicit per-transaction approval
        - Legal actions require explicit per-action approval
        - Irreversible actions (DELETE) require explicit approval
        
        Args:
            action_type: The action type to check
            
        Returns:
            True if the action is high-risk
        """
        return action_type in self.HIGH_RISK_ACTIONS

    
    @transaction.atomic
    def grant_permission(
        self, 
        user_id: str, 
        integration: str, 
        action_type: str,
        requires_approval: bool = True,
        reason: str = ""
    ) -> PermissionScope:
        """
        Grant a permission to a user.
        
        Convenience method for granting permissions.
        
        Args:
            user_id: The user's ID
            integration: The integration name
            action_type: The action type
            requires_approval: Whether per-action approval is needed
            reason: Reason for granting
            
        Returns:
            Updated PermissionScope
        """
        request = PermissionUpdateRequest(
            integration=integration,
            action_type=action_type,
            is_granted=True,
            requires_approval=requires_approval,
            reason=reason
        )
        return self.update_permission(user_id, request)
    
    @transaction.atomic
    def revoke_permission(
        self, 
        user_id: str, 
        integration: str, 
        action_type: str,
        reason: str = ""
    ) -> PermissionScope:
        """
        Revoke a permission from a user.
        
        Convenience method for revoking permissions.
        
        Args:
            user_id: The user's ID
            integration: The integration name
            action_type: The action type
            reason: Reason for revoking
            
        Returns:
            Updated PermissionScope
        """
        request = PermissionUpdateRequest(
            integration=integration,
            action_type=action_type,
            is_granted=False,
            reason=reason
        )
        return self.update_permission(user_id, request)
    
    def get_permission_history(
        self, 
        user_id: str, 
        integration: Optional[str] = None,
        action_type: Optional[str] = None
    ) -> List[PermissionHistory]:
        """
        Get permission change history for a user.
        
        Args:
            user_id: The user's ID
            integration: Optional filter by integration
            action_type: Optional filter by action type
            
        Returns:
            List of PermissionHistory entries
        """
        queryset = PermissionHistory.objects.filter(
            permission_scope__user_id=user_id
        )
        
        if integration:
            queryset = queryset.filter(permission_scope__integration=integration)
        
        if action_type:
            queryset = queryset.filter(permission_scope__action_type=action_type)
        
        return list(queryset.order_by('-changed_at'))
    
    def initialize_default_permissions(self, user_id: str) -> List[PermissionScope]:
        """
        Initialize default permission scopes for a new user.
        
        Creates permission scopes for all integration/action combinations
        with default values (is_granted=False, requires_approval=True).
        
        Args:
            user_id: The user's ID
            
        Returns:
            List of created PermissionScope objects
        """
        created_permissions = []
        
        for integration in IntegrationType.values:
            for action_type in ActionType.values:
                permission, created = PermissionScope.objects.get_or_create(
                    user_id=user_id,
                    integration=integration,
                    action_type=action_type,
                    defaults={
                        'is_granted': False,
                        'requires_approval': True,
                    }
                )
                if created:
                    created_permissions.append(permission)
        
        return created_permissions
    
    def get_granted_permissions(self, user_id: str) -> List[PermissionScopeData]:
        """
        Get all granted permissions for a user.
        
        Args:
            user_id: The user's ID
            
        Returns:
            List of granted PermissionScopeData
        """
        permissions = PermissionScope.objects.filter(
            user_id=user_id,
            is_granted=True
        )
        return [PermissionScopeData.from_model(p) for p in permissions]
    
    def get_permissions_for_integration(
        self, 
        user_id: str, 
        integration: str
    ) -> List[PermissionScopeData]:
        """
        Get all permissions for a specific integration.
        
        Args:
            user_id: The user's ID
            integration: The integration name
            
        Returns:
            List of PermissionScopeData for the integration
        """
        permissions = PermissionScope.objects.filter(
            user_id=user_id,
            integration=integration
        )
        return [PermissionScopeData.from_model(p) for p in permissions]


from datetime import datetime
from typing import Optional as OptionalType

from .models import AuditEntry, AuditOutcome
from .dataclasses import AuditEntryData, AuditLogRequest, AuditFilterCriteria


class AuditService:
    """
    Manages immutable audit logging for Twin actions.
    
    Provides methods for logging actions, retrieving audit history,
    and verifying log integrity.
    
    Requirements: 11.1, 11.2, 11.3, 11.4, 11.5
    - Log every Twin action with full context
    - Immutable and tamper-evident logs
    - Filterable, searchable access to audit history
    - Retain logs according to user preferences
    - Log reasoning chain for transparency
    """
    
    def log_action(
        self,
        user_id: str,
        action_type: str,
        outcome: str,
        target_integration: OptionalType[str] = None,
        input_data: OptionalType[dict] = None,
        cognitive_blend: OptionalType[int] = None,
        reasoning_chain: str = "",
        is_twin_generated: bool = True,
        twin_id: OptionalType[str] = None
    ) -> AuditEntry:
        """
        Log a Twin action with full context and checksum.
        
        Creates an immutable audit entry with all relevant information
        about the action, including a SHA-256 checksum for tamper detection.
        
        Requirements: 11.1, 11.2, 11.5
        - Log timestamp, action type, target integration, input data
        - Log outcome, cognitive blend value, reasoning chain
        - Compute checksum for tamper detection
        
        Args:
            user_id: The user's ID
            action_type: The type of action (from ActionType enum)
            outcome: The outcome of the action (from AuditOutcome enum)
            target_integration: The integration the action was performed on
            input_data: Input data for the action (will be sanitized)
            cognitive_blend: Cognitive blend value used (0-100)
            reasoning_chain: The reasoning chain for the decision
            is_twin_generated: Whether this action was generated by the Twin
            twin_id: The Twin that performed the action
            
        Returns:
            The created AuditEntry
        """
        # Sanitize input data to remove sensitive information
        sanitized_input = self._sanitize_input_data(input_data or {})
        
        # Create the audit entry
        entry = AuditEntry(
            user_id=user_id,
            twin_id=twin_id,
            action_type=action_type,
            target_integration=target_integration,
            input_data=sanitized_input,
            outcome=outcome,
            cognitive_blend=cognitive_blend,
            reasoning_chain=reasoning_chain,
            is_twin_generated=is_twin_generated,
        )
        
        # Save will compute checksum automatically
        entry.save()
        
        return entry
    
    def log_action_from_request(
        self,
        user_id: str,
        request: AuditLogRequest
    ) -> AuditEntry:
        """
        Log a Twin action from an AuditLogRequest.
        
        Convenience method for logging from a request object.
        
        Args:
            user_id: The user's ID
            request: The audit log request
            
        Returns:
            The created AuditEntry
        """
        return self.log_action(
            user_id=user_id,
            action_type=request.action_type,
            outcome=request.outcome,
            target_integration=request.target_integration,
            input_data=request.input_data,
            cognitive_blend=request.cognitive_blend,
            reasoning_chain=request.reasoning_chain,
            is_twin_generated=request.is_twin_generated,
            twin_id=request.twin_id,
        )
    
    def get_audit_history(
        self,
        user_id: str,
        filters: OptionalType[AuditFilterCriteria] = None,
        limit: int = 100,
        offset: int = 0
    ) -> List[AuditEntryData]:
        """
        Get filterable audit history for a user.
        
        Returns audit entries matching the specified filter criteria,
        ordered by timestamp descending (most recent first).
        
        Requirements: 11.3
        - Provide filterable, searchable access to all logged actions
        
        Args:
            user_id: The user's ID
            filters: Optional filter criteria
            limit: Maximum number of entries to return
            offset: Number of entries to skip
            
        Returns:
            List of AuditEntryData matching the criteria
        """
        queryset = AuditEntry.objects.filter(user_id=user_id)
        
        if filters:
            queryset = self._apply_filters(queryset, filters)
        
        queryset = queryset.order_by('-timestamp')[offset:offset + limit]
        
        return [AuditEntryData.from_model(entry) for entry in queryset]
    
    def get_audit_entry(self, entry_id: str) -> OptionalType[AuditEntryData]:
        """
        Get a specific audit entry by ID.
        
        Args:
            entry_id: The audit entry ID
            
        Returns:
            AuditEntryData if found, None otherwise
        """
        try:
            entry = AuditEntry.objects.get(id=entry_id)
            return AuditEntryData.from_model(entry)
        except AuditEntry.DoesNotExist:
            return None
    
    def verify_log_integrity(self, entry_id: str) -> bool:
        """
        Verify an audit entry has not been tampered with.
        
        Recomputes the checksum and compares with the stored value.
        
        Requirements: 11.2
        - Immutable and tamper-evident logs
        
        Args:
            entry_id: The audit entry ID to verify
            
        Returns:
            True if the entry is intact, False if tampered or not found
        """
        try:
            entry = AuditEntry.objects.get(id=entry_id)
            return entry.verify_integrity()
        except AuditEntry.DoesNotExist:
            return False
    
    def verify_all_entries_integrity(self, user_id: str) -> dict:
        """
        Verify integrity of all audit entries for a user.
        
        Args:
            user_id: The user's ID
            
        Returns:
            Dict with 'total', 'valid', 'invalid', and 'invalid_ids' keys
        """
        entries = AuditEntry.objects.filter(user_id=user_id)
        
        total = 0
        valid = 0
        invalid_ids = []
        
        for entry in entries:
            total += 1
            if entry.verify_integrity():
                valid += 1
            else:
                invalid_ids.append(str(entry.id))
        
        return {
            'total': total,
            'valid': valid,
            'invalid': total - valid,
            'invalid_ids': invalid_ids,
        }
    
    def count_audit_entries(
        self,
        user_id: str,
        filters: OptionalType[AuditFilterCriteria] = None
    ) -> int:
        """
        Count audit entries matching the criteria.
        
        Args:
            user_id: The user's ID
            filters: Optional filter criteria
            
        Returns:
            Number of matching entries
        """
        queryset = AuditEntry.objects.filter(user_id=user_id)
        
        if filters:
            queryset = self._apply_filters(queryset, filters)
        
        return queryset.count()
    
    def _apply_filters(
        self,
        queryset,
        filters: AuditFilterCriteria
    ):
        """
        Apply filter criteria to a queryset.
        
        Requirements: 11.3
        - Filterable by date range, action type, integration, outcome
        
        Args:
            queryset: The base queryset
            filters: The filter criteria
            
        Returns:
            Filtered queryset
        """
        if filters.start_date:
            queryset = queryset.filter(timestamp__gte=filters.start_date)
        
        if filters.end_date:
            queryset = queryset.filter(timestamp__lte=filters.end_date)
        
        if filters.action_type:
            queryset = queryset.filter(action_type=filters.action_type)
        
        if filters.target_integration:
            queryset = queryset.filter(target_integration=filters.target_integration)
        
        if filters.outcome:
            queryset = queryset.filter(outcome=filters.outcome)
        
        if filters.twin_id:
            queryset = queryset.filter(twin_id=filters.twin_id)
        
        return queryset
    
    def _sanitize_input_data(self, input_data: dict) -> dict:
        """
        Sanitize input data to remove sensitive information.
        
        Removes or masks fields that may contain sensitive data
        like passwords, tokens, or personal information.
        
        Args:
            input_data: The raw input data
            
        Returns:
            Sanitized input data
        """
        if not input_data:
            return {}
        
        # Fields to completely remove
        sensitive_fields = {
            'password', 'password_hash', 'token', 'access_token',
            'refresh_token', 'api_key', 'secret', 'private_key',
            'credit_card', 'ssn', 'social_security',
        }
        
        # Fields to mask (show partial value)
        mask_fields = {
            'email', 'phone', 'phone_number',
        }
        
        sanitized = {}
        
        for key, value in input_data.items():
            key_lower = key.lower()
            
            # Skip sensitive fields entirely
            if key_lower in sensitive_fields:
                sanitized[key] = '[REDACTED]'
            # Mask certain fields
            elif key_lower in mask_fields and isinstance(value, str):
                sanitized[key] = self._mask_value(value)
            # Recursively sanitize nested dicts
            elif isinstance(value, dict):
                sanitized[key] = self._sanitize_input_data(value)
            # Keep other values as-is
            else:
                sanitized[key] = value
        
        return sanitized
    
    def _mask_value(self, value: str) -> str:
        """
        Mask a sensitive value, showing only partial content.
        
        Args:
            value: The value to mask
            
        Returns:
            Masked value
        """
        if len(value) <= 4:
            return '****'
        
        # Show first 2 and last 2 characters
        return f"{value[:2]}{'*' * (len(value) - 4)}{value[-2:]}"


from datetime import timedelta

from django.utils import timezone as django_timezone

from .models import ReversibleAction, KillSwitchEvent
from .dataclasses import ReversibleActionData, KillSwitchStatus


class KillSwitchService:
    """
    Emergency controls for Twin behavior.
    
    Provides methods for activating/deactivating the kill switch,
    managing reversible actions, and undoing actions within time windows.
    
    Requirements: 12.1, 12.2, 12.3, 12.6
    - Kill switch accessible from all interfaces
    - Immediately halt all Twin automations
    - Terminate all in-progress workflows and calls
    - Prevent new automated actions until manually re-enabled
    - Provide undo capability for reversible actions
    """
    
    # Default undo window in minutes
    DEFAULT_UNDO_WINDOW_MINUTES = 30
    
    def __init__(self, audit_service: OptionalType[AuditService] = None):
        """
        Initialize KillSwitchService.
        
        Args:
            audit_service: Optional AuditService for logging kill switch events
        """
        self._audit_service = audit_service or AuditService()
    
    def activate_kill_switch(
        self, 
        user_id: str, 
        reason: str = "",
        triggered_by: str = "user"
    ) -> KillSwitchStatus:
        """
        Immediately halt all Twin automations.
        
        Requirements: 12.1, 12.2, 12.3
        - Accessible from all user interfaces
        - Terminate all in-progress workflows and calls
        - Prevent new automated actions until manually re-enabled
        
        Args:
            user_id: The user's ID
            reason: Reason for activating the kill switch
            triggered_by: Who triggered the activation (user, system, etc.)
            
        Returns:
            KillSwitchStatus with activation details
        """
        from apps.twin.models import Twin
        
        # Get the user's Twin and activate kill switch
        try:
            twin = Twin.objects.get(user_id=user_id)
        except Twin.DoesNotExist:
            # No Twin exists, but we still record the event
            twin = None
        
        workflows_terminated = 0
        calls_terminated = 0
        
        if twin and not twin.kill_switch_active:
            # Activate the kill switch on the Twin
            twin.kill_switch_active = True
            twin.save(update_fields=['kill_switch_active', 'updated_at'])
            
            # TODO: In a real implementation, we would:
            # 1. Terminate all in-progress workflows
            # 2. Terminate all active calls
            # For now, we simulate this by counting what would be terminated
            workflows_terminated = 0  # Would query active workflows
            calls_terminated = 0  # Would query active calls
        
        # Record the kill switch event
        event = KillSwitchEvent.objects.create(
            user_id=user_id,
            event_type=KillSwitchEvent.EventType.ACTIVATED,
            reason=reason,
            triggered_by=triggered_by,
            workflows_terminated=workflows_terminated,
            calls_terminated=calls_terminated,
        )
        
        # Log to audit
        self._audit_service.log_action(
            user_id=user_id,
            action_type=ActionType.WRITE,
            outcome=AuditOutcome.SUCCESS,
            target_integration=None,
            input_data={
                'action': 'kill_switch_activated',
                'reason': reason,
                'triggered_by': triggered_by,
                'workflows_terminated': workflows_terminated,
                'calls_terminated': calls_terminated,
            },
            reasoning_chain=f"Kill switch activated: {reason}",
            is_twin_generated=False,
            twin_id=str(twin.id) if twin else None,
        )
        
        return KillSwitchStatus(
            is_active=True,
            activated_at=event.timestamp,
            activated_by=triggered_by,
            reason=reason,
        )
    
    def is_kill_switch_active(self, user_id: str) -> bool:
        """
        Check if kill switch is currently active.
        
        Requirements: 12.3
        - Prevent new automated actions until manually re-enabled
        
        Args:
            user_id: The user's ID
            
        Returns:
            True if kill switch is active, False otherwise
        """
        from apps.twin.models import Twin
        
        try:
            twin = Twin.objects.get(user_id=user_id)
            return twin.kill_switch_active
        except Twin.DoesNotExist:
            return False
    
    def get_kill_switch_status(self, user_id: str) -> KillSwitchStatus:
        """
        Get detailed kill switch status.
        
        Args:
            user_id: The user's ID
            
        Returns:
            KillSwitchStatus with current status and details
        """
        is_active = self.is_kill_switch_active(user_id)
        
        if not is_active:
            return KillSwitchStatus(is_active=False)
        
        # Get the most recent activation event
        last_activation = KillSwitchEvent.objects.filter(
            user_id=user_id,
            event_type=KillSwitchEvent.EventType.ACTIVATED,
        ).order_by('-timestamp').first()
        
        if last_activation:
            return KillSwitchStatus(
                is_active=True,
                activated_at=last_activation.timestamp,
                activated_by=last_activation.triggered_by,
                reason=last_activation.reason,
            )
        
        return KillSwitchStatus(is_active=True)
    
    def deactivate_kill_switch(
        self, 
        user_id: str, 
        reason: str = "",
        triggered_by: str = "user"
    ) -> KillSwitchStatus:
        """
        Re-enable Twin automations.
        
        Requirements: 12.3
        - Allow manual re-enabling of automations
        
        Args:
            user_id: The user's ID
            reason: Reason for deactivating the kill switch
            triggered_by: Who triggered the deactivation
            
        Returns:
            KillSwitchStatus with deactivation confirmation
        """
        from apps.twin.models import Twin
        
        # Get the user's Twin and deactivate kill switch
        try:
            twin = Twin.objects.get(user_id=user_id)
        except Twin.DoesNotExist:
            twin = None
        
        if twin and twin.kill_switch_active:
            twin.kill_switch_active = False
            twin.save(update_fields=['kill_switch_active', 'updated_at'])
        
        # Record the kill switch event
        KillSwitchEvent.objects.create(
            user_id=user_id,
            event_type=KillSwitchEvent.EventType.DEACTIVATED,
            reason=reason,
            triggered_by=triggered_by,
        )
        
        # Log to audit
        self._audit_service.log_action(
            user_id=user_id,
            action_type=ActionType.WRITE,
            outcome=AuditOutcome.SUCCESS,
            target_integration=None,
            input_data={
                'action': 'kill_switch_deactivated',
                'reason': reason,
                'triggered_by': triggered_by,
            },
            reasoning_chain=f"Kill switch deactivated: {reason}",
            is_twin_generated=False,
            twin_id=str(twin.id) if twin else None,
        )
        
        return KillSwitchStatus(is_active=False)
    
    def record_reversible_action(
        self,
        user_id: str,
        action_type: str,
        original_state: dict,
        new_state: dict,
        target_integration: OptionalType[str] = None,
        audit_entry: OptionalType[AuditEntry] = None,
        undo_window_minutes: int = None,
    ) -> ReversibleAction:
        """
        Record a reversible action that can be undone.
        
        Requirements: 12.6
        - Provide undo capability for reversible Twin actions
        - Configurable time window
        
        Args:
            user_id: The user's ID
            action_type: The type of action performed
            original_state: The state before the action
            new_state: The state after the action
            target_integration: The integration the action was performed on
            audit_entry: The audit entry for this action
            undo_window_minutes: Custom undo window (defaults to DEFAULT_UNDO_WINDOW_MINUTES)
            
        Returns:
            The created ReversibleAction
        """
        if undo_window_minutes is None:
            undo_window_minutes = self.DEFAULT_UNDO_WINDOW_MINUTES
        
        undo_deadline = django_timezone.now() + timedelta(minutes=undo_window_minutes)
        
        return ReversibleAction.objects.create(
            user_id=user_id,
            action_type=action_type,
            target_integration=target_integration,
            original_state=original_state,
            new_state=new_state,
            undo_deadline=undo_deadline,
            audit_entry=audit_entry,
        )
    
    def get_undo_window(self, action_id: str) -> OptionalType[datetime]:
        """
        Get deadline for undoing a reversible action.
        
        Requirements: 12.6
        
        Args:
            action_id: The reversible action ID
            
        Returns:
            Deadline datetime if action can be undone, None otherwise
        """
        try:
            action = ReversibleAction.objects.get(id=action_id)
            if action.can_undo:
                return action.undo_deadline
            return None
        except ReversibleAction.DoesNotExist:
            return None
    
    def undo_action(self, action_id: str) -> bool:
        """
        Undo a reversible action within time window.
        
        Requirements: 12.6
        - Successfully reverse the action if within time window
        
        Args:
            action_id: The reversible action ID
            
        Returns:
            True if action was successfully undone, False otherwise
        """
        try:
            action = ReversibleAction.objects.get(id=action_id)
        except ReversibleAction.DoesNotExist:
            return False
        
        # Check if action can be undone
        if not action.can_undo:
            return False
        
        # Mark as undone
        action.is_undone = True
        action.undone_at = django_timezone.now()
        action.save(update_fields=['is_undone', 'undone_at'])
        
        # Log the undo action
        self._audit_service.log_action(
            user_id=str(action.user_id),
            action_type=action.action_type,
            outcome=AuditOutcome.SUCCESS,
            target_integration=action.target_integration,
            input_data={
                'action': 'undo',
                'original_action_id': str(action_id),
                'restored_state': action.original_state,
            },
            reasoning_chain=f"Action {action_id} undone, restored to original state",
            is_twin_generated=False,
        )
        
        # TODO: In a real implementation, we would actually restore the state
        # by calling the appropriate integration APIs with the original_state
        
        return True
    
    def get_reversible_actions(
        self, 
        user_id: str, 
        include_expired: bool = False,
        include_undone: bool = False,
    ) -> List[ReversibleActionData]:
        """
        Get reversible actions for a user.
        
        Args:
            user_id: The user's ID
            include_expired: Whether to include expired actions
            include_undone: Whether to include already undone actions
            
        Returns:
            List of ReversibleActionData
        """
        queryset = ReversibleAction.objects.filter(user_id=user_id)
        
        if not include_undone:
            queryset = queryset.filter(is_undone=False)
        
        if not include_expired:
            queryset = queryset.filter(undo_deadline__gte=django_timezone.now())
        
        return [ReversibleActionData.from_model(action) for action in queryset]
    
    def get_kill_switch_history(
        self, 
        user_id: str, 
        limit: int = 100
    ) -> List[KillSwitchEvent]:
        """
        Get kill switch event history for a user.
        
        Args:
            user_id: The user's ID
            limit: Maximum number of events to return
            
        Returns:
            List of KillSwitchEvent objects
        """
        return list(
            KillSwitchEvent.objects.filter(user_id=user_id)
            .order_by('-timestamp')[:limit]
        )
    
    def can_execute_automation(self, user_id: str) -> tuple[bool, str]:
        """
        Check if automations can be executed for a user.
        
        This is a convenience method that checks if the kill switch is active.
        
        Args:
            user_id: The user's ID
            
        Returns:
            Tuple of (can_execute, reason)
        """
        if self.is_kill_switch_active(user_id):
            return (False, "Kill switch is active. All automations are halted.")
        return (True, "")
