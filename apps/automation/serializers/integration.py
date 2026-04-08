"""
IntegrationSerializer for user-installed integrations.

Handles serialization for Integration model with nested integration type data.
Requirements: 5.1-5.7
"""

from rest_framework import serializers
from apps.automation.models import Integration, IntegrationTypeModel
from .integration_type import IntegrationTypeSerializer


class IntegrationSerializer(serializers.ModelSerializer):
    """
    Serializer for Integration model.
    
    Includes user, integration_type, scopes, permissions, status, and timestamps.
    Excludes encrypted token fields for security.
    Provides nested integration_type data.
    
    Requirements: 5.1-5.7
    """
    
    # Nested integration type data (read-only)
    integration_type_detail = IntegrationTypeSerializer(
        source='integration_type',
        read_only=True
    )
    
    # Write-only field for creating integrations
    integration_type_id = serializers.UUIDField(write_only=True, required=False)
    
    # Computed fields
    is_token_expired = serializers.BooleanField(read_only=True)
    has_refresh_token = serializers.BooleanField(read_only=True)
    
    # Health monitoring fields
    health_status = serializers.CharField(read_only=True)
    last_successful_sync_at = serializers.DateTimeField(read_only=True)
    consecutive_failures = serializers.IntegerField(read_only=True)
    
    # Meta-specific fields (for WhatsApp integrations)
    waba_id = serializers.CharField(read_only=True, allow_null=True)
    phone_number_id = serializers.CharField(read_only=True, allow_null=True)
    business_id = serializers.CharField(read_only=True, allow_null=True)
    
    class Meta:
        model = Integration
        fields = [
            'id',
            'user',
            'integration_type',
            'integration_type_id',
            'integration_type_detail',
            'scopes',
            'steering_rules',
            'permissions',
            'token_expires_at',
            'status',
            'is_active',
            'is_token_expired',
            'has_refresh_token',
            'health_status',
            'last_successful_sync_at',
            'consecutive_failures',
            'waba_id',
            'phone_number_id',
            'business_id',
            'user_config',
            'created_at',
            'updated_at',
        ]
        read_only_fields = [
            'id',
            'user',
            'integration_type',
            'is_token_expired',
            'has_refresh_token',
            'created_at',
            'updated_at',
        ]
        # Explicitly exclude encrypted token fields
        extra_kwargs = {
            'oauth_token_encrypted': {'write_only': True},
            'refresh_token_encrypted': {'write_only': True},
        }
    
    def validate_integration_type_id(self, value):
        """
        Validate that the integration type exists and is active.
        """
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
    
    def validate_scopes(self, value):
        """
        Validate scopes format.
        
        Ensures scopes is a list of strings.
        """
        if not isinstance(value, list):
            raise serializers.ValidationError("Scopes must be a list")
        
        if not all(isinstance(scope, str) for scope in value):
            raise serializers.ValidationError("All scopes must be strings")
        
        return value
    
    def validate_permissions(self, value):
        """
        Validate permissions format.
        
        Ensures permissions is a dictionary.
        """
        if not isinstance(value, dict):
            raise serializers.ValidationError("Permissions must be a dictionary")
        
        return value
    
    def validate_steering_rules(self, value):
        """
        Validate steering rules format.
        
        Ensures steering_rules is a dictionary.
        """
        if not isinstance(value, dict):
            raise serializers.ValidationError("Steering rules must be a dictionary")
        
        return value
    
    def validate(self, attrs):
        """
        Object-level validation.
        
        Ensures user doesn't already have this integration type installed.
        """
        # Only validate on create
        if self.instance is None:
            user = self.context.get('request').user if self.context.get('request') else None
            integration_type_id = attrs.get('integration_type_id')
            
            if user and integration_type_id:
                # Check if user already has this integration type
                if Integration.objects.filter(
                    user=user,
                    integration_type_id=integration_type_id
                ).exists():
                    raise serializers.ValidationError(
                        "You have already installed this integration type"
                    )
        
        return attrs
    
    def create(self, validated_data):
        """
        Create integration with user from request context.
        """
        # Get user from request context
        request = self.context.get('request')
        if request and hasattr(request, 'user'):
            validated_data['user'] = request.user
        
        # Handle integration_type_id
        integration_type_id = validated_data.pop('integration_type_id', None)
        if integration_type_id:
            validated_data['integration_type_id'] = integration_type_id
        
        return super().create(validated_data)
    
    def to_representation(self, instance):
        """
        Customize output representation.
        
        Ensures encrypted token fields are never exposed.
        """
        data = super().to_representation(instance)
        
        # Double-check that encrypted fields are not in response
        data.pop('oauth_token_encrypted', None)
        data.pop('refresh_token_encrypted', None)
        
        return data


class IntegrationListSerializer(serializers.ModelSerializer):
    """
    Lightweight serializer for listing integrations.
    
    Used for list views where full nested data is not needed.
    """
    
    integration_type_name = serializers.CharField(
        source='integration_type.name',
        read_only=True
    )
    integration_type_icon = serializers.FileField(
        source='integration_type.icon',
        read_only=True
    )
    integration_type_category = serializers.CharField(
        source='integration_type.category',
        read_only=True
    )
    
    class Meta:
        model = Integration
        fields = [
            'id',
            'integration_type',
            'integration_type_name',
            'integration_type_icon',
            'integration_type_category',
            'is_active',
            'is_token_expired',
            'created_at',
        ]
        read_only_fields = fields
