"""
Automation Template Service.

Manages automation templates and workflow instantiation.
Requirements: 6.1-6.7
"""

import re
from uuid import UUID
from typing import List, Tuple, Optional, Any
from django.core.exceptions import ValidationError
from django.db import transaction

from apps.automation.models import (
    AutomationTemplate,
    IntegrationTypeModel,
    TriggerType,
    Workflow,
)


class AutomationTemplateService:
    """Service for automation template management."""
    
    @staticmethod
    def create_template(
        integration_type_id: UUID,
        name: str,
        description: str,
        trigger_type: str,
        trigger_config: dict,
        steps: list[dict],
        is_enabled_by_default: bool = False
    ) -> AutomationTemplate:
        """
        Create a new automation template.
        
        Validates required fields and step structure before creation.
        
        Args:
            integration_type_id: ID of integration type
            name: Template name
            description: Template description
            trigger_type: Type of trigger (scheduled, event_driven, manual)
            trigger_config: Trigger configuration
            steps: List of workflow steps
            is_enabled_by_default: Whether to enable by default
            
        Returns:
            AutomationTemplate: Created template
            
        Raises:
            ValidationError: If validation fails
            IntegrationTypeModel.DoesNotExist: If integration type not found
            
        Requirements: 6.1-6.6
        """
        # Validate required fields
        if not name:
            raise ValidationError("Template name is required")
        if not trigger_type:
            raise ValidationError("Trigger type is required")
        if not steps:
            raise ValidationError("At least one step is required")
        
        # Validate trigger_type is one of allowed values
        valid_trigger_types = [choice[0] for choice in TriggerType.choices]
        if trigger_type not in valid_trigger_types:
            raise ValidationError(
                f"Trigger type must be one of: {', '.join(valid_trigger_types)}"
            )
        
        # Validate step structure
        is_valid, errors = AutomationTemplateService.validate_template_structure({
            'steps': steps
        })
        if not is_valid:
            raise ValidationError(f"Invalid template structure: {'; '.join(errors)}")
        
        # Verify integration type exists
        integration_type = IntegrationTypeModel.objects.get(id=integration_type_id)
        
        # Create template
        template = AutomationTemplate.objects.create(
            integration_type=integration_type,
            name=name,
            description=description,
            trigger_type=trigger_type,
            trigger_config=trigger_config,
            steps=steps,
            is_enabled_by_default=is_enabled_by_default,
            is_active=True
        )
        
        return template
    
    @staticmethod
    @transaction.atomic
    def instantiate_templates_for_user(
        user,
        integration
    ) -> List[Workflow]:
        """
        Create workflow instances from templates.
        
        Gets all active templates for the integration type and creates
        workflow instances with variable substitution.
        
        Args:
            user: Current user
            integration: Integration instance
            
        Returns:
            list[Workflow]: Created workflows
            
        Requirements: 4.11, 6.3-6.4
        """
        created_workflows = []
        
        # Get all active templates for this integration type
        templates = AutomationTemplate.objects.filter(
            integration_type=integration.integration_type,
            is_active=True
        )
        
        for template in templates:
            # Parse and substitute template variables
            parsed_trigger_config = AutomationTemplateService.parse_template_variables(
                template.trigger_config,
                user,
                integration
            )
            
            parsed_steps = []
            for step in template.get_steps_list():
                parsed_step = AutomationTemplateService.parse_template_variables(
                    step,
                    user,
                    integration
                )
                parsed_steps.append(parsed_step)
            
            # Create workflow instance
            workflow = Workflow.objects.create(
                user=user,
                automation_template=template,
                is_custom=False,
                name=template.name,
                trigger_config=parsed_trigger_config,
                steps=parsed_steps,
                is_active=template.is_enabled_by_default,
                last_modified_by_twin=False,
                twin_modification_count=0
            )
            
            created_workflows.append(workflow)
        
        return created_workflows
    
    @staticmethod
    def parse_template_variables(
        template_config: dict,
        user,
        integration
    ) -> dict:
        """
        Replace template variables with actual values.
        
        Supports variables like:
        - {{user.email}}, {{user.id}}, {{user.first_name}}, etc.
        - {{integration.user_id}}, {{integration.id}}, etc.
        - Nested paths like {{user.profile.timezone}}
        
        Args:
            template_config: Template configuration with variables
            user: Current user
            integration: Integration instance
            
        Returns:
            dict: Configuration with substituted values
            
        Requirements: 6.7
        """
        import json
        
        # Convert to JSON string for easier replacement
        config_str = json.dumps(template_config)
        
        # Find all template variables ({{variable.path}})
        variable_pattern = r'\{\{([^}]+)\}\}'
        matches = re.findall(variable_pattern, config_str)
        
        for match in matches:
            variable_path = match.strip()
            value = AutomationTemplateService._resolve_variable_path(
                variable_path,
                user,
                integration
            )
            
            # Replace the variable with its value
            if value is not None:
                # Handle different value types
                if isinstance(value, str):
                    replacement = f'"{value}"'
                elif isinstance(value, bool):
                    replacement = 'true' if value else 'false'
                elif value is None:
                    replacement = 'null'
                else:
                    replacement = str(value)
                
                config_str = config_str.replace(f'{{{{{match}}}}}', replacement)
        
        # Convert back to dict
        return json.loads(config_str)
    
    @staticmethod
    def _resolve_variable_path(
        variable_path: str,
        user,
        integration
    ) -> Any:
        """
        Resolve a variable path to its actual value.
        
        Args:
            variable_path: Dot-separated path (e.g., "user.email")
            user: Current user
            integration: Integration instance
            
        Returns:
            Resolved value or None if not found
        """
        parts = variable_path.split('.')
        
        if not parts:
            return None
        
        # Determine root object
        root = parts[0]
        if root == 'user':
            obj = user
        elif root == 'integration':
            obj = integration
        else:
            return None
        
        # Navigate nested path
        for part in parts[1:]:
            try:
                if hasattr(obj, part):
                    obj = getattr(obj, part)
                elif isinstance(obj, dict) and part in obj:
                    obj = obj[part]
                else:
                    return None
            except (AttributeError, KeyError, TypeError):
                return None
        
        return obj
    
    @staticmethod
    def validate_template_structure(template: dict) -> Tuple[bool, List[str]]:
        """
        Validate template JSON structure.
        
        Checks that all required fields are present and properly formatted.
        
        Args:
            template: Template configuration to validate
            
        Returns:
            tuple: (is_valid, list_of_errors)
            
        Requirements: 16.2-16.3, 16.7
        """
        errors = []
        
        # Check steps field exists
        if 'steps' not in template:
            errors.append("Template must contain 'steps' field")
            return False, errors
        
        steps = template['steps']
        
        # Validate steps is a list
        if not isinstance(steps, list):
            errors.append("Steps must be a list")
            return False, errors
        
        # Validate at least one step
        if len(steps) == 0:
            errors.append("At least one step is required")
        
        # Validate each step structure
        for i, step in enumerate(steps):
            if not isinstance(step, dict):
                errors.append(f"Step {i}: must be a dictionary")
                continue
            
            # Check required fields
            if 'action_type' not in step:
                errors.append(f"Step {i}: missing required field 'action_type'")
            
            if 'integration_type_id' not in step:
                errors.append(f"Step {i}: missing required field 'integration_type_id'")
            
            # Validate action_type is not empty
            if 'action_type' in step and not step['action_type']:
                errors.append(f"Step {i}: 'action_type' cannot be empty")
            
            # Validate integration_type_id format (should be UUID string)
            if 'integration_type_id' in step:
                integration_type_id = step['integration_type_id']
                if not integration_type_id:
                    errors.append(f"Step {i}: 'integration_type_id' cannot be empty")
                elif not isinstance(integration_type_id, str):
                    errors.append(f"Step {i}: 'integration_type_id' must be a string")
        
        return len(errors) == 0, errors
