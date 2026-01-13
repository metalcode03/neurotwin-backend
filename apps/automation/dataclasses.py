"""
Dataclasses for the automation app.

Provides data transfer objects for integration operations.
Requirements: 7.1-7.6
"""

from dataclasses import dataclass, field
from typing import Optional, List, Dict, Any
from datetime import datetime


@dataclass
class IntegrationData:
    """
    Data transfer object for integration information.
    
    Requirements: 7.1
    
    Attributes:
        id: Unique identifier
        user_id: The user who owns this integration
        type: The integration type
        scopes: OAuth scopes granted
        steering_rules: Rules defining allowed actions
        permissions: Permission settings for the integration
        token_expires_at: When the OAuth token expires
        is_active: Whether the integration is active
        created_at: When the integration was created
    """
    
    id: str
    user_id: str
    type: str
    scopes: List[str]
    steering_rules: Dict[str, Any]
    permissions: Dict[str, bool]
    token_expires_at: Optional[datetime]
    is_active: bool
    created_at: datetime
    
    @classmethod
    def from_model(cls, integration) -> 'IntegrationData':
        """Create from an Integration model instance."""
        return cls(
            id=str(integration.id),
            user_id=str(integration.user_id),
            type=integration.type,
            scopes=integration.scopes or [],
            steering_rules=integration.steering_rules or {},
            permissions=integration.permissions or {},
            token_expires_at=integration.token_expires_at,
            is_active=integration.is_active,
            created_at=integration.created_at,
        )


@dataclass
class ConnectIntegrationRequest:
    """
    Request to connect a new integration.
    
    Requirements: 7.2
    
    Attributes:
        integration_type: The type of integration to connect
        oauth_code: The OAuth authorization code
        redirect_uri: The redirect URI used in OAuth flow
        requested_scopes: Optional list of specific scopes to request
    """
    
    integration_type: str
    oauth_code: str
    redirect_uri: str = ""
    requested_scopes: Optional[List[str]] = None


@dataclass
class UpdatePermissionsRequest:
    """
    Request to update integration permissions.
    
    Requirements: 7.4
    
    Attributes:
        permissions: Dictionary of permission name to granted status
    """
    
    permissions: Dict[str, bool]


@dataclass
class UpdateSteeringRulesRequest:
    """
    Request to update integration steering rules.
    
    Requirements: 7.3
    
    Attributes:
        steering_rules: Dictionary of steering rules
    """
    
    steering_rules: Dict[str, Any]


@dataclass
class TokenRefreshResult:
    """
    Result of a token refresh operation.
    
    Requirements: 7.5
    
    Attributes:
        success: Whether the refresh was successful
        new_expires_at: New expiration time if successful
        error: Error message if failed
        needs_reconnect: Whether user needs to reconnect
    """
    
    success: bool
    new_expires_at: Optional[datetime] = None
    error: Optional[str] = None
    needs_reconnect: bool = False
    
    @classmethod
    def successful(cls, expires_at: datetime) -> 'TokenRefreshResult':
        """Create a successful result."""
        return cls(success=True, new_expires_at=expires_at)
    
    @classmethod
    def failed(cls, error: str, needs_reconnect: bool = False) -> 'TokenRefreshResult':
        """Create a failed result."""
        return cls(success=False, error=error, needs_reconnect=needs_reconnect)


@dataclass
class MinimalScopesConfig:
    """
    Configuration for minimal OAuth scopes per integration type.
    
    Requirements: 7.2 - Request only necessary OAuth scopes
    
    Attributes:
        integration_type: The integration type
        required_scopes: Minimum scopes needed for basic functionality
        optional_scopes: Additional scopes for extended features
    """
    
    integration_type: str
    required_scopes: List[str] = field(default_factory=list)
    optional_scopes: List[str] = field(default_factory=list)


# Workflow-related dataclasses
# Requirements: 8.1-8.6

@dataclass
class WorkflowStepData:
    """
    Data transfer object for a workflow step.
    
    Requirements: 8.1
    
    Attributes:
        integration: The integration type for this step
        action: The action to perform
        parameters: Parameters for the action
        requires_confirmation: Whether this step requires user confirmation
        order: The order of this step in the workflow
    """
    
    integration: str
    action: str
    parameters: Dict[str, Any] = field(default_factory=dict)
    requires_confirmation: bool = False
    order: int = 0


@dataclass
class WorkflowData:
    """
    Data transfer object for workflow information.
    
    Requirements: 8.1
    
    Attributes:
        id: Unique identifier
        user_id: The user who owns this workflow
        name: Human-readable name for the workflow
        trigger: The trigger configuration for the workflow
        steps: List of workflow steps
        is_active: Whether the workflow is active
        created_at: When the workflow was created
    """
    
    id: str
    user_id: str
    name: str
    trigger: Dict[str, Any]
    steps: List[WorkflowStepData]
    is_active: bool
    created_at: datetime
    
    @classmethod
    def from_model(cls, workflow) -> 'WorkflowData':
        """Create from a Workflow model instance."""
        steps = [
            WorkflowStepData(
                integration=step.get('integration', ''),
                action=step.get('action', ''),
                parameters=step.get('parameters', {}),
                requires_confirmation=step.get('requires_confirmation', False),
                order=step.get('order', idx),
            )
            for idx, step in enumerate(workflow.steps or [])
        ]
        
        return cls(
            id=str(workflow.id),
            user_id=str(workflow.user_id),
            name=workflow.name,
            trigger=workflow.trigger_config or {},
            steps=steps,
            is_active=workflow.is_active,
            created_at=workflow.created_at,
        )


@dataclass
class WorkflowResult:
    """
    Result of a workflow execution.
    
    Requirements: 8.3, 8.4
    
    Attributes:
        success: Whether the workflow completed successfully
        workflow_id: The workflow that was executed
        steps_completed: Number of steps completed
        total_steps: Total number of steps in the workflow
        error: Error message if failed
        requires_confirmation: Whether user confirmation is needed
        pending_step: The step awaiting confirmation (if any)
        is_twin_generated: Whether the content was generated by the Twin
    """
    
    success: bool
    workflow_id: str
    steps_completed: int = 0
    total_steps: int = 0
    error: Optional[str] = None
    requires_confirmation: bool = False
    pending_step: Optional[WorkflowStepData] = None
    is_twin_generated: bool = True
    
    @classmethod
    def successful(cls, workflow_id: str, steps_completed: int, total_steps: int) -> 'WorkflowResult':
        """Create a successful result."""
        return cls(
            success=True,
            workflow_id=workflow_id,
            steps_completed=steps_completed,
            total_steps=total_steps,
        )
    
    @classmethod
    def failed(cls, workflow_id: str, error: str, steps_completed: int = 0, total_steps: int = 0) -> 'WorkflowResult':
        """Create a failed result."""
        return cls(
            success=False,
            workflow_id=workflow_id,
            steps_completed=steps_completed,
            total_steps=total_steps,
            error=error,
        )
    
    @classmethod
    def needs_confirmation(
        cls, 
        workflow_id: str, 
        pending_step: WorkflowStepData,
        steps_completed: int,
        total_steps: int
    ) -> 'WorkflowResult':
        """Create a result indicating confirmation is needed."""
        return cls(
            success=False,
            workflow_id=workflow_id,
            steps_completed=steps_completed,
            total_steps=total_steps,
            requires_confirmation=True,
            pending_step=pending_step,
        )


@dataclass
class CreateWorkflowRequest:
    """
    Request to create a new workflow.
    
    Requirements: 8.1
    
    Attributes:
        name: Human-readable name for the workflow
        trigger_config: Configuration for when the workflow triggers
        steps: List of workflow steps
    """
    
    name: str
    trigger_config: Dict[str, Any]
    steps: List[WorkflowStepData]


@dataclass
class ExecuteWorkflowRequest:
    """
    Request to execute a workflow.
    
    Requirements: 8.1, 8.2, 8.5
    
    Attributes:
        workflow_id: The workflow to execute
        permission_flag: Whether permission has been granted for external actions
        cognitive_blend: The current cognitive blend value (0-100)
        confirmation_token: Token for confirming high-blend actions
    """
    
    workflow_id: str
    permission_flag: bool = False
    cognitive_blend: int = 50
    confirmation_token: Optional[str] = None
