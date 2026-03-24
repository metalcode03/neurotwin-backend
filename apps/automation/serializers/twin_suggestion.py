"""
Twin Suggestion Serializers.

Requirements: 8.6
"""

from rest_framework import serializers

from apps.automation.models import TwinSuggestion, SuggestionStatus


class TwinSuggestionSerializer(serializers.ModelSerializer):
    """Serializer for Twin workflow suggestions."""
    
    workflow_name = serializers.CharField(
        source='workflow.name',
        read_only=True
    )
    workflow_id = serializers.UUIDField(
        source='workflow.id',
        read_only=True
    )
    is_expired = serializers.BooleanField(read_only=True)
    is_pending = serializers.BooleanField(read_only=True)
    
    class Meta:
        model = TwinSuggestion
        fields = [
            'id',
            'workflow_id',
            'workflow_name',
            'suggested_changes',
            'reasoning',
            'cognitive_blend_value',
            'based_on_pattern',
            'status',
            'reviewed_at',
            'review_notes',
            'created_at',
            'expires_at',
            'is_expired',
            'is_pending',
        ]
        read_only_fields = [
            'id',
            'workflow_id',
            'workflow_name',
            'status',
            'reviewed_at',
            'created_at',
            'expires_at',
            'is_expired',
            'is_pending',
        ]


class CreateTwinSuggestionSerializer(serializers.Serializer):
    """Serializer for creating Twin suggestions."""
    
    workflow_id = serializers.UUIDField(required=True)
    suggested_changes = serializers.JSONField(required=True)
    reasoning = serializers.CharField(
        required=True,
        min_length=10,
        max_length=2000
    )
    cognitive_blend_value = serializers.IntegerField(
        required=True,
        min_value=0,
        max_value=100
    )
    based_on_pattern = serializers.CharField(
        required=False,
        allow_blank=True,
        max_length=1000
    )
    expires_in_days = serializers.IntegerField(
        required=False,
        default=7,
        min_value=1,
        max_value=30
    )
    
    def validate_suggested_changes(self, value):
        """Validate suggested changes is not empty."""
        if not value or not isinstance(value, dict):
            raise serializers.ValidationError(
                'Suggested changes must be a non-empty dictionary'
            )
        return value


class ReviewTwinSuggestionSerializer(serializers.Serializer):
    """Serializer for reviewing (approving/rejecting) Twin suggestions."""
    
    action = serializers.ChoiceField(
        choices=['approve', 'reject'],
        required=True
    )
    review_notes = serializers.CharField(
        required=False,
        allow_blank=True,
        max_length=1000
    )
