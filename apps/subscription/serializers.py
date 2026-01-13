"""
Subscription API serializers.

Requirements: 3.1-3.7, 13.2
"""

from rest_framework import serializers
from .models import SubscriptionTier


class TierFeaturesSerializer(serializers.Serializer):
    """Serializer for tier features."""
    
    tier_name = serializers.CharField(read_only=True)
    available_models = serializers.ListField(
        child=serializers.CharField(),
        read_only=True
    )
    has_cognitive_learning = serializers.BooleanField(read_only=True)
    has_voice_twin = serializers.BooleanField(read_only=True)
    has_autonomous_workflows = serializers.BooleanField(read_only=True)
    has_custom_models = serializers.BooleanField(read_only=True)


class SubscriptionResponseSerializer(serializers.Serializer):
    """Serializer for subscription response."""
    
    id = serializers.UUIDField(read_only=True)
    user_id = serializers.UUIDField(read_only=True)
    tier = serializers.CharField(read_only=True)
    tier_display = serializers.CharField(read_only=True)
    started_at = serializers.DateTimeField(read_only=True)
    expires_at = serializers.DateTimeField(read_only=True, allow_null=True)
    is_active = serializers.BooleanField(read_only=True)
    is_premium = serializers.BooleanField(read_only=True)
    is_lapsed = serializers.BooleanField(read_only=True)
    features = TierFeaturesSerializer(read_only=True)


class SubscriptionUpgradeSerializer(serializers.Serializer):
    """Serializer for subscription upgrade."""
    
    tier = serializers.ChoiceField(
        choices=[t.value for t in SubscriptionTier if t != SubscriptionTier.FREE],
        required=True,
        help_text="Target subscription tier"
    )


class SubscriptionDowngradeSerializer(serializers.Serializer):
    """Serializer for subscription downgrade."""
    
    tier = serializers.ChoiceField(
        choices=[t.value for t in SubscriptionTier],
        required=True,
        help_text="Target subscription tier"
    )


class SubscriptionHistorySerializer(serializers.Serializer):
    """Serializer for subscription history."""
    
    id = serializers.UUIDField(read_only=True)
    from_tier = serializers.CharField(read_only=True)
    to_tier = serializers.CharField(read_only=True)
    changed_at = serializers.DateTimeField(read_only=True)
    reason = serializers.CharField(read_only=True)
