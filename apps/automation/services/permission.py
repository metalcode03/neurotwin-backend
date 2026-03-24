"""
Permission checking service for integrations and workflows.

Verifies Integration.permissions contains required permission.
Skips workflow steps if permission disabled.
Logs permission_denied events.

Requirements: 12.4-12.5
"""

import logging
from typing import Optional, Tuple, List
from uuid import UUID

from django.contrib.auth import get_user_model

from apps.automation.models import Integration, Workflow, WorkflowExecution
from apps.twin.services.audit import AuditLogService


User = get_user_model()
logger = logging.getLogger(__name__)


class PermissionService:
    """
    Service for checking integration permissions.
    
    Requirements: 12.4-12.5
    """
    
    @staticmethod
    def check_integration_permission(
        integration: Integration,
        permission_name: str
    ) -> bool:
        """
        Check if an integration has a specific permission enabled.
        
        Args:
            integration: Integration instance
            permission_name: Name of the permission to check
            
        Returns:
            True if permission is enabled, False otherwise
        """
        if not isinstance(integration.permissions, dict):
            logger.warning(
                f'Integration {integration.id} has invalid permissions format'
            )
            return False
        
        has_permission = integration.permissions.get(permission_name, False)
        
        if not has_permission:
            logger.info(
                f'Permission {permission_name} not granted for integration '
                f'{integration.id} (user: {integration.user.id})'
            )
        
        return has_permission
    
    @staticmethod
    def check_workflow_step_permission(
        user: User,
        step: dict,
        workflow: Workflow
    ) -> Tuple[bool, Optional[str]]:
        """
        Check if a workflow step has required permissions.
        
        Args:
            user: User who owns the workflow
            step: Workflow step dictionary
            workflow: Workflow instance
            
        Returns:
            Tuple of (has_permission, error_message)
        """
        # Extract integration_type_id from step
        integration_type_id = step.get('integration_type_id')
        if not integration_type_id:
            return False, 'Step missing integration_type_id'
        
        # Get the integration for this type
        try:
            integration = Integration.objects.get(
                user=user,
                integration_type_id=integration_type_id,
                is_active=True
            )
        except Integration.DoesNotExist:
            return False, f'Integration {integration_type_id} not installed'
        
        # Extract required permission from step
        required_permission = step.get('required_permission')
        if not required_permission:
            # No specific permission required, allow
            return True, None
        
        # Check if integration has the required permission
        has_permission = PermissionService.check_integration_permission(
            integration=integration,
            permission_name=required_permission
        )
        
        if not has_permission:
            error_msg = (
                f'Permission {required_permission} not granted for '
                f'integration {integration.integration_type.name}'
            )
            
            # Log permission denial
            AuditLogService.log_permission_denied(
                user=user,
                resource_type='Workflow Step',
                resource_id=str(workflow.id),
                action='execute',
                details={
                    'workflow_id': str(workflow.id),
                    'workflow_name': workflow.name,
                    'step': step,
                    'integration_type_id': str(integration_type_id),
                    'required_permission': required_permission,
                    'reason': 'Permission not granted in integration settings',
                }
            )
            
            return False, error_msg
        
        return True, None
    
    @staticmethod
    def validate_workflow_permissions(
        user: User,
        workflow: Workflow
    ) -> Tuple[bool, List[str]]:
        """
        Validate all steps in a workflow have required permissions.
        
        Args:
            user: User who owns the workflow
            workflow: Workflow instance
            
        Returns:
            Tuple of (all_valid, error_messages)
        """
        errors = []
        steps = workflow.get_steps_list()
        
        for i, step in enumerate(steps):
            has_permission, error_msg = PermissionService.check_workflow_step_permission(
                user=user,
                step=step,
                workflow=workflow
            )
            
            if not has_permission:
                errors.append(f'Step {i + 1}: {error_msg}')
        
        return len(errors) == 0, errors
    
    @staticmethod
    def should_skip_step(
        execution: WorkflowExecution,
        step_index: int,
        step: dict
    ) -> Tuple[bool, Optional[str]]:
        """
        Determine if a workflow step should be skipped due to permissions.
        
        Args:
            execution: WorkflowExecution instance
            step_index: Index of the step
            step: Step dictionary
            
        Returns:
            Tuple of (should_skip, skip_reason)
        """
        # Check if step has required permission
        required_permission = step.get('required_permission')
        if not required_permission:
            # No permission required, don't skip
            return False, None
        
        # Get integration for this step
        integration_type_id = step.get('integration_type_id')
        if not integration_type_id:
            # Invalid step, skip it
            return True, 'Step missing integration_type_id'
        
        try:
            integration = Integration.objects.get(
                user=execution.user,
                integration_type_id=integration_type_id,
                is_active=True
            )
        except Integration.DoesNotExist:
            # Integration not found, skip step
            return True, f'Integration {integration_type_id} not installed'
        
        # Check permission
        has_permission = PermissionService.check_integration_permission(
            integration=integration,
            permission_name=required_permission
        )
        
        if not has_permission:
            skip_reason = (
                f'Permission {required_permission} not granted for '
                f'{integration.integration_type.name}'
            )
            
            # Log permission denial
            logger.info(
                f'Skipping step {step_index} in execution {execution.id}: {skip_reason}'
            )
            
            AuditLogService.log_permission_denied(
                user=execution.user,
                resource_type='Workflow Execution Step',
                resource_id=str(execution.id),
                action='execute',
                details={
                    'execution_id': str(execution.id),
                    'workflow_id': str(execution.workflow.id),
                    'step_index': step_index,
                    'step': step,
                    'integration_type_id': str(integration_type_id),
                    'required_permission': required_permission,
                    'reason': 'Permission disabled in integration settings',
                }
            )
            
            return True, skip_reason
        
        return False, None
    
    @staticmethod
    def get_missing_permissions(
        user: User,
        workflow: Workflow
    ) -> List[dict]:
        """
        Get list of missing permissions for a workflow.
        
        Args:
            user: User who owns the workflow
            workflow: Workflow instance
            
        Returns:
            List of dictionaries with missing permission details
        """
        missing = []
        steps = workflow.get_steps_list()
        
        for i, step in enumerate(steps):
            required_permission = step.get('required_permission')
            if not required_permission:
                continue
            
            integration_type_id = step.get('integration_type_id')
            if not integration_type_id:
                continue
            
            try:
                integration = Integration.objects.get(
                    user=user,
                    integration_type_id=integration_type_id,
                    is_active=True
                )
                
                has_permission = PermissionService.check_integration_permission(
                    integration=integration,
                    permission_name=required_permission
                )
                
                if not has_permission:
                    missing.append({
                        'step_index': i,
                        'step_name': step.get('name', f'Step {i + 1}'),
                        'integration_type': integration.integration_type.name,
                        'integration_type_id': str(integration_type_id),
                        'required_permission': required_permission,
                    })
            except Integration.DoesNotExist:
                missing.append({
                    'step_index': i,
                    'step_name': step.get('name', f'Step {i + 1}'),
                    'integration_type_id': str(integration_type_id),
                    'required_permission': required_permission,
                    'error': 'Integration not installed',
                })
        
        return missing
