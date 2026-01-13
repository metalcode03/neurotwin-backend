"""
Automation API serializers.

Requirements: 7.1-7.6, 8.1-8.6, 13.2
"""

from rest_framework import serializers
from .models import IntegrationType


class IntegrationResponseSerializer(serializers.Serializer):
    """Serializer for integration response."""
    
    id = serializers.UUIDField(read_only=True)
    user_id = serializers.UUIDField(read_only=True)
    type = serializers.CharField(read_only=True)
    type_display = serializers.CharField(read_only=True)
    scopes = serializers.ListField(child=serializers.CharField(), read_only=True)
    steering_rules = serializers.DictField(read_only=True)
    permissions = serializers.DictField(read_only=True)
    token_expires_at = serializers.DateTimeField(read_only=True, allow_null=True)
    is_active = serializers.BooleanField(read_only=True)
    is_token_expired = serializers.BooleanField(read_only=True)
    created_at = serializers.DateTimeField(read_only=True)


class ConnectIntegrationSerializer(serializers.Serializer):
    """Serializer for connecting an integration."""
    
    oauth_code = serializers.CharField(
        required=True,
        help_text="OAuth authorization code"
    )
    redirect_uri = serializers.CharField(
        required=False,
        default="",
        help_text="OAuth redirect URI"
    )
    requested_scopes = serializers.ListField(
        child=serializers.CharField(),
        required=False,
        help_text="Specific scopes to request (optional)"
    )


class UpdatePermissionsSerializer(serializers.Serializer):
    """Serializer for updating integration permissions."""
    
    permissions = serializers.DictField(
        child=serializers.BooleanField(),
        required=True,
        help_text="Permission name to granted status mapping"
    )


class UpdateSteeringRulesSerializer(serializers.Serializer):
    """Serializer for updating steering rules."""
    
    steering_rules = serializers.DictField(
        required=True,
        help_text="Steering rules configuration"
    )


# Workflow serializers

class WorkflowStepSerializer(serializers.Serializer):
    """Serializer for a workflow step."""
    
    integration = serializers.ChoiceField(
        choices=[t.value for t in IntegrationType],
        required=True
    )
    action = serializers.CharField(required=True)
    parameters = serializers.DictField(required=False, default=dict)
    requires_confirmation = serializers.BooleanField(required=False, default=False)
    order = serializers.IntegerField(required=False, default=0)


class CreateWorkflowSerializer(serializers.Serializer):
    """Serializer for creating a workflow."""
    
    name = serializers.CharField(max_length=255, required=True)
    trigger_config = serializers.DictField(required=True)
    steps = WorkflowStepSerializer(many=True, required=True)


class WorkflowResponseSerializer(serializers.Serializer):
    """Serializer for workflow response."""
    
    id = serializers.UUIDField(read_only=True)
    user_id = serializers.UUIDField(read_only=True)
    name = serializers.CharField(read_only=True)
    trigger_config = serializers.DictField(read_only=True)
    steps = WorkflowStepSerializer(many=True, read_only=True)
    is_active = serializers.BooleanField(read_only=True)
    created_at = serializers.DateTimeField(read_only=True)


class ExecuteWorkflowSerializer(serializers.Serializer):
    """Serializer for executing a workflow."""
    
    permission_flag = serializers.BooleanField(
        required=True,
        help_text="Must be True to execute external actions"
    )
    cognitive_blend = serializers.IntegerField(
        min_value=0,
        max_value=100,
        required=False,
        default=50,
        help_text="Cognitive blend value (0-100)"
    )
    confirmation_token = serializers.CharField(
        required=False,
        allow_null=True,
        help_text="Token for confirming high-blend actions"
    )


class WorkflowResultSerializer(serializers.Serializer):
    """Serializer for workflow execution result."""
    
    success = serializers.BooleanField(read_only=True)
    workflow_id = serializers.UUIDField(read_only=True)
    steps_completed = serializers.IntegerField(read_only=True)
    total_steps = serializers.IntegerField(read_only=True)
    error = serializers.CharField(read_only=True, allow_null=True)
    requires_confirmation = serializers.BooleanField(read_only=True)
    is_twin_generated = serializers.BooleanField(read_only=True)
