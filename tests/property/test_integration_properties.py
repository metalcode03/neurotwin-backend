"""
Property-based tests for integration service.

Feature: neurotwin-platform
Validates: Requirements 7.2-7.5

These tests use Hypothesis to verify integration properties hold
across a wide range of inputs.
"""

import pytest
from hypothesis import given, strategies as st, settings, assume
from django.utils import timezone
from datetime import timedelta

from apps.automation.services import IntegrationService
from apps.automation.models import Integration, IntegrationType
from apps.automation.dataclasses import (
    ConnectIntegrationRequest,
    UpdatePermissionsRequest,
    UpdateSteeringRulesRequest,
)
from apps.authentication.models import User


# Custom strategies for generating test data
integration_type_strategy = st.sampled_from([
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
])

# Strategy for generating OAuth codes
oauth_code_strategy = st.text(
    alphabet=st.characters(whitelist_categories=('L', 'N')),
    min_size=10,
    max_size=50
).filter(lambda x: len(x.strip()) >= 10)

# Strategy for generating permission names
permission_name_strategy = st.sampled_from([
    'read', 'write', 'send', 'delete', 'admin', 'manage'
])

# Strategy for generating steering rule names
steering_rule_name_strategy = st.sampled_from([
    'max_messages_per_day', 'allowed_recipients', 'blocked_keywords',
    'auto_reply_enabled', 'notification_settings'
])


@pytest.fixture
def integration_service():
    """Provide an IntegrationService instance."""
    return IntegrationService()


def create_test_user(email_suffix: str) -> User:
    """Create a test user with unique email."""
    email = f"integration_test_{email_suffix}@example.com"
    User.objects.filter(email=email).delete()
    return User.objects.create_user(email=email, password="testpass123")


@pytest.mark.django_db(transaction=True)
class TestMinimalOAuthScopes:
    """
    Property 27: Minimal OAuth scopes
    
    *For any* integration connection, the system SHALL request only the
    minimum necessary OAuth scopes.
    
    **Validates: Requirements 7.2**
    """
    
    @settings(max_examples=20, deadline=None)
    @given(
        integration_type=integration_type_strategy,
        oauth_code=oauth_code_strategy
    )
    def test_connect_uses_minimal_scopes_by_default(
        self,
        integration_type: str,
        oauth_code: str
    ):
        """
        Feature: neurotwin-platform, Property 27: Minimal OAuth scopes
        
        For any integration connection without explicit scope request,
        only minimal required scopes should be used.
        """
        service = IntegrationService()
        
        # Create test user
        user = create_test_user(f"p27_{integration_type}_{hash(oauth_code) % 10000}")
        
        try:
            # Connect without specifying scopes
            request = ConnectIntegrationRequest(
                integration_type=integration_type,
                oauth_code=oauth_code,
                requested_scopes=None  # Don't specify scopes
            )
            
            integration = service.connect_integration(str(user.id), request)
            
            # Get minimal scopes for this integration type
            minimal_scopes = service.get_minimal_scopes(integration_type)
            
            # Verify only minimal scopes were used
            assert set(integration.scopes) == set(minimal_scopes), (
                f"Integration should use minimal scopes {minimal_scopes}, "
                f"but got {integration.scopes}"
            )
        finally:
            User.objects.filter(id=user.id).delete()

    @settings(max_examples=20, deadline=None)
    @given(integration_type=integration_type_strategy)
    def test_minimal_scopes_are_subset_of_all_scopes(
        self,
        integration_type: str
    ):
        """
        Feature: neurotwin-platform, Property 27: Minimal OAuth scopes
        
        For any integration type, minimal scopes should be a subset of
        all available scopes.
        """
        service = IntegrationService()
        
        minimal_scopes = set(service.get_minimal_scopes(integration_type))
        all_scopes = set(service.get_all_available_scopes(integration_type))
        
        # Minimal scopes should be subset of all available scopes
        assert minimal_scopes.issubset(all_scopes), (
            f"Minimal scopes {minimal_scopes} should be subset of "
            f"all scopes {all_scopes} for {integration_type}"
        )
    
    @settings(max_examples=20, deadline=None)
    @given(
        integration_type=integration_type_strategy,
        oauth_code=oauth_code_strategy
    )
    def test_requested_scopes_filtered_to_available(
        self,
        integration_type: str,
        oauth_code: str
    ):
        """
        Feature: neurotwin-platform, Property 27: Minimal OAuth scopes
        
        For any integration connection with explicit scope request,
        only valid scopes should be used.
        """
        service = IntegrationService()
        
        # Create test user
        user = create_test_user(f"p27_filter_{integration_type}_{hash(oauth_code) % 10000}")
        
        try:
            # Get available scopes
            available_scopes = service.get_all_available_scopes(integration_type)
            
            # Request with some invalid scopes
            requested_scopes = available_scopes + ['invalid_scope_xyz', 'another_invalid']
            
            request = ConnectIntegrationRequest(
                integration_type=integration_type,
                oauth_code=oauth_code,
                requested_scopes=requested_scopes
            )
            
            integration = service.connect_integration(str(user.id), request)
            
            # If there are available scopes, verify invalid ones were filtered
            if available_scopes:
                for scope in integration.scopes:
                    assert scope in available_scopes, (
                        f"Scope {scope} should be in available scopes {available_scopes}"
                    )
        finally:
            User.objects.filter(id=user.id).delete()


@pytest.mark.django_db(transaction=True)
class TestIntegrationConfigurability:
    """
    Property 28: Integration configurability
    
    *For any* connected integration, the user SHALL be able to configure
    steering rules and modify permissions.
    
    **Validates: Requirements 7.3, 7.4**
    """
    
    @settings(max_examples=20, deadline=None)
    @given(
        integration_type=integration_type_strategy,
        oauth_code=oauth_code_strategy,
        permission_name=permission_name_strategy,
        permission_value=st.booleans()
    )
    def test_permissions_can_be_modified(
        self,
        integration_type: str,
        oauth_code: str,
        permission_name: str,
        permission_value: bool
    ):
        """
        Feature: neurotwin-platform, Property 28: Integration configurability
        
        For any connected integration, permissions can be modified.
        """
        service = IntegrationService()
        
        # Create test user
        user = create_test_user(f"p28_perm_{integration_type}_{hash((oauth_code, permission_name)) % 10000}")
        
        try:
            # Connect integration
            connect_request = ConnectIntegrationRequest(
                integration_type=integration_type,
                oauth_code=oauth_code
            )
            integration = service.connect_integration(str(user.id), connect_request)
            
            # Update permissions
            update_request = UpdatePermissionsRequest(
                permissions={permission_name: permission_value}
            )
            updated = service.update_permissions(str(integration.id), update_request)
            
            # Verify permission was updated
            assert updated.permissions.get(permission_name) == permission_value, (
                f"Permission {permission_name} should be {permission_value}, "
                f"but got {updated.permissions.get(permission_name)}"
            )
        finally:
            User.objects.filter(id=user.id).delete()
    
    @settings(max_examples=20, deadline=None)
    @given(
        integration_type=integration_type_strategy,
        oauth_code=oauth_code_strategy,
        rule_name=steering_rule_name_strategy,
        rule_value=st.one_of(
            st.integers(min_value=0, max_value=1000),
            st.booleans(),
            st.lists(st.text(min_size=1, max_size=20), max_size=5)
        )
    )
    def test_steering_rules_can_be_configured(
        self,
        integration_type: str,
        oauth_code: str,
        rule_name: str,
        rule_value
    ):
        """
        Feature: neurotwin-platform, Property 28: Integration configurability
        
        For any connected integration, steering rules can be configured.
        """
        service = IntegrationService()
        
        # Create test user
        user = create_test_user(f"p28_steer_{integration_type}_{hash((oauth_code, rule_name)) % 10000}")
        
        try:
            # Connect integration
            connect_request = ConnectIntegrationRequest(
                integration_type=integration_type,
                oauth_code=oauth_code
            )
            integration = service.connect_integration(str(user.id), connect_request)
            
            # Update steering rules
            update_request = UpdateSteeringRulesRequest(
                steering_rules={rule_name: rule_value}
            )
            updated = service.update_steering_rules(str(integration.id), update_request)
            
            # Verify steering rule was updated
            assert updated.steering_rules.get(rule_name) == rule_value, (
                f"Steering rule {rule_name} should be {rule_value}, "
                f"but got {updated.steering_rules.get(rule_name)}"
            )
        finally:
            User.objects.filter(id=user.id).delete()

    @settings(max_examples=20, deadline=None)
    @given(
        integration_type=integration_type_strategy,
        oauth_code=oauth_code_strategy,
        permissions=st.dictionaries(
            keys=permission_name_strategy,
            values=st.booleans(),
            min_size=1,
            max_size=5
        )
    )
    def test_multiple_permissions_can_be_updated_at_once(
        self,
        integration_type: str,
        oauth_code: str,
        permissions: dict
    ):
        """
        Feature: neurotwin-platform, Property 28: Integration configurability
        
        For any connected integration, multiple permissions can be updated
        in a single operation.
        """
        service = IntegrationService()
        
        # Create test user
        user = create_test_user(f"p28_multi_{integration_type}_{hash(oauth_code) % 10000}")
        
        try:
            # Connect integration
            connect_request = ConnectIntegrationRequest(
                integration_type=integration_type,
                oauth_code=oauth_code
            )
            integration = service.connect_integration(str(user.id), connect_request)
            
            # Update multiple permissions
            update_request = UpdatePermissionsRequest(permissions=permissions)
            updated = service.update_permissions(str(integration.id), update_request)
            
            # Verify all permissions were updated
            for perm_name, perm_value in permissions.items():
                assert updated.permissions.get(perm_name) == perm_value, (
                    f"Permission {perm_name} should be {perm_value}"
                )
        finally:
            User.objects.filter(id=user.id).delete()


@pytest.mark.django_db(transaction=True)
class TestTokenRefreshHandling:
    """
    Property 29: Token refresh handling
    
    *For any* expired integration token, the system SHALL attempt refresh
    or notify the user to reconnect.
    
    **Validates: Requirements 7.5**
    """
    
    @settings(max_examples=20, deadline=None)
    @given(
        integration_type=integration_type_strategy,
        oauth_code=oauth_code_strategy
    )
    def test_expired_token_triggers_refresh_attempt(
        self,
        integration_type: str,
        oauth_code: str
    ):
        """
        Feature: neurotwin-platform, Property 29: Token refresh handling
        
        For any integration with expired token and refresh token available,
        refresh should be attempted.
        """
        service = IntegrationService()
        
        # Create test user
        user = create_test_user(f"p29_refresh_{integration_type}_{hash(oauth_code) % 10000}")
        
        try:
            # Connect integration
            connect_request = ConnectIntegrationRequest(
                integration_type=integration_type,
                oauth_code=oauth_code
            )
            integration = service.connect_integration(str(user.id), connect_request)
            
            # Manually expire the token
            integration.token_expires_at = timezone.now() - timedelta(hours=1)
            integration.save()
            
            # Verify token is expired
            assert integration.is_token_expired, "Token should be expired"
            
            # Attempt refresh
            result = service.refresh_token(str(integration.id))
            
            # With a refresh token available, refresh should succeed
            # (in our simulated implementation)
            if integration.has_refresh_token:
                assert result.success, (
                    f"Token refresh should succeed when refresh token is available, "
                    f"but got error: {result.error}"
                )
                assert result.new_expires_at is not None, (
                    "New expiration time should be set after successful refresh"
                )
        finally:
            User.objects.filter(id=user.id).delete()
    
    @settings(max_examples=20, deadline=None)
    @given(
        integration_type=integration_type_strategy,
        oauth_code=oauth_code_strategy
    )
    def test_refresh_without_refresh_token_indicates_reconnect(
        self,
        integration_type: str,
        oauth_code: str
    ):
        """
        Feature: neurotwin-platform, Property 29: Token refresh handling
        
        For any integration without refresh token, refresh should fail
        and indicate user needs to reconnect.
        """
        service = IntegrationService()
        
        # Create test user
        user = create_test_user(f"p29_no_refresh_{integration_type}_{hash(oauth_code) % 10000}")
        
        try:
            # Connect integration
            connect_request = ConnectIntegrationRequest(
                integration_type=integration_type,
                oauth_code=oauth_code
            )
            integration = service.connect_integration(str(user.id), connect_request)
            
            # Remove refresh token
            integration.refresh_token_encrypted = None
            integration.token_expires_at = timezone.now() - timedelta(hours=1)
            integration.save()
            
            # Attempt refresh
            result = service.refresh_token(str(integration.id))
            
            # Without refresh token, should fail and indicate reconnect needed
            assert not result.success, "Refresh should fail without refresh token"
            assert result.needs_reconnect, (
                "Should indicate user needs to reconnect when no refresh token"
            )
        finally:
            User.objects.filter(id=user.id).delete()
    
    @settings(max_examples=20, deadline=None)
    @given(
        integration_type=integration_type_strategy,
        oauth_code=oauth_code_strategy
    )
    def test_successful_refresh_updates_expiration(
        self,
        integration_type: str,
        oauth_code: str
    ):
        """
        Feature: neurotwin-platform, Property 29: Token refresh handling
        
        For any successful token refresh, the expiration time should be
        updated to a future time.
        """
        service = IntegrationService()
        
        # Create test user
        user = create_test_user(f"p29_expiry_{integration_type}_{hash(oauth_code) % 10000}")
        
        try:
            # Connect integration
            connect_request = ConnectIntegrationRequest(
                integration_type=integration_type,
                oauth_code=oauth_code
            )
            integration = service.connect_integration(str(user.id), connect_request)
            
            # Expire the token
            old_expiry = timezone.now() - timedelta(hours=1)
            integration.token_expires_at = old_expiry
            integration.save()
            
            # Refresh
            result = service.refresh_token(str(integration.id))
            
            if result.success:
                # Reload integration
                integration.refresh_from_db()
                
                # New expiration should be in the future
                assert integration.token_expires_at > timezone.now(), (
                    "After successful refresh, token should not be expired"
                )
                assert not integration.is_token_expired, (
                    "is_token_expired should return False after refresh"
                )
        finally:
            User.objects.filter(id=user.id).delete()
    
    @settings(max_examples=20, deadline=None)
    @given(integration_type=integration_type_strategy)
    def test_refresh_nonexistent_integration_fails_gracefully(
        self,
        integration_type: str
    ):
        """
        Feature: neurotwin-platform, Property 29: Token refresh handling
        
        For any non-existent integration ID, refresh should fail gracefully.
        """
        service = IntegrationService()
        
        # Use a random UUID that doesn't exist
        import uuid
        fake_id = str(uuid.uuid4())
        
        result = service.refresh_token(fake_id)
        
        assert not result.success, "Refresh should fail for non-existent integration"
        assert result.error is not None, "Error message should be provided"
