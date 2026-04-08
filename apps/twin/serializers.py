"""
Twin API serializers.

Requirements: 2.1-2.6, 13.2, 15.3, 15.4
"""

from rest_framework import serializers
from .dataclasses import AIModel
from apps.credits.enums import BrainMode, OperationType
from apps.credits.constants import BRAIN_MODE_TIER_REQUIREMENTS


class OnboardingStartResponseSerializer(serializers.Serializer):
    """Serializer for onboarding start response."""
    
    status = serializers.CharField(read_only=True)
    message = serializers.CharField(read_only=True, required=False)
    twin_id = serializers.UUIDField(read_only=True, required=False)
    questionnaire = serializers.DictField(read_only=True, required=False)
    available_models = serializers.ListField(read_only=True, required=False)
    cognitive_blend = serializers.DictField(read_only=True, required=False)
    saved_responses = serializers.DictField(read_only=True, required=False)


class QuestionnaireResponseSerializer(serializers.Serializer):
    """Serializer for questionnaire responses."""
    
    communication_style = serializers.DictField(required=True)
    decision_patterns = serializers.DictField(required=True)
    preferences = serializers.DictField(required=True)


class OnboardingCompleteSerializer(serializers.Serializer):
    """Serializer for completing onboarding."""
    
    responses = QuestionnaireResponseSerializer(required=True)
    model = serializers.ChoiceField(
        choices=[m.value for m in AIModel],
        required=True,
        help_text="Selected AI model"
    )
    cognitive_blend = serializers.IntegerField(
        min_value=0,
        max_value=100,
        required=True,
        help_text="Cognitive blend value (0-100)"
    )


class TwinSerializer(serializers.Serializer):
    """Serializer for Twin response."""
    
    id = serializers.UUIDField(read_only=True)
    user_id = serializers.UUIDField(read_only=True)
    model = serializers.CharField(read_only=True)
    cognitive_blend = serializers.IntegerField(read_only=True)
    blend_mode = serializers.CharField(read_only=True)
    requires_confirmation = serializers.BooleanField(read_only=True)
    is_active = serializers.BooleanField(read_only=True)
    kill_switch_active = serializers.BooleanField(read_only=True)
    csm_profile_id = serializers.UUIDField(read_only=True, allow_null=True)
    created_at = serializers.DateTimeField(read_only=True)
    updated_at = serializers.DateTimeField(read_only=True)


class CognitiveBlendUpdateSerializer(serializers.Serializer):
    """Serializer for updating cognitive blend."""
    
    cognitive_blend = serializers.IntegerField(
        min_value=0,
        max_value=100,
        required=True,
        help_text="New cognitive blend value (0-100)"
    )


class OnboardingProgressSerializer(serializers.Serializer):
    """Serializer for saving onboarding progress."""
    
    responses = serializers.DictField(required=False)
    model = serializers.CharField(required=False)
    cognitive_blend = serializers.IntegerField(
        min_value=0,
        max_value=100,
        required=False
    )



class TwinChatRequestSerializer(serializers.Serializer):
    """
    Serializer for Twin chat request.
    
    Requirements: 15.1, 15.2, 15.3, 15.4
    """
    
    message = serializers.CharField(
        required=True,
        max_length=10000,
        help_text="User's message/prompt"
    )
    brain_mode = serializers.ChoiceField(
        choices=[mode.value for mode in BrainMode],
        required=False,
        allow_null=True,
        help_text="Brain intelligence level (optional, uses user preference if not provided)"
    )
    operation_type = serializers.ChoiceField(
        choices=[op.value for op in OperationType],
        required=False,
        default='long_response',
        help_text="Type of operation (default: long_response)"
    )
    context = serializers.DictField(
        required=False,
        default=dict,
        help_text="Optional context dictionary"
    )
    
    def validate_brain_mode(self, value):
        """
        Validate brain_mode against user's subscription tier.
        
        Requirements: 15.3, 15.4
        """
        if value is None:
            return value
        
        # Get user from context
        request = self.context.get('request')
        if not request or not request.user:
            raise serializers.ValidationError("User not authenticated")
        
        user = request.user
        
        # Get user's subscription tier
        try:
            user_tier = user.subscription.tier.upper()
        except AttributeError:
            # If no subscription exists, default to FREE
            user_tier = 'FREE'
        
        # Check if user's tier allows this brain mode
        allowed_tiers = BRAIN_MODE_TIER_REQUIREMENTS.get(value, [])
        
        if user_tier not in allowed_tiers:
            # Find required tier
            tier_hierarchy = ['FREE', 'PRO', 'TWIN_PLUS', 'EXECUTIVE']
            required_tier = None
            for tier in tier_hierarchy:
                if tier in allowed_tiers:
                    required_tier = tier
                    break
            
            raise serializers.ValidationError(
                f"Brain mode '{value}' requires {required_tier} tier or higher. "
                f"Your current tier: {user_tier}"
            )
        
        return value


class TwinGenerateRequestSerializer(serializers.Serializer):
    """
    Serializer for Twin generate request (automation workflows).
    
    Requirements: 9.1-9.11
    """
    
    prompt = serializers.CharField(
        required=True,
        max_length=10000,
        help_text="Generation prompt"
    )
    brain_mode = serializers.ChoiceField(
        choices=[mode.value for mode in BrainMode],
        required=False,
        allow_null=True,
        help_text="Brain intelligence level (optional, uses user preference if not provided)"
    )
    operation_type = serializers.ChoiceField(
        choices=[op.value for op in OperationType],
        required=False,
        default='automation',
        help_text="Type of operation (default: automation)"
    )
    max_tokens = serializers.IntegerField(
        required=False,
        default=1000,
        min_value=1,
        max_value=4000,
        help_text="Maximum tokens for response"
    )
    temperature = serializers.FloatField(
        required=False,
        default=0.7,
        min_value=0.0,
        max_value=2.0,
        help_text="Temperature for response generation"
    )
    context = serializers.DictField(
        required=False,
        default=dict,
        help_text="Optional context dictionary"
    )
    
    def validate_brain_mode(self, value):
        """
        Validate brain_mode against user's subscription tier.
        
        Requirements: 15.3, 15.4
        """
        if value is None:
            return value
        
        # Get user from context
        request = self.context.get('request')
        if not request or not request.user:
            raise serializers.ValidationError("User not authenticated")
        
        user = request.user
        
        # Get user's subscription tier
        try:
            user_tier = user.subscription.tier.upper()
        except AttributeError:
            # If no subscription exists, default to FREE
            user_tier = 'FREE'
        
        # Check if user's tier allows this brain mode
        allowed_tiers = BRAIN_MODE_TIER_REQUIREMENTS.get(value, [])
        
        if user_tier not in allowed_tiers:
            # Find required tier
            tier_hierarchy = ['FREE', 'PRO', 'TWIN_PLUS', 'EXECUTIVE']
            required_tier = None
            for tier in tier_hierarchy:
                if tier in allowed_tiers:
                    required_tier = tier
                    break
            
            raise serializers.ValidationError(
                f"Brain mode '{value}' requires {required_tier} tier or higher. "
                f"Your current tier: {user_tier}"
            )
        
        return value


class TwinChatResponseSerializer(serializers.Serializer):
    """
    Serializer for Twin chat response.
    
    Requirements: 9.11, 15.1, 15.2
    """
    
    response = serializers.CharField(read_only=True)
    metadata = serializers.DictField(read_only=True)
    credits = serializers.DictField(read_only=True)
