"""
Subscription models for NeuroTwin platform.

Defines Subscription model with tier enum for managing user subscriptions.
Requirements: 3.1
"""

import uuid
from datetime import datetime
from typing import Optional

from django.db import models
from django.conf import settings
from django.utils import timezone


class SubscriptionTier(models.TextChoices):
    """
    Subscription tier enum.
    
    Requirements: 3.1
    - FREE: Basic tier with limited features
    - PRO: Full cognitive learning capabilities
    - TWIN_PLUS: Pro features plus Voice_Twin
    - EXECUTIVE: All features including autonomous workflows
    """
    
    FREE = 'free', 'Free'
    PRO = 'pro', 'Pro'
    TWIN_PLUS = 'twin_plus', 'Twin+'
    EXECUTIVE = 'executive', 'Executive'


class Subscription(models.Model):
    """
    Subscription model for managing user subscriptions.
    
    Requirements: 3.1, 3.6, 3.7
    """
    
    id = models.UUIDField(
        primary_key=True,
        default=uuid.uuid4,
        editable=False
    )
    user = models.OneToOneField(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name='subscription'
    )
    tier = models.CharField(
        max_length=20,
        choices=SubscriptionTier.choices,
        default=SubscriptionTier.FREE,
        db_index=True
    )
    started_at = models.DateTimeField(
        default=timezone.now,
        help_text='When the current subscription tier started'
    )
    expires_at = models.DateTimeField(
        null=True,
        blank=True,
        help_text='When the subscription expires (null for free tier)'
    )
    is_active = models.BooleanField(
        default=True,
        help_text='Whether the subscription is currently active'
    )
    
    # Metadata
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    # Track previous tier for history
    previous_tier = models.CharField(
        max_length=20,
        choices=SubscriptionTier.choices,
        null=True,
        blank=True,
        help_text='Previous tier before last change'
    )
    tier_changed_at = models.DateTimeField(
        null=True,
        blank=True,
        help_text='When the tier was last changed'
    )
    
    class Meta:
        db_table = 'subscriptions'
        verbose_name = 'subscription'
        verbose_name_plural = 'subscriptions'
        indexes = [
            models.Index(fields=['user']),
            models.Index(fields=['tier']),
            models.Index(fields=['expires_at']),
        ]
    
    def __str__(self) -> str:
        return f"{self.user.email} - {self.get_tier_display()}"
    
    @property
    def is_expired(self) -> bool:
        """Check if the subscription has expired."""
        if self.expires_at is None:
            return False
        return timezone.now() > self.expires_at
    
    @property
    def is_premium(self) -> bool:
        """Check if the subscription is a premium tier (not free)."""
        return self.tier != SubscriptionTier.FREE
    
    @property
    def is_lapsed(self) -> bool:
        """
        Check if the subscription has lapsed.
        
        A subscription is lapsed if it's a premium tier that has expired.
        Requirements: 3.7
        """
        return self.is_premium and self.is_expired


class SubscriptionHistory(models.Model):
    """
    Track subscription tier changes for audit purposes.
    
    Requirements: 3.6 - preserving data during tier changes
    """
    
    id = models.UUIDField(
        primary_key=True,
        default=uuid.uuid4,
        editable=False
    )
    subscription = models.ForeignKey(
        Subscription,
        on_delete=models.CASCADE,
        related_name='history'
    )
    from_tier = models.CharField(
        max_length=20,
        choices=SubscriptionTier.choices
    )
    to_tier = models.CharField(
        max_length=20,
        choices=SubscriptionTier.choices
    )
    changed_at = models.DateTimeField(default=timezone.now)
    reason = models.CharField(
        max_length=50,
        choices=[
            ('upgrade', 'Upgrade'),
            ('downgrade', 'Downgrade'),
            ('lapsed', 'Subscription Lapsed'),
            ('manual', 'Manual Change'),
        ],
        default='manual'
    )
    
    class Meta:
        db_table = 'subscription_history'
        verbose_name = 'subscription history'
        verbose_name_plural = 'subscription histories'
        ordering = ['-changed_at']
        indexes = [
            models.Index(fields=['subscription', '-changed_at']),
        ]
    
    def __str__(self) -> str:
        return f"{self.subscription.user.email}: {self.from_tier} -> {self.to_tier}"
