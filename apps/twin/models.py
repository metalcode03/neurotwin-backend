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
        (AIModel.GEMINI_FLASH.value, 'Gemini 3 Flash'),
        (AIModel.QWEN.value, 'Qwen'),
        (AIModel.MISTRAL.value, 'Mistral'),
        (AIModel.GEMINI_PRO.value, 'Gemini 3 Pro'),
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
