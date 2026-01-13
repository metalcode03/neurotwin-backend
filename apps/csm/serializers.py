"""
CSM API serializers.

Requirements: 4.1-4.7, 13.2
"""

from rest_framework import serializers


class PersonalityTraitsSerializer(serializers.Serializer):
    """Serializer for personality traits."""
    
    openness = serializers.FloatField(min_value=0.0, max_value=1.0)
    conscientiousness = serializers.FloatField(min_value=0.0, max_value=1.0)
    extraversion = serializers.FloatField(min_value=0.0, max_value=1.0)
    agreeableness = serializers.FloatField(min_value=0.0, max_value=1.0)
    neuroticism = serializers.FloatField(min_value=0.0, max_value=1.0)


class TonePreferencesSerializer(serializers.Serializer):
    """Serializer for tone preferences."""
    
    formality = serializers.FloatField(min_value=0.0, max_value=1.0)
    warmth = serializers.FloatField(min_value=0.0, max_value=1.0)
    directness = serializers.FloatField(min_value=0.0, max_value=1.0)
    humor_level = serializers.FloatField(min_value=0.0, max_value=1.0)


class CommunicationHabitsSerializer(serializers.Serializer):
    """Serializer for communication habits."""
    
    preferred_greeting = serializers.CharField(max_length=100)
    sign_off_style = serializers.CharField(max_length=100)
    response_length = serializers.ChoiceField(
        choices=['brief', 'moderate', 'detailed']
    )
    emoji_usage = serializers.ChoiceField(
        choices=['none', 'minimal', 'moderate', 'frequent']
    )


class DecisionStyleSerializer(serializers.Serializer):
    """Serializer for decision style."""
    
    risk_tolerance = serializers.FloatField(min_value=0.0, max_value=1.0)
    speed_vs_accuracy = serializers.FloatField(min_value=0.0, max_value=1.0)
    collaboration_preference = serializers.FloatField(min_value=0.0, max_value=1.0)


class CSMProfileDataSerializer(serializers.Serializer):
    """Serializer for complete CSM profile data."""
    
    personality = PersonalityTraitsSerializer()
    tone = TonePreferencesSerializer()
    vocabulary_patterns = serializers.ListField(
        child=serializers.CharField(max_length=100),
        required=False,
        default=list
    )
    communication = CommunicationHabitsSerializer()
    decision_style = DecisionStyleSerializer()
    custom_rules = serializers.DictField(
        child=serializers.CharField(),
        required=False,
        default=dict
    )


class CSMProfileResponseSerializer(serializers.Serializer):
    """Serializer for CSM profile response."""
    
    id = serializers.UUIDField(read_only=True)
    user_id = serializers.UUIDField(read_only=True)
    version = serializers.IntegerField(read_only=True)
    profile_data = CSMProfileDataSerializer(read_only=True)
    is_current = serializers.BooleanField(read_only=True)
    created_at = serializers.DateTimeField(read_only=True)
    updated_at = serializers.DateTimeField(read_only=True)


class CSMProfileUpdateSerializer(serializers.Serializer):
    """Serializer for updating CSM profile."""
    
    personality = PersonalityTraitsSerializer(required=False)
    tone = TonePreferencesSerializer(required=False)
    vocabulary_patterns = serializers.ListField(
        child=serializers.CharField(max_length=100),
        required=False
    )
    communication = CommunicationHabitsSerializer(required=False)
    decision_style = DecisionStyleSerializer(required=False)
    custom_rules = serializers.DictField(
        child=serializers.CharField(),
        required=False
    )


class CSMVersionHistorySerializer(serializers.Serializer):
    """Serializer for CSM version history item."""
    
    id = serializers.UUIDField(read_only=True)
    version = serializers.IntegerField(read_only=True)
    is_current = serializers.BooleanField(read_only=True)
    created_at = serializers.DateTimeField(read_only=True)


class CSMRollbackSerializer(serializers.Serializer):
    """Serializer for CSM rollback request."""
    
    version = serializers.IntegerField(
        min_value=1,
        required=True,
        help_text="Version number to rollback to"
    )
