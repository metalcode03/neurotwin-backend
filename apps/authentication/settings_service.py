"""
User settings service for NeuroTwin platform.

Business logic for managing user settings including brain_mode preferences.
Requirements: 5.8, 15.7, 15.8
"""

from typing import Dict, Any, Optional
from django.db import transaction
from django.core.exceptions import ValidationError

from .user_settings_models import UserSettings, BrainMode
from .models import User
from apps.subscription.models import SubscriptionTier


class UserSettingsService:
    """
    Service for managing user settings.
    
    Handles retrieval and updates of user preferences including brain_mode.
    Requirements: 5.8, 15.7, 15.8
    """
    
    @staticmethod
    def get_or_create_settings(user: User) -> UserSettings:
        """
        Get or create user settings.
        
        Args:
            user: User instance
            
        Returns:
            UserSettings instance
        """
        settings, created = UserSettings.objects.get_or_create(
            user=user,
            defaults={
                'brain_mode': BrainMode.BRAIN,
                'notification_preferences': {}
            }
        )
        return settings
    
    @staticmethod
    def get_settings_data(user: User) -> Dict[str, Any]:
        """
        Get user settings with additional context.
        
        Returns settings data including brain_mode, cognitive_blend from Twin,
        notification_preferences, and subscription_tier.
        
        Args:
            user: User instance
            
        Returns:
            Dictionary with settings data
            
        Requirements: 15.7
        """
        # Get or create settings
        settings = UserSettingsService.get_or_create_settings(user)
        
        # Get cognitive_blend from Twin if exists
        cognitive_blend = 50  # Default
        try:
            twin = user.twin
            if twin and twin.is_active:
                cognitive_blend = twin.cognitive_blend
        except AttributeError:
            pass
        
        # Get subscription tier
        subscription_tier = SubscriptionTier.FREE
        try:
            subscription = user.subscription
            if subscription:
                subscription_tier = subscription.tier
        except AttributeError:
            pass
        
        return {
            'brain_mode': settings.brain_mode,
            'cognitive_blend': cognitive_blend,
            'notification_preferences': settings.notification_preferences,
            'subscription_tier': subscription_tier
        }
    
    @staticmethod
    def update_brain_mode(user: User, brain_mode: str) -> UserSettings:
        """
        Update user's brain_mode preference.
        
        Validates brain_mode against user's subscription tier before updating.
        
        Args:
            user: User instance
            brain_mode: New brain mode value
            
        Returns:
            Updated UserSettings instance
            
        Raises:
            ValidationError: If brain_mode is not allowed for user's tier
            
        Requirements: 15.8, 15.9, 15.10
        """
        # Get or create settings
        settings = UserSettingsService.get_or_create_settings(user)
        
        # Get user's subscription tier
        try:
            subscription = user.subscription
            tier = subscription.tier
        except AttributeError:
            tier = SubscriptionTier.FREE
        
        # Validate brain_mode against tier
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
        
        allowed_tiers = tier_requirements.get(brain_mode, [])
        if tier not in allowed_tiers:
            required_tier_names = {
                BrainMode.BRAIN_PRO: 'PRO',
                BrainMode.BRAIN_GEN: 'EXECUTIVE'
            }
            required = required_tier_names.get(brain_mode, 'UNKNOWN')
            raise ValidationError(
                f'Brain mode {dict(BrainMode.choices).get(brain_mode)} requires {required} tier or higher. '
                f'Your current tier is {tier}.'
            )
        
        # Update brain_mode
        with transaction.atomic():
            settings.brain_mode = brain_mode
            settings.save()
        
        return settings
    
    @staticmethod
    def validate_brain_mode_access(user: User, brain_mode: str) -> bool:
        """
        Check if user has access to specified brain_mode.
        
        Args:
            user: User instance
            brain_mode: Brain mode to check
            
        Returns:
            True if user has access, False otherwise
            
        Requirements: 5.6, 5.7, 5.10
        """
        # Get user's subscription tier
        try:
            subscription = user.subscription
            tier = subscription.tier
        except AttributeError:
            tier = SubscriptionTier.FREE
        
        # Define tier requirements
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
        
        allowed_tiers = tier_requirements.get(brain_mode, [])
        return tier in allowed_tiers
