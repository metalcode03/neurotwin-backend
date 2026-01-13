"""
Property-based tests for subscription service.

Feature: neurotwin-platform
Validates: Requirements 3.2, 3.3, 3.4, 3.5, 3.6, 3.7

These tests use Hypothesis to verify subscription properties hold
across a wide range of inputs.
"""

import pytest
from datetime import timedelta
from hypothesis import given, strategies as st, settings, assume
from django.utils import timezone

from apps.subscription.services import SubscriptionService
from apps.subscription.models import Subscription, SubscriptionHistory, SubscriptionTier
from apps.subscription.dataclasses import TierFeatures
from apps.authentication.models import User


# Custom strategies for generating test data
tier_strategy = st.sampled_from([
    SubscriptionTier.FREE,
    SubscriptionTier.PRO,
    SubscriptionTier.TWIN_PLUS,
    SubscriptionTier.EXECUTIVE,
])

# Strategy for tier pairs (for upgrade/downgrade tests)
upgrade_pair_strategy = st.sampled_from([
    (SubscriptionTier.FREE, SubscriptionTier.PRO),
    (SubscriptionTier.FREE, SubscriptionTier.TWIN_PLUS),
    (SubscriptionTier.FREE, SubscriptionTier.EXECUTIVE),
    (SubscriptionTier.PRO, SubscriptionTier.TWIN_PLUS),
    (SubscriptionTier.PRO, SubscriptionTier.EXECUTIVE),
    (SubscriptionTier.TWIN_PLUS, SubscriptionTier.EXECUTIVE),
])

downgrade_pair_strategy = st.sampled_from([
    (SubscriptionTier.PRO, SubscriptionTier.FREE),
    (SubscriptionTier.TWIN_PLUS, SubscriptionTier.FREE),
    (SubscriptionTier.TWIN_PLUS, SubscriptionTier.PRO),
    (SubscriptionTier.EXECUTIVE, SubscriptionTier.FREE),
    (SubscriptionTier.EXECUTIVE, SubscriptionTier.PRO),
    (SubscriptionTier.EXECUTIVE, SubscriptionTier.TWIN_PLUS),
])

# Strategy for features
feature_strategy = st.sampled_from([
    'cognitive_learning',
    'voice_twin',
    'autonomous_workflows',
    'custom_models',
    'gemini-3-flash',
    'qwen',
    'mistral',
    'gemini-3-pro',
])


@pytest.fixture
def subscription_service():
    """Provide a SubscriptionService instance."""
    return SubscriptionService()


def create_test_user(email_suffix: str) -> User:
    """Create a test user with unique email."""
    email = f"sub_test_{email_suffix}@example.com"
    User.objects.filter(email=email).delete()
    return User.objects.create_user(email=email, password="testpass123")


@pytest.mark.django_db(transaction=True)
class TestTierFeatureAccess:
    """
    Property 18: Tier feature access
    
    *For any* user on a given subscription tier, the system SHALL provide
    access to exactly the features defined for that tier and deny access
    to features of higher tiers.
    
    **Validates: Requirements 3.2, 3.3, 3.4, 3.5**
    """
    
    # Define expected features per tier
    TIER_FEATURES = {
        SubscriptionTier.FREE: {
            'cognitive_learning': False,
            'voice_twin': False,
            'autonomous_workflows': False,
            'custom_models': False,
            'gemini-3-flash': True,
            'qwen': True,
            'mistral': True,
            'gemini-3-pro': False,
        },
        SubscriptionTier.PRO: {
            'cognitive_learning': True,
            'voice_twin': False,
            'autonomous_workflows': False,
            'custom_models': False,
            'gemini-3-flash': True,
            'qwen': True,
            'mistral': True,
            'gemini-3-pro': True,
        },
        SubscriptionTier.TWIN_PLUS: {
            'cognitive_learning': True,
            'voice_twin': True,
            'autonomous_workflows': False,
            'custom_models': False,
            'gemini-3-flash': True,
            'qwen': True,
            'mistral': True,
            'gemini-3-pro': True,
        },
        SubscriptionTier.EXECUTIVE: {
            'cognitive_learning': True,
            'voice_twin': True,
            'autonomous_workflows': True,
            'custom_models': True,
            'gemini-3-flash': True,
            'qwen': True,
            'mistral': True,
            'gemini-3-pro': True,
        },
    }
    
    @settings(deadline=None)
    @given(tier=tier_strategy, feature=feature_strategy)
    def test_tier_feature_access(self, tier: str, feature: str):
        """
        Feature: neurotwin-platform, Property 18: Tier feature access
        
        For any tier and feature combination, the system should provide
        access exactly as defined for that tier.
        """
        service = SubscriptionService()
        
        # Create test user
        user = create_test_user(f"{tier}_{feature}_{hash((tier, feature)) % 10000}")
        
        try:
            # Get subscription and set tier
            subscription = service.get_subscription(str(user.id))
            subscription.tier = tier
            subscription.save()
            
            # Check feature access
            has_access = service.check_feature_access(str(user.id), feature)
            expected_access = self.TIER_FEATURES[tier][feature]
            
            assert has_access == expected_access, (
                f"Tier {tier} should {'have' if expected_access else 'NOT have'} "
                f"access to {feature}, but got {has_access}"
            )
        finally:
            # Cleanup
            User.objects.filter(id=user.id).delete()
    
    @settings(deadline=None)
    @given(tier=tier_strategy)
    def test_tier_features_dataclass_matches_service(self, tier: str):
        """
        Feature: neurotwin-platform, Property 18: Tier feature access
        
        The TierFeatures dataclass should match the service's feature access.
        """
        service = SubscriptionService()
        tier_features = service.get_tier_features(tier)
        
        # Verify dataclass fields match expected
        expected = self.TIER_FEATURES[tier]
        
        assert tier_features.has_cognitive_learning == expected['cognitive_learning']
        assert tier_features.has_voice_twin == expected['voice_twin']
        assert tier_features.has_autonomous_workflows == expected['autonomous_workflows']
        assert tier_features.has_custom_models == expected['custom_models']
        
        # Verify model access
        assert ('gemini-3-flash' in tier_features.available_models) == expected['gemini-3-flash']
        assert ('qwen' in tier_features.available_models) == expected['qwen']
        assert ('mistral' in tier_features.available_models) == expected['mistral']
        assert ('gemini-3-pro' in tier_features.available_models) == expected['gemini-3-pro']


@pytest.mark.django_db(transaction=True)
class TestTierChangePreservesData:
    """
    Property 19: Tier change preserves data
    
    *For any* subscription upgrade or downgrade, the system SHALL adjust
    feature access immediately while preserving all existing user data.
    
    **Validates: Requirements 3.6**
    """
    
    @settings(deadline=None)
    @given(tier_pair=upgrade_pair_strategy)
    def test_upgrade_preserves_data(self, tier_pair: tuple):
        """
        Feature: neurotwin-platform, Property 19: Tier change preserves data
        
        For any upgrade, user data should be preserved and feature access
        should change immediately.
        """
        from_tier, to_tier = tier_pair
        service = SubscriptionService()
        
        # Create test user
        user = create_test_user(f"upgrade_{from_tier}_{to_tier}_{hash(tier_pair) % 10000}")
        
        try:
            # Set initial tier
            subscription = service.get_subscription(str(user.id))
            subscription.tier = from_tier
            subscription.save()
            
            # Record initial state
            initial_user_id = str(subscription.user_id)
            initial_created_at = subscription.created_at
            
            # Perform upgrade
            upgraded = service.upgrade(str(user.id), to_tier)
            
            # Verify data preserved
            assert str(upgraded.user_id) == initial_user_id, "User ID should be preserved"
            assert upgraded.created_at == initial_created_at, "Created timestamp should be preserved"
            
            # Verify tier changed
            assert upgraded.tier == to_tier, f"Tier should be {to_tier}"
            
            # Verify history recorded
            history = SubscriptionHistory.objects.filter(
                subscription=upgraded,
                from_tier=from_tier,
                to_tier=to_tier,
                reason='upgrade'
            ).first()
            assert history is not None, "Upgrade should be recorded in history"
            
            # Verify feature access changed immediately
            to_tier_features = service.get_tier_features(to_tier)
            if to_tier_features.has_cognitive_learning:
                assert service.check_feature_access(str(user.id), 'cognitive_learning')
            if to_tier_features.has_voice_twin:
                assert service.check_feature_access(str(user.id), 'voice_twin')
        finally:
            User.objects.filter(id=user.id).delete()
    
    @settings(deadline=None)
    @given(tier_pair=downgrade_pair_strategy)
    def test_downgrade_preserves_data(self, tier_pair: tuple):
        """
        Feature: neurotwin-platform, Property 19: Tier change preserves data
        
        For any downgrade, user data should be preserved and feature access
        should change immediately.
        """
        from_tier, to_tier = tier_pair
        service = SubscriptionService()
        
        # Create test user
        user = create_test_user(f"downgrade_{from_tier}_{to_tier}_{hash(tier_pair) % 10000}")
        
        try:
            # Set initial tier
            subscription = service.get_subscription(str(user.id))
            subscription.tier = from_tier
            subscription.save()
            
            # Record initial state
            initial_user_id = str(subscription.user_id)
            initial_created_at = subscription.created_at
            
            # Perform downgrade
            downgraded = service.downgrade(str(user.id), to_tier)
            
            # Verify data preserved
            assert str(downgraded.user_id) == initial_user_id, "User ID should be preserved"
            assert downgraded.created_at == initial_created_at, "Created timestamp should be preserved"
            
            # Verify tier changed
            assert downgraded.tier == to_tier, f"Tier should be {to_tier}"
            
            # Verify history recorded
            history = SubscriptionHistory.objects.filter(
                subscription=downgraded,
                from_tier=from_tier,
                to_tier=to_tier,
                reason='downgrade'
            ).first()
            assert history is not None, "Downgrade should be recorded in history"
            
            # Verify feature access changed immediately
            to_tier_features = service.get_tier_features(to_tier)
            from_tier_features = service.get_tier_features(from_tier)
            
            # If from_tier had voice_twin but to_tier doesn't, access should be denied
            if from_tier_features.has_voice_twin and not to_tier_features.has_voice_twin:
                assert not service.check_feature_access(str(user.id), 'voice_twin')
        finally:
            User.objects.filter(id=user.id).delete()


@pytest.mark.django_db(transaction=True)
class TestLapsedSubscriptionDowngrade:
    """
    Property 20: Lapsed subscription downgrade
    
    *For any* lapsed subscription, the system SHALL automatically downgrade
    to Free tier and disable premium features.
    
    **Validates: Requirements 3.7**
    """
    
    @settings(deadline=None)
    @given(tier=st.sampled_from([
        SubscriptionTier.PRO,
        SubscriptionTier.TWIN_PLUS,
        SubscriptionTier.EXECUTIVE,
    ]))
    def test_lapsed_subscription_downgrades_to_free(self, tier: str):
        """
        Feature: neurotwin-platform, Property 20: Lapsed subscription downgrade
        
        For any premium tier that lapses, the system should downgrade to free.
        """
        service = SubscriptionService()
        
        # Create test user
        user = create_test_user(f"lapsed_{tier}_{hash(tier) % 10000}")
        
        try:
            # Set premium tier with expired date
            subscription = service.get_subscription(str(user.id))
            subscription.tier = tier
            subscription.expires_at = timezone.now() - timedelta(days=1)  # Expired yesterday
            subscription.save()
            
            # Verify subscription is lapsed
            assert subscription.is_lapsed, "Subscription should be lapsed"
            
            # Handle lapsed subscription
            result = service.handle_lapsed_subscription(str(user.id))
            
            # Verify downgraded to free
            assert result.tier == SubscriptionTier.FREE, "Should be downgraded to FREE"
            
            # Verify history recorded with 'lapsed' reason
            history = SubscriptionHistory.objects.filter(
                subscription=result,
                from_tier=tier,
                to_tier=SubscriptionTier.FREE,
                reason='lapsed'
            ).first()
            assert history is not None, "Lapsed downgrade should be recorded"
            
            # Verify premium features disabled
            assert not service.check_feature_access(str(user.id), 'cognitive_learning')
            assert not service.check_feature_access(str(user.id), 'voice_twin')
            assert not service.check_feature_access(str(user.id), 'autonomous_workflows')
            assert not service.check_feature_access(str(user.id), 'gemini-3-pro')
        finally:
            User.objects.filter(id=user.id).delete()
    
    @settings(deadline=None)
    @given(tier=st.sampled_from([
        SubscriptionTier.PRO,
        SubscriptionTier.TWIN_PLUS,
        SubscriptionTier.EXECUTIVE,
    ]))
    def test_lapsed_subscription_denies_premium_features(self, tier: str):
        """
        Feature: neurotwin-platform, Property 20: Lapsed subscription downgrade
        
        For any lapsed premium subscription, premium features should be denied
        even before explicit downgrade handling.
        """
        service = SubscriptionService()
        
        # Create test user
        user = create_test_user(f"lapsed_deny_{tier}_{hash(tier) % 10000}")
        
        try:
            # Set premium tier with expired date
            subscription = service.get_subscription(str(user.id))
            subscription.tier = tier
            subscription.expires_at = timezone.now() - timedelta(days=1)
            subscription.save()
            
            # Even without calling handle_lapsed_subscription,
            # check_feature_access should deny premium features
            # because it checks is_lapsed internally
            assert not service.check_feature_access(str(user.id), 'cognitive_learning'), \
                "Lapsed subscription should not have cognitive_learning"
            assert not service.check_feature_access(str(user.id), 'voice_twin'), \
                "Lapsed subscription should not have voice_twin"
            assert not service.check_feature_access(str(user.id), 'autonomous_workflows'), \
                "Lapsed subscription should not have autonomous_workflows"
            
            # But free tier features should still work
            assert service.check_feature_access(str(user.id), 'gemini-3-flash'), \
                "Lapsed subscription should still have gemini-3-flash"
            assert service.check_feature_access(str(user.id), 'qwen'), \
                "Lapsed subscription should still have qwen"
        finally:
            User.objects.filter(id=user.id).delete()
    
    @settings(deadline=None)
    @given(tier=tier_strategy)
    def test_non_lapsed_subscription_not_downgraded(self, tier: str):
        """
        Feature: neurotwin-platform, Property 20: Lapsed subscription downgrade
        
        Non-lapsed subscriptions should not be downgraded.
        """
        service = SubscriptionService()
        
        # Create test user
        user = create_test_user(f"not_lapsed_{tier}_{hash(tier) % 10000}")
        
        try:
            # Set tier with future expiration (or no expiration for free)
            subscription = service.get_subscription(str(user.id))
            subscription.tier = tier
            if tier != SubscriptionTier.FREE:
                subscription.expires_at = timezone.now() + timedelta(days=30)
            subscription.save()
            
            # Verify not lapsed
            assert not subscription.is_lapsed, "Subscription should not be lapsed"
            
            # Handle should not change tier
            result = service.handle_lapsed_subscription(str(user.id))
            assert result.tier == tier, f"Tier should remain {tier}"
        finally:
            User.objects.filter(id=user.id).delete()
