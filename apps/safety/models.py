"""
Safety models for NeuroTwin platform.

Defines PermissionScope model with integration, action_type, and is_granted fields.
Defines AuditEntry model for immutable, tamper-evident audit logging.
Requirements: 10.1, 11.1, 11.2
"""

import uuid
import hashlib
import json
from datetime import datetime, timedelta
from typing import Optional

from django.db import models
from django.conf import settings
from django.utils import timezone


class ActionType(models.TextChoices):
    """
    Action type enum for permission scopes.
    
    Requirements: 10.1, 10.3, 10.4, 10.5
    - READ: Read data from integration
    - WRITE: Write/modify data in integration
    - SEND: Send messages/communications
    - DELETE: Delete data from integration
    - FINANCIAL: Financial transactions (high-risk)
    - LEGAL: Legal actions (high-risk)
    - CALL: Voice/phone calls
    """
    
    READ = 'read', 'Read'
    WRITE = 'write', 'Write'
    SEND = 'send', 'Send'
    DELETE = 'delete', 'Delete'
    FINANCIAL = 'financial', 'Financial'
    LEGAL = 'legal', 'Legal'
    CALL = 'call', 'Call'


class IntegrationType(models.TextChoices):
    """
    Integration type enum for permission scopes.
    
    Requirements: 7.1
    """
    
    WHATSAPP = 'whatsapp', 'WhatsApp'
    TELEGRAM = 'telegram', 'Telegram'
    SLACK = 'slack', 'Slack'
    GMAIL = 'gmail', 'Gmail'
    OUTLOOK = 'outlook', 'Outlook'
    GOOGLE_CALENDAR = 'google_calendar', 'Google Calendar'
    GOOGLE_DOCS = 'google_docs', 'Google Docs'
    MICROSOFT_OFFICE = 'microsoft_office', 'Microsoft Office'
    ZOOM = 'zoom', 'Zoom'
    GOOGLE_MEET = 'google_meet', 'Google Meet'
    CRM = 'crm', 'CRM'
    VOICE = 'voice', 'Voice Twin'



class PermissionScope(models.Model):
    """
    Permission scope model for controlling Twin actions.
    
    Defines what actions the Twin can perform on each integration.
    
    Requirements: 10.1, 10.2, 10.6, 10.7
    - Define scopes for each integration and action type
    - Verify actions fall within granted permission scopes
    - Request user approval for out-of-scope actions
    - Allow users to modify permission scopes at any time
    """
    
    id = models.UUIDField(
        primary_key=True,
        default=uuid.uuid4,
        editable=False
    )
    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name='permission_scopes'
    )
    integration = models.CharField(
        max_length=50,
        choices=IntegrationType.choices,
        db_index=True,
        help_text='The integration this permission applies to'
    )
    action_type = models.CharField(
        max_length=20,
        choices=ActionType.choices,
        db_index=True,
        help_text='The type of action this permission controls'
    )
    is_granted = models.BooleanField(
        default=False,
        help_text='Whether this permission is granted'
    )
    requires_approval = models.BooleanField(
        default=True,
        help_text='Whether per-action approval is needed even when granted'
    )
    
    # Metadata
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        db_table = 'permission_scopes'
        verbose_name = 'permission scope'
        verbose_name_plural = 'permission scopes'
        unique_together = [['user', 'integration', 'action_type']]
        indexes = [
            models.Index(fields=['user', 'integration']),
            models.Index(fields=['user', 'action_type']),
            models.Index(fields=['integration', 'action_type']),
        ]
    
    def __str__(self) -> str:
        status = 'granted' if self.is_granted else 'denied'
        approval = ' (requires approval)' if self.requires_approval else ''
        return f"{self.user.email}: {self.integration}/{self.action_type} - {status}{approval}"
    
    @property
    def is_high_risk(self) -> bool:
        """
        Check if this permission scope is for a high-risk action.
        
        High-risk actions include financial, legal, and irreversible actions.
        Requirements: 10.3, 10.4, 10.5
        """
        return self.action_type in [
            ActionType.FINANCIAL,
            ActionType.LEGAL,
            ActionType.DELETE,
        ]


class PermissionHistory(models.Model):
    """
    Track permission changes for audit purposes.
    
    Requirements: 10.7 - Users can modify permissions at any time
    """
    
    id = models.UUIDField(
        primary_key=True,
        default=uuid.uuid4,
        editable=False
    )
    permission_scope = models.ForeignKey(
        PermissionScope,
        on_delete=models.CASCADE,
        related_name='history'
    )
    previous_is_granted = models.BooleanField()
    new_is_granted = models.BooleanField()
    previous_requires_approval = models.BooleanField()
    new_requires_approval = models.BooleanField()
    changed_at = models.DateTimeField(default=timezone.now)
    reason = models.CharField(
        max_length=255,
        blank=True,
        help_text='Reason for the permission change'
    )
    
    class Meta:
        db_table = 'permission_history'
        verbose_name = 'permission history'
        verbose_name_plural = 'permission histories'
        ordering = ['-changed_at']
        indexes = [
            models.Index(fields=['permission_scope', '-changed_at']),
        ]
    
    def __str__(self) -> str:
        return f"{self.permission_scope}: {self.previous_is_granted} -> {self.new_is_granted}"


class AuditOutcome(models.TextChoices):
    """
    Outcome status for audit entries.
    
    Requirements: 11.1
    """
    
    SUCCESS = 'success', 'Success'
    FAILURE = 'failure', 'Failure'
    PENDING_APPROVAL = 'pending_approval', 'Pending Approval'
    DENIED = 'denied', 'Denied'
    CANCELLED = 'cancelled', 'Cancelled'


class AuditEntry(models.Model):
    """
    Immutable, tamper-evident audit log entry for Twin actions.
    
    Every Twin action is logged with full context including timestamp,
    action type, target integration, input data, outcome, cognitive blend,
    and reasoning chain.
    
    Requirements: 11.1, 11.2, 11.5
    - Log every Twin action with full context
    - Immutable and tamper-evident via checksum
    - Log reasoning chain for transparency
    """
    
    id = models.UUIDField(
        primary_key=True,
        default=uuid.uuid4,
        editable=False
    )
    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name='audit_entries'
    )
    twin_id = models.UUIDField(
        null=True,
        blank=True,
        db_index=True,
        help_text='The Twin that performed the action'
    )
    timestamp = models.DateTimeField(
        default=timezone.now,
        db_index=True,
        help_text='When the action occurred'
    )
    action_type = models.CharField(
        max_length=20,
        choices=ActionType.choices,
        db_index=True,
        help_text='The type of action performed'
    )
    target_integration = models.CharField(
        max_length=50,
        choices=IntegrationType.choices,
        null=True,
        blank=True,
        db_index=True,
        help_text='The integration the action was performed on'
    )
    input_data = models.JSONField(
        default=dict,
        help_text='Input data for the action (sanitized)'
    )
    outcome = models.CharField(
        max_length=20,
        choices=AuditOutcome.choices,
        db_index=True,
        help_text='The outcome of the action'
    )
    cognitive_blend = models.IntegerField(
        null=True,
        blank=True,
        help_text='Cognitive blend value used (0-100)'
    )
    reasoning_chain = models.TextField(
        blank=True,
        help_text='The reasoning chain for the decision (for transparency)'
    )
    is_twin_generated = models.BooleanField(
        default=True,
        help_text='Whether this action was generated by the Twin'
    )
    checksum = models.CharField(
        max_length=64,
        editable=False,
        help_text='SHA-256 checksum for tamper detection'
    )
    
    class Meta:
        db_table = 'audit_log'
        verbose_name = 'audit entry'
        verbose_name_plural = 'audit entries'
        ordering = ['-timestamp']
        indexes = [
            models.Index(fields=['user', '-timestamp']),
            models.Index(fields=['user', 'action_type']),
            models.Index(fields=['user', 'target_integration']),
            models.Index(fields=['user', 'outcome']),
            models.Index(fields=['twin_id', '-timestamp']),
        ]
    
    def __str__(self) -> str:
        return f"{self.user.email}: {self.action_type} on {self.target_integration} - {self.outcome}"
    
    def save(self, *args, **kwargs):
        """
        Override save to compute checksum before saving.
        
        The checksum is computed from all audit-relevant fields to ensure
        tamper detection. Once saved, the entry should not be modified.
        
        Requirements: 11.2 - Immutable and tamper-evident
        """
        # Only compute checksum on initial save (not updates)
        if not self.checksum:
            self.checksum = self.compute_checksum()
        super().save(*args, **kwargs)
    
    def compute_checksum(self) -> str:
        """
        Compute SHA-256 checksum of audit-relevant fields.
        
        The checksum includes all fields that should be immutable:
        - id, user_id, twin_id, timestamp
        - action_type, target_integration, input_data
        - outcome, cognitive_blend, reasoning_chain
        - is_twin_generated
        
        Requirements: 11.2 - Tamper-evident
        
        Returns:
            SHA-256 hex digest of the audit entry data
        """
        # Create a deterministic representation of the entry
        data = {
            'id': str(self.id),
            'user_id': str(self.user_id),
            'twin_id': str(self.twin_id) if self.twin_id else None,
            'timestamp': self.timestamp.isoformat() if self.timestamp else None,
            'action_type': self.action_type,
            'target_integration': self.target_integration,
            'input_data': self.input_data,
            'outcome': self.outcome,
            'cognitive_blend': self.cognitive_blend,
            'reasoning_chain': self.reasoning_chain,
            'is_twin_generated': self.is_twin_generated,
        }
        
        # Serialize to JSON with sorted keys for deterministic output
        json_str = json.dumps(data, sort_keys=True, default=str)
        
        # Compute SHA-256 hash
        return hashlib.sha256(json_str.encode('utf-8')).hexdigest()
    
    def verify_integrity(self) -> bool:
        """
        Verify the audit entry has not been tampered with.
        
        Recomputes the checksum and compares with stored value.
        
        Requirements: 11.2 - Tamper-evident
        
        Returns:
            True if the entry is intact, False if tampered
        """
        return self.checksum == self.compute_checksum()


class ReversibleAction(models.Model):
    """
    Tracks reversible actions that can be undone within a time window.
    
    Requirements: 12.6
    - Provide undo capability for reversible Twin actions
    - Configurable time window for undo operations
    """
    
    id = models.UUIDField(
        primary_key=True,
        default=uuid.uuid4,
        editable=False
    )
    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name='reversible_actions'
    )
    audit_entry = models.OneToOneField(
        AuditEntry,
        on_delete=models.CASCADE,
        null=True,
        blank=True,
        related_name='reversible_action',
        help_text='The audit entry for this action'
    )
    action_type = models.CharField(
        max_length=20,
        choices=ActionType.choices,
        db_index=True,
        help_text='The type of action performed'
    )
    target_integration = models.CharField(
        max_length=50,
        choices=IntegrationType.choices,
        null=True,
        blank=True,
        db_index=True,
        help_text='The integration the action was performed on'
    )
    original_state = models.JSONField(
        default=dict,
        help_text='The state before the action (for rollback)'
    )
    new_state = models.JSONField(
        default=dict,
        help_text='The state after the action'
    )
    undo_deadline = models.DateTimeField(
        db_index=True,
        help_text='Deadline for undoing the action'
    )
    is_undone = models.BooleanField(
        default=False,
        help_text='Whether the action has been undone'
    )
    undone_at = models.DateTimeField(
        null=True,
        blank=True,
        help_text='When the action was undone'
    )
    
    # Timestamps
    created_at = models.DateTimeField(auto_now_add=True)
    
    class Meta:
        db_table = 'reversible_actions'
        verbose_name = 'reversible action'
        verbose_name_plural = 'reversible actions'
        ordering = ['-created_at']
        indexes = [
            models.Index(fields=['user', '-created_at']),
            models.Index(fields=['user', 'undo_deadline']),
            models.Index(fields=['is_undone']),
        ]
    
    def __str__(self) -> str:
        status = 'undone' if self.is_undone else 'active'
        return f"{self.user.email}: {self.action_type} on {self.target_integration} ({status})"
    
    @property
    def can_undo(self) -> bool:
        """
        Check if this action can still be undone.
        
        Returns:
            True if the action can be undone (not already undone and within deadline)
        """
        if self.is_undone:
            return False
        return timezone.now() <= self.undo_deadline
    
    @property
    def time_remaining(self) -> Optional[timedelta]:
        """
        Get the time remaining to undo this action.
        
        Returns:
            timedelta if action can be undone, None otherwise
        """
        if self.is_undone:
            return None
        remaining = self.undo_deadline - timezone.now()
        return remaining if remaining.total_seconds() > 0 else None


class KillSwitchEvent(models.Model):
    """
    Tracks kill switch activation and deactivation events.
    
    Requirements: 12.1, 12.2, 12.3
    """
    
    class EventType(models.TextChoices):
        ACTIVATED = 'activated', 'Activated'
        DEACTIVATED = 'deactivated', 'Deactivated'
    
    id = models.UUIDField(
        primary_key=True,
        default=uuid.uuid4,
        editable=False
    )
    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name='kill_switch_events'
    )
    event_type = models.CharField(
        max_length=20,
        choices=EventType.choices,
        help_text='Type of kill switch event'
    )
    reason = models.CharField(
        max_length=255,
        blank=True,
        help_text='Reason for the event'
    )
    triggered_by = models.CharField(
        max_length=50,
        default='user',
        help_text='Who triggered the event (user, system, etc.)'
    )
    workflows_terminated = models.IntegerField(
        default=0,
        help_text='Number of workflows terminated (for activation events)'
    )
    calls_terminated = models.IntegerField(
        default=0,
        help_text='Number of calls terminated (for activation events)'
    )
    timestamp = models.DateTimeField(
        default=timezone.now,
        db_index=True
    )
    
    class Meta:
        db_table = 'kill_switch_events'
        verbose_name = 'kill switch event'
        verbose_name_plural = 'kill switch events'
        ordering = ['-timestamp']
        indexes = [
            models.Index(fields=['user', '-timestamp']),
            models.Index(fields=['event_type']),
        ]
    
    def __str__(self) -> str:
        return f"{self.user.email}: {self.event_type} at {self.timestamp}"
