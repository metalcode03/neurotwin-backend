"""
Twin models for NeuroTwin platform.

Defines Twin model with user_id, model, cognitive_blend, and csm_id.
Requirements: 2.1, 2.3, 2.4, 2.5, 2.6
"""

import uuid
from typing import Optional

from django.db import models
from django.conf import settings
from django.core.validators import MinValueValidator, MaxValueValidator

from .dataclasses import AIModel


class Twin(models.Model):
    """
    The AI replica of a user's cognitive patterns and personality.
    
    A Twin is created during onboarding and linked to a CSM profile.
    The cognitive_blend controls how much personality vs AI logic is used.
    
    Requirements: 2.1, 2.3, 2.4, 2.5, 2.6
    """
    
    # Model choices from AIModel enum
    MODEL_CHOICES = [
        (AIModel.CEREBRAS.value, 'Cerebras'),
        (AIModel.GEMINI_FLASH.value, 'Gemini 2.5 Flash'),
        (AIModel.GEMINI_PRO_25.value, 'Gemini 2.5 Pro'),
        (AIModel.GEMINI_PRO_3.value, 'Gemini 3 Pro'),
        (AIModel.GEMINI_PRO_31.value, 'Gemini 3.1 Pro'),
        (AIModel.MISTRAL.value, 'Mistral'),
    ]
    
    id = models.UUIDField(
        primary_key=True,
        default=uuid.uuid4,
        editable=False
    )
    user = models.OneToOneField(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name='twin',
        help_text='The user this Twin belongs to'
    )
    model = models.CharField(
        max_length=50,
        choices=MODEL_CHOICES,
        default=AIModel.GEMINI_FLASH.value,
        help_text='AI model used for this Twin'
    )
    cognitive_blend = models.IntegerField(
        default=50,
        validators=[
            MinValueValidator(0),
            MaxValueValidator(100)
        ],
        help_text='Cognitive blend value (0-100). 0=pure AI, 100=full personality'
    )
    csm_profile = models.OneToOneField(
        'csm.CSMProfile',
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='twin',
        help_text='The CSM profile for this Twin'
    )
    
    # Brain mode for credit-based AI routing
    brain_mode = models.CharField(
        max_length=20,
        choices=[
            ('brain', 'Brain'),
            ('brain_pro', 'Brain Pro'),
            ('brain_gen', 'Brain Gen'),
        ],
        default='brain',
        null=True,
        blank=True,
        help_text='Brain mode for AI request routing'
    )
    
    # Status flags
    is_active = models.BooleanField(
        default=True,
        help_text='Whether this Twin is active'
    )
    kill_switch_active = models.BooleanField(
        default=False,
        help_text='Whether the kill switch is currently active'
    )
    
    # Timestamps
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        db_table = 'twins'
        verbose_name = 'Twin'
        verbose_name_plural = 'Twins'
        indexes = [
            models.Index(fields=['user']),
            models.Index(fields=['is_active']),
        ]
    
    def __str__(self) -> str:
        return f"Twin for {self.user.email} ({self.model})"
    
    def get_ai_model(self) -> AIModel:
        """Get the AIModel enum value for this Twin."""
        return AIModel(self.model)
    
    def set_ai_model(self, model: AIModel) -> None:
        """Set the AI model from an AIModel enum."""
        self.model = model.value
    
    @property
    def blend_mode(self) -> str:
        """
        Get the blend mode based on cognitive_blend value.
        
        Requirements: 4.3, 4.4, 4.5
        - 0-30%: ai_logic (pure AI with minimal personality)
        - 31-70%: balanced (user personality + AI reasoning)
        - 71-100%: personality_heavy (heavy mimicry, requires confirmation)
        """
        if self.cognitive_blend <= 30:
            return 'ai_logic'
        elif self.cognitive_blend <= 70:
            return 'balanced'
        else:
            return 'personality_heavy'
    
    @property
    def requires_confirmation(self) -> bool:
        """
        Check if actions require user confirmation.
        
        Requirements: 4.5, 8.5
        Returns True when cognitive_blend > 80%
        """
        return self.cognitive_blend > 80
    
    @classmethod
    def get_for_user(cls, user_id: str) -> Optional['Twin']:
        """
        Get the Twin for a user.
        
        Args:
            user_id: UUID of the user
            
        Returns:
            Twin instance or None if not found
        """
        try:
            return cls.objects.get(user_id=user_id, is_active=True)
        except cls.DoesNotExist:
            return None


class OnboardingProgress(models.Model):
    """
    Tracks onboarding progress for users who haven't completed Twin creation.
    
    Requirements: 2.1
    """
    
    id = models.UUIDField(
        primary_key=True,
        default=uuid.uuid4,
        editable=False
    )
    user = models.OneToOneField(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name='onboarding_progress'
    )
    questionnaire_responses = models.JSONField(
        default=dict,
        help_text='Partial questionnaire responses'
    )
    selected_model = models.CharField(
        max_length=50,
        blank=True,
        null=True,
        help_text='Selected AI model (if chosen)'
    )
    selected_blend = models.IntegerField(
        null=True,
        blank=True,
        validators=[
            MinValueValidator(0),
            MaxValueValidator(100)
        ],
        help_text='Selected cognitive blend (if chosen)'
    )
    is_complete = models.BooleanField(
        default=False,
        help_text='Whether onboarding is complete'
    )
    
    # Timestamps
    started_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        db_table = 'onboarding_progress'
        verbose_name = 'Onboarding Progress'
        verbose_name_plural = 'Onboarding Progress'
    
    def __str__(self) -> str:
        status = 'complete' if self.is_complete else 'in progress'
        return f"Onboarding for {self.user.email} ({status})"


class AuditLog(models.Model):
    """
    Audit log for Twin actions and system events.

    Tracks all Twin-initiated actions, installations, uninstallations,
    and permission-related events for security and compliance.

    Requirements: 8.2, 18.6
    """

    # Event type choices
    EVENT_TYPE_CHOICES = [
        ('twin_action', 'Twin Action'),
        ('workflow_modification', 'Workflow Modification'),
        ('installation', 'Integration Installation'),
        ('uninstallation', 'Integration Uninstallation'),
        ('permission_denied', 'Permission Denied'),
        ('permission_granted', 'Permission Granted'),
        ('kill_switch_activated', 'Kill Switch Activated'),
        ('kill_switch_deactivated', 'Kill Switch Deactivated'),
        ('cognitive_blend_changed', 'Cognitive Blend Changed'),
        ('oauth_token_refresh', 'OAuth Token Refresh'),
    ]

    # Action choices
    ACTION_CHOICES = [
        ('create', 'Create'),
        ('read', 'Read'),
        ('update', 'Update'),
        ('delete', 'Delete'),
        ('execute', 'Execute'),
        ('approve', 'Approve'),
        ('reject', 'Reject'),
    ]

    # Result choices
    RESULT_CHOICES = [
        ('success', 'Success'),
        ('failure', 'Failure'),
        ('denied', 'Denied'),
        ('pending', 'Pending'),
    ]

    id = models.UUIDField(
        primary_key=True,
        default=uuid.uuid4,
        editable=False
    )

    # Event metadata
    timestamp = models.DateTimeField(
        auto_now_add=True,
        db_index=True,
        help_text='When the event occurred'
    )
    event_type = models.CharField(
        max_length=50,
        choices=EVENT_TYPE_CHOICES,
        db_index=True,
        help_text='Type of event being logged'
    )

    # User and resource information
    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name='audit_logs',
        db_index=True,
        help_text='User associated with this event'
    )
    resource_type = models.CharField(
        max_length=100,
        db_index=True,
        help_text='Type of resource (e.g., Workflow, Integration, Twin)'
    )
    resource_id = models.CharField(
        max_length=255,
        db_index=True,
        help_text='ID of the resource affected'
    )

    # Action details
    action = models.CharField(
        max_length=50,
        choices=ACTION_CHOICES,
        help_text='Action performed'
    )
    result = models.CharField(
        max_length=50,
        choices=RESULT_CHOICES,
        help_text='Result of the action'
    )

    # Additional context
    details = models.JSONField(
        default=dict,
        help_text='Additional details about the event (structured data)'
    )

    # Twin-specific fields
    initiated_by_twin = models.BooleanField(
        default=False,
        db_index=True,
        help_text='Whether this action was initiated by the Twin'
    )
    cognitive_blend_value = models.IntegerField(
        null=True,
        blank=True,
        help_text='Cognitive blend value at time of action (for Twin actions)'
    )
    permission_flag = models.BooleanField(
        default=False,
        help_text='Whether permission was granted for this action'
    )

    # IP and user agent for security
    ip_address = models.GenericIPAddressField(
        null=True,
        blank=True,
        help_text='IP address of the request'
    )
    user_agent = models.TextField(
        blank=True,
        default='',
        help_text='User agent string'
    )

    class Meta:
        db_table = 'audit_logs'
        verbose_name = 'Audit Log'
        verbose_name_plural = 'Audit Logs'
        ordering = ['-timestamp']
        indexes = [
            models.Index(fields=['user', 'timestamp']),
            models.Index(fields=['event_type', 'timestamp']),
            models.Index(fields=['resource_type', 'resource_id']),
            models.Index(fields=['initiated_by_twin', 'timestamp']),
            models.Index(fields=['result', 'timestamp']),
        ]

    def __str__(self) -> str:
        actor = 'Twin' if self.initiated_by_twin else 'User'
        return f"{actor} {self.action} {self.resource_type} - {self.result} ({self.timestamp})"

    @property
    def is_twin_action(self) -> bool:
        """Check if this was a Twin-initiated action."""
        return self.initiated_by_twin

    @property
    def requires_attention(self) -> bool:
        """
        Check if this log entry requires attention.

        Returns True for:
        - Failed actions
        - Denied permissions
        - Twin actions with high cognitive blend (>80%)
        """
        if self.result in ['failure', 'denied']:
            return True
        if self.initiated_by_twin and self.cognitive_blend_value and self.cognitive_blend_value > 80:
            return True
        return False
