"""
InstallationSessionSerializer for tracking installation progress.

Handles serialization for InstallationSession model.
Requirements: 11.1-11.7
"""

from rest_framework import serializers
from apps.automation.models import InstallationSession, InstallationStatus


class InstallationSessionSerializer(serializers.ModelSerializer):
    """
    Serializer for InstallationSession model.
    
    Includes status, progress, and error messages.
    Excludes oauth_state for security.
    
    Requirements: 11.1-11.7
    """
    
    # Nested integration type info for display
    integration_type_name = serializers.CharField(
        source='integration_type.name',
        read_only=True
    )
    integration_type_icon = serializers.FileField(
        source='integration_type.icon',
        read_only=True
    )
    
    # Computed fields
    is_complete = serializers.BooleanField(read_only=True)
    is_expired = serializers.BooleanField(read_only=True)
    can_retry = serializers.BooleanField(read_only=True)
    
    class Meta:
        model = InstallationSession
        fields = [
            'id',
            'user',
            'integration_type',
            'integration_type_name',
            'integration_type_icon',
            'status',
            'progress',
            'error_message',
            'retry_count',
            'is_complete',
            'is_expired',
            'can_retry',
            'created_at',
            'updated_at',
            'completed_at',
        ]
        read_only_fields = [
            'id',
            'user',
            'integration_type',
            'integration_type_name',
            'integration_type_icon',
            'is_complete',
            'is_expired',
            'can_retry',
            'created_at',
            'updated_at',
            'completed_at',
        ]
        # Explicitly exclude oauth_state for security
        extra_kwargs = {
            'oauth_state': {'write_only': True},
        }
    
    def validate_status(self, value):
        """
        Validate status is one of the allowed values.
        """
        if value not in [choice[0] for choice in InstallationStatus.choices]:
            raise serializers.ValidationError(
                f"Invalid status. Must be one of: "
                f"{', '.join([choice[0] for choice in InstallationStatus.choices])}"
            )
        return value
    
    def validate_progress(self, value):
        """
        Validate progress is between 0 and 100.
        """
        if not isinstance(value, int):
            raise serializers.ValidationError("Progress must be an integer")
        
        if value < 0 or value > 100:
            raise serializers.ValidationError(
                "Progress must be between 0 and 100"
            )
        
        return value
    
    def to_representation(self, instance):
        """
        Customize output representation.
        
        Ensures oauth_state is never exposed in response.
        """
        data = super().to_representation(instance)
        
        # Double-check that oauth_state is not in response
        data.pop('oauth_state', None)
        
        return data


class InstallationProgressSerializer(serializers.Serializer):
    """
    Serializer for installation progress polling endpoint.
    
    Lightweight serializer for real-time progress updates.
    Requirements: 11.2-11.5
    """
    
    session_id = serializers.UUIDField(read_only=True, source='id')
    status = serializers.CharField(read_only=True)
    progress = serializers.IntegerField(read_only=True)
    message = serializers.SerializerMethodField()
    error_message = serializers.CharField(read_only=True)
    is_complete = serializers.BooleanField(read_only=True)
    can_retry = serializers.BooleanField(read_only=True)
    
    def get_message(self, obj) -> str:
        """
        Get user-friendly status message.
        """
        status_messages = {
            InstallationStatus.DOWNLOADING: "Downloading integration...",
            InstallationStatus.OAUTH_SETUP: "Setting up authentication...",
            InstallationStatus.COMPLETED: "Installation completed successfully!",
            InstallationStatus.FAILED: "Installation failed. Please try again.",
        }
        return status_messages.get(obj.status, "Processing...")


class InstallationStartSerializer(serializers.Serializer):
    """
    Serializer for starting an installation.
    
    Used for POST /api/v1/integrations/install/ endpoint.
    Requirements: 10.4
    """
    
    integration_type_id = serializers.UUIDField(required=True)
    
    def validate_integration_type_id(self, value):
        """
        Validate that the integration type exists and is active.
        """
        from apps.automation.models import IntegrationTypeModel
        
        try:
            integration_type = IntegrationTypeModel.objects.get(id=value)
            if not integration_type.is_active:
                raise serializers.ValidationError(
                    "This integration type is not currently available"
                )
            return value
        except IntegrationTypeModel.DoesNotExist:
            raise serializers.ValidationError(
                f"Integration type with id '{value}' does not exist"
            )
    
    def validate(self, attrs):
        """
        Object-level validation.
        
        Check if user already has this integration installed.
        """
        from apps.automation.models import Integration
        
        request = self.context.get('request')
        if request and hasattr(request, 'user'):
            user = request.user
            integration_type_id = attrs['integration_type_id']
            
            # Check if already installed
            if Integration.objects.filter(
                user=user,
                integration_type_id=integration_type_id
            ).exists():
                raise serializers.ValidationError(
                    "You have already installed this integration type"
                )
        
        return attrs


class InstallationResponseSerializer(serializers.Serializer):
    """
    Serializer for installation start response.
    
    Returns session ID and OAuth URL for Phase 2.
    """
    
    session_id = serializers.UUIDField()
    oauth_url = serializers.CharField()  # URL already validated upstream in OAuthClient
    status = serializers.CharField()
    message = serializers.CharField()
