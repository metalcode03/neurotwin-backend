"""
Automation models for NeuroTwin platform.

Defines Integration model with encrypted tokens and IntegrationType enum.
Defines Workflow model with trigger and steps for automated workflows.
Requirements: 7.1, 8.1
"""

import uuid
from datetime import datetime
from typing import Optional, List

from django.db import models
from django.conf import settings
from django.utils import timezone
from cryptography.fernet import Fernet
import base64
import os


class IntegrationType(models.TextChoices):
    """
    Integration type enum for supported integrations.
    
    Requirements: 7.1
    - Support integrations with: WhatsApp, Telegram, Slack, Gmail, Outlook,
      Google Calendar, Google Docs, Microsoft Office, Zoom, Google Meet, CRM tools
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


class TokenEncryption:
    """
    Utility class for encrypting and decrypting OAuth tokens.
    
    Uses Fernet symmetric encryption for secure token storage.
    Requirements: 7.2 - Store tokens securely
    """
    
    _fernet: Optional[Fernet] = None
    
    @classmethod
    def _get_fernet(cls) -> Fernet:
        """Get or create Fernet instance with encryption key."""
        if cls._fernet is None:
            # Get encryption key from settings or environment
            key = getattr(settings, 'TOKEN_ENCRYPTION_KEY', None)
            if key is None:
                key = os.environ.get('TOKEN_ENCRYPTION_KEY')
            
            if key is None:
                # Generate a key for development (should be set in production)
                key = Fernet.generate_key()
            elif isinstance(key, str):
                # Ensure key is bytes
                key = key.encode() if len(key) == 44 else base64.urlsafe_b64encode(key.ljust(32)[:32].encode())
            
            cls._fernet = Fernet(key)
        
        return cls._fernet
    
    @classmethod
    def encrypt(cls, plaintext: str) -> bytes:
        """Encrypt a plaintext string."""
        if not plaintext:
            return b''
        return cls._get_fernet().encrypt(plaintext.encode())
    
    @classmethod
    def decrypt(cls, ciphertext: bytes) -> str:
        """Decrypt ciphertext to plaintext string."""
        if not ciphertext:
            return ''
        return cls._get_fernet().decrypt(ciphertext).decode()


class Integration(models.Model):
    """
    Integration model for connected applications.
    
    Stores OAuth tokens securely with encryption and manages
    integration configuration including scopes, steering rules,
    and permissions.
    
    Requirements: 7.1, 7.2, 7.3, 7.4
    - Support multiple integration types
    - Store tokens securely (encrypted)
    - Configurable steering rules
    - Modifiable permission settings
    """
    
    id = models.UUIDField(
        primary_key=True,
        default=uuid.uuid4,
        editable=False
    )
    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name='integrations'
    )
    type = models.CharField(
        max_length=50,
        choices=IntegrationType.choices,
        db_index=True,
        help_text='The type of integration'
    )

    # Encrypted OAuth tokens
    oauth_token_encrypted = models.BinaryField(
        null=True,
        blank=True,
        help_text='Encrypted OAuth access token'
    )
    refresh_token_encrypted = models.BinaryField(
        null=True,
        blank=True,
        help_text='Encrypted OAuth refresh token'
    )
    
    # OAuth configuration
    scopes = models.JSONField(
        default=list,
        help_text='OAuth scopes granted for this integration'
    )
    
    # Integration configuration
    steering_rules = models.JSONField(
        default=dict,
        help_text='Rules defining allowed actions for this integration'
    )
    permissions = models.JSONField(
        default=dict,
        help_text='Permission settings for this integration'
    )
    
    # Token expiration
    token_expires_at = models.DateTimeField(
        null=True,
        blank=True,
        db_index=True,
        help_text='When the OAuth token expires'
    )
    
    # Status
    is_active = models.BooleanField(
        default=True,
        help_text='Whether this integration is active'
    )
    
    # Timestamps
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        db_table = 'integrations'
        verbose_name = 'integration'
        verbose_name_plural = 'integrations'
        unique_together = [['user', 'type']]
        indexes = [
            models.Index(fields=['user', 'type']),
            models.Index(fields=['user', 'is_active']),
            models.Index(fields=['type', 'is_active']),
            models.Index(fields=['token_expires_at']),
        ]
    
    def __str__(self) -> str:
        status = 'active' if self.is_active else 'inactive'
        return f"{self.user.email}: {self.get_type_display()} ({status})"
    
    @property
    def oauth_token(self) -> str:
        """Get decrypted OAuth access token."""
        if self.oauth_token_encrypted:
            return TokenEncryption.decrypt(bytes(self.oauth_token_encrypted))
        return ''
    
    @oauth_token.setter
    def oauth_token(self, value: str):
        """Set and encrypt OAuth access token."""
        if value:
            self.oauth_token_encrypted = TokenEncryption.encrypt(value)
        else:
            self.oauth_token_encrypted = None
    
    @property
    def refresh_token(self) -> str:
        """Get decrypted OAuth refresh token."""
        if self.refresh_token_encrypted:
            return TokenEncryption.decrypt(bytes(self.refresh_token_encrypted))
        return ''
    
    @refresh_token.setter
    def refresh_token(self, value: str):
        """Set and encrypt OAuth refresh token."""
        if value:
            self.refresh_token_encrypted = TokenEncryption.encrypt(value)
        else:
            self.refresh_token_encrypted = None
    
    @property
    def is_token_expired(self) -> bool:
        """Check if the OAuth token has expired."""
        if self.token_expires_at is None:
            return False
        return timezone.now() >= self.token_expires_at
    
    @property
    def has_refresh_token(self) -> bool:
        """Check if a refresh token is available."""
        return bool(self.refresh_token_encrypted)
    
    def get_scopes_list(self) -> List[str]:
        """Get scopes as a list."""
        if isinstance(self.scopes, list):
            return self.scopes
        return []
    
    def has_scope(self, scope: str) -> bool:
        """Check if the integration has a specific scope."""
        return scope in self.get_scopes_list()
    
    def get_permission(self, permission_name: str) -> bool:
        """Get a specific permission value."""
        if isinstance(self.permissions, dict):
            return self.permissions.get(permission_name, False)
        return False
    
    def set_permission(self, permission_name: str, value: bool):
        """Set a specific permission value."""
        if not isinstance(self.permissions, dict):
            self.permissions = {}
        self.permissions[permission_name] = value
    
    def get_steering_rule(self, rule_name: str) -> Optional[dict]:
        """Get a specific steering rule."""
        if isinstance(self.steering_rules, dict):
            return self.steering_rules.get(rule_name)
        return None
    
    def set_steering_rule(self, rule_name: str, rule_config: dict):
        """Set a specific steering rule."""
        if not isinstance(self.steering_rules, dict):
            self.steering_rules = {}
        self.steering_rules[rule_name] = rule_config


class WorkflowStatus(models.TextChoices):
    """
    Status of a workflow execution.
    
    Requirements: 8.3, 8.4
    """
    
    PENDING = 'pending', 'Pending'
    RUNNING = 'running', 'Running'
    COMPLETED = 'completed', 'Completed'
    FAILED = 'failed', 'Failed'
    AWAITING_CONFIRMATION = 'awaiting_confirmation', 'Awaiting Confirmation'
    CANCELLED = 'cancelled', 'Cancelled'


class Workflow(models.Model):
    """
    Workflow model for automated task execution.
    
    Stores workflow configuration including trigger conditions and
    execution steps across connected integrations.
    
    Requirements: 8.1
    - Workflows can be triggered and executed
    - Each workflow has steps that execute on integrations
    """
    
    id = models.UUIDField(
        primary_key=True,
        default=uuid.uuid4,
        editable=False
    )
    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name='workflows'
    )
    name = models.CharField(
        max_length=255,
        help_text='Human-readable name for the workflow'
    )
    
    # Trigger configuration (e.g., schedule, event, manual)
    trigger_config = models.JSONField(
        default=dict,
        help_text='Configuration for when the workflow triggers'
    )
    
    # Workflow steps as JSON array
    # Each step: {integration, action, parameters, requires_confirmation, order}
    steps = models.JSONField(
        default=list,
        help_text='List of workflow steps to execute'
    )
    
    # Status
    is_active = models.BooleanField(
        default=True,
        help_text='Whether this workflow is active'
    )
    
    # Timestamps
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        db_table = 'workflows'
        verbose_name = 'workflow'
        verbose_name_plural = 'workflows'
        indexes = [
            models.Index(fields=['user', 'is_active']),
            models.Index(fields=['user', 'created_at']),
        ]
    
    def __str__(self) -> str:
        status = 'active' if self.is_active else 'inactive'
        return f"{self.name} ({status})"
    
    def get_steps_list(self) -> List[dict]:
        """Get steps as a list of dictionaries."""
        if isinstance(self.steps, list):
            return self.steps
        return []
    
    def get_step_count(self) -> int:
        """Get the number of steps in this workflow."""
        return len(self.get_steps_list())
    
    def get_step(self, index: int) -> Optional[dict]:
        """Get a specific step by index."""
        steps = self.get_steps_list()
        if 0 <= index < len(steps):
            return steps[index]
        return None
    
    def get_integrations_used(self) -> List[str]:
        """Get list of unique integrations used in this workflow."""
        integrations = set()
        for step in self.get_steps_list():
            if 'integration' in step:
                integrations.add(step['integration'])
        return list(integrations)


class WorkflowExecution(models.Model):
    """
    Record of a workflow execution.
    
    Tracks the execution state, progress, and results of a workflow run.
    
    Requirements: 8.3, 8.4
    - Execute workflows asynchronously
    - Log errors and notify user on failure
    """
    
    id = models.UUIDField(
        primary_key=True,
        default=uuid.uuid4,
        editable=False
    )
    workflow = models.ForeignKey(
        Workflow,
        on_delete=models.CASCADE,
        related_name='executions'
    )
    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name='workflow_executions'
    )
    
    # Execution state
    status = models.CharField(
        max_length=30,
        choices=WorkflowStatus.choices,
        default=WorkflowStatus.PENDING,
        db_index=True,
        help_text='Current status of the execution'
    )
    
    # Progress tracking
    current_step = models.IntegerField(
        default=0,
        help_text='Index of the current step being executed'
    )
    steps_completed = models.IntegerField(
        default=0,
        help_text='Number of steps completed successfully'
    )
    total_steps = models.IntegerField(
        default=0,
        help_text='Total number of steps in the workflow'
    )
    
    # Execution context
    permission_flag = models.BooleanField(
        default=False,
        help_text='Whether permission was granted for external actions'
    )
    cognitive_blend = models.IntegerField(
        default=50,
        help_text='Cognitive blend value used for this execution (0-100)'
    )
    
    # Content origin tracking
    # Requirements: 8.6 - Distinguish Twin-generated from user-authored content
    is_twin_generated = models.BooleanField(
        default=True,
        help_text='Whether this execution was initiated by the Twin'
    )
    
    # Error tracking
    error_message = models.TextField(
        blank=True,
        default='',
        help_text='Error message if execution failed'
    )
    error_step = models.IntegerField(
        null=True,
        blank=True,
        help_text='Index of the step that failed'
    )
    
    # Step results as JSON array
    step_results = models.JSONField(
        default=list,
        help_text='Results of each completed step'
    )
    
    # Timestamps
    started_at = models.DateTimeField(
        null=True,
        blank=True,
        help_text='When execution started'
    )
    completed_at = models.DateTimeField(
        null=True,
        blank=True,
        help_text='When execution completed'
    )
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        db_table = 'workflow_executions'
        verbose_name = 'workflow execution'
        verbose_name_plural = 'workflow executions'
        indexes = [
            models.Index(fields=['user', 'status']),
            models.Index(fields=['workflow', 'status']),
            models.Index(fields=['user', 'created_at']),
            models.Index(fields=['status', 'created_at']),
        ]
    
    def __str__(self) -> str:
        return f"{self.workflow.name} - {self.status} ({self.steps_completed}/{self.total_steps})"
    
    @property
    def is_complete(self) -> bool:
        """Check if execution is complete (success or failure)."""
        return self.status in [
            WorkflowStatus.COMPLETED,
            WorkflowStatus.FAILED,
            WorkflowStatus.CANCELLED,
        ]
    
    @property
    def is_running(self) -> bool:
        """Check if execution is currently running."""
        return self.status == WorkflowStatus.RUNNING
    
    @property
    def is_awaiting_confirmation(self) -> bool:
        """Check if execution is awaiting user confirmation."""
        return self.status == WorkflowStatus.AWAITING_CONFIRMATION
    
    def add_step_result(self, step_index: int, success: bool, result: dict = None):
        """Add a result for a completed step."""
        if not isinstance(self.step_results, list):
            self.step_results = []
        
        self.step_results.append({
            'step_index': step_index,
            'success': success,
            'result': result or {},
            'timestamp': timezone.now().isoformat(),
        })
