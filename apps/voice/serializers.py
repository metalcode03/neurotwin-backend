"""
Voice API serializers.

Requirements: 9.1-9.7, 13.1
"""

from rest_framework import serializers


class EnableVoiceSerializer(serializers.Serializer):
    """Serializer for enabling Voice Twin."""
    
    area_code = serializers.CharField(
        max_length=10,
        required=False,
        help_text="Preferred area code for phone number"
    )
    country_code = serializers.CharField(
        max_length=2,
        default="US",
        help_text="Country code for phone number"
    )


class ApproveSessionSerializer(serializers.Serializer):
    """Serializer for approving voice session."""
    
    duration_minutes = serializers.IntegerField(
        min_value=1,
        max_value=480,
        default=60,
        help_text="Duration of approval in minutes (max 8 hours)"
    )
    reason = serializers.CharField(
        max_length=500,
        required=False,
        default="",
        help_text="Reason for approval"
    )


class MakeCallSerializer(serializers.Serializer):
    """Serializer for making outbound calls."""
    
    target_number = serializers.CharField(
        max_length=20,
        help_text="Target phone number"
    )
    script = serializers.CharField(
        max_length=5000,
        required=False,
        allow_blank=True,
        help_text="Optional script for the call"
    )
    cognitive_blend = serializers.IntegerField(
        min_value=0,
        max_value=100,
        required=False,
        help_text="Cognitive blend value (0-100)"
    )
    permission_flag = serializers.BooleanField(
        default=False,
        help_text="Explicit permission to make call as user"
    )


class CallFilterSerializer(serializers.Serializer):
    """Serializer for filtering call history."""
    
    direction = serializers.ChoiceField(
        choices=['inbound', 'outbound'],
        required=False,
        help_text="Filter by call direction"
    )
    status = serializers.ChoiceField(
        choices=['pending', 'ringing', 'in_progress', 'completed', 'failed', 'terminated'],
        required=False,
        help_text="Filter by call status"
    )
    start_date = serializers.DateTimeField(
        required=False,
        help_text="Filter calls from this date"
    )
    end_date = serializers.DateTimeField(
        required=False,
        help_text="Filter calls until this date"
    )
    limit = serializers.IntegerField(
        min_value=1,
        max_value=100,
        default=50,
        help_text="Maximum number of results"
    )
    offset = serializers.IntegerField(
        min_value=0,
        default=0,
        help_text="Number of results to skip"
    )
