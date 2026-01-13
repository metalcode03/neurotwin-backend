"""
Property-based tests for authentication service.

Feature: neurotwin-platform
Validates: Requirements 1.1, 1.2, 1.3, 1.4, 1.6, 1.7

These tests use Hypothesis to verify authentication properties hold
across a wide range of inputs.
"""

import pytest
from datetime import timedelta
from hypothesis import given, strategies as st, settings, assume
from django.utils import timezone
from rest_framework_simplejwt.tokens import RefreshToken
from rest_framework_simplejwt.token_blacklist.models import OutstandingToken, BlacklistedToken

from apps.authentication.services import AuthService
from apps.authentication.models import User, VerificationToken


# Custom strategies for generating valid test data
email_strategy = st.emails()
password_strategy = st.text(
    alphabet=st.characters(whitelist_categories=('L', 'N', 'P', 'S')),
    min_size=8,
    max_size=64
).filter(lambda x: len(x.strip()) >= 8)

# Strategy for invalid passwords (too short)
invalid_password_strategy = st.text(max_size=7)


@pytest.fixture
def auth_service():
    """Provide an AuthService instance."""
    return AuthService()


@pytest.mark.django_db(transaction=True)
class TestRegistrationCreatesAccount:
    """
    Property 1: Registration creates account
    
    *For any* valid email and password combination, registration SHALL create
    a new user account and queue a verification email.
    
    **Validates: Requirements 1.1**
    """
    
    @settings(max_examples=10, deadline=None)
    @given(email=email_strategy, password=password_strategy)
    def test_registration_creates_account(self, email: str, password: str):
        """
        Feature: neurotwin-platform, Property 1: Registration creates account
        
        For any valid email and password, registration should:
        1. Create a new user account
        2. Generate a verification token
        3. Return success with user_id
        """
        # Ensure email is unique for this test
        email = f"test_{hash(email) % 10000000}_{email}"
        
        auth_service = AuthService()
        
        # Clean up any existing user with this email
        User.objects.filter(email=email.lower()).delete()
        
        result = auth_service.register(email, password)
        
        # Registration should succeed
        assert result.success is True, f"Registration failed: {result.error}"
        assert result.user_id is not None
        
        # User should exist in database
        user = User.objects.filter(id=result.user_id).first()
        assert user is not None
        assert user.email == email.lower()
        assert user.is_verified is False  # Not verified yet
        
        # Verification token should be created
        verification_token = VerificationToken.objects.filter(
            user=user,
            is_used=False
        ).first()
        assert verification_token is not None
        assert verification_token.is_valid is True
        
        # Cleanup
        User.objects.filter(id=result.user_id).delete()


@pytest.mark.django_db(transaction=True)
class TestVerificationActivatesAccount:
    """
    Property 2: Verification activates account
    
    *For any* valid verification token, clicking the verification link SHALL
    activate the associated account and enable login.
    
    **Validates: Requirements 1.2**
    """
    
    @settings(max_examples=10, deadline=None)
    @given(email=email_strategy, password=password_strategy)
    def test_verification_activates_account(self, email: str, password: str):
        """
        Feature: neurotwin-platform, Property 2: Verification activates account
        
        For any valid verification token, verifying should:
        1. Activate the account (is_verified = True)
        2. Mark the token as used
        3. Enable login
        """
        email = f"verify_{hash(email) % 10000000}_{email}"
        
        auth_service = AuthService()
        
        # Clean up any existing user
        User.objects.filter(email=email.lower()).delete()
        
        # Register user
        reg_result = auth_service.register(email, password)
        assert reg_result.success is True
        
        # Get the verification token
        user = User.objects.get(id=reg_result.user_id)
        verification_token = VerificationToken.objects.filter(
            user=user,
            is_used=False
        ).first()
        assert verification_token is not None
        
        # User should not be verified yet
        assert user.is_verified is False
        
        # Verify the email
        verify_result = auth_service.verify_email(str(verification_token.token))
        
        # Verification should succeed
        assert verify_result.success is True
        
        # User should now be verified
        user.refresh_from_db()
        assert user.is_verified is True
        
        # Token should be marked as used
        verification_token.refresh_from_db()
        assert verification_token.is_used is True
        
        # Login should now work
        login_result = auth_service.login(email, password)
        assert login_result.success is True
        
        # Cleanup
        User.objects.filter(id=reg_result.user_id).delete()
    
    @settings(max_examples=10, deadline=None)
    @given(email=email_strategy, password=password_strategy)
    def test_invalid_verification_token_fails(self, email: str, password: str):
        """
        Feature: neurotwin-platform, Property 2: Verification activates account
        
        For any invalid verification token, verification should fail.
        """
        import uuid
        
        auth_service = AuthService()
        
        # Try to verify with a random invalid token
        invalid_token = str(uuid.uuid4())
        verify_result = auth_service.verify_email(invalid_token)
        
        # Verification should fail
        assert verify_result.success is False
        assert verify_result.error is not None


@pytest.mark.django_db(transaction=True)
class TestValidCredentialsAuthenticate:
    """
    Property 3: Valid credentials authenticate
    
    *For any* user with valid credentials, login SHALL succeed and return
    a valid JWT session token (access and refresh tokens).
    
    **Validates: Requirements 1.3**
    """
    
    @settings(max_examples=10, deadline=None)
    @given(email=email_strategy, password=password_strategy)
    def test_valid_credentials_authenticate(self, email: str, password: str):
        """
        Feature: neurotwin-platform, Property 3: Valid credentials authenticate
        
        For any registered and verified user with valid credentials,
        login should succeed and return valid JWT access and refresh tokens.
        """
        # Ensure email is unique
        email = f"valid_{hash(email) % 10000000}_{email}"
        
        auth_service = AuthService()
        
        # Clean up any existing user
        User.objects.filter(email=email.lower()).delete()
        
        # Register user
        reg_result = auth_service.register(email, password)
        assert reg_result.success is True
        
        # Verify the user (simulate clicking verification link)
        user = User.objects.get(id=reg_result.user_id)
        user.is_verified = True
        user.save()
        
        # Login with valid credentials
        login_result = auth_service.login(email, password)
        
        # Login should succeed
        assert login_result.success is True, f"Login failed: {login_result.error}"
        assert login_result.token is not None  # Access token
        assert login_result.refresh_token is not None  # Refresh token
        assert login_result.user_id == reg_result.user_id
        
        # Access token should be valid
        validated_user_id = auth_service.validate_token(login_result.token)
        assert validated_user_id == reg_result.user_id
        
        # Refresh token should work
        refresh_result = auth_service.refresh_access_token(login_result.refresh_token)
        assert refresh_result.success is True
        assert refresh_result.token is not None
        
        # Cleanup
        User.objects.filter(id=reg_result.user_id).delete()


@pytest.mark.django_db(transaction=True)
class TestInvalidCredentialsReject:
    """
    Property 4: Invalid credentials reject
    
    *For any* invalid credential combination (wrong email, wrong password,
    or non-existent user), login SHALL fail and return an error message.
    
    **Validates: Requirements 1.4**
    """
    
    @settings(max_examples=10, deadline=None)
    @given(
        email=email_strategy, 
        correct_password=password_strategy,
        wrong_password=password_strategy
    )
    def test_wrong_password_rejects(
        self, 
        email: str, 
        correct_password: str, 
        wrong_password: str
    ):
        """
        Feature: neurotwin-platform, Property 4: Invalid credentials reject
        
        For any user, login with wrong password should fail.
        """
        # Ensure passwords are different
        assume(correct_password != wrong_password)
        
        email = f"wrong_pw_{hash(email) % 10000000}_{email}"
        
        auth_service = AuthService()
        
        # Clean up
        User.objects.filter(email=email.lower()).delete()
        
        # Register and verify user
        reg_result = auth_service.register(email, correct_password)
        assert reg_result.success is True
        
        user = User.objects.get(id=reg_result.user_id)
        user.is_verified = True
        user.save()
        
        # Try login with wrong password
        login_result = auth_service.login(email, wrong_password)
        
        # Login should fail
        assert login_result.success is False
        assert login_result.error is not None
        assert login_result.token is None
        
        # Cleanup
        User.objects.filter(id=reg_result.user_id).delete()
    
    @settings(max_examples=10, deadline=None)
    @given(email=email_strategy, password=password_strategy)
    def test_nonexistent_user_rejects(self, email: str, password: str):
        """
        Feature: neurotwin-platform, Property 4: Invalid credentials reject
        
        Login attempt for non-existent user should fail.
        """
        email = f"nonexistent_{hash(email) % 10000000}_{email}"
        
        auth_service = AuthService()
        
        # Ensure user doesn't exist
        User.objects.filter(email=email.lower()).delete()
        
        # Try login
        login_result = auth_service.login(email, password)
        
        # Login should fail
        assert login_result.success is False
        assert login_result.error is not None
        assert login_result.token is None


@pytest.mark.django_db(transaction=True)
class TestExpiredTokensRequireReauth:
    """
    Property 5: Expired tokens require re-authentication
    
    *For any* expired session token, authentication SHALL fail and require
    the user to re-authenticate.
    
    **Validates: Requirements 1.6**
    """
    
    @settings(max_examples=10, deadline=None)
    @given(email=email_strategy, password=password_strategy)
    def test_blacklisted_tokens_require_reauth(self, email: str, password: str):
        """
        Feature: neurotwin-platform, Property 5: Expired tokens require re-authentication
        
        For any blacklisted token, validation should fail.
        """
        email = f"blacklisted_{hash(email) % 10000000}_{email}"
        
        auth_service = AuthService()
        
        # Clean up
        User.objects.filter(email=email.lower()).delete()
        
        # Register and verify user
        reg_result = auth_service.register(email, password)
        assert reg_result.success is True
        
        user = User.objects.get(id=reg_result.user_id)
        user.is_verified = True
        user.save()
        
        # Login to get tokens
        login_result = auth_service.login(email, password)
        assert login_result.success is True
        
        # Logout (blacklist the refresh token)
        logout_success = auth_service.logout(login_result.refresh_token)
        assert logout_success is True
        
        # Refresh token should no longer work
        refresh_result = auth_service.refresh_access_token(login_result.refresh_token)
        assert refresh_result.success is False
        
        # Cleanup
        User.objects.filter(id=reg_result.user_id).delete()
    
    @settings(max_examples=10, deadline=None)
    @given(email=email_strategy, password=password_strategy)
    def test_logout_all_devices_invalidates_tokens(self, email: str, password: str):
        """
        Feature: neurotwin-platform, Property 5: Expired tokens require re-authentication
        
        Logging out from all devices should invalidate all tokens.
        """
        email = f"logout_all_{hash(email) % 10000000}_{email}"
        
        auth_service = AuthService()
        
        # Clean up
        User.objects.filter(email=email.lower()).delete()
        
        # Register and verify user
        reg_result = auth_service.register(email, password)
        assert reg_result.success is True
        
        user = User.objects.get(id=reg_result.user_id)
        user.is_verified = True
        user.save()
        
        # Login multiple times to simulate multiple devices
        login_result1 = auth_service.login(email, password)
        login_result2 = auth_service.login(email, password)
        assert login_result1.success is True
        assert login_result2.success is True
        
        # Logout from all devices
        blacklisted_count = auth_service.logout_all_devices(str(user.id))
        assert blacklisted_count >= 2
        
        # Both refresh tokens should no longer work
        refresh_result1 = auth_service.refresh_access_token(login_result1.refresh_token)
        refresh_result2 = auth_service.refresh_access_token(login_result2.refresh_token)
        assert refresh_result1.success is False
        assert refresh_result2.success is False
        
        # Cleanup
        User.objects.filter(id=reg_result.user_id).delete()


@pytest.mark.django_db(transaction=True)
class TestPasswordResetTokenValidity:
    """
    Property 6: Password reset token validity
    
    *For any* password reset request, the system SHALL generate a reset token
    that expires after exactly 24 hours.
    
    **Validates: Requirements 1.7**
    """
    
    @settings(max_examples=10, deadline=None)
    @given(email=email_strategy, password=password_strategy)
    def test_password_reset_creates_valid_token(self, email: str, password: str):
        """
        Feature: neurotwin-platform, Property 6: Password reset token validity
        
        For any password reset request, a valid token should be created
        that expires after 24 hours.
        """
        from apps.authentication.models import PasswordResetToken
        
        email = f"reset_{hash(email) % 10000000}_{email}"
        
        auth_service = AuthService()
        
        # Clean up
        User.objects.filter(email=email.lower()).delete()
        
        # Register and verify user
        reg_result = auth_service.register(email, password)
        assert reg_result.success is True
        
        user = User.objects.get(id=reg_result.user_id)
        user.is_verified = True
        user.save()
        
        # Request password reset
        reset_requested = auth_service.request_password_reset(email)
        assert reset_requested is True
        
        # Token should exist
        reset_token = PasswordResetToken.objects.filter(
            user=user,
            is_used=False
        ).first()
        assert reset_token is not None
        
        # Token should expire in approximately 24 hours
        expected_expiry = timezone.now() + timedelta(hours=24)
        time_diff = abs((reset_token.expires_at - expected_expiry).total_seconds())
        assert time_diff < 60  # Within 1 minute tolerance
        
        # Token should be valid
        assert reset_token.is_valid is True
        
        # Cleanup
        User.objects.filter(id=reg_result.user_id).delete()
    
    @settings(max_examples=10, deadline=None)
    @given(
        email=email_strategy, 
        old_password=password_strategy,
        new_password=password_strategy
    )
    def test_password_reset_with_valid_token(
        self, 
        email: str, 
        old_password: str, 
        new_password: str
    ):
        """
        Feature: neurotwin-platform, Property 6: Password reset token validity
        
        For any valid reset token, password reset should succeed.
        """
        from apps.authentication.models import PasswordResetToken
        
        assume(old_password != new_password)
        
        email = f"reset_valid_{hash(email) % 10000000}_{email}"
        
        auth_service = AuthService()
        
        # Clean up
        User.objects.filter(email=email.lower()).delete()
        
        # Register and verify user
        reg_result = auth_service.register(email, old_password)
        assert reg_result.success is True
        
        user = User.objects.get(id=reg_result.user_id)
        user.is_verified = True
        user.save()
        
        # Request password reset
        auth_service.request_password_reset(email)
        
        # Get the reset token
        reset_token = PasswordResetToken.objects.filter(
            user=user,
            is_used=False
        ).first()
        assert reset_token is not None
        
        # Reset password
        reset_result = auth_service.reset_password(str(reset_token.token), new_password)
        assert reset_result.success is True
        
        # Token should be marked as used
        reset_token.refresh_from_db()
        assert reset_token.is_used is True
        
        # Old password should no longer work
        old_login = auth_service.login(email, old_password)
        assert old_login.success is False
        
        # New password should work
        new_login = auth_service.login(email, new_password)
        assert new_login.success is True
        
        # Cleanup
        User.objects.filter(id=reg_result.user_id).delete()
