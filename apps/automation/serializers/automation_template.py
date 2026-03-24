"""
AutomationTemplateSerializer for pre-configured workflows.

Handles serialization and validation for AutomationTemplate model.
Requirements: 6.1-6.7
"""

from rest_framework import serializers
from apps.automation.models import AutomationTemplate, TriggerType, IntegrationTypeModel


class AutomationTemplateSerializer(serializers.ModelSerializer):
    """
    Serializer for AutomationTemplate model.
    
    Includes all fields and validates step structure.
    
    Requirements: 6.1-6.7
    """
    
    # Nested integration type name for display
    integration_type_name = serializers.CharField(
        source='integration_type.name',
        read_only=True
    )
    
    # Write-only field for creating templates
    integration_type_id = serializers.UUIDField(write_only=True, required=False)
    
    # Computed field
    step_count = serializers.SerializerMethodField()
    
    class Meta:
        model = AutomationTemplate
        fields = [
            'id',
            'integration_type',
            'integration_type_id',
            'integration_type_name',
            'name',
            'description',
            'trigger_type',
            'trigger_config',
            'steps',
            'step_count',
            'is_enabled_by_default',
            'is_active',
            'created_at',
            'updated_at',
        ]
        read_only_fields = [
            'id',
            'integration_type',
            'integration_type_name',
            'step_count',
            'created_at',
            'updated_at',
        ]
    
    def get_step_count(self, obj) -> int:
        """Get the number of steps in this template."""
        return len(obj.get_steps_list())
    
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
    
    def validate_trigger_type(self, value):
        """
        Validate trigger type is one of the allowed values.
        """
        if value not in [choice[0] for choice in TriggerType.choices]:
            raise serializers.ValidationError(
                f"Invalid trigger type. Must be one of: "
                f"{', '.join([choice[0] for choice in TriggerType.choices])}"
            )
        return value
    
    def validate_trigger_config(self, value):
        """
        Validate trigger configuration format.
        
        Ensures trigger_config is a dictionary.
        """
        if not isinstance(value, dict):
            raise serializers.ValidationError("Trigger config must be a dictionary")
        
        return value
    
    def validate_steps(self, value):
        """
        Validate step structure.
        
        Requirements: 6.6
        - Steps must be a list
        - Each step must have action_type and integration_type_id
        - Parameters must be a dictionary
        """
        if not isinstance(value, list):
            raise serializers.ValidationError("Steps must be a list")
        
        if not value:
            raise serializers.ValidationError("At least one step is required")
        
        for i, step in enumerate(value):
            if not isinstance(step, dict):
                raise serializers.ValidationError(
                    f"Step {i}: must be a dictionary"
                )
            
            # Check required fields
            if 'action_type' not in step:
                raise serializers.ValidationError(
                    f"Step {i}: missing required field 'action_type'"
                )
            
            if 'integration_type_id' not in step:
                raise serializers.ValidationError(
                    f"Step {i}: missing required field 'integration_type_id'"
                )
            
            # Validate action_type is a string
            if not isinstance(step['action_type'], str):
                raise serializers.ValidationError(
                    f"Step {i}: 'action_type' must be a string"
                )
            
            # Validate integration_type_id format (should be UUID string)
            integration_type_id = step['integration_type_id']
            if not isinstance(integration_type_id, str):
                raise serializers.ValidationError(
                    f"Step {i}: 'integration_type_id' must be a string (UUID)"
                )
            
            # Validate parameters if present
            if 'parameters' in step:
                if not isinstance(step['parameters'], dict):
                    raise serializers.ValidationError(
                        f"Step {i}: 'parameters' must be a dictionary"
                    )
        
        return value
    
    def validate(self, attrs):
        """
        Object-level validation.
        
        Additional validation for template structure.
        """
        # Validate trigger_config based on trigger_type
        trigger_type = attrs.get('trigger_type')
        trigger_config = attrs.get('trigger_config', {})
        
        if trigger_type == TriggerType.SCHEDULED:
            # Scheduled triggers should have schedule information
            if not trigger_config.get('schedule'):
                raise serializers.ValidationError({
                    'trigger_config': "Scheduled triggers must include 'schedule' field"
                })
        
        elif trigger_type == TriggerType.EVENT_DRIVEN:
            # Event-driven triggers should have event type
            if not trigger_config.get('event_type'):
                raise serializers.ValidationError({
                    'trigger_config': "Event-driven triggers must include 'event_type' field"
                })
        
        return attrs
    
    def create(self, validated_data):
        """
        Create automation template.
        
        Handles integration_type_id conversion.
        """
        # Handle integration_type_id
        integration_type_id = validated_data.pop('integration_type_id', None)
        if integration_type_id:
            validated_data['integration_type_id'] = integration_type_id
        
        return super().create(validated_data)
    
    def update(self, instance, validated_data):
        """
        Update automation template.
        
        Handles integration_type_id conversion.
        """
        # Handle integration_type_id
        integration_type_id = validated_data.pop('integration_type_id', None)
        if integration_type_id:
            validated_data['integration_type_id'] = integration_type_id
        
        return super().update(instance, validated_data)


class AutomationTemplateListSerializer(serializers.ModelSerializer):
    """
    Lightweight serializer for listing automation templates.
    
    Used for list views where full step data is not needed.
    """
    
    integration_type_name = serializers.CharField(
        source='integration_type.name',
        read_only=True
    )
    step_count = serializers.SerializerMethodField()
    
    class Meta:
        model = AutomationTemplate
        fields = [
            'id',
            'integration_type',
            'integration_type_name',
            'name',
            'description',
            'trigger_type',
            'step_count',
            'is_enabled_by_default',
            'is_active',
            'created_at',
        ]
        read_only_fields = fields
    
    def get_step_count(self, obj) -> int:
        """Get the number of steps in this template."""
        return len(obj.get_steps_list())
