"""
Integration service for NeuroTwin platform.

Handles integration management, OAuth token handling, and permissions.
Requirements: 7.2, 7.3, 7.4, 7.5
"""

from typing import List, Optional, Dict, Any
from datetime import datetime, timedelta

from django.db import transaction
from django.utils import timezone

from .models import Integration, IntegrationType
from .dataclasses import (
    IntegrationData,
    ConnectIntegrationRequest,
    UpdatePermissionsRequest,
    UpdateSteeringRulesRequest,
    TokenRefreshResult,
    MinimalScopesConfig,
)


class IntegrationService:
    """
    Manages app integrations and OAuth tokens.
    
    Provides methods for connecting integrations, managing permissions,
    and handling token refresh.
    
    Requirements: 7.2, 7.3, 7.4, 7.5
    - Request only necessary OAuth scopes
    - Configurable steering rules
    - Modifiable permission settings
    - Handle token expiration and refresh
    """
    
    # Minimal OAuth scopes per integration type
    # Requirements: 7.2 - Request only necessary OAuth scopes
    MINIMAL_SCOPES: Dict[str, MinimalScopesConfig] = {
        IntegrationType.GMAIL: MinimalScopesConfig(
            integration_type=IntegrationType.GMAIL,
            required_scopes=[
                'https://www.googleapis.com/auth/gmail.readonly',
            ],
            optional_scopes=[
                'https://www.googleapis.com/auth/gmail.send',
                'https://www.googleapis.com/auth/gmail.compose',
            ],
        ),
        IntegrationType.GOOGLE_CALENDAR: MinimalScopesConfig(
            integration_type=IntegrationType.GOOGLE_CALENDAR,
            required_scopes=[
                'https://www.googleapis.com/auth/calendar.readonly',
            ],
            optional_scopes=[
                'https://www.googleapis.com/auth/calendar.events',
            ],
        ),
        IntegrationType.GOOGLE_DOCS: MinimalScopesConfig(
            integration_type=IntegrationType.GOOGLE_DOCS,
            required_scopes=[
                'https://www.googleapis.com/auth/documents.readonly',
            ],
            optional_scopes=[
                'https://www.googleapis.com/auth/documents',
            ],
        ),
        IntegrationType.GOOGLE_MEET: MinimalScopesConfig(
            integration_type=IntegrationType.GOOGLE_MEET,
            required_scopes=[
                'https://www.googleapis.com/auth/calendar.readonly',
            ],
            optional_scopes=[
                'https://www.googleapis.com/auth/calendar.events',
            ],
        ),
        IntegrationType.OUTLOOK: MinimalScopesConfig(
            integration_type=IntegrationType.OUTLOOK,
            required_scopes=[
                'Mail.Read',
            ],
            optional_scopes=[
                'Mail.Send',
                'Mail.ReadWrite',
            ],
        ),
        IntegrationType.MICROSOFT_OFFICE: MinimalScopesConfig(
            integration_type=IntegrationType.MICROSOFT_OFFICE,
            required_scopes=[
                'Files.Read',
            ],
            optional_scopes=[
                'Files.ReadWrite',
            ],
        ),
        IntegrationType.SLACK: MinimalScopesConfig(
            integration_type=IntegrationType.SLACK,
            required_scopes=[
                'channels:read',
                'users:read',
            ],
            optional_scopes=[
                'chat:write',
                'channels:history',
            ],
        ),
        IntegrationType.ZOOM: MinimalScopesConfig(
            integration_type=IntegrationType.ZOOM,
            required_scopes=[
                'meeting:read',
            ],
            optional_scopes=[
                'meeting:write',
            ],
        ),
        IntegrationType.WHATSAPP: MinimalScopesConfig(
            integration_type=IntegrationType.WHATSAPP,
            required_scopes=[
                'whatsapp_business_messaging',
            ],
            optional_scopes=[],
        ),
        IntegrationType.TELEGRAM: MinimalScopesConfig(
            integration_type=IntegrationType.TELEGRAM,
            required_scopes=[],  # Telegram uses bot tokens, not OAuth
            optional_scopes=[],
        ),
        IntegrationType.CRM: MinimalScopesConfig(
            integration_type=IntegrationType.CRM,
            required_scopes=[
                'contacts:read',
            ],
            optional_scopes=[
                'contacts:write',
                'deals:read',
                'deals:write',
            ],
        ),
    }
    
    def get_minimal_scopes(self, integration_type: str) -> List[str]:
        """
        Get the minimal required OAuth scopes for an integration type.
        
        Requirements: 7.2 - Request only necessary OAuth scopes
        
        Args:
            integration_type: The integration type
            
        Returns:
            List of minimal required scopes
        """
        config = self.MINIMAL_SCOPES.get(integration_type)
        if config:
            return config.required_scopes.copy()
        return []
    
    def get_all_available_scopes(self, integration_type: str) -> List[str]:
        """
        Get all available OAuth scopes for an integration type.
        
        Args:
            integration_type: The integration type
            
        Returns:
            List of all available scopes (required + optional)
        """
        config = self.MINIMAL_SCOPES.get(integration_type)
        if config:
            return config.required_scopes + config.optional_scopes
        return []

    @transaction.atomic
    def connect_integration(
        self,
        user_id: str,
        request: ConnectIntegrationRequest
    ) -> Integration:
        """
        Connect integration with minimal required scopes.
        
        Requirements: 7.2
        - Request only necessary OAuth scopes
        - Store tokens securely
        
        Args:
            user_id: The user's ID
            request: The connection request with OAuth code
            
        Returns:
            The created or updated Integration
        """
        # Determine scopes to use
        if request.requested_scopes:
            # Use requested scopes, but ensure they're valid
            available_scopes = set(self.get_all_available_scopes(request.integration_type))
            scopes = [s for s in request.requested_scopes if s in available_scopes or not available_scopes]
        else:
            # Use minimal required scopes
            scopes = self.get_minimal_scopes(request.integration_type)
        
        # Exchange OAuth code for tokens (simulated - in real implementation
        # this would call the OAuth provider's token endpoint)
        token_data = self._exchange_oauth_code(
            request.integration_type,
            request.oauth_code,
            request.redirect_uri,
            scopes
        )
        
        # Create or update integration
        integration, created = Integration.objects.update_or_create(
            user_id=user_id,
            type=request.integration_type,
            defaults={
                'scopes': scopes,
                'is_active': True,
                'token_expires_at': token_data.get('expires_at'),
                'steering_rules': {},
                'permissions': self._get_default_permissions(request.integration_type),
            }
        )
        
        # Set encrypted tokens
        integration.oauth_token = token_data.get('access_token', '')
        integration.refresh_token = token_data.get('refresh_token', '')
        integration.save()
        
        return integration
    
    def _exchange_oauth_code(
        self,
        integration_type: str,
        oauth_code: str,
        redirect_uri: str,
        scopes: List[str]
    ) -> Dict[str, Any]:
        """
        Exchange OAuth authorization code for tokens.
        
        In a real implementation, this would call the OAuth provider's
        token endpoint. For now, we simulate the response.
        
        Args:
            integration_type: The integration type
            oauth_code: The authorization code
            redirect_uri: The redirect URI
            scopes: The requested scopes
            
        Returns:
            Dictionary with access_token, refresh_token, and expires_at
        """
        # Simulate token exchange - in production, this would make
        # actual HTTP requests to OAuth providers
        expires_at = timezone.now() + timedelta(hours=1)
        
        return {
            'access_token': f'simulated_access_token_{oauth_code}',
            'refresh_token': f'simulated_refresh_token_{oauth_code}',
            'expires_at': expires_at,
            'scopes': scopes,
        }
    
    def _get_default_permissions(self, integration_type: str) -> Dict[str, bool]:
        """
        Get default permissions for an integration type.
        
        By default, all permissions are disabled for safety.
        
        Args:
            integration_type: The integration type
            
        Returns:
            Dictionary of permission name to default value
        """
        return {
            'read': True,  # Read is generally safe
            'write': False,
            'send': False,
            'delete': False,
        }
    
    def get_integrations(self, user_id: str) -> List[IntegrationData]:
        """
        Get all connected integrations for user.
        
        Args:
            user_id: The user's ID
            
        Returns:
            List of IntegrationData for all connected integrations
        """
        integrations = Integration.objects.filter(user_id=user_id)
        return [IntegrationData.from_model(i) for i in integrations]
    
    def get_integration(
        self,
        user_id: str,
        integration_type: str
    ) -> Optional[Integration]:
        """
        Get a specific integration for a user.
        
        Args:
            user_id: The user's ID
            integration_type: The integration type
            
        Returns:
            Integration if found, None otherwise
        """
        return Integration.objects.filter(
            user_id=user_id,
            type=integration_type
        ).first()
    
    def get_integration_by_id(self, integration_id: str) -> Optional[Integration]:
        """
        Get an integration by its ID.
        
        Args:
            integration_id: The integration ID
            
        Returns:
            Integration if found, None otherwise
        """
        try:
            return Integration.objects.get(id=integration_id)
        except Integration.DoesNotExist:
            return None

    @transaction.atomic
    def update_permissions(
        self,
        integration_id: str,
        request: UpdatePermissionsRequest
    ) -> Integration:
        """
        Update integration permissions.
        
        Requirements: 7.4
        - Each integration has permission settings that the user can modify
        
        Args:
            integration_id: The integration ID
            request: The update request with new permissions
            
        Returns:
            Updated Integration
            
        Raises:
            Integration.DoesNotExist: If integration not found
        """
        integration = Integration.objects.get(id=integration_id)
        
        # Update permissions
        if not isinstance(integration.permissions, dict):
            integration.permissions = {}
        
        for permission_name, value in request.permissions.items():
            integration.permissions[permission_name] = value
        
        integration.save(update_fields=['permissions', 'updated_at'])
        
        return integration
    
    @transaction.atomic
    def update_steering_rules(
        self,
        integration_id: str,
        request: UpdateSteeringRulesRequest
    ) -> Integration:
        """
        Update integration steering rules.
        
        Requirements: 7.3
        - Each integration has configurable steering rules defining allowed actions
        
        Args:
            integration_id: The integration ID
            request: The update request with new steering rules
            
        Returns:
            Updated Integration
            
        Raises:
            Integration.DoesNotExist: If integration not found
        """
        integration = Integration.objects.get(id=integration_id)
        
        # Update steering rules
        if not isinstance(integration.steering_rules, dict):
            integration.steering_rules = {}
        
        integration.steering_rules.update(request.steering_rules)
        integration.save(update_fields=['steering_rules', 'updated_at'])
        
        return integration
    
    def refresh_token(self, integration_id: str) -> TokenRefreshResult:
        """
        Attempt to refresh an expired OAuth token.
        
        Requirements: 7.5
        - When an integration token expires, attempt refresh or notify user to reconnect
        
        Args:
            integration_id: The integration ID
            
        Returns:
            TokenRefreshResult indicating success or failure
        """
        try:
            integration = Integration.objects.get(id=integration_id)
        except Integration.DoesNotExist:
            return TokenRefreshResult.failed(
                "Integration not found",
                needs_reconnect=False
            )
        
        # Check if we have a refresh token
        if not integration.has_refresh_token:
            return TokenRefreshResult.failed(
                "No refresh token available",
                needs_reconnect=True
            )
        
        # Attempt to refresh the token
        try:
            new_token_data = self._refresh_oauth_token(
                integration.type,
                integration.refresh_token
            )
            
            # Update the integration with new tokens
            integration.oauth_token = new_token_data.get('access_token', '')
            if new_token_data.get('refresh_token'):
                integration.refresh_token = new_token_data['refresh_token']
            integration.token_expires_at = new_token_data.get('expires_at')
            integration.save()
            
            return TokenRefreshResult.successful(integration.token_expires_at)
            
        except Exception as e:
            return TokenRefreshResult.failed(
                str(e),
                needs_reconnect=True
            )
    
    def _refresh_oauth_token(
        self,
        integration_type: str,
        refresh_token: str
    ) -> Dict[str, Any]:
        """
        Refresh OAuth token using refresh token.
        
        In a real implementation, this would call the OAuth provider's
        token endpoint with the refresh token.
        
        Args:
            integration_type: The integration type
            refresh_token: The refresh token
            
        Returns:
            Dictionary with new access_token, optional refresh_token, and expires_at
        """
        # Simulate token refresh - in production, this would make
        # actual HTTP requests to OAuth providers
        expires_at = timezone.now() + timedelta(hours=1)
        
        return {
            'access_token': f'refreshed_access_token_{refresh_token[:10]}',
            'refresh_token': None,  # Some providers don't rotate refresh tokens
            'expires_at': expires_at,
        }
    
    @transaction.atomic
    def disconnect(self, integration_id: str) -> bool:
        """
        Disconnect and remove an integration.
        
        Args:
            integration_id: The integration ID
            
        Returns:
            True if disconnected successfully, False if not found
        """
        try:
            integration = Integration.objects.get(id=integration_id)
            integration.delete()
            return True
        except Integration.DoesNotExist:
            return False
    
    def get_active_integrations(self, user_id: str) -> List[IntegrationData]:
        """
        Get all active integrations for a user.
        
        Args:
            user_id: The user's ID
            
        Returns:
            List of active IntegrationData
        """
        integrations = Integration.objects.filter(
            user_id=user_id,
            is_active=True
        )
        return [IntegrationData.from_model(i) for i in integrations]
    
    def get_expired_integrations(self, user_id: str) -> List[IntegrationData]:
        """
        Get all integrations with expired tokens for a user.
        
        Args:
            user_id: The user's ID
            
        Returns:
            List of IntegrationData with expired tokens
        """
        integrations = Integration.objects.filter(
            user_id=user_id,
            is_active=True,
            token_expires_at__lt=timezone.now()
        )
        return [IntegrationData.from_model(i) for i in integrations]
    
    def check_and_refresh_expired_tokens(self, user_id: str) -> Dict[str, TokenRefreshResult]:
        """
        Check all integrations for expired tokens and attempt refresh.
        
        Requirements: 7.5
        - When an integration token expires, attempt refresh
        
        Args:
            user_id: The user's ID
            
        Returns:
            Dictionary mapping integration type to refresh result
        """
        results = {}
        expired = self.get_expired_integrations(user_id)
        
        for integration_data in expired:
            result = self.refresh_token(integration_data.id)
            results[integration_data.type] = result
        
        return results
    
    def deactivate_integration(self, integration_id: str) -> bool:
        """
        Deactivate an integration without deleting it.
        
        Args:
            integration_id: The integration ID
            
        Returns:
            True if deactivated, False if not found
        """
        try:
            integration = Integration.objects.get(id=integration_id)
            integration.is_active = False
            integration.save(update_fields=['is_active', 'updated_at'])
            return True
        except Integration.DoesNotExist:
            return False
    
    def reactivate_integration(self, integration_id: str) -> bool:
        """
        Reactivate a deactivated integration.
        
        Args:
            integration_id: The integration ID
            
        Returns:
            True if reactivated, False if not found
        """
        try:
            integration = Integration.objects.get(id=integration_id)
            integration.is_active = True
            integration.save(update_fields=['is_active', 'updated_at'])
            return True
        except Integration.DoesNotExist:
            return False


from .models import Workflow, WorkflowExecution, WorkflowStatus
from .dataclasses import (
    WorkflowData,
    WorkflowStepData,
    WorkflowResult,
    CreateWorkflowRequest,
    ExecuteWorkflowRequest,
)
from apps.safety.services import PermissionService, AuditService
from apps.safety.models import ActionType, AuditOutcome


class WorkflowEngine:
    """
    Executes automated workflows across integrations.
    
    Provides methods for workflow execution with permission checks,
    confirmation requirements, and audit logging.
    
    Requirements: 8.1, 8.2, 8.3, 8.4, 8.5, 8.6
    - Verify user has granted permission for required actions
    - Require permission_flag=True for external actions
    - Execute workflows asynchronously
    - Log errors and notify user on failure
    - Require confirmation when Cognitive_Blend > 80%
    - Distinguish Twin-generated from user-authored content
    """
    
    # Cognitive blend threshold for requiring confirmation
    # Requirements: 8.5
    HIGH_BLEND_THRESHOLD = 80
    
    def __init__(
        self,
        permission_service: Optional[PermissionService] = None,
        audit_service: Optional[AuditService] = None,
        integration_service: Optional[IntegrationService] = None,
    ):
        """
        Initialize WorkflowEngine.
        
        Args:
            permission_service: Service for permission checks
            audit_service: Service for audit logging
            integration_service: Service for integration management
        """
        self._permission_service = permission_service or PermissionService()
        self._audit_service = audit_service or AuditService()
        self._integration_service = integration_service or IntegrationService()
    
    def create_workflow(
        self,
        user_id: str,
        request: CreateWorkflowRequest
    ) -> Workflow:
        """
        Create a new workflow.
        
        Args:
            user_id: The user's ID
            request: The workflow creation request
            
        Returns:
            The created Workflow
        """
        # Convert steps to JSON-serializable format
        steps_data = [
            {
                'integration': step.integration,
                'action': step.action,
                'parameters': step.parameters,
                'requires_confirmation': step.requires_confirmation,
                'order': step.order,
            }
            for step in request.steps
        ]
        
        workflow = Workflow.objects.create(
            user_id=user_id,
            name=request.name,
            trigger_config=request.trigger_config,
            steps=steps_data,
            is_active=True,
        )
        
        return workflow
    
    def get_workflow(self, workflow_id: str) -> Optional[Workflow]:
        """
        Get a workflow by ID.
        
        Args:
            workflow_id: The workflow ID
            
        Returns:
            Workflow if found, None otherwise
        """
        try:
            return Workflow.objects.get(id=workflow_id)
        except Workflow.DoesNotExist:
            return None
    
    def get_user_workflows(self, user_id: str, active_only: bool = True) -> List[WorkflowData]:
        """
        Get all workflows for a user.
        
        Args:
            user_id: The user's ID
            active_only: Whether to return only active workflows
            
        Returns:
            List of WorkflowData
        """
        queryset = Workflow.objects.filter(user_id=user_id)
        if active_only:
            queryset = queryset.filter(is_active=True)
        
        return [WorkflowData.from_model(w) for w in queryset]
    
    def verify_permissions(
        self,
        user_id: str,
        workflow: Workflow
    ) -> tuple[bool, List[str]]:
        """
        Verify user has granted all required permissions for a workflow.
        
        Requirements: 8.1
        - Verify the user has granted permission for the required actions
        
        Args:
            user_id: The user's ID
            workflow: The workflow to verify
            
        Returns:
            Tuple of (all_permitted, list of missing permissions)
        """
        missing_permissions = []
        
        for step in workflow.get_steps_list():
            integration = step.get('integration', '')
            action = step.get('action', '')
            
            # Map action to ActionType
            action_type = self._map_action_to_type(action)
            
            # Check permission
            allowed, needs_approval = self._permission_service.check_permission(
                user_id, integration, action_type
            )
            
            if not allowed:
                missing_permissions.append(f"{integration}/{action_type}")
        
        return (len(missing_permissions) == 0, missing_permissions)
    
    def _map_action_to_type(self, action: str) -> str:
        """
        Map a workflow action to an ActionType.
        
        Args:
            action: The action string from the workflow step
            
        Returns:
            The corresponding ActionType value
        """
        action_lower = action.lower()
        
        if 'read' in action_lower or 'get' in action_lower or 'list' in action_lower:
            return ActionType.READ
        elif 'send' in action_lower or 'post' in action_lower or 'message' in action_lower:
            return ActionType.SEND
        elif 'delete' in action_lower or 'remove' in action_lower:
            return ActionType.DELETE
        elif 'financial' in action_lower or 'payment' in action_lower or 'transfer' in action_lower:
            return ActionType.FINANCIAL
        elif 'legal' in action_lower or 'contract' in action_lower or 'sign' in action_lower:
            return ActionType.LEGAL
        elif 'call' in action_lower or 'phone' in action_lower:
            return ActionType.CALL
        else:
            return ActionType.WRITE
    
    def requires_confirmation(self, cognitive_blend: int, action: str = None) -> bool:
        """
        Check if action requires user confirmation based on blend.
        
        Requirements: 8.5
        - When Cognitive_Blend exceeds 80%, require explicit user confirmation
        
        Args:
            cognitive_blend: The current cognitive blend value (0-100)
            action: Optional action string for additional checks
            
        Returns:
            True if confirmation is required
        """
        # High blend always requires confirmation
        if cognitive_blend > self.HIGH_BLEND_THRESHOLD:
            return True
        
        # Check if action is high-risk
        if action:
            action_type = self._map_action_to_type(action)
            if self._permission_service.is_high_risk_action(action_type):
                return True
        
        return False
    
    def execute_workflow_sync(
        self,
        user_id: str,
        request: ExecuteWorkflowRequest
    ) -> WorkflowResult:
        """
        Execute workflow synchronously with permission checks.
        
        This is the synchronous version for use in non-async contexts.
        
        Requirements: 8.1, 8.2, 8.3, 8.4, 8.5, 8.6
        
        Args:
            user_id: The user's ID
            request: The execution request
            
        Returns:
            WorkflowResult with execution status
        """
        # Get the workflow
        workflow = self.get_workflow(request.workflow_id)
        if not workflow:
            return WorkflowResult.failed(
                request.workflow_id,
                "Workflow not found"
            )
        
        # Check if workflow belongs to user
        if str(workflow.user_id) != user_id:
            return WorkflowResult.failed(
                request.workflow_id,
                "Workflow does not belong to user"
            )
        
        # Check if workflow is active
        if not workflow.is_active:
            return WorkflowResult.failed(
                request.workflow_id,
                "Workflow is not active"
            )
        
        # Check kill switch
        from apps.safety.services import KillSwitchService
        kill_switch_service = KillSwitchService(self._audit_service)
        can_execute, reason = kill_switch_service.can_execute_automation(user_id)
        if not can_execute:
            return WorkflowResult.failed(
                request.workflow_id,
                reason
            )
        
        # Verify permissions
        # Requirements: 8.1
        all_permitted, missing = self.verify_permissions(user_id, workflow)
        if not all_permitted:
            self._log_workflow_error(
                user_id,
                workflow,
                f"Missing permissions: {', '.join(missing)}",
                request.cognitive_blend,
            )
            return WorkflowResult.failed(
                request.workflow_id,
                f"Missing permissions: {', '.join(missing)}"
            )
        
        # Check permission flag for external actions
        # Requirements: 8.2
        if not request.permission_flag:
            self._log_workflow_error(
                user_id,
                workflow,
                "Permission flag not set for external actions",
                request.cognitive_blend,
            )
            return WorkflowResult.failed(
                request.workflow_id,
                "Permission flag must be True for external actions"
            )
        
        # Create execution record
        execution = WorkflowExecution.objects.create(
            workflow=workflow,
            user_id=user_id,
            status=WorkflowStatus.RUNNING,
            total_steps=workflow.get_step_count(),
            permission_flag=request.permission_flag,
            cognitive_blend=request.cognitive_blend,
            is_twin_generated=True,
            started_at=timezone.now(),
        )
        
        # Execute steps
        steps = workflow.get_steps_list()
        for idx, step in enumerate(steps):
            step_data = WorkflowStepData(
                integration=step.get('integration', ''),
                action=step.get('action', ''),
                parameters=step.get('parameters', {}),
                requires_confirmation=step.get('requires_confirmation', False),
                order=idx,
            )
            
            # Check if confirmation is required
            # Requirements: 8.5
            needs_confirmation = (
                step_data.requires_confirmation or
                self.requires_confirmation(request.cognitive_blend, step_data.action)
            )
            
            if needs_confirmation and not request.confirmation_token:
                # Pause execution and request confirmation
                execution.status = WorkflowStatus.AWAITING_CONFIRMATION
                execution.current_step = idx
                execution.save()
                
                return WorkflowResult.needs_confirmation(
                    request.workflow_id,
                    step_data,
                    idx,
                    len(steps),
                )
            
            # Execute the step synchronously
            try:
                step_result = self._execute_step_sync(user_id, step_data, execution)
                
                # Record step result
                execution.add_step_result(idx, step_result.get('success', True), step_result)
                execution.steps_completed = idx + 1
                execution.current_step = idx + 1
                execution.save()
                
                # Log successful step
                self._log_workflow_step(
                    user_id,
                    workflow,
                    step_data,
                    AuditOutcome.SUCCESS,
                    request.cognitive_blend,
                )
                
            except Exception as e:
                # Log error and update execution
                # Requirements: 8.4
                error_msg = str(e)
                execution.status = WorkflowStatus.FAILED
                execution.error_message = error_msg
                execution.error_step = idx
                execution.completed_at = timezone.now()
                execution.save()
                
                self._log_workflow_error(
                    user_id,
                    workflow,
                    f"Step {idx} failed: {error_msg}",
                    request.cognitive_blend,
                    step_data,
                )
                
                return WorkflowResult.failed(
                    request.workflow_id,
                    f"Step {idx} failed: {error_msg}",
                    idx,
                    len(steps),
                )
        
        # All steps completed successfully
        execution.status = WorkflowStatus.COMPLETED
        execution.completed_at = timezone.now()
        execution.save()
        
        # Log successful completion
        self._audit_service.log_action(
            user_id=user_id,
            action_type=ActionType.WRITE,
            outcome=AuditOutcome.SUCCESS,
            target_integration=None,
            input_data={
                'workflow_id': str(workflow.id),
                'workflow_name': workflow.name,
                'steps_completed': len(steps),
            },
            cognitive_blend=request.cognitive_blend,
            reasoning_chain=f"Workflow '{workflow.name}' completed successfully",
            is_twin_generated=True,
        )
        
        result = WorkflowResult.successful(
            request.workflow_id,
            len(steps),
            len(steps),
        )
        result.is_twin_generated = True
        return result
    
    def _execute_step_sync(
        self,
        user_id: str,
        step: WorkflowStepData,
        execution: WorkflowExecution
    ) -> dict:
        """
        Execute a single workflow step synchronously.
        
        In a real implementation, this would call the appropriate
        integration API to perform the action.
        
        Args:
            user_id: The user's ID
            step: The step to execute
            execution: The execution record
            
        Returns:
            Dictionary with step result
        """
        # Get the integration
        integration = self._integration_service.get_integration(user_id, step.integration)
        
        if not integration:
            raise ValueError(f"Integration {step.integration} not connected")
        
        if not integration.is_active:
            raise ValueError(f"Integration {step.integration} is not active")
        
        if integration.is_token_expired:
            # Try to refresh the token
            refresh_result = self._integration_service.refresh_token(str(integration.id))
            if not refresh_result.success:
                raise ValueError(f"Integration {step.integration} token expired and refresh failed")
        
        # In a real implementation, we would call the integration API here
        # For now, we simulate successful execution
        return {
            'success': True,
            'integration': step.integration,
            'action': step.action,
            'parameters': step.parameters,
            'executed_at': timezone.now().isoformat(),
        }
    
    async def execute_workflow(
        self,
        user_id: str,
        request: ExecuteWorkflowRequest
    ) -> WorkflowResult:
        """
        Execute workflow asynchronously with permission checks.
        
        Requirements: 8.1, 8.2, 8.3, 8.4, 8.5, 8.6
        - Verify permissions before execution
        - Require permission_flag=True for external actions
        - Execute asynchronously
        - Log errors and notify user on failure
        - Require confirmation when blend > 80%
        - Track content origin
        
        Args:
            user_id: The user's ID
            request: The execution request
            
        Returns:
            WorkflowResult with execution status
        """
        from asgiref.sync import sync_to_async
        
        # Use sync_to_async to wrap the synchronous execution
        return await sync_to_async(self.execute_workflow_sync)(user_id, request)
    
    def _log_workflow_step(
        self,
        user_id: str,
        workflow: Workflow,
        step: WorkflowStepData,
        outcome: str,
        cognitive_blend: int,
    ):
        """Log a workflow step execution."""
        action_type = self._map_action_to_type(step.action)
        
        self._audit_service.log_action(
            user_id=user_id,
            action_type=action_type,
            outcome=outcome,
            target_integration=step.integration,
            input_data={
                'workflow_id': str(workflow.id),
                'workflow_name': workflow.name,
                'action': step.action,
                'parameters': step.parameters,
            },
            cognitive_blend=cognitive_blend,
            reasoning_chain=f"Workflow step: {step.action} on {step.integration}",
            is_twin_generated=True,
        )
    
    def _log_workflow_error(
        self,
        user_id: str,
        workflow: Workflow,
        error: str,
        cognitive_blend: int,
        step: Optional[WorkflowStepData] = None,
    ):
        """
        Log a workflow error.
        
        Requirements: 8.4
        - Log errors and notify user on failure
        """
        input_data = {
            'workflow_id': str(workflow.id),
            'workflow_name': workflow.name,
            'error': error,
        }
        
        if step:
            input_data['step_integration'] = step.integration
            input_data['step_action'] = step.action
        
        self._audit_service.log_action(
            user_id=user_id,
            action_type=ActionType.WRITE,
            outcome=AuditOutcome.FAILURE,
            target_integration=step.integration if step else None,
            input_data=input_data,
            cognitive_blend=cognitive_blend,
            reasoning_chain=f"Workflow error: {error}",
            is_twin_generated=True,
        )
    
    def get_execution(self, execution_id: str) -> Optional[WorkflowExecution]:
        """
        Get a workflow execution by ID.
        
        Args:
            execution_id: The execution ID
            
        Returns:
            WorkflowExecution if found, None otherwise
        """
        try:
            return WorkflowExecution.objects.get(id=execution_id)
        except WorkflowExecution.DoesNotExist:
            return None
    
    def get_user_executions(
        self,
        user_id: str,
        status: Optional[str] = None,
        limit: int = 100
    ) -> List[WorkflowExecution]:
        """
        Get workflow executions for a user.
        
        Args:
            user_id: The user's ID
            status: Optional filter by status
            limit: Maximum number of executions to return
            
        Returns:
            List of WorkflowExecution objects
        """
        queryset = WorkflowExecution.objects.filter(user_id=user_id)
        
        if status:
            queryset = queryset.filter(status=status)
        
        return list(queryset.order_by('-created_at')[:limit])
    
    def cancel_execution(self, execution_id: str) -> bool:
        """
        Cancel a pending or running workflow execution.
        
        Args:
            execution_id: The execution ID
            
        Returns:
            True if cancelled, False otherwise
        """
        try:
            execution = WorkflowExecution.objects.get(id=execution_id)
        except WorkflowExecution.DoesNotExist:
            return False
        
        if execution.is_complete:
            return False
        
        execution.status = WorkflowStatus.CANCELLED
        execution.completed_at = timezone.now()
        execution.save()
        
        return True
    
    def deactivate_workflow(self, workflow_id: str) -> bool:
        """
        Deactivate a workflow.
        
        Args:
            workflow_id: The workflow ID
            
        Returns:
            True if deactivated, False otherwise
        """
        try:
            workflow = Workflow.objects.get(id=workflow_id)
            workflow.is_active = False
            workflow.save(update_fields=['is_active', 'updated_at'])
            return True
        except Workflow.DoesNotExist:
            return False
    
    def activate_workflow(self, workflow_id: str) -> bool:
        """
        Activate a workflow.
        
        Args:
            workflow_id: The workflow ID
            
        Returns:
            True if activated, False otherwise
        """
        try:
            workflow = Workflow.objects.get(id=workflow_id)
            workflow.is_active = True
            workflow.save(update_fields=['is_active', 'updated_at'])
            return True
        except Workflow.DoesNotExist:
            return False
    
    def delete_workflow(self, workflow_id: str) -> bool:
        """
        Delete a workflow.
        
        Args:
            workflow_id: The workflow ID
            
        Returns:
            True if deleted, False otherwise
        """
        try:
            workflow = Workflow.objects.get(id=workflow_id)
            workflow.delete()
            return True
        except Workflow.DoesNotExist:
            return False
