"""
Safety API serializers.

Requirements: 10.1-10.7, 11.1-11.5, 12.1-12.6, 13.1
"""

from rest_framework import serializers


class PermissionUpdateSerializer(serializers.Serializer):
    """Serializer for updating a permission scope."""
    
    integration = serializers.CharField(
        max_length=50,
        help_text="Integration name"
    )
    action_type = serializers.CharField(
        max_length=50,
        help_text="Action type"
    )
    is_granted = serializers.BooleanField(
        required=False,
        help_text="Whether permission is granted"
    )
    requires_approval = serializers.BooleanField(
        required=False,
        help_text="Whether per-action approval is required"
    )
    reason = serializers.CharField(
        max_length=500,
        required=False,
        default="",
        help_text="Reason for the change"
    )


class BulkPermissionUpdateSerializer(serializers.Serializer):
    """Serializer for bulk permission updates."""
    
    permissions = PermissionUpdateSerializer(many=True)


class AuditFilterSerializer(serializers.Serializer):
    """Serializer for filtering audit history."""
    
    start_date = serializers.DateTimeField(
        required=False,
        help_text="Filter entries from this date"
    )
    end_date = serializers.DateTimeField(
        required=False,
        help_text="Filter entries until this date"
    )
    action_type = serializers.CharField(
        max_length=50,
        required=False,
        help_text="Filter by action type"
    )
    target_integration = serializers.CharField(
        max_length=50,
        required=False,
        help_text="Filter by target integration"
    )
    outcome = serializers.ChoiceField(
        choices=['success', 'failure', 'pending', 'blocked'],
        required=False,
        help_text="Filter by outcome"
    )
    limit = serializers.IntegerField(
        min_value=1,
        max_value=500,
        default=100,
        help_text="Maximum number of results"
    )
    offset = serializers.IntegerField(
        min_value=0,
        default=0,
        help_text="Number of results to skip"
    )


class KillSwitchSerializer(serializers.Serializer):
    """Serializer for kill switch activation/deactivation."""
    
    reason = serializers.CharField(
        max_length=500,
        required=False,
        default="",
        help_text="Reason for activation/deactivation"
    )
