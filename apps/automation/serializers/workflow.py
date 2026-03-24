"""
WorkflowSerializer for user workflows.

Handles serialization and validation for Workflow model.
Requirements: 7.1-7.9
"""

from rest_framework import serializers
from apps.automation.models import Workflow, AutomationTemplate
from .automation_template import AutomationTemplateListSerializer


class WorkflowSerializer(serializers.ModelSerializer):
    """
    Serializer for Workflow model.
    
    Includes all fields with nested automation template data.
    Adds computed field for integration types used.
    
    Requirements: 7.1-7.9
    """
    
    # Nested automation template data (read-only)
    automation_template_detail = AutomationTemplateListSerializer(
        source='automation_template',
        read_only=True
    )
    
    # Write-only field for creating workflows from templates
    automation_template_id = serializers.UUIDField(
        write_only=True,
        required=False,
        allow_null=True
    )
    
    # Computed fields
    integration_types_used = serializers.SerializerMethodField()
    step_count = serializers.SerializerMethodField()
    
    class Meta:
        model = Workflow
        fields = [
            'id',
            'user',
            'automation_template',
            'automation_template_id',
            'automation_template_detail',
            'is_custom',
            'name',
            'trigger_config',
            'steps',
            'step_count',
            'integration_types_used',
            'is_active',
            'last_modified_by_twin',
            'twin_modification_count',
            'created_at',
            'updated_at',
        ]
        read_only_fields = [
            'id',
            'user',
            'automation_template',
            'integration_types_used',
            'step_count',
            'twin_modification_count',
            'created_at',
            'updated_at',
        ]
    
    def get_integration_types_used(self, obj) -> list:
        """
        Get list of integration type IDs used in workflow steps.
        
        Requirements: 7.9
        """
        return obj.get_integration_types_used()
    
    def get_step_count(self, obj) -> int:
        """Get the number of steps in this workflow."""
        return obj.get_step_count()
    
    def validate_automation_template_id(self, value):
        """
        Validate that the automation template exists and is active.
        """
        if value is None:
            return value
        
        try:
            template = AutomationTemplate.objects.get(id=value)
            if not template.is_active:
                raise serializers.ValidationError(
                    "This automation template is not currently available"
                )
            return value
        except AutomationTemplate.DoesNotExist:
            raise serializers.ValidationError(
                f"Automation template with id '{value}' does not exist"
            )
    
    def validate_trigger_config(self, value):
        """
        Validate trigger configuration format.
        """
        if not isinstance(value, dict):
            raise serializers.ValidationError("Trigger config must be a dictionary")
        
        return value
    
    def validate_steps(self, value):
        """
        Validate workflow steps structure.
        
        Requirements: 7.6-7.8
        - Steps must be a list
        - At least one step required
        - Each step must have required fields
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
            required_fields = ['action_type', 'integration_type_id']
            for field in required_fields:
                if field not in step:
                    raise serializers.ValidationError(
                        f"Step {i}: missing required field '{field}'"
                    )
            
            # Validate action_type is a string
            if not isinstance(step['action_type'], str):
                raise serializers.ValidationError(
                    f"Step {i}: 'action_type' must be a string"
                )
            
            # Validate integration_type_id format
            if not isinstance(step['integration_type_id'], str):
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
        
        Validates workflow configuration and Twin modification rules.
        """
        # If automation_template_id is provided, set is_custom to False
        if attrs.get('automation_template_id'):
            attrs['is_custom'] = False
        else:
            # If no template, this is a custom workflow
            if 'is_custom' not in attrs:
                attrs['is_custom'] = True
        
        # Validate Twin modification rules
        last_modified_by_twin = attrs.get('last_modified_by_twin', False)
        
        if last_modified_by_twin:
            # Twin modifications require permission_flag in context
            request = self.context.get('request')
            if request:
                permission_flag = request.data.get('permission_flag', False)
                if not permission_flag:
                    raise serializers.ValidationError({
                        'permission_flag': "Twin modifications require permission_flag=True"
                    })
                
                # Check cognitive blend for high-blend modifications
                cognitive_blend = request.data.get('cognitive_blend', 50)
                if cognitive_blend > 80:
                    requires_confirmation = request.data.get('requires_confirmation', False)
                    if not requires_confirmation:
                        raise serializers.ValidationError({
                            'requires_confirmation': 
                                "Modifications with cognitive_blend > 80% require explicit confirmation"
                        })
        
        return attrs
    
    def create(self, validated_data):
        """
        Create workflow with user from request context.
        """
        # Get user from request context
        request = self.context.get('request')
        if request and hasattr(request, 'user'):
            validated_data['user'] = request.user
        
        # Handle automation_template_id
        automation_template_id = validated_data.pop('automation_template_id', None)
        if automation_template_id:
            validated_data['automation_template_id'] = automation_template_id
        
        return super().create(validated_data)
    
    def update(self, instance, validated_data):
        """
        Update workflow with Twin modification tracking.
        
        Requirements: 8.1-8.7
        """
        # Track Twin modifications
        last_modified_by_twin = validated_data.get('last_modified_by_twin', False)
        
        if last_modified_by_twin and not instance.last_modified_by_twin:
            # Increment Twin modification count
            instance.twin_modification_count += 1
        
        # Handle automation_template_id
        automation_template_id = validated_data.pop('automation_template_id', None)
        if automation_template_id:
            validated_data['automation_template_id'] = automation_template_id
        
        return super().update(instance, validated_data)


class WorkflowListSerializer(serializers.ModelSerializer):
    """
    Lightweight serializer for listing workflows.
    
    Used for list views where full step data is not needed.
    """
    
    automation_template_name = serializers.CharField(
        source='automation_template.name',
        read_only=True,
        allow_null=True
    )
    step_count = serializers.SerializerMethodField()
    integration_types_used = serializers.SerializerMethodField()
    
    class Meta:
        model = Workflow
        fields = [
            'id',
            'name',
            'automation_template',
            'automation_template_name',
            'is_custom',
            'step_count',
            'integration_types_used',
            'is_active',
            'last_modified_by_twin',
            'twin_modification_count',
            'created_at',
            'updated_at',
        ]
        read_only_fields = fields
    
    def get_step_count(self, obj) -> int:
        """Get the number of steps in this workflow."""
        return obj.get_step_count()
    
    def get_integration_types_used(self, obj) -> list:
        """Get list of integration type IDs used in workflow steps."""
        return obj.get_integration_types_used()


class WorkflowCreateSerializer(serializers.ModelSerializer):
    """
    Serializer for creating workflows.
    
    Simplified serializer focused on workflow creation.
    """
    
    automation_template_id = serializers.UUIDField(
        required=False,
        allow_null=True
    )
    
    class Meta:
        model = Workflow
        fields = [
            'automation_template_id',
            'name',
            'trigger_config',
            'steps',
            'is_active',
        ]
    
    def validate_steps(self, value):
        """Validate workflow steps structure."""
        if not isinstance(value, list):
            raise serializers.ValidationError("Steps must be a list")
        
        if not value:
            raise serializers.ValidationError("At least one step is required")
        
        return value
    
    def create(self, validated_data):
        """Create workflow with user from request context."""
        request = self.context.get('request')
        if request and hasattr(request, 'user'):
            validated_data['user'] = request.user
        
        # Set is_custom based on template presence
        automation_template_id = validated_data.pop('automation_template_id', None)
        if automation_template_id:
            validated_data['automation_template_id'] = automation_template_id
            validated_data['is_custom'] = False
        else:
            validated_data['is_custom'] = True
        
        return super().create(validated_data)



class WorkflowChangeHistorySerializer(serializers.ModelSerializer):
    """
    Serializer for WorkflowChangeHistory.
    
    Shows all modifications to workflows with author attribution,
    changes made, reasoning, and Twin-specific metadata.
    
    Requirements: 8.7
    """
    
    author = serializers.SerializerMethodField()
    user_email = serializers.EmailField(source='user.email', read_only=True)
    workflow_name = serializers.CharField(source='workflow.name', read_only=True)
    
    class Meta:
        model = Workflow.change_history.rel.related_model  # WorkflowChangeHistory
        fields = [
            'id',
            'workflow',
            'workflow_name',
            'user',
            'user_email',
            'author',
            'modified_by_twin',
            'cognitive_blend_value',
            'changes_made',
            'reasoning',
            'permission_flag',
            'required_confirmation',
            'created_at',
        ]
        read_only_fields = fields
    
    def get_author(self, obj) -> str:
        """Get human-readable author (User or Twin)."""
        return 'Twin' if obj.modified_by_twin else 'User'
