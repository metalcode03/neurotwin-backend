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
import logging
from datetime import datetime
from typing import Optional, List

from django.db import models
from django.conf import settings
from django.core.exceptions import ValidationError
from django.utils import timezone

from .utils.encryption import TokenEncryption

logger = logging.getLogger(__name__)


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


class AuthType(models.TextChoices):
    """
    Authentication type choices for integration types.
    
    Requirements: 1.1
    """
    OAUTH = 'oauth', 'OAuth 2.0'
    META = 'meta', 'Meta Business'
    API_KEY = 'api_key', 'API Key'


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


class MessageDirection(models.TextChoices):
    """
    Direction of message flow.
    
    Requirements: 15.1
    """
    INBOUND = 'inbound', 'Inbound'
    OUTBOUND = 'outbound', 'Outbound'


class MessageStatus(models.TextChoices):
    """
    Status of a message in its lifecycle.
    
    Requirements: 15.1, 21.1
    """
    PENDING = 'pending', 'Pending'
    SENT = 'sent', 'Sent'
    DELIVERED = 'delivered', 'Delivered'
    READ = 'read', 'Read'
    FAILED = 'failed', 'Failed'
    RECEIVED = 'received', 'Received'


class ConversationStatus(models.TextChoices):
    """
    Status of a conversation.
    
    Requirements: 15.1
    """
    ACTIVE = 'active', 'Active'
    ARCHIVED = 'archived', 'Archived'
    CLOSED = 'closed', 'Closed'


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
    
    # Authentication type
    auth_type = models.CharField(
        max_length=20,
        choices=AuthType.choices,
        default=AuthType.OAUTH,
        db_index=True,
        help_text='Authentication strategy for this integration type'
    )

    # Authentication configuration (encrypted)
    auth_config = models.JSONField(
        default=dict,
        help_text='Authentication configuration including credentials, '
                  'URLs, and auth-type-specific parameters'
    )
    
    # Rate limit configuration
    rate_limit_config = models.JSONField(
        default=dict,
        help_text='Rate limit configuration: messages_per_minute, '
                  'requests_per_minute, burst_limit'
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
            models.Index(fields=['auth_type']),
            models.Index(fields=['category']),
            models.Index(fields=['is_active']),
            models.Index(fields=['is_active', 'category']),
            models.Index(fields=['is_active', 'created_at']),
        ]
    
    def __str__(self) -> str:
        return f"{self.name} ({self.type})"
    
    def clean(self):
        """
        Validate type identifier format and auth_config based on auth_type.
        
        Requirements: 1.4, 2.6
        """
        # Validate type identifier format
        if not re.match(r'^[a-z0-9]+(-[a-z0-9]+)*$', self.type):
            raise ValidationError(
                'Type must be in kebab-case format (lowercase, hyphens only)'
            )
        
        # Validate auth_config based on auth_type
        required_fields = self.get_required_auth_fields()
        missing_fields = [
            field for field in required_fields
            if field not in self.auth_config
        ]
        
        if missing_fields:
            raise ValidationError(
                f"Missing required auth_config fields for {self.get_auth_type_display()}: "
                f"{', '.join(missing_fields)}"
            )
    
    # Backward compatibility property
    def get_required_auth_fields(self) -> List[str]:
        """
        Get list of required auth_config fields based on auth_type.
        
        Returns:
            List of required field names for the current auth_type
            
        Requirements: 1.5, 2.2
        """
        if self.auth_type == AuthType.OAUTH:
            return [
                'client_id',
                'client_secret_encrypted',
                'authorization_url',
                'token_url',
                'scopes'
            ]
        elif self.auth_type == AuthType.META:
            return [
                'app_id',
                'app_secret_encrypted',
                'config_id',
                'business_verification_url'
            ]
        elif self.auth_type == AuthType.API_KEY:
            return [
                'api_endpoint',
                'authentication_header_name'
            ]
        else:
            return []
    
    @property
    def oauth_config(self) -> dict:
        """
        Backward compatibility accessor for auth_config.
        
        Requirements: 15.5
        """
        return self.auth_config
    
    @oauth_config.setter
    def oauth_config(self, value: dict):
        """Backward compatibility setter for auth_config."""
        self.auth_config = value
    
    @property
    def oauth_client_id(self) -> str:
        """Get OAuth client ID."""
        return self.auth_config.get('client_id', '')
    
    @property
    def oauth_client_secret(self) -> str:
        """Get decrypted OAuth client secret."""
        encrypted = self.auth_config.get('client_secret_encrypted', '')
        if encrypted:
            return TokenEncryption.decrypt(base64.b64decode(encrypted))
        return ''
    
    def set_oauth_client_secret(self, secret: str):
        """Encrypt and store OAuth client secret."""
        if secret:
            encrypted = TokenEncryption.encrypt(secret)
            self.auth_config['client_secret_encrypted'] = \
                base64.b64encode(encrypted).decode()
    
    @property
    def oauth_scopes(self) -> List[str]:
        """Get OAuth scopes as list."""
        scopes = self.auth_config.get('scopes', [])
        if isinstance(scopes, str):
            return [s.strip() for s in scopes.split(',')]
        return scopes
    
    def get_rate_limit_config(self) -> dict:
        """
        Get rate limit configuration with defaults.
        
        Returns rate_limit_config with default values if not configured.
        
        Returns:
            Dictionary with:
            - messages_per_minute: Maximum messages per minute (default: 20)
            - requests_per_minute: Maximum requests per minute (default: 100)
            - burst_limit: Maximum burst requests (default: 5)
            
        Requirements: 26.1-26.5
        """
        # Default rate limits
        defaults = {
            'messages_per_minute': 20,
            'requests_per_minute': 100,
            'burst_limit': 5
        }
        
        # Merge with configured values
        if isinstance(self.rate_limit_config, dict):
            return {**defaults, **self.rate_limit_config}
        
        return defaults
    
    @property
    def messages_per_minute(self) -> int:
        """Get messages per minute rate limit."""
        return self.get_rate_limit_config().get('messages_per_minute', 20)
    
    @property
    def requests_per_minute(self) -> int:
        """Get requests per minute rate limit."""
        return self.get_rate_limit_config().get('requests_per_minute', 100)
    
    @property
    def burst_limit(self) -> int:
        """Get burst limit."""
        return self.get_rate_limit_config().get('burst_limit', 5)


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
    access_token_encrypted = models.BinaryField(
        null=True,
        blank=True,
        help_text='Encrypted OAuth access token'
    )
    refresh_token_encrypted = models.BinaryField(
        null=True,
        blank=True,
        help_text='Encrypted OAuth refresh token'
    )
    api_key_encrypted = models.BinaryField(
        null=True,
        blank=True,
        help_text='Encrypted API key for API key authentication'
    )
    
    # OAuth configuration
    scopes = models.JSONField(
        default=list,
        help_text='OAuth scopes granted for this integration'
    )
    
    # Meta-specific fields
    waba_id = models.CharField(
        max_length=255,
        null=True,
        blank=True,
        db_index=True,
        help_text='WhatsApp Business Account ID'
    )
    phone_number_id = models.CharField(
        max_length=255,
        null=True,
        blank=True,
        db_index=True,
        help_text='WhatsApp Business phone number ID'
    )
    business_id = models.CharField(
        max_length=255,
        null=True,
        blank=True,
        db_index=True,
        help_text='Meta Business account ID'
    )
    
    # Integration configuration
    user_config = models.JSONField(
        default=dict,
        help_text='User-specific configuration and settings'
    )
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
    status = models.CharField(
        max_length=20,
        choices=[
            ('active', 'Active'),
            ('disconnected', 'Disconnected'),
            ('expired', 'Expired'),
            ('revoked', 'Revoked'),
        ],
        default='active',
        db_index=True,
        help_text='Current status of the integration'
    )
    is_active = models.BooleanField(
        default=True,
        help_text='Whether this integration is active'
    )
    
    # Health monitoring
    health_status = models.CharField(
        max_length=20,
        choices=[
            ('healthy', 'Healthy'),
            ('degraded', 'Degraded'),
            ('disconnected', 'Disconnected'),
        ],
        default='healthy',
        db_index=True,
        help_text='Health status of the integration'
    )
    consecutive_failures = models.IntegerField(
        default=0,
        help_text='Number of consecutive operation failures'
    )
    last_successful_sync_at = models.DateTimeField(
        null=True,
        blank=True,
        help_text='Timestamp of last successful operation'
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
            models.Index(fields=['user', 'status']),
            models.Index(fields=['integration_type', 'is_active']),
            models.Index(fields=['token_expires_at']),
            models.Index(fields=['waba_id']),
            models.Index(fields=['phone_number_id']),
            models.Index(fields=['business_id']),
            models.Index(fields=['health_status']),
            models.Index(fields=['status']),
        ]
    
    def __str__(self) -> str:
        status = 'active' if self.is_active else 'inactive'
        return f"{self.user.email}: {self.integration_type.name} ({status})"
    
    def clean(self):
        """
        Validate integration configuration based on auth_type.
        
        Requirements: 10.6
        """
        super().clean()
        
        # Require business_id for Meta integrations
        if self.integration_type.auth_type == AuthType.META:
            if not self.business_id:
                raise ValidationError(
                    'business_id is required for Meta integrations'
                )
    
    @property
    def oauth_token(self) -> str:
        """
        Get decrypted OAuth access token.
        
        Requirements: 10.7
        """
        if self.access_token_encrypted:
            auth_type = self.integration_type.auth_type
            return TokenEncryption.decrypt(
                bytes(self.access_token_encrypted),
                auth_type=auth_type
            )
        return ''
    
    @oauth_token.setter
    def oauth_token(self, value: str):
        """
        Set and encrypt OAuth access token.
        
        Requirements: 10.7
        """
        if value:
            auth_type = self.integration_type.auth_type if self.integration_type_id else 'oauth'
            self.access_token_encrypted = TokenEncryption.encrypt(value, auth_type=auth_type)
        else:
            self.access_token_encrypted = None
    
    @property
    def refresh_token(self) -> str:
        """
        Get decrypted OAuth refresh token.
        
        Requirements: 10.7
        """
        if self.refresh_token_encrypted:
            auth_type = self.integration_type.auth_type if self.integration_type_id else 'oauth'
            return TokenEncryption.decrypt(
                bytes(self.refresh_token_encrypted),
                auth_type=auth_type
            )
        return ''
    
    @refresh_token.setter
    def refresh_token(self, value: str):
        """
        Set and encrypt OAuth refresh token.
        
        Requirements: 10.7
        """
        if value:
            auth_type = self.integration_type.auth_type if self.integration_type_id else 'oauth'
            self.refresh_token_encrypted = TokenEncryption.encrypt(value, auth_type=auth_type)
        else:
            self.refresh_token_encrypted = None
    
    @property
    def is_token_expired(self) -> bool:
        """Check if the OAuth token has expired."""
        if self.token_expires_at is None:
            return False
        return timezone.now() >= self.token_expires_at
    
    @property
    def api_key(self) -> str:
        """
        Get decrypted API key.
        
        Requirements: 2.1, 17.2
        """
        if self.api_key_encrypted:
            auth_type = self.integration_type.auth_type if self.integration_type_id else 'api_key'
            return TokenEncryption.decrypt(
                bytes(self.api_key_encrypted),
                auth_type=auth_type
            )
        return ''
    
    @api_key.setter
    def api_key(self, value: str):
        """
        Set and encrypt API key.
        
        Requirements: 2.1, 17.2
        """
        if value:
            auth_type = self.integration_type.auth_type if self.integration_type_id else 'api_key'
            self.api_key_encrypted = TokenEncryption.encrypt(value, auth_type=auth_type)
        else:
            self.api_key_encrypted = None
    
    @property
    def has_refresh_token(self) -> bool:
        """Check if a refresh token is available."""
        return bool(self.refresh_token_encrypted)
    
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
    INITIATED = 'initiated', 'Initiated'
    OAUTH_PENDING = 'oauth_pending', 'OAuth Pending'
    COMPLETING = 'completing', 'Completing'
    COMPLETED = 'completed', 'Completed'
    FAILED = 'failed', 'Failed'
    EXPIRED = 'expired', 'Expired'


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
        default=InstallationStatus.INITIATED,
        db_index=True,
        help_text='Current installation phase'
    )
    progress = models.IntegerField(
        default=0,
        help_text='Progress percentage (0-100)'
    )
    
    # Authentication type (auto-populated from integration_type)
    auth_type = models.CharField(
        max_length=20,
        choices=AuthType.choices,
        default=AuthType.OAUTH,
        help_text='Authentication type for this installation session'
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
    expires_at = models.DateTimeField(
        db_index=True,
        help_text='When this session expires (15 minutes from creation)'
    )
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
            models.Index(fields=['oauth_state']),
            models.Index(fields=['status']),
            models.Index(fields=['expires_at']),
            models.Index(fields=['created_at']),
            models.Index(fields=['auth_type', 'status']),
        ]
    
    def __str__(self) -> str:
        return f"{self.user.email}: {self.integration_type.name} - {self.status}"
    
    def save(self, *args, **kwargs):
        """
        Override save to auto-populate auth_type and expires_at.
        
        Requirements: 3.3, 12.8
        """
        # Auto-populate auth_type from integration_type
        if self.integration_type_id and not self.auth_type:
            self.auth_type = self.integration_type.auth_type
        
        # Set expires_at to 15 minutes from creation if not set
        if not self.expires_at:
            from datetime import timedelta
            self.expires_at = timezone.now() + timedelta(minutes=15)
        
        super().save(*args, **kwargs)
    
    @property
    def is_complete(self) -> bool:
        """Check if session is complete."""
        return self.status in [
            InstallationStatus.COMPLETED,
            InstallationStatus.FAILED,
            InstallationStatus.EXPIRED,
        ]
    
    @property
    def is_expired(self) -> bool:
        """Check if session has expired."""
        return timezone.now() >= self.expires_at
    
    def increment_retry(self):
        """Increment retry counter."""
        self.retry_count += 1
        self.save(update_fields=['retry_count', 'updated_at'])
    
    @property
    def can_retry(self) -> bool:
        """Check if retry is allowed."""
        return self.retry_count < 3


class Conversation(models.Model):
    """
    Conversation model for tracking message threads.
    
    Tracks conversations between users and external contacts
    across different integration platforms.
    
    Requirements: 15.1-15.2, 20.1-20.3
    """
    
    id = models.UUIDField(
        primary_key=True,
        default=uuid.uuid4,
        editable=False
    )
    
    integration = models.ForeignKey(
        Integration,
        on_delete=models.CASCADE,
        related_name='conversations',
        db_index=True,
        help_text='Integration this conversation belongs to'
    )
    
    # External contact information
    external_contact_id = models.CharField(
        max_length=255,
        db_index=True,
        help_text='Contact identifier from external platform'
    )
    external_contact_name = models.CharField(
        max_length=255,
        blank=True,
        default='',
        help_text='Contact name from external platform'
    )
    
    # Status
    status = models.CharField(
        max_length=20,
        choices=ConversationStatus.choices,
        default=ConversationStatus.ACTIVE,
        db_index=True,
        help_text='Current status of the conversation'
    )
    
    # Tracking
    last_message_at = models.DateTimeField(
        db_index=True,
        help_text='Timestamp of last message in conversation'
    )
    
    # Timestamps
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        db_table = 'conversations'
        verbose_name = 'conversation'
        verbose_name_plural = 'conversations'
        unique_together = [['integration', 'external_contact_id']]
        ordering = ['-last_message_at']
        indexes = [
            models.Index(fields=['integration', 'external_contact_id']),
            models.Index(fields=['integration', 'status']),
            models.Index(fields=['integration', 'last_message_at']),
            models.Index(fields=['last_message_at']),
            models.Index(fields=['status']),
        ]
    
    def __str__(self) -> str:
        contact = self.external_contact_name or self.external_contact_id
        return f"{self.integration.integration_type.name}: {contact}"
    
    @property
    def unread_count(self) -> int:
        """Get count of unread messages in this conversation."""
        return self.messages.filter(
            direction=MessageDirection.INBOUND,
            status=MessageStatus.RECEIVED
        ).count()


class Message(models.Model):
    """
    Message model for individual messages within conversations.
    
    Stores message content, status, and retry information for
    reliable message delivery.
    
    Requirements: 15.3-15.7, 21.1-21.7
    """
    
    id = models.UUIDField(
        primary_key=True,
        default=uuid.uuid4,
        editable=False
    )
    
    conversation = models.ForeignKey(
        Conversation,
        on_delete=models.CASCADE,
        related_name='messages',
        db_index=True,
        help_text='Conversation this message belongs to'
    )
    
    # Message details
    direction = models.CharField(
        max_length=10,
        choices=MessageDirection.choices,
        db_index=True,
        help_text='Direction of message flow'
    )
    content = models.TextField(
        help_text='Message content'
    )
    
    # Status tracking
    status = models.CharField(
        max_length=20,
        choices=MessageStatus.choices,
        default=MessageStatus.PENDING,
        db_index=True,
        help_text='Current status of the message'
    )
    
    # External platform tracking
    external_message_id = models.CharField(
        max_length=255,
        blank=True,
        default='',
        db_index=True,
        help_text='Message ID from external platform'
    )
    
    # Retry tracking
    retry_count = models.IntegerField(
        default=0,
        help_text='Number of delivery retry attempts'
    )
    last_retry_at = models.DateTimeField(
        null=True,
        blank=True,
        help_text='Timestamp of last retry attempt'
    )
    
    # Additional data
    metadata = models.JSONField(
        default=dict,
        help_text='Platform-specific metadata'
    )
    
    # Timestamps
    created_at = models.DateTimeField(
        auto_now_add=True,
        db_index=True,
        help_text='When message was created'
    )
    updated_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        db_table = 'messages'
        verbose_name = 'message'
        verbose_name_plural = 'messages'
        ordering = ['created_at']
        indexes = [
            models.Index(fields=['conversation', 'created_at']),
            models.Index(fields=['conversation', 'status']),
            models.Index(fields=['status']),
            models.Index(fields=['external_message_id']),
            models.Index(fields=['created_at']),
            models.Index(fields=['direction', 'status']),
        ]
    
    def __str__(self) -> str:
        direction_str = 'from' if self.direction == MessageDirection.INBOUND else 'to'
        contact = self.conversation.external_contact_name or self.conversation.external_contact_id
        return f"Message {direction_str} {contact}: {self.content[:50]}"
    
    @property
    def is_failed(self) -> bool:
        """Check if message delivery failed."""
        return self.status == MessageStatus.FAILED
    
    @property
    def can_retry(self) -> bool:
        """Check if message can be retried."""
        return self.retry_count < 5 and self.status in [
            MessageStatus.PENDING,
            MessageStatus.FAILED
        ]
    
    def increment_retry(self):
        """Increment retry counter and update timestamp."""
        self.retry_count += 1
        self.last_retry_at = timezone.now()
        self.save(update_fields=['retry_count', 'last_retry_at', 'updated_at'])


class WebhookEventStatus(models.TextChoices):
    """
    Status of webhook event processing.
    
    Requirements: 22.1
    """
    PENDING = 'pending', 'Pending'
    PROCESSING = 'processing', 'Processing'
    PROCESSED = 'processed', 'Processed'
    FAILED = 'failed', 'Failed'


class WebhookEvent(models.Model):
    """
    Webhook event model for storing incoming webhook events.
    
    Stores raw webhook payloads for asynchronous processing
    and audit trail.
    
    Requirements: 10.4, 22.1-22.7
    """
    
    id = models.UUIDField(
        primary_key=True,
        default=uuid.uuid4,
        editable=False
    )
    
    # Integration tracking
    integration_type = models.ForeignKey(
        IntegrationTypeModel,
        on_delete=models.CASCADE,
        related_name='webhook_events',
        db_index=True,
        help_text='Integration type that sent this webhook'
    )
    integration = models.ForeignKey(
        Integration,
        on_delete=models.CASCADE,
        null=True,
        blank=True,
        related_name='webhook_events',
        db_index=True,
        help_text='Specific integration instance (if identified)'
    )
    
    # Webhook data
    payload = models.JSONField(
        help_text='Raw webhook payload as JSON'
    )
    signature = models.CharField(
        max_length=500,
        blank=True,
        default='',
        help_text='Webhook signature for verification'
    )
    
    # Processing status
    status = models.CharField(
        max_length=20,
        choices=WebhookEventStatus.choices,
        default=WebhookEventStatus.PENDING,
        db_index=True,
        help_text='Processing status of the webhook'
    )
    error_message = models.TextField(
        blank=True,
        default='',
        help_text='Error message if processing failed'
    )
    processed_at = models.DateTimeField(
        null=True,
        blank=True,
        help_text='When webhook was processed'
    )
    
    # Timestamps
    created_at = models.DateTimeField(
        auto_now_add=True,
        db_index=True,
        help_text='When webhook was received'
    )
    updated_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        db_table = 'webhook_events'
        verbose_name = 'webhook event'
        verbose_name_plural = 'webhook events'
        ordering = ['-created_at']
        indexes = [
            models.Index(fields=['status', 'created_at']),
            models.Index(fields=['integration_type', 'created_at']),
            models.Index(fields=['integration', 'created_at']),
            models.Index(fields=['status']),
            models.Index(fields=['created_at']),
        ]
    
    def __str__(self) -> str:
        integration_name = self.integration_type.name if self.integration_type else 'Unknown'
        return f"Webhook from {integration_name} - {self.status} - {self.created_at}"
    
    @property
    def is_processed(self) -> bool:
        """Check if webhook has been processed."""
        return self.status in [
            WebhookEventStatus.PROCESSED,
            WebhookEventStatus.FAILED
        ]
    
    def mark_processing(self):
        """Mark webhook as currently being processed."""
        self.status = WebhookEventStatus.PROCESSING
        self.save(update_fields=['status', 'updated_at'])
    
    def mark_processed(self):
        """Mark webhook as successfully processed."""
        self.status = WebhookEventStatus.PROCESSED
        self.processed_at = timezone.now()
        self.save(update_fields=['status', 'processed_at', 'updated_at'])
    
    def mark_failed(self, error_message: str):
        """Mark webhook as failed with error message."""
        self.status = WebhookEventStatus.FAILED
        self.error_message = error_message
        self.processed_at = timezone.now()
        self.save(update_fields=['status', 'error_message', 'processed_at', 'updated_at'])
    
    @classmethod
    def cleanup_old_events(cls, days: int = 30):
        """
        Delete webhook events older than specified days.
        
        Args:
            days: Number of days to retain events (default 30)
            
        Returns:
            Number of events deleted
        """
        from datetime import timedelta
        
        cutoff = timezone.now() - timedelta(days=days)
        count, _ = cls.objects.filter(created_at__lt=cutoff).delete()
        
        if count > 0:
            import logging
            logger = logging.getLogger(__name__)
            logger.info(f'Deleted {count} webhook events older than {days} days')
        
        return count


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



class AuthenticationAction(models.TextChoices):
    """
    Actions tracked in authentication audit log.
    
    Requirements: 16.6, 23.1
    """
    INSTALL_START = 'install_start', 'Installation Started'
    INSTALL_COMPLETE = 'install_complete', 'Installation Completed'
    INSTALL_FAILED = 'install_failed', 'Installation Failed'
    TOKEN_REFRESH = 'token_refresh', 'Token Refresh'
    TOKEN_REVOKE = 'token_revoke', 'Token Revocation'
    CALLBACK_RECEIVED = 'callback_received', 'Callback Received'
    API_KEY_VALIDATION = 'api_key_validation', 'API Key Validation'


class AuthenticationAuditLog(models.Model):
    """
    Audit log for all authentication attempts and operations.
    
    Tracks authentication attempts, token operations, and security events
    for compliance and monitoring purposes.
    
    Requirements: 16.6, 23.1
    """
    
    id = models.UUIDField(
        primary_key=True,
        default=uuid.uuid4,
        editable=False
    )
    
    # User and integration tracking
    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='auth_audit_logs',
        help_text='User who initiated the authentication'
    )
    integration_type = models.ForeignKey(
        IntegrationTypeModel,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='auth_audit_logs',
        help_text='Integration type being authenticated'
    )
    auth_type = models.CharField(
        max_length=20,
        choices=AuthType.choices,
        db_index=True,
        help_text='Authentication type used'
    )
    
    # Action tracking
    action = models.CharField(
        max_length=50,
        choices=AuthenticationAction.choices,
        db_index=True,
        help_text='Authentication action performed'
    )
    success = models.BooleanField(
        db_index=True,
        help_text='Whether the action succeeded'
    )
    error_code = models.CharField(
        max_length=100,
        blank=True,
        default='',
        help_text='Error code if action failed'
    )
    error_message = models.TextField(
        blank=True,
        default='',
        help_text='Error message if action failed'
    )
    
    # Performance tracking
    duration_ms = models.IntegerField(
        null=True,
        blank=True,
        help_text='Duration of the operation in milliseconds'
    )
    
    # Security tracking
    ip_address = models.GenericIPAddressField(
        null=True,
        blank=True,
        db_index=True,
        help_text='IP address of the request'
    )
    user_agent = models.TextField(
        blank=True,
        default='',
        help_text='User agent string from the request'
    )
    
    # Additional context
    metadata = models.JSONField(
        default=dict,
        help_text='Additional context and metadata for the action'
    )
    
    # Timestamps
    created_at = models.DateTimeField(
        auto_now_add=True,
        db_index=True,
        help_text='When the action occurred'
    )
    
    class Meta:
        db_table = 'authentication_audit_logs'
        verbose_name = 'authentication audit log'
        verbose_name_plural = 'authentication audit logs'
        ordering = ['-created_at']
        indexes = [
            models.Index(fields=['user', 'created_at']),
            models.Index(fields=['integration_type', 'created_at']),
            models.Index(fields=['auth_type', 'action', 'created_at']),
            models.Index(fields=['success', 'created_at']),
            models.Index(fields=['action', 'success', 'created_at']),
            models.Index(fields=['ip_address', 'created_at']),
        ]
    
    def __str__(self) -> str:
        user_str = self.user.email if self.user else 'Anonymous'
        integration_str = self.integration_type.name if self.integration_type else 'Unknown'
        status = 'Success' if self.success else 'Failed'
        return f"{user_str} - {integration_str} - {self.get_action_display()} - {status}"
    
    @classmethod
    def log_authentication_attempt(
        cls,
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
    ) -> 'AuthenticationAuditLog':
        """
        Create an authentication audit log entry.
        
        Args:
            action: Authentication action performed
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
        """
        return cls.objects.create(
            user=user,
            integration_type=integration_type,
            auth_type=auth_type,
            action=action,
            success=success,
            error_code=error_code,
            error_message=error_message,
            duration_ms=duration_ms,
            ip_address=ip_address,
            user_agent=user_agent,
            metadata=metadata or {}
        )
    
    @classmethod
    def get_success_rate_by_auth_type(cls, auth_type: str, days: int = 7) -> float:
        """
        Calculate success rate for an authentication type.
        
        Args:
            auth_type: Authentication type to analyze
            days: Number of days to look back
            
        Returns:
            Success rate as percentage (0-100)
        """
        from datetime import timedelta
        
        cutoff = timezone.now() - timedelta(days=days)
        logs = cls.objects.filter(
            auth_type=auth_type,
            created_at__gte=cutoff
        )
        
        total = logs.count()
        if total == 0:
            return 100.0
        
        successful = logs.filter(success=True).count()
        return (successful / total) * 100
    
    @classmethod
    def get_average_duration_by_auth_type(cls, auth_type: str, days: int = 7) -> float:
        """
        Calculate average duration for an authentication type.
        
        Args:
            auth_type: Authentication type to analyze
            days: Number of days to look back
            
        Returns:
            Average duration in milliseconds
        """
        from datetime import timedelta
        from django.db.models import Avg
        
        cutoff = timezone.now() - timedelta(days=days)
        result = cls.objects.filter(
            auth_type=auth_type,
            created_at__gte=cutoff,
            duration_ms__isnull=False
        ).aggregate(avg_duration=Avg('duration_ms'))
        
        return result['avg_duration'] or 0.0
    
    @classmethod
    def cleanup_old_logs(cls, days: int = 90):
        """
        Delete audit logs older than specified days.
        
        Args:
            days: Number of days to retain logs
            
        Returns:
            Number of logs deleted
        """
        from datetime import timedelta
        
        cutoff = timezone.now() - timedelta(days=days)
        count, _ = cls.objects.filter(created_at__lt=cutoff).delete()
        
        if count > 0:
            logger.info(f'Deleted {count} authentication audit logs older than {days} days')
        
        return count
