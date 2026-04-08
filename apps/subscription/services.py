"""
Subscription service for NeuroTwin platform.

Handles subscription management, tier features, and feature access control.
Requirements: 3.2, 3.3, 3.4, 3.5, 3.6, 3.7
"""

from typing import Optional
from datetime import datetime

from django.db import transaction
from django.utils import timezone

from .models import Subscription, SubscriptionHistory, SubscriptionTier
from .dataclasses import TierFeatures


class SubscriptionService:
    """
    Manages subscriptions and feature access.
    
    Provides methods for subscription management, tier changes, and feature access control.
    """
    
    # Tier hierarchy for upgrade/downgrade determination
    TIER_HIERARCHY = {
        SubscriptionTier.FREE: 0,
        SubscriptionTier.PRO: 1,
        SubscriptionTier.TWIN_PLUS: 2,
        SubscriptionTier.EXECUTIVE: 3,
    }
    
    # Feature mapping for access control
    FEATURE_TIER_REQUIREMENTS = {
        'cognitive_learning': SubscriptionTier.PRO,
        'voice_twin': SubscriptionTier.TWIN_PLUS,
        'autonomous_workflows': SubscriptionTier.EXECUTIVE,
        'custom_models': SubscriptionTier.EXECUTIVE,
        'gemini_pro': SubscriptionTier.PRO,
    }
    
    def get_subscription(self, user_id: str) -> Subscription:
        """
        Get user's current subscription.
        
        Creates a free subscription if none exists.
        
        Args:
            user_id: The user's ID
            
        Returns:
            The user's subscription
        """
        subscription, created = Subscription.objects.get_or_create(
            user_id=user_id,
            defaults={
                'tier': SubscriptionTier.FREE,
                'is_active': True,
            }
        )
        return subscription
    
    def get_tier_features(self, tier: str) -> TierFeatures:
        """
        Get features available for a tier.
        
        Requirements: 3.2, 3.3, 3.4, 3.5
        
        Args:
            tier: The subscription tier name
            
        Returns:
            TierFeatures for the specified tier
        """
        tier_map = {
            SubscriptionTier.FREE: TierFeatures.free_tier,
            SubscriptionTier.PRO: TierFeatures.pro_tier,
            SubscriptionTier.TWIN_PLUS: TierFeatures.twin_plus_tier,
            SubscriptionTier.EXECUTIVE: TierFeatures.executive_tier,
            # Also support string values
            'free': TierFeatures.free_tier,
            'pro': TierFeatures.pro_tier,
            'twin_plus': TierFeatures.twin_plus_tier,
            'executive': TierFeatures.executive_tier,
        }
        
        factory = tier_map.get(tier, TierFeatures.free_tier)
        return factory()
    
    def _is_upgrade(self, from_tier: str, to_tier: str) -> bool:
        """Check if tier change is an upgrade."""
        from_level = self.TIER_HIERARCHY.get(from_tier, 0)
        to_level = self.TIER_HIERARCHY.get(to_tier, 0)
        return to_level > from_level
    
    def _is_downgrade(self, from_tier: str, to_tier: str) -> bool:
        """Check if tier change is a downgrade."""
        from_level = self.TIER_HIERARCHY.get(from_tier, 0)
        to_level = self.TIER_HIERARCHY.get(to_tier, 0)
        return to_level < from_level
    
    @transaction.atomic
    def upgrade(
        self, 
        user_id: str, 
        new_tier: str,
        expires_at: Optional[datetime] = None
    ) -> Subscription:
        """
        Upgrade subscription and enable features immediately.
        
        Requirements: 3.6
        - Adjust feature access immediately
        - Preserve existing data
        
        Args:
            user_id: The user's ID
            new_tier: The new subscription tier
            expires_at: Optional expiration date for the subscription
            
        Returns:
            Updated subscription
            
        Raises:
            ValueError: If new_tier is not higher than current tier
        """
        subscription = self.get_subscription(user_id)
        old_tier = subscription.tier
        
        # Validate this is actually an upgrade
        if not self._is_upgrade(old_tier, new_tier):
            raise ValueError(
                f"Cannot upgrade from {old_tier} to {new_tier}. "
                f"Use downgrade() for tier reductions."
            )
        
        # Record history
        SubscriptionHistory.objects.create(
            subscription=subscription,
            from_tier=old_tier,
            to_tier=new_tier,
            reason='upgrade'
        )
        
        # Update subscription
        subscription.previous_tier = old_tier
        subscription.tier = new_tier
        subscription.tier_changed_at = timezone.now()
        subscription.started_at = timezone.now()
        subscription.expires_at = expires_at
        subscription.is_active = True
        subscription.save()
        
        return subscription
    
    @transaction.atomic
    def downgrade(
        self, 
        user_id: str, 
        new_tier: str,
        reason: str = 'downgrade'
    ) -> Subscription:
        """
        Downgrade subscription while preserving data.
        
        Requirements: 3.6
        - Adjust feature access immediately
        - Preserve existing data (user data is NOT deleted)
        
        Args:
            user_id: The user's ID
            new_tier: The new subscription tier
            reason: Reason for downgrade ('downgrade', 'lapsed', 'manual')
            
        Returns:
            Updated subscription
            
        Raises:
            ValueError: If new_tier is not lower than current tier
        """
        subscription = self.get_subscription(user_id)
        old_tier = subscription.tier
        
        # Validate this is actually a downgrade
        if not self._is_downgrade(old_tier, new_tier):
            raise ValueError(
                f"Cannot downgrade from {old_tier} to {new_tier}. "
                f"Use upgrade() for tier increases."
            )
        
        # Record history
        SubscriptionHistory.objects.create(
            subscription=subscription,
            from_tier=old_tier,
            to_tier=new_tier,
            reason=reason
        )
        
        # Update subscription
        subscription.previous_tier = old_tier
        subscription.tier = new_tier
        subscription.tier_changed_at = timezone.now()
        
        # Clear expiration for free tier
        if new_tier == SubscriptionTier.FREE:
            subscription.expires_at = None
        
        subscription.save()
        
        return subscription
    
    def check_feature_access(self, user_id: str, feature: str) -> bool:
        """
        Check if user has access to a specific feature.
        
        Requirements: 3.2, 3.3, 3.4, 3.5
        - Provide access to exactly the features defined for that tier
        - Deny access to features of higher tiers
        
        Args:
            user_id: The user's ID
            feature: The feature to check access for
            
        Returns:
            True if user has access, False otherwise
        """
        subscription = self.get_subscription(user_id)
        
        # Check if subscription is lapsed
        if subscription.is_lapsed:
            # Lapsed subscriptions get free tier access
            return self._tier_has_feature(SubscriptionTier.FREE, feature)
        
        return self._tier_has_feature(subscription.tier, feature)
    
    def _tier_has_feature(self, tier: str, feature: str) -> bool:
        """
        Check if a tier has access to a specific feature.
        
        Args:
            tier: The subscription tier
            feature: The feature to check
            
        Returns:
            True if tier has access to feature
        """
        tier_features = self.get_tier_features(tier)
        
        # Check specific features
        feature_checks = {
            'cognitive_learning': tier_features.has_cognitive_learning,
            'voice_twin': tier_features.has_voice_twin,
            'autonomous_workflows': tier_features.has_autonomous_workflows,
            'custom_models': tier_features.has_custom_models,
        }
        
        if feature in feature_checks:
            return feature_checks[feature]
        
        # Check model access
        if feature.startswith('model:'):
            model_name = feature.replace('model:', '')
            return model_name in tier_features.available_models
        
        # Check for specific model names
        if feature in ['gemini-3-flash', 'cerebras', 'mistral', 'gemini-3-pro']:
            return feature in tier_features.available_models
        
        # Unknown features default to False
        return False
    
    @transaction.atomic
    def handle_lapsed_subscription(self, user_id: str) -> Subscription:
        """
        Downgrade to Free tier when subscription lapses.
        
        Requirements: 3.7
        - Automatically downgrade to Free tier
        - Disable premium features
        
        Args:
            user_id: The user's ID
            
        Returns:
            Updated subscription (downgraded to free)
        """
        subscription = self.get_subscription(user_id)
        
        # Only process if subscription is actually lapsed
        if not subscription.is_lapsed:
            return subscription
        
        # Downgrade to free tier
        return self.downgrade(user_id, SubscriptionTier.FREE, reason='lapsed')
    
    def check_and_handle_lapsed(self, user_id: str) -> Subscription:
        """
        Check if subscription is lapsed and handle accordingly.
        
        This is a convenience method that combines checking and handling.
        
        Args:
            user_id: The user's ID
            
        Returns:
            The subscription (possibly downgraded)
        """
        subscription = self.get_subscription(user_id)
        
        if subscription.is_lapsed:
            return self.handle_lapsed_subscription(user_id)
        
        return subscription
    
    def get_subscription_history(self, user_id: str) -> list:
        """
        Get subscription tier change history.
        
        Args:
            user_id: The user's ID
            
        Returns:
            List of SubscriptionHistory entries
        """
        subscription = self.get_subscription(user_id)
        return list(subscription.history.all())
    
    def can_access_model(self, user_id: str, model_name: str) -> bool:
        """
        Check if user can access a specific AI model.
        
        Args:
            user_id: The user's ID
            model_name: The model name to check
            
        Returns:
            True if user can access the model
        """
        subscription = self.check_and_handle_lapsed(user_id)
        tier_features = self.get_tier_features(subscription.tier)
        return model_name in tier_features.available_models
    
    def can_access_brain_mode(self, user_id: str, brain_mode: str) -> bool:
        """
        Check if user can access a specific Brain mode.
        
        Brain mode access is determined by subscription tier:
        - brain: Available to all tiers (FREE, PRO, TWIN_PLUS, EXECUTIVE)
        - brain_pro: Requires PRO tier or higher
        - brain_gen: Requires EXECUTIVE tier only
        
        Requirements: 5.6, 5.7, 5.10
        
        Args:
            user_id: The user's ID
            brain_mode: The brain mode to check ('brain', 'brain_pro', 'brain_gen')
            
        Returns:
            True if user can access the brain mode, False otherwise
        """
        # Import here to avoid circular dependency
        from apps.credits.constants import BRAIN_MODE_TIER_REQUIREMENTS
        
        # Get user's subscription and handle lapsed subscriptions
        subscription = self.check_and_handle_lapsed(user_id)
        
        # Get current tier (uppercase to match constants)
        current_tier = subscription.tier.upper()
        
        # Get allowed tiers for this brain mode
        allowed_tiers = BRAIN_MODE_TIER_REQUIREMENTS.get(brain_mode, [])
        
        # Check if current tier is in allowed tiers
        return current_tier in allowed_tiers
