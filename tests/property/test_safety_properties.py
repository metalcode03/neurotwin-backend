"""
Property-based tests for safety/permission service.

Feature: neurotwin-platform
Validates: Requirements 10.1-10.7

These tests use Hypothesis to verify permission properties hold
across a wide range of inputs.
"""

import pytest
from hypothesis import given, strategies as st, settings, assume
from django.utils import timezone

from apps.safety.services import PermissionService
from apps.safety.models import PermissionScope, PermissionHistory, ActionType, IntegrationType
from apps.safety.dataclasses import PermissionUpdateRequest, PermissionCheckResult
from apps.authentication.models import User


# Custom strategies for generating test data
action_type_strategy = st.sampled_from([
    ActionType.READ,
    ActionType.WRITE,
    ActionType.SEND,
    ActionType.DELETE,
    ActionType.FINANCIAL,
    ActionType.LEGAL,
    ActionType.CALL,
])

integration_strategy = st.sampled_from([
    IntegrationType.WHATSAPP,
    IntegrationType.TELEGRAM,
    IntegrationType.SLACK,
    IntegrationType.GMAIL,
    IntegrationType.OUTLOOK,
    IntegrationType.GOOGLE_CALENDAR,
    IntegrationType.GOOGLE_DOCS,
    IntegrationType.MICROSOFT_OFFICE,
    IntegrationType.ZOOM,
    IntegrationType.GOOGLE_MEET,
    IntegrationType.CRM,
    IntegrationType.VOICE,
])

# High-risk action types
high_risk_action_strategy = st.sampled_from([
    ActionType.FINANCIAL,
    ActionType.LEGAL,
    ActionType.DELETE,
])

# Non-high-risk action types
non_high_risk_action_strategy = st.sampled_from([
    ActionType.READ,
    ActionType.WRITE,
    ActionType.SEND,
    ActionType.CALL,
])


@pytest.fixture
def permission_service():
    """Provide a PermissionService instance."""
    return PermissionService()


def create_test_user(email_suffix: str) -> User:
    """Create a test user with unique email."""
    email = f"safety_test_{email_suffix}@example.com"
    User.objects.filter(email=email).delete()
    return User.objects.create_user(email=email, password="testpass123")



@pytest.mark.django_db(transaction=True)
class TestPermissionVerificationBeforeAction:
    """
    Property 21: Permission verification before action
    
    *For any* Twin action attempt, the system SHALL verify the action falls
    within granted permission scopes before execution.
    
    **Validates: Requirements 8.1, 10.2**
    """
    
    @settings(deadline=None)
    @given(
        integration=integration_strategy,
        action_type=action_type_strategy,
        is_granted=st.booleans()
    )
    def test_permission_verification_respects_granted_status(
        self, 
        integration: str, 
        action_type: str,
        is_granted: bool
    ):
        """
        Feature: neurotwin-platform, Property 21: Permission verification before action
        
        For any permission scope, the check_permission result should respect
        the is_granted status.
        """
        service = PermissionService()
        
        # Create test user with unique identifier
        user = create_test_user(f"p21_{integration}_{action_type}_{is_granted}_{hash((integration, action_type, is_granted)) % 10000}")
        
        try:
            # Set up permission with specific granted status
            request = PermissionUpdateRequest(
                integration=integration,
                action_type=action_type,
                is_granted=is_granted,
                requires_approval=False,  # Simplify test by not requiring approval
                reason="Test setup"
            )
            service.update_permission(str(user.id), request)
            
            # Check permission
            allowed, needs_approval = service.check_permission(
                str(user.id), 
                integration, 
                action_type
            )
            
            # If not granted, should not be allowed
            if not is_granted:
                assert not allowed, (
                    f"Permission for {integration}/{action_type} should NOT be allowed "
                    f"when is_granted={is_granted}"
                )
            else:
                # If granted, should be allowed (may or may not need approval)
                assert allowed, (
                    f"Permission for {integration}/{action_type} should be allowed "
                    f"when is_granted={is_granted}"
                )
        finally:
            User.objects.filter(id=user.id).delete()


@pytest.mark.django_db(transaction=True)
class TestPermissionScopeDefinition:
    """
    Property 34: Permission scope definition
    
    *For any* integration and action type combination, the permission system
    SHALL have a defined scope.
    
    **Validates: Requirements 10.1**
    """
    
    @settings(deadline=None)
    @given(
        integration=integration_strategy,
        action_type=action_type_strategy
    )
    def test_permission_scope_can_be_defined(
        self, 
        integration: str, 
        action_type: str
    ):
        """
        Feature: neurotwin-platform, Property 34: Permission scope definition
        
        For any integration and action type combination, a permission scope
        can be created and retrieved.
        """
        service = PermissionService()
        
        # Create test user
        user = create_test_user(f"p34_{integration}_{action_type}_{hash((integration, action_type)) % 10000}")
        
        try:
            # Create permission scope
            permission = service.get_or_create_permission(
                str(user.id),
                integration,
                action_type
            )
            
            # Verify scope was created with correct values
            assert permission is not None, "Permission scope should be created"
            assert permission.integration == integration, f"Integration should be {integration}"
            assert permission.action_type == action_type, f"Action type should be {action_type}"
            assert str(permission.user_id) == str(user.id), "User ID should match"
            
            # Verify scope can be retrieved
            retrieved = service.get_permission(str(user.id), integration, action_type)
            assert retrieved is not None, "Permission scope should be retrievable"
            assert retrieved.id == permission.id, "Retrieved permission should match created"
        finally:
            User.objects.filter(id=user.id).delete()
    
    @settings(deadline=None)
    @given(
        integration=integration_strategy,
        action_type=action_type_strategy
    )
    def test_permission_scope_uniqueness(
        self, 
        integration: str, 
        action_type: str
    ):
        """
        Feature: neurotwin-platform, Property 34: Permission scope definition
        
        For any user, integration, and action type combination, there should
        be exactly one permission scope.
        """
        service = PermissionService()
        
        # Create test user
        user = create_test_user(f"p34_unique_{integration}_{action_type}_{hash((integration, action_type)) % 10000}")
        
        try:
            # Create permission scope twice
            permission1 = service.get_or_create_permission(
                str(user.id),
                integration,
                action_type
            )
            permission2 = service.get_or_create_permission(
                str(user.id),
                integration,
                action_type
            )
            
            # Should return the same permission
            assert permission1.id == permission2.id, (
                "get_or_create_permission should return the same permission "
                "for the same user/integration/action_type"
            )
            
            # Verify only one exists in database
            count = PermissionScope.objects.filter(
                user_id=user.id,
                integration=integration,
                action_type=action_type
            ).count()
            assert count == 1, f"Should have exactly 1 permission scope, found {count}"
        finally:
            User.objects.filter(id=user.id).delete()



@pytest.mark.django_db(transaction=True)
class TestHighRiskActionApproval:
    """
    Property 35: High-risk action approval
    
    *For any* financial, legal, or irreversible action, the system SHALL
    require explicit per-action approval.
    
    **Validates: Requirements 10.3, 10.4, 10.5**
    """
    
    @settings(deadline=None)
    @given(
        integration=integration_strategy,
        action_type=high_risk_action_strategy
    )
    def test_high_risk_actions_require_approval(
        self, 
        integration: str, 
        action_type: str
    ):
        """
        Feature: neurotwin-platform, Property 35: High-risk action approval
        
        For any high-risk action (financial, legal, delete), even when
        permission is granted, approval should be required.
        """
        service = PermissionService()
        
        # Create test user
        user = create_test_user(f"p35_{integration}_{action_type}_{hash((integration, action_type)) % 10000}")
        
        try:
            # Grant permission without requiring approval
            request = PermissionUpdateRequest(
                integration=integration,
                action_type=action_type,
                is_granted=True,
                requires_approval=False,  # Try to disable approval
                reason="Test setup"
            )
            service.update_permission(str(user.id), request)
            
            # Check permission
            allowed, needs_approval = service.check_permission(
                str(user.id), 
                integration, 
                action_type
            )
            
            # High-risk actions should always require approval
            assert allowed, f"Permission should be allowed for granted {action_type}"
            assert needs_approval, (
                f"High-risk action {action_type} should ALWAYS require approval, "
                f"even when requires_approval=False in the permission scope"
            )
        finally:
            User.objects.filter(id=user.id).delete()
    
    @settings(deadline=None)
    @given(action_type=high_risk_action_strategy)
    def test_is_high_risk_action_identifies_high_risk(self, action_type: str):
        """
        Feature: neurotwin-platform, Property 35: High-risk action approval
        
        The is_high_risk_action method should correctly identify high-risk actions.
        """
        service = PermissionService()
        
        assert service.is_high_risk_action(action_type), (
            f"Action type {action_type} should be identified as high-risk"
        )
    
    @settings(deadline=None)
    @given(action_type=non_high_risk_action_strategy)
    def test_is_high_risk_action_identifies_non_high_risk(self, action_type: str):
        """
        Feature: neurotwin-platform, Property 35: High-risk action approval
        
        The is_high_risk_action method should correctly identify non-high-risk actions.
        """
        service = PermissionService()
        
        assert not service.is_high_risk_action(action_type), (
            f"Action type {action_type} should NOT be identified as high-risk"
        )


@pytest.mark.django_db(transaction=True)
class TestOutOfScopeActionHandling:
    """
    Property 36: Out-of-scope action handling
    
    *For any* action outside granted permission scope, the system SHALL
    request user approval before proceeding.
    
    **Validates: Requirements 10.6**
    """
    
    @settings(deadline=None)
    @given(
        integration=integration_strategy,
        action_type=action_type_strategy
    )
    def test_undefined_permission_denies_action(
        self, 
        integration: str, 
        action_type: str
    ):
        """
        Feature: neurotwin-platform, Property 36: Out-of-scope action handling
        
        For any action without a defined permission scope, the action should
        be denied (requiring user approval to proceed).
        """
        service = PermissionService()
        
        # Create test user
        user = create_test_user(f"p36_{integration}_{action_type}_{hash((integration, action_type)) % 10000}")
        
        try:
            # Do NOT create any permission scope
            # Check permission for undefined scope
            allowed, needs_approval = service.check_permission(
                str(user.id), 
                integration, 
                action_type
            )
            
            # Should not be allowed when no permission scope exists
            assert not allowed, (
                f"Action {integration}/{action_type} should NOT be allowed "
                f"when no permission scope is defined"
            )
        finally:
            User.objects.filter(id=user.id).delete()
    
    @settings(deadline=None)
    @given(
        integration=integration_strategy,
        action_type=action_type_strategy
    )
    def test_denied_permission_blocks_action(
        self, 
        integration: str, 
        action_type: str
    ):
        """
        Feature: neurotwin-platform, Property 36: Out-of-scope action handling
        
        For any action with is_granted=False, the action should be denied.
        """
        service = PermissionService()
        
        # Create test user
        user = create_test_user(f"p36_denied_{integration}_{action_type}_{hash((integration, action_type)) % 10000}")
        
        try:
            # Create permission scope with is_granted=False
            request = PermissionUpdateRequest(
                integration=integration,
                action_type=action_type,
                is_granted=False,
                reason="Test setup - denied"
            )
            service.update_permission(str(user.id), request)
            
            # Check permission
            allowed, needs_approval = service.check_permission(
                str(user.id), 
                integration, 
                action_type
            )
            
            # Should not be allowed
            assert not allowed, (
                f"Action {integration}/{action_type} should NOT be allowed "
                f"when is_granted=False"
            )
        finally:
            User.objects.filter(id=user.id).delete()



@pytest.mark.django_db(transaction=True)
class TestPermissionModifiability:
    """
    Property 37: Permission modifiability
    
    *For any* permission scope, the user SHALL be able to modify it at any
    time through settings.
    
    **Validates: Requirements 10.7**
    """
    
    @settings(deadline=None)
    @given(
        integration=integration_strategy,
        action_type=action_type_strategy,
        initial_granted=st.booleans(),
        new_granted=st.booleans()
    )
    def test_permission_can_be_modified(
        self, 
        integration: str, 
        action_type: str,
        initial_granted: bool,
        new_granted: bool
    ):
        """
        Feature: neurotwin-platform, Property 37: Permission modifiability
        
        For any permission scope, the is_granted status can be modified.
        """
        service = PermissionService()
        
        # Create test user
        user = create_test_user(f"p37_{integration}_{action_type}_{initial_granted}_{new_granted}_{hash((integration, action_type, initial_granted, new_granted)) % 10000}")
        
        try:
            # Set initial permission
            initial_request = PermissionUpdateRequest(
                integration=integration,
                action_type=action_type,
                is_granted=initial_granted,
                reason="Initial setup"
            )
            service.update_permission(str(user.id), initial_request)
            
            # Verify initial state
            permission = service.get_permission(str(user.id), integration, action_type)
            assert permission.is_granted == initial_granted, "Initial state should be set"
            
            # Modify permission
            modify_request = PermissionUpdateRequest(
                integration=integration,
                action_type=action_type,
                is_granted=new_granted,
                reason="User modification"
            )
            service.update_permission(str(user.id), modify_request)
            
            # Verify modified state
            permission = service.get_permission(str(user.id), integration, action_type)
            assert permission.is_granted == new_granted, (
                f"Permission should be modified from {initial_granted} to {new_granted}"
            )
        finally:
            User.objects.filter(id=user.id).delete()
    
    @settings(deadline=None)
    @given(
        integration=integration_strategy,
        action_type=action_type_strategy,
        initial_approval=st.booleans(),
        new_approval=st.booleans()
    )
    def test_approval_requirement_can_be_modified(
        self, 
        integration: str, 
        action_type: str,
        initial_approval: bool,
        new_approval: bool
    ):
        """
        Feature: neurotwin-platform, Property 37: Permission modifiability
        
        For any permission scope, the requires_approval status can be modified.
        """
        service = PermissionService()
        
        # Create test user
        user = create_test_user(f"p37_approval_{integration}_{action_type}_{initial_approval}_{new_approval}_{hash((integration, action_type, initial_approval, new_approval)) % 10000}")
        
        try:
            # Set initial permission
            initial_request = PermissionUpdateRequest(
                integration=integration,
                action_type=action_type,
                is_granted=True,
                requires_approval=initial_approval,
                reason="Initial setup"
            )
            service.update_permission(str(user.id), initial_request)
            
            # Verify initial state
            permission = service.get_permission(str(user.id), integration, action_type)
            assert permission.requires_approval == initial_approval, "Initial approval state should be set"
            
            # Modify permission
            modify_request = PermissionUpdateRequest(
                integration=integration,
                action_type=action_type,
                requires_approval=new_approval,
                reason="User modification"
            )
            service.update_permission(str(user.id), modify_request)
            
            # Verify modified state
            permission = service.get_permission(str(user.id), integration, action_type)
            assert permission.requires_approval == new_approval, (
                f"Approval requirement should be modified from {initial_approval} to {new_approval}"
            )
        finally:
            User.objects.filter(id=user.id).delete()
    
    @settings(deadline=None)
    @given(
        integration=integration_strategy,
        action_type=action_type_strategy
    )
    def test_permission_modification_creates_history(
        self, 
        integration: str, 
        action_type: str
    ):
        """
        Feature: neurotwin-platform, Property 37: Permission modifiability
        
        For any permission modification, a history entry should be created.
        """
        service = PermissionService()
        
        # Create test user
        user = create_test_user(f"p37_history_{integration}_{action_type}_{hash((integration, action_type)) % 10000}")
        
        try:
            # Set initial permission (denied)
            initial_request = PermissionUpdateRequest(
                integration=integration,
                action_type=action_type,
                is_granted=False,
                requires_approval=True,
                reason="Initial setup"
            )
            service.update_permission(str(user.id), initial_request)
            
            # Modify permission (grant)
            modify_request = PermissionUpdateRequest(
                integration=integration,
                action_type=action_type,
                is_granted=True,
                requires_approval=False,
                reason="User granted permission"
            )
            service.update_permission(str(user.id), modify_request)
            
            # Check history
            history = service.get_permission_history(str(user.id), integration, action_type)
            
            # Should have at least one history entry for the modification
            assert len(history) >= 1, "Should have history entry for modification"
            
            # Find the modification entry
            modification_entry = next(
                (h for h in history if h.previous_is_granted == False and h.new_is_granted == True),
                None
            )
            assert modification_entry is not None, "Should have history entry for grant modification"
            assert modification_entry.reason == "User granted permission", "Reason should be recorded"
        finally:
            User.objects.filter(id=user.id).delete()
