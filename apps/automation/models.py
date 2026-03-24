"""
Automation models for NeuroTwin platform.

Defines Integration model with encrypted tokens and IntegrationType enum.
Defines Workflow model with trigger and steps for automated workflows.
Requirements: 7.1, 8.1
"""

import uuid
import re
import base64
import os
from datetime import datetime
from typing import Optional, List

from django.db import models
from django.conf import settings
from django.core.exceptions import ValidationError
from django.utils import timezone

from .utils.encryption import TokenEncryption


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


class IntegrationCategory(models.TextChoices):
    """
    Categories for organizing integration types.
    
    Requirements: 13.1
    """
    COMMUNICATION = 'communication', 'Communication'
    PRODUCTIVITY = 'productivity', 'Productivity'
    CRM = 'crm', 'CRM'
    CALENDAR = 'calendar', 'Calendar'
    DOCUMENTS = 'documents', 'Documents'
    VIDEO_CONFERENCING = 'video_conferencing', 'Video Conferencing'
    OTHER = 'other', 'Other'


class IntegrationTypeModel(models.Model):
    """
    Dynamic integration type model.
    
    Replaces hardcoded IntegrationType enum to enable
    runtime addition of new integration types.
    
    Requirements: 1.1-1.7, 2.1-2.6
    """
    
    id = models.UUIDField(
        primary_key=True,
        default=uuid.uuid4,
        editable=False
    )
    
    # Type identifier (kebab-case, unique)
    type = models.CharField(
        max_length=100,
        unique=True,
        db_index=True,
        help_text='Unique identifier in kebab-case (e.g., "gmail", "slack")'
    )
    
    # Display information
    name = models.CharField(
        max_length=255,
        help_text='Human-readable name (e.g., "Gmail", "Slack")'
    )
    icon = models.FileField(
        upload_to='integration_icons/',
        help_text='SVG or PNG icon (max 500KB)',
        blank=True,
        null=True
    )
    description = models.TextField(
        help_text='Full description of the integration'
    )
    brief_description = models.CharField(
        max_length=200,
        help_text='Short description for card display'
    )
    
    # Categorization
    category = models.CharField(
        max_length=50,
        choices=IntegrationCategory.choices,
        default=IntegrationCategory.OTHER,
        db_index=True,
        help_text='Category for filtering and organization'
    )
    
    # OAuth configuration (encrypted)
    oauth_config = models.JSONField(
        default=dict,
        help_text='OAuth 2.0 configuration including client_id, '
                  'client_secret (encrypted), authorization_url, '
                  'token_url, scopes'
    )
    
    # Default permissions
    default_permissions = models.JSONField(
        default=dict,
        help_text='Default permission settings for new installations'
    )
    
    # Status
    is_active = models.BooleanField(
        default=True,
        db_index=True,
        help_text='Whether this integration type is visible in marketplace'
    )
    
    # Metadata
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    created_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='created_integration_types'
    )
    
    class Meta:
        db_table = 'integration_types'
        verbose_name = 'integration type'
        verbose_name_plural = 'integration types'
        ordering = ['name']
        indexes = [
            models.Index(fields=['is_active', 'category']),
            models.Index(fields=['is_active', 'created_at']),
        ]
    
    def __str__(self) -> str:
        return f"{self.name} ({self.type})"
    
    def clean(self):
        """Validate type identifier format."""
        if not re.match(r'^[a-z0-9]+(-[a-z0-9]+)*$', self.type):
            raise ValidationError(
                'Type must be in kebab-case format (lowercase, hyphens only)'
            )
    
    @property
    def oauth_client_id(self) -> str:
        """Get OAuth client ID."""
        return self.oauth_config.get('client_id', '')
    
    @property
    def oauth_client_secret(self) -> str:
        """Get decrypted OAuth client secret."""
        encrypted = self.oauth_config.get('client_secret_encrypted', '')
        if encrypted:
            return TokenEncryption.decrypt(base64.b64decode(encrypted))
        return ''
    
    def set_oauth_client_secret(self, secret: str):
        """Encrypt and store OAuth client secret."""
        if secret:
            encrypted = TokenEncryption.encrypt(secret)
            self.oauth_config['client_secret_encrypted'] = \
                base64.b64encode(encrypted).decode()
    
    @property
    def oauth_scopes(self) -> List[str]:
        """Get OAuth scopes as list."""
        scopes = self.oauth_config.get('scopes', [])
        if isinstance(scopes, str):
            return [s.strip() for s in scopes.split(',')]
        return scopes


class Integration(models.Model):
    """
    Integration model for connected applications.
    
    Modified to use ForeignKey to IntegrationType instead of enum.
    Stores OAuth tokens securely with encryption and manages
    integration configuration including scopes, steering rules,
    and permissions.
    
    Requirements: 5.1-5.7
    - Support multiple integration types via FK
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
    
    # Changed from CharField with choices to ForeignKey
    integration_type = models.ForeignKey(
        IntegrationTypeModel,
        on_delete=models.PROTECT,  # Prevent deletion if installed
        related_name='installations',
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
        unique_together = [['user', 'integration_type']]
        indexes = [
            models.Index(fields=['user', 'integration_type']),
            models.Index(fields=['user', 'is_active']),
            models.Index(fields=['integration_type', 'is_active']),
            models.Index(fields=['token_expires_at']),
        ]
    
    def __str__(self) -> str:
        status = 'active' if self.is_active else 'inactive'
        return f"{self.user.email}: {self.integration_type.name} ({status})"
    
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


class TriggerType(models.TextChoices):
    """Types of workflow triggers."""
    SCHEDULED = 'scheduled', 'Scheduled'
    EVENT_DRIVEN = 'event_driven', 'Event-Driven'
    MANUAL = 'manual', 'Manual'


class AutomationTemplate(models.Model):
    """
    Automation template for integration types.
    
    Defines pre-configured workflows that are instantiated
    when a user installs an integration type.
    
    Requirements: 6.1-6.7
    """
    
    id = models.UUIDField(
        primary_key=True,
        default=uuid.uuid4,
        editable=False
    )
    
    integration_type = models.ForeignKey(
        IntegrationTypeModel,
        on_delete=models.CASCADE,
        related_name='automation_templates',
        help_text='The integration type this template belongs to'
    )
    
    # Template information
    name = models.CharField(
        max_length=255,
        help_text='Template name'
    )
    description = models.TextField(
        help_text='Description of what this automation does'
    )
    
    # Trigger configuration
    trigger_type = models.CharField(
        max_length=50,
        choices=TriggerType.choices,
        help_text='Type of trigger for this automation'
    )
    trigger_config = models.JSONField(
        default=dict,
        help_text='Trigger configuration (schedule, event filters, etc.)'
    )
    
    # Workflow steps
    steps = models.JSONField(
        default=list,
        help_text='Array of workflow steps with action_type, '
                  'integration_type_id, parameters'
    )
    
    # Default state
    is_enabled_by_default = models.BooleanField(
        default=False,
        help_text='Whether workflows created from this template '
                  'should be enabled by default'
    )
    
    # Status
    is_active = models.BooleanField(
        default=True,
        help_text='Whether this template is active'
    )
    
    # Metadata
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    created_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='created_automation_templates'
    )
    
    class Meta:
        db_table = 'automation_templates'
        verbose_name = 'automation template'
        verbose_name_plural = 'automation templates'
        ordering = ['integration_type', 'name']
        indexes = [
            models.Index(fields=['integration_type', 'is_active']),
        ]
    
    def __str__(self) -> str:
        return f"{self.integration_type.name}: {self.name}"
    
    def get_steps_list(self) -> List[dict]:
        """Get steps as list."""
        if isinstance(self.steps, list):
            return self.steps
        return []
    
    def validate_steps(self) -> tuple[bool, List[str]]:
        """Validate step structure."""
        errors = []
        steps = self.get_steps_list()
        
        if not steps:
            errors.append('At least one step is required')
        
        for i, step in enumerate(steps):
            if 'action_type' not in step:
                errors.append(f'Step {i}: missing action_type')
            if 'integration_type_id' not in step:
                errors.append(f'Step {i}: missing integration_type_id')
        
        return len(errors) == 0, errors


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


class InstallationStatus(models.TextChoices):
    """Status of an installation session."""
    DOWNLOADING = 'downloading', 'Downloading'
    OAUTH_SETUP = 'oauth_setup', 'OAuth Setup'
    COMPLETED = 'completed', 'Completed'
    FAILED = 'failed', 'Failed'


class InstallationSession(models.Model):
    """
    Installation session for tracking progress.
    
    Manages the two-phase installation process with
    real-time progress updates.
    
    Requirements: 4.1-4.11, 11.1-11.7
    """
    
    id = models.UUIDField(
        primary_key=True,
        default=uuid.uuid4,
        editable=False
    )
    
    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name='installation_sessions'
    )
    integration_type = models.ForeignKey(
        IntegrationTypeModel,
        on_delete=models.CASCADE,
        related_name='installation_sessions'
    )
    
    # Status tracking
    status = models.CharField(
        max_length=50,
        choices=InstallationStatus.choices,
        default=InstallationStatus.DOWNLOADING,
        db_index=True,
        help_text='Current installation phase'
    )
    progress = models.IntegerField(
        default=0,
        help_text='Progress percentage (0-100)'
    )
    
    # OAuth state for CSRF protection
    oauth_state = models.CharField(
        max_length=255,
        unique=True,
        db_index=True,
        help_text='OAuth state parameter for validation'
    )
    
    # Error tracking
    error_message = models.TextField(
        blank=True,
        default='',
        help_text='Error message if installation failed'
    )
    retry_count = models.IntegerField(
        default=0,
        help_text='Number of retry attempts'
    )
    
    # Timestamps
    created_at = models.DateTimeField(auto_now_add=True, db_index=True)
    updated_at = models.DateTimeField(auto_now=True)
    completed_at = models.DateTimeField(
        null=True,
        blank=True,
        help_text='When installation completed or failed'
    )
    
    class Meta:
        db_table = 'installation_sessions'
        verbose_name = 'installation session'
        verbose_name_plural = 'installation sessions'
        ordering = ['-created_at']
        indexes = [
            models.Index(fields=['user', 'status']),
            models.Index(fields=['created_at']),
        ]
    
    def __str__(self) -> str:
        return f"{self.user.email}: {self.integration_type.name} - {self.status}"
    
    @property
    def is_complete(self) -> bool:
        """Check if session is complete."""
        return self.status in [
            InstallationStatus.COMPLETED,
            InstallationStatus.FAILED
        ]
    
    @property
    def is_expired(self) -> bool:
        """Check if session is older than 24 hours."""
        from datetime import timedelta
        return timezone.now() - self.created_at > timedelta(hours=24)
    
    def increment_retry(self):
        """Increment retry counter."""
        self.retry_count += 1
        self.save(update_fields=['retry_count', 'updated_at'])
    
    @property
    def can_retry(self) -> bool:
        """Check if retry is allowed."""
        return self.retry_count < 3


class Workflow(models.Model):
    """
    Workflow model for automated task execution.
    
    Enhanced to track template origin and Twin modifications.
    Stores workflow configuration including trigger conditions and
    execution steps across connected integrations.
    
    Requirements: 7.1-7.9, 8.1-8.7
    - Workflows can be triggered and executed
    - Each workflow has steps that execute on integrations
    - Track template origin and custom workflows
    - Track Twin modifications
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
    
    # Template tracking (new)
    automation_template = models.ForeignKey(
        'AutomationTemplate',
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='workflow_instances',
        help_text='Template this workflow was created from (if any)'
    )
    is_custom = models.BooleanField(
        default=False,
        help_text='Whether this is a custom user-created workflow'
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
    
    # Twin modification tracking (new)
    last_modified_by_twin = models.BooleanField(
        default=False,
        help_text='Whether last modification was by Twin'
    )
    twin_modification_count = models.IntegerField(
        default=0,
        help_text='Number of times Twin has modified this workflow'
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
            models.Index(fields=['automation_template']),
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
    
    def get_integration_types_used(self) -> List[str]:
        """
        Get list of integration type IDs used in workflow steps.
        
        Returns:
            List of integration_type_id values from steps
        """
        integration_types = set()
        for step in self.get_steps_list():
            if 'integration_type_id' in step:
                integration_types.add(step['integration_type_id'])
        return list(integration_types)


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


class WorkflowChangeHistory(models.Model):
    """
    Change history for workflow modifications.
    
    Tracks all changes to workflows with author attribution
    and reasoning for Twin modifications.
    
    Requirements: 8.2, 8.6, 8.7
    """
    
    id = models.UUIDField(
        primary_key=True,
        default=uuid.uuid4,
        editable=False
    )
    
    workflow = models.ForeignKey(
        Workflow,
        on_delete=models.CASCADE,
        related_name='change_history'
    )
    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name='workflow_changes'
    )
    
    # Change tracking
    modified_by_twin = models.BooleanField(
        default=False,
        help_text='Whether this change was made by Twin'
    )
    cognitive_blend_value = models.IntegerField(
        null=True,
        blank=True,
        help_text='Cognitive blend value at time of Twin modification'
    )
    
    # Change details
    changes_made = models.JSONField(
        default=dict,
        help_text='Dictionary of field changes (before/after)'
    )
    reasoning = models.TextField(
        blank=True,
        default='',
        help_text='Explanation for the change (especially for Twin mods)'
    )
    
    # Permission tracking
    permission_flag = models.BooleanField(
        default=False,
        help_text='Whether permission was granted for this change'
    )
    required_confirmation = models.BooleanField(
        default=False,
        help_text='Whether user confirmation was required'
    )
    
    # Timestamps
    created_at = models.DateTimeField(auto_now_add=True, db_index=True)
    
    class Meta:
        db_table = 'workflow_change_history'
        verbose_name = 'workflow change'
        verbose_name_plural = 'workflow change history'
        ordering = ['-created_at']
        indexes = [
            models.Index(fields=['workflow', 'created_at']),
            models.Index(fields=['user', 'modified_by_twin']),
        ]
    
    def __str__(self) -> str:
        author = 'Twin' if self.modified_by_twin else 'User'
        return f"{self.workflow.name} - {author} - {self.created_at}"


class SuggestionStatus(models.TextChoices):
    """Status of a Twin suggestion."""
    PENDING = 'pending', 'Pending'
    APPROVED = 'approved', 'Approved'
    REJECTED = 'rejected', 'Rejected'
    EXPIRED = 'expired', 'Expired'


class TwinSuggestion(models.Model):
    """
    Twin workflow modification suggestions.
    
    Stores suggested modifications with reasoning for user review.
    Users can approve or reject suggestions before they are applied.
    
    Requirements: 8.6
    """
    
    id = models.UUIDField(
        primary_key=True,
        default=uuid.uuid4,
        editable=False
    )
    
    workflow = models.ForeignKey(
        Workflow,
        on_delete=models.CASCADE,
        related_name='twin_suggestions',
        help_text='The workflow this suggestion applies to'
    )
    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name='twin_suggestions',
        help_text='The user who owns the workflow'
    )
    
    # Suggestion details
    suggested_changes = models.JSONField(
        default=dict,
        help_text='Dictionary of proposed field changes'
    )
    reasoning = models.TextField(
        help_text='Explanation for why Twin suggests this modification'
    )
    
    # Context
    cognitive_blend_value = models.IntegerField(
        help_text='Cognitive blend value at time of suggestion'
    )
    based_on_pattern = models.TextField(
        blank=True,
        default='',
        help_text='Description of the learned pattern that triggered this suggestion'
    )
    
    # Status
    status = models.CharField(
        max_length=20,
        choices=SuggestionStatus.choices,
        default=SuggestionStatus.PENDING,
        db_index=True,
        help_text='Current status of the suggestion'
    )
    
    # Review tracking
    reviewed_at = models.DateTimeField(
        null=True,
        blank=True,
        help_text='When the user reviewed this suggestion'
    )
    review_notes = models.TextField(
        blank=True,
        default='',
        help_text='Optional notes from user when reviewing'
    )
    
    # Timestamps
    created_at = models.DateTimeField(auto_now_add=True, db_index=True)
    updated_at = models.DateTimeField(auto_now=True)
    expires_at = models.DateTimeField(
        db_index=True,
        help_text='When this suggestion expires if not reviewed'
    )
    
    class Meta:
        db_table = 'twin_suggestions'
        verbose_name = 'Twin suggestion'
        verbose_name_plural = 'Twin suggestions'
        ordering = ['-created_at']
        indexes = [
            models.Index(fields=['user', 'status']),
            models.Index(fields=['workflow', 'status']),
            models.Index(fields=['status', 'expires_at']),
        ]
    
    def __str__(self) -> str:
        return f"Suggestion for {self.workflow.name} - {self.status}"
    
    @property
    def is_expired(self) -> bool:
        """Check if suggestion has expired."""
        return timezone.now() >= self.expires_at and self.status == SuggestionStatus.PENDING
    
    @property
    def is_pending(self) -> bool:
        """Check if suggestion is pending review."""
        return self.status == SuggestionStatus.PENDING and not self.is_expired
    
    def approve(self, review_notes: str = '') -> Workflow:
        """
        Approve the suggestion and apply changes to workflow.
        
        Args:
            review_notes: Optional notes from user
            
        Returns:
            Updated workflow
        """
        from apps.automation.services.workflow import WorkflowService
        
        self.status = SuggestionStatus.APPROVED
        self.reviewed_at = timezone.now()
        self.review_notes = review_notes
        self.save()
        
        # Apply changes to workflow
        workflow = WorkflowService.update_workflow(
            workflow_id=self.workflow.id,
            user=self.user,
            updates={
                **self.suggested_changes,
                '_reasoning': self.reasoning
            },
            modified_by_twin=True,
            cognitive_blend=self.cognitive_blend_value,
            permission_flag=True  # User approved, so permission is granted
        )
        
        logger.info(
            f'Twin suggestion {self.id} approved and applied to workflow {self.workflow.id}'
        )
        
        return workflow
    
    def reject(self, review_notes: str = ''):
        """
        Reject the suggestion.
        
        Args:
            review_notes: Optional notes from user
        """
        self.status = SuggestionStatus.REJECTED
        self.reviewed_at = timezone.now()
        self.review_notes = review_notes
        self.save()
        
        logger.info(
            f'Twin suggestion {self.id} rejected for workflow {self.workflow.id}'
        )
    
    def mark_expired(self):
        """Mark suggestion as expired."""
        if self.status == SuggestionStatus.PENDING:
            self.status = SuggestionStatus.EXPIRED
            self.save()
            
            logger.info(
                f'Twin suggestion {self.id} expired for workflow {self.workflow.id}'
            )
    
    @classmethod
    def cleanup_expired(cls):
        """Mark all expired pending suggestions as expired."""
        expired_suggestions = cls.objects.filter(
            status=SuggestionStatus.PENDING,
            expires_at__lte=timezone.now()
        )
        
        count = expired_suggestions.count()
        expired_suggestions.update(status=SuggestionStatus.EXPIRED)
        
        if count > 0:
            logger.info(f'Marked {count} Twin suggestions as expired')
        
        return count
