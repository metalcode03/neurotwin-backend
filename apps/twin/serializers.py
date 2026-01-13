"""
Twin API serializers.

Requirements: 2.1-2.6, 13.2
"""

from rest_framework import serializers
from .dataclasses import AIModel


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
