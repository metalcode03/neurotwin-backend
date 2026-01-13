"""
Property-based tests for workflow execution.

Feature: neurotwin-platform
Validates: Requirements 8.1-8.6

These tests use Hypothesis to verify workflow properties hold
across a wide range of inputs.
"""

import pytest
from hypothesis import given, strategies as st, settings, assume
from django.utils import timezone
from datetime import timedelta

from apps.automation.services import WorkflowEngine, IntegrationService
from apps.automation.models import (
    Integration, IntegrationType, Workflow, WorkflowExecution, WorkflowStatus
)
from apps.automation.dataclasses import (
    WorkflowStepData,
    WorkflowResult,
    CreateWorkflowRequest,
    ExecuteWorkflowRequest,
)
from apps.safety.services import PermissionService, AuditService
from apps.safety.models import ActionType, AuditOutcome
from apps.authentication.models import User
from apps.twin.models import Twin


# Custom strategies for generating test data
integration_type_strategy = st.sampled_from([
    IntegrationType.WHATSAPP,
    IntegrationType.TELEGRAM,
    IntegrationType.SLACK,
    IntegrationType.GMAIL,
    IntegrationType.OUTLOOK,
    IntegrationType.GOOGLE_CALENDAR,
])

action_strategy = st.sampled_from([
    'read_messages', 'send_message', 'list_contacts',
    'create_event', 'update_event', 'delete_event',
])

# Non-high-risk actions only (excludes delete which maps to DELETE action type)
non_high_risk_action_strategy = st.sampled_from([
    'read_messages', 'send_message', 'list_contacts',
    'create_event', 'update_event',
])

cognitive_blend_strategy = st.integers(min_value=0, max_value=100)


workflow_name_strategy = st.text(
    alphabet=st.characters(whitelist_categories=('L', 'N', 'Zs')),
    min_size=3,
    max_size=50
).filter(lambda x: len(x.strip()) >= 3)


def create_test_user(email_suffix: str) -> User:
    """Create a test user with unique email."""
    email = f"workflow_test_{email_suffix}@example.com"
    User.objects.filter(email=email).delete()
    return User.objects.create_user(email=email, password="testpass123")


def create_test_twin(user: User) -> Twin:
    """Create a test Twin for a user."""
    Twin.objects.filter(user=user).delete()
    return Twin.objects.create(
        user=user,
        model='gemini-3-flash',
        cognitive_blend=50,
        is_active=True,
        kill_switch_active=False,
    )


def create_test_integration(user: User, integration_type: str) -> Integration:
    """Create a test integration for a user."""
    Integration.objects.filter(user=user, type=integration_type).delete()
    integration = Integration.objects.create(
        user=user,
        type=integration_type,
        scopes=['read', 'write'],
        permissions={'read': True, 'write': True, 'send': True},
        is_active=True,
        token_expires_at=timezone.now() + timedelta(hours=1),
    )
    integration.oauth_token = 'test_token'
    integration.refresh_token = 'test_refresh_token'
    integration.save()
    return integration


def grant_permission(user_id: str, integration: str, action_type: str):
    """Grant a permission to a user."""
    service = PermissionService()
    service.grant_permission(
        user_id=user_id,
        integration=integration,
        action_type=action_type,
        requires_approval=False,
        reason="Test setup"
    )


@pytest.mark.django_db(transaction=True)
class TestExternalActionPermissionFlag:
    """
    Property 22: External action permission flag
    
    *For any* action on external integrations, the Twin SHALL NOT execute
    unless permission_flag=True.
    
    **Validates: Requirements 8.2**
    """
    
    @settings(max_examples=5, deadline=None)
    @given(
        integration_type=integration_type_strategy,
        action=action_strategy,
        cognitive_blend=cognitive_blend_strategy,
    )
    def test_workflow_fails_without_permission_flag(
        self,
        integration_type: str,
        action: str,
        cognitive_blend: int,
    ):
        """
        Feature: neurotwin-platform, Property 22: External action permission flag
        
        For any workflow execution without permission_flag=True,
        execution should fail.
        """
        # Create test user and twin
        user = create_test_user(f"p22_no_flag_{hash((integration_type, action)) % 10000}")
        
        try:
            twin = create_test_twin(user)
            integration = create_test_integration(user, integration_type)
            
            # Grant ALL action types so we can test permission_flag specifically
            # This includes DELETE, FINANCIAL, LEGAL, CALL which some actions map to
            for action_type in [
                ActionType.READ, ActionType.WRITE, ActionType.SEND,
                ActionType.DELETE, ActionType.FINANCIAL, ActionType.LEGAL, ActionType.CALL
            ]:
                grant_permission(str(user.id), integration_type, action_type)
            
            # Create workflow
            engine = WorkflowEngine()
            workflow = engine.create_workflow(
                str(user.id),
                CreateWorkflowRequest(
                    name="Test Workflow",
                    trigger_config={"type": "manual"},
                    steps=[
                        WorkflowStepData(
                            integration=integration_type,
                            action=action,
                            parameters={},
                            order=0,
                        )
                    ],
                )
            )
            
            # Execute WITHOUT permission_flag
            request = ExecuteWorkflowRequest(
                workflow_id=str(workflow.id),
                permission_flag=False,  # This should cause failure
                cognitive_blend=cognitive_blend,
            )
            
            result = engine.execute_workflow_sync(str(user.id), request)
            
            # Should fail because permission_flag is False
            assert not result.success, (
                "Workflow should fail when permission_flag is False"
            )
            assert "permission flag" in result.error.lower(), (
                f"Error should mention permission flag, got: {result.error}"
            )
        finally:
            User.objects.filter(id=user.id).delete()


    @settings(max_examples=5, deadline=None)
    @given(
        integration_type=integration_type_strategy,
        action=non_high_risk_action_strategy,  # Use non-high-risk actions to avoid confirmation requirement
        cognitive_blend=st.integers(min_value=0, max_value=79),  # Below confirmation threshold
    )
    def test_workflow_succeeds_with_permission_flag(
        self,
        integration_type: str,
        action: str,
        cognitive_blend: int,
    ):
        """
        Feature: neurotwin-platform, Property 22: External action permission flag
        
        For any workflow execution with permission_flag=True and proper permissions,
        execution should succeed.
        """
        # Create test user and twin
        user = create_test_user(f"p22_with_flag_{hash((integration_type, action)) % 10000}")
        
        try:
            twin = create_test_twin(user)
            integration = create_test_integration(user, integration_type)
            
            # Grant ALL action types to ensure any action can execute
            for action_type in [
                ActionType.READ, ActionType.WRITE, ActionType.SEND,
                ActionType.DELETE, ActionType.FINANCIAL, ActionType.LEGAL, ActionType.CALL
            ]:
                grant_permission(str(user.id), integration_type, action_type)
            
            # Create workflow
            engine = WorkflowEngine()
            workflow = engine.create_workflow(
                str(user.id),
                CreateWorkflowRequest(
                    name="Test Workflow",
                    trigger_config={"type": "manual"},
                    steps=[
                        WorkflowStepData(
                            integration=integration_type,
                            action=action,
                            parameters={},
                            order=0,
                        )
                    ],
                )
            )
            
            # Execute WITH permission_flag
            request = ExecuteWorkflowRequest(
                workflow_id=str(workflow.id),
                permission_flag=True,  # This should allow execution
                cognitive_blend=cognitive_blend,
            )
            
            result = engine.execute_workflow_sync(str(user.id), request)
            
            # Should succeed with permission_flag=True
            assert result.success, (
                f"Workflow should succeed with permission_flag=True, got error: {result.error}"
            )
        finally:
            User.objects.filter(id=user.id).delete()


@pytest.mark.django_db(transaction=True)
class TestWorkflowAsyncExecution:
    """
    Property 23: Workflow async execution
    
    *For any* workflow execution, the system SHALL execute asynchronously
    without blocking user interactions.
    
    **Validates: Requirements 8.3**
    """
    
    @settings(max_examples=5, deadline=None)
    @given(
        integration_type=integration_type_strategy,
        num_steps=st.integers(min_value=1, max_value=5),
    )
    def test_workflow_creates_execution_record(
        self,
        integration_type: str,
        num_steps: int,
    ):
        """
        Feature: neurotwin-platform, Property 23: Workflow async execution
        
        For any workflow execution, an execution record should be created
        to track async progress.
        """
        user = create_test_user(f"p23_exec_{hash(integration_type) % 10000}")
        
        try:
            twin = create_test_twin(user)
            integration = create_test_integration(user, integration_type)
            
            # Grant permissions
            grant_permission(str(user.id), integration_type, ActionType.READ)
            grant_permission(str(user.id), integration_type, ActionType.WRITE)
            
            # Create workflow with multiple steps
            steps = [
                WorkflowStepData(
                    integration=integration_type,
                    action='read_messages',
                    parameters={},
                    order=i,
                )
                for i in range(num_steps)
            ]
            
            engine = WorkflowEngine()
            workflow = engine.create_workflow(
                str(user.id),
                CreateWorkflowRequest(
                    name="Multi-step Workflow",
                    trigger_config={"type": "manual"},
                    steps=steps,
                )
            )
            
            # Execute workflow
            request = ExecuteWorkflowRequest(
                workflow_id=str(workflow.id),
                permission_flag=True,
                cognitive_blend=50,
            )
            
            result = engine.execute_workflow_sync(str(user.id), request)
            
            # Verify execution record was created
            executions = engine.get_user_executions(str(user.id))
            assert len(executions) > 0, "Execution record should be created"
            
            # Verify execution tracks progress
            latest = executions[0]
            assert latest.total_steps == num_steps, (
                f"Execution should track {num_steps} total steps"
            )
        finally:
            User.objects.filter(id=user.id).delete()


@pytest.mark.django_db(transaction=True)
class TestWorkflowErrorLogging:
    """
    Property 24: Workflow error logging
    
    *For any* failed workflow step, the system SHALL log the error
    and notify the user.
    
    **Validates: Requirements 8.4**
    """
    
    @settings(max_examples=5, deadline=None)
    @given(
        integration_type=integration_type_strategy,
        cognitive_blend=cognitive_blend_strategy,
    )
    def test_missing_permission_logs_error(
        self,
        integration_type: str,
        cognitive_blend: int,
    ):
        """
        Feature: neurotwin-platform, Property 24: Workflow error logging
        
        For any workflow that fails due to missing permissions,
        the error should be logged.
        """
        user = create_test_user(f"p24_perm_{hash(integration_type) % 10000}")
        
        try:
            twin = create_test_twin(user)
            # Don't create integration - this will cause failure
            
            engine = WorkflowEngine()
            workflow = engine.create_workflow(
                str(user.id),
                CreateWorkflowRequest(
                    name="Test Workflow",
                    trigger_config={"type": "manual"},
                    steps=[
                        WorkflowStepData(
                            integration=integration_type,
                            action='send_message',
                            parameters={},
                            order=0,
                        )
                    ],
                )
            )
            
            # Execute without proper permissions
            request = ExecuteWorkflowRequest(
                workflow_id=str(workflow.id),
                permission_flag=True,
                cognitive_blend=cognitive_blend,
            )
            
            result = engine.execute_workflow_sync(str(user.id), request)
            
            # Should fail
            assert not result.success, "Workflow should fail without permissions"
            
            # Check audit log for error
            audit_service = AuditService()
            history = audit_service.get_audit_history(str(user.id), limit=10)
            
            # Should have logged the error
            error_logs = [
                h for h in history 
                if h.outcome == AuditOutcome.FAILURE
            ]
            assert len(error_logs) > 0, (
                "Error should be logged to audit when workflow fails"
            )
        finally:
            User.objects.filter(id=user.id).delete()


@pytest.mark.django_db(transaction=True)
class TestHighBlendConfirmationRequirement:
    """
    Property 25: High blend confirmation requirement
    
    *For any* external action when Cognitive_Blend exceeds 80%,
    the system SHALL require explicit user confirmation before execution.
    
    **Validates: Requirements 8.5**
    """
    
    @settings(max_examples=5, deadline=None)
    @given(
        integration_type=integration_type_strategy,
        action=action_strategy,
        high_blend=st.integers(min_value=81, max_value=100),
    )
    def test_high_blend_requires_confirmation(
        self,
        integration_type: str,
        action: str,
        high_blend: int,
    ):
        """
        Feature: neurotwin-platform, Property 25: High blend confirmation requirement
        
        For any workflow with cognitive_blend > 80%, execution should
        require confirmation.
        """
        user = create_test_user(f"p25_high_{hash((integration_type, action)) % 10000}")
        
        try:
            twin = create_test_twin(user)
            integration = create_test_integration(user, integration_type)
            
            # Grant ALL action types to ensure any action can execute
            for action_type in [
                ActionType.READ, ActionType.WRITE, ActionType.SEND,
                ActionType.DELETE, ActionType.FINANCIAL, ActionType.LEGAL, ActionType.CALL
            ]:
                grant_permission(str(user.id), integration_type, action_type)
            
            engine = WorkflowEngine()
            workflow = engine.create_workflow(
                str(user.id),
                CreateWorkflowRequest(
                    name="High Blend Workflow",
                    trigger_config={"type": "manual"},
                    steps=[
                        WorkflowStepData(
                            integration=integration_type,
                            action=action,
                            parameters={},
                            order=0,
                        )
                    ],
                )
            )
            
            # Execute with high blend but no confirmation token
            request = ExecuteWorkflowRequest(
                workflow_id=str(workflow.id),
                permission_flag=True,
                cognitive_blend=high_blend,
                confirmation_token=None,  # No confirmation
            )
            
            result = engine.execute_workflow_sync(str(user.id), request)
            
            # Should require confirmation
            assert result.requires_confirmation, (
                f"Workflow with blend {high_blend} should require confirmation"
            )
            assert result.pending_step is not None, (
                "Should indicate which step is pending confirmation"
            )
        finally:
            User.objects.filter(id=user.id).delete()


    @settings(max_examples=5, deadline=None)
    @given(
        integration_type=integration_type_strategy,
        action=non_high_risk_action_strategy,  # Use non-high-risk actions to avoid confirmation requirement
        low_blend=st.integers(min_value=0, max_value=80),
    )
    def test_low_blend_does_not_require_confirmation(
        self,
        integration_type: str,
        action: str,
        low_blend: int,
    ):
        """
        Feature: neurotwin-platform, Property 25: High blend confirmation requirement
        
        For any workflow with cognitive_blend <= 80%, execution should
        not require confirmation (unless step explicitly requires it or action is high-risk).
        """
        user = create_test_user(f"p25_low_{hash((integration_type, action)) % 10000}")
        
        try:
            twin = create_test_twin(user)
            integration = create_test_integration(user, integration_type)
            
            # Grant ALL action types to ensure any action can execute
            for action_type in [
                ActionType.READ, ActionType.WRITE, ActionType.SEND,
                ActionType.DELETE, ActionType.FINANCIAL, ActionType.LEGAL, ActionType.CALL
            ]:
                grant_permission(str(user.id), integration_type, action_type)
            
            engine = WorkflowEngine()
            workflow = engine.create_workflow(
                str(user.id),
                CreateWorkflowRequest(
                    name="Low Blend Workflow",
                    trigger_config={"type": "manual"},
                    steps=[
                        WorkflowStepData(
                            integration=integration_type,
                            action=action,
                            parameters={},
                            requires_confirmation=False,  # Explicitly no confirmation
                            order=0,
                        )
                    ],
                )
            )
            
            # Execute with low blend
            request = ExecuteWorkflowRequest(
                workflow_id=str(workflow.id),
                permission_flag=True,
                cognitive_blend=low_blend,
            )
            
            result = engine.execute_workflow_sync(str(user.id), request)
            
            # Should not require confirmation (should succeed or fail for other reasons)
            assert not result.requires_confirmation, (
                f"Workflow with blend {low_blend} should not require confirmation"
            )
        finally:
            User.objects.filter(id=user.id).delete()


@pytest.mark.django_db(transaction=True)
class TestContentOriginTracking:
    """
    Property 26: Content origin tracking
    
    *For any* content in integrations, the system SHALL distinguish
    Twin-generated content from user-authored content.
    
    **Validates: Requirements 8.6**
    """
    
    @settings(max_examples=5, deadline=None)
    @given(
        integration_type=integration_type_strategy,
        action=non_high_risk_action_strategy,  # Use non-high-risk actions to avoid confirmation requirement
    )
    def test_workflow_execution_tracks_twin_origin(
        self,
        integration_type: str,
        action: str,
    ):
        """
        Feature: neurotwin-platform, Property 26: Content origin tracking
        
        For any workflow execution, the system should track that
        content was generated by the Twin.
        """
        user = create_test_user(f"p26_origin_{hash((integration_type, action)) % 10000}")
        
        try:
            twin = create_test_twin(user)
            integration = create_test_integration(user, integration_type)
            
            # Grant ALL action types to ensure any action can execute
            for action_type in [
                ActionType.READ, ActionType.WRITE, ActionType.SEND,
                ActionType.DELETE, ActionType.FINANCIAL, ActionType.LEGAL, ActionType.CALL
            ]:
                grant_permission(str(user.id), integration_type, action_type)
            
            engine = WorkflowEngine()
            workflow = engine.create_workflow(
                str(user.id),
                CreateWorkflowRequest(
                    name="Origin Tracking Workflow",
                    trigger_config={"type": "manual"},
                    steps=[
                        WorkflowStepData(
                            integration=integration_type,
                            action=action,
                            parameters={},
                            order=0,
                        )
                    ],
                )
            )
            
            # Execute workflow
            request = ExecuteWorkflowRequest(
                workflow_id=str(workflow.id),
                permission_flag=True,
                cognitive_blend=50,
            )
            
            result = engine.execute_workflow_sync(str(user.id), request)
            
            # Check execution record tracks Twin origin
            executions = engine.get_user_executions(str(user.id))
            if executions:
                latest = executions[0]
                assert latest.is_twin_generated, (
                    "Execution should be marked as Twin-generated"
                )
            
            # Check result tracks Twin origin
            assert result.is_twin_generated, (
                "Result should indicate content is Twin-generated"
            )
        finally:
            User.objects.filter(id=user.id).delete()


    @settings(max_examples=5, deadline=None)
    @given(
        integration_type=integration_type_strategy,
        action=non_high_risk_action_strategy,  # Use non-high-risk actions to avoid confirmation requirement
    )
    def test_audit_log_tracks_twin_generated_flag(
        self,
        integration_type: str,
        action: str,
    ):
        """
        Feature: neurotwin-platform, Property 26: Content origin tracking
        
        For any workflow execution, audit logs should track whether
        content was Twin-generated.
        """
        user = create_test_user(f"p26_audit_{hash((integration_type, action)) % 10000}")
        
        try:
            twin = create_test_twin(user)
            integration = create_test_integration(user, integration_type)
            
            # Grant ALL action types to ensure any action can execute
            for action_type in [
                ActionType.READ, ActionType.WRITE, ActionType.SEND,
                ActionType.DELETE, ActionType.FINANCIAL, ActionType.LEGAL, ActionType.CALL
            ]:
                grant_permission(str(user.id), integration_type, action_type)
            
            engine = WorkflowEngine()
            workflow = engine.create_workflow(
                str(user.id),
                CreateWorkflowRequest(
                    name="Audit Origin Workflow",
                    trigger_config={"type": "manual"},
                    steps=[
                        WorkflowStepData(
                            integration=integration_type,
                            action=action,
                            parameters={},
                            order=0,
                        )
                    ],
                )
            )
            
            # Execute workflow
            request = ExecuteWorkflowRequest(
                workflow_id=str(workflow.id),
                permission_flag=True,
                cognitive_blend=50,
            )
            
            result = engine.execute_workflow_sync(str(user.id), request)
            
            # Check audit logs track Twin origin
            audit_service = AuditService()
            history = audit_service.get_audit_history(str(user.id), limit=10)
            
            # Find workflow-related audit entries
            workflow_logs = [
                h for h in history
                if h.input_data and 'workflow_id' in h.input_data
            ]
            
            for log in workflow_logs:
                assert log.is_twin_generated, (
                    "Audit log should mark workflow actions as Twin-generated"
                )
        finally:
            User.objects.filter(id=user.id).delete()
