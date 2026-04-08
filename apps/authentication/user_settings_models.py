"""
User settings models for NeuroTwin platform.

Defines UserSettings model for storing user preferences including brain_mode.
Requirements: 5.8, 15.7
"""

import uuid
from django.db import models
from django.conf import settings
from django.core.exceptions import ValidationError


class BrainMode(models.TextChoices):
    """
    Brain mode choices for AI request routing.
    
    Requirements: 5.1-5.5
    """
    BRAIN = 'brain', 'Brain'
    BRAIN_PRO = 'brain_pro', 'Brain Pro'
    BRAIN_GEN = 'brain_gen', 'Brain Gen'


class UserSettings(models.Model):
    """
    User settings model for storing user preferences.
    
    Stores brain_mode preference and other user-specific settings.
    Brain mode selection is validated against user's subscription tier.
    
    Requirements: 5.8, 15.7
    """
    
    id = models.UUIDField(
        primary_key=True,
        default=uuid.uuid4,
        editable=False
    )
    user = models.OneToOneField(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name='settings'
    )
    brain_mode = models.CharField(
        max_length=20,
        choices=BrainMode.choices,
        default=BrainMode.BRAIN,
        help_text='Preferred Brain mode for AI requests'
    )
    notification_preferences = models.JSONField(
        default=dict,
        blank=True,
        help_text='User notification preferences'
    )
    
    # Timestamps
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        db_table = 'user_settings'
        verbose_name = 'User Settings'
        verbose_name_plural = 'User Settings'
        indexes = [
            models.Index(fields=['user']),
        ]
    
    def __str__(self) -> str:
        return f"Settings for {self.user.email}"
    
    def clean(self):
        """
        Validate brain_mode against user's subscription tier.
        
        Requirements: 5.6, 5.7, 5.10
        """
        super().clean()
        
        # Import here to avoid circular dependency
        from apps.subscription.models import SubscriptionTier
        
        # Get user's subscription tier
        try:
            subscription = self.user.subscription
            tier = subscription.tier
        except AttributeError:
            # No subscription, default to FREE
            tier = SubscriptionTier.FREE
        
        # Define tier requirements for each brain mode
        tier_requirements = {
            BrainMode.BRAIN: [
                SubscriptionTier.FREE,
                SubscriptionTier.PRO,
                SubscriptionTier.TWIN_PLUS,
                SubscriptionTier.EXECUTIVE
            ],
            BrainMode.BRAIN_PRO: [
                SubscriptionTier.PRO,
                SubscriptionTier.TWIN_PLUS,
                SubscriptionTier.EXECUTIVE
            ],
            BrainMode.BRAIN_GEN: [
                SubscriptionTier.EXECUTIVE
            ]
        }
        
        # Validate brain_mode against tier
        allowed_tiers = tier_requirements.get(self.brain_mode, [])
        if tier not in allowed_tiers:
            required_tier_names = {
                BrainMode.BRAIN_PRO: 'PRO',
                BrainMode.BRAIN_GEN: 'EXECUTIVE'
            }
            required = required_tier_names.get(self.brain_mode, 'UNKNOWN')
            raise ValidationError({
                'brain_mode': f'Brain mode {self.get_brain_mode_display()} requires {required} tier or higher'
            })
    
    def save(self, *args, **kwargs):
        """Override save to run validation."""
        self.full_clean()
        super().save(*args, **kwargs)
