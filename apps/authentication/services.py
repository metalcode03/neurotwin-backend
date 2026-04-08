"""
Authentication service for NeuroTwin platform.

Handles user registration, verification, login, and token management.
Uses djangorestframework-simplejwt for JWT token management with access/refresh tokens.
Requirements: 1.1, 1.2, 1.3, 1.4, 1.6, 1.7
"""

import secrets
import re
from datetime import timedelta
from typing import Optional, Tuple

from django.conf import settings
from django.db import transaction
from django.utils import timezone
from django.core.validators import validate_email
from django.core.exceptions import ValidationError
from rest_framework_simplejwt.tokens import RefreshToken, AccessToken
from rest_framework_simplejwt.token_blacklist.models import OutstandingToken, BlacklistedToken
from rest_framework_simplejwt.exceptions import TokenError

from .models import User, VerificationToken, PasswordResetToken
from .dataclasses import AuthResult, TokenPair


class AuthService:
    """
    Handles authentication operations.
    
    Uses djangorestframework-simplejwt for JWT token management with
    access and refresh tokens, including token blacklisting.
    """
    
    # Email validation regex pattern
    EMAIL_PATTERN = re.compile(r'^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$')
    
    # Minimum password requirements
    MIN_PASSWORD_LENGTH = 8
    
    def __init__(self):
        """Initialize the auth service with configuration from settings."""
        self.verification_token_lifetime = timedelta(
            hours=getattr(settings, 'EMAIL_VERIFICATION_TOKEN_LIFETIME_HOURS', 24)
        )
        self.password_reset_lifetime = timedelta(hours=24)  # Fixed at 24 hours per Req 1.7
    
    def _validate_email(self, email: str) -> Tuple[bool, Optional[str]]:
        """
        Validate email format.
        
        Returns:
            Tuple of (is_valid, error_message)
        """
        if not email:
            return False, "Email is required"
        
        email = email.strip().lower()
        
        try:
            validate_email(email)
        except ValidationError:
            return False, "Invalid email format"
        
        return True, None
    
    def _validate_password(self, password: str) -> Tuple[bool, Optional[str]]:
        """
        Validate password meets requirements.
        
        Returns:
            Tuple of (is_valid, error_message)
        """
        if not password:
            return False, "Password is required"
        
        if len(password) < self.MIN_PASSWORD_LENGTH:
            return False, f"Password must be at least {self.MIN_PASSWORD_LENGTH} characters"
        
        return True, None
    
    def _generate_token(self, length: int = 32) -> str:
        """Generate a secure random token."""
        return secrets.token_hex(length)
    
    def _create_tokens_for_user(self, user: User) -> TokenPair:
        """
        Create access and refresh tokens for a user using SimpleJWT.
        
        Args:
            user: The user to create tokens for
            
        Returns:
            TokenPair with access and refresh tokens
        """
        refresh = RefreshToken.for_user(user)
        return TokenPair(
            access_token=str(refresh.access_token),
            refresh_token=str(refresh)
        )
    
    @transaction.atomic
    def register(self, email: str, password: str) -> AuthResult:
        """
        Create new account and generate verification token.
        
        Requirements: 1.1
        
        Args:
            email: User's email address
            password: User's password
            
        Returns:
            AuthResult with success status and user_id or error
        """
        # Validate email
        email_valid, email_error = self._validate_email(email)
        if not email_valid:
            return AuthResult.failure_result(email_error)
        
        email = email.strip().lower()
        
        # Validate password
        password_valid, password_error = self._validate_password(password)
        if not password_valid:
            return AuthResult.failure_result(password_error)
        
        # Check if user already exists
        if User.objects.filter(email=email).exists():
            return AuthResult.failure_result("An account with this email already exists")
        
        # Create user
        user = User.objects.create_user(email=email, password=password)
        
        # Create verification token
        self._create_verification_token(user)
        
        # Generate JWT tokens for instant login upon registration
        tokens = self._create_tokens_for_user(user)
        
        # Update last login timestamp
        user.last_login = timezone.now()
        user.save(update_fields=['last_login'])
        
        return AuthResult.success_result(
            user_id=str(user.id),
            token=tokens.access_token,
            refresh_token=tokens.refresh_token
        )
    
    def _create_verification_token(self, user: User) -> VerificationToken:
        """
        Create a verification token for email verification.
        
        The token is queued for async email sending.
        """
        # Invalidate any existing tokens
        VerificationToken.objects.filter(user=user, is_used=False).update(is_used=True)
        
        token = self._generate_token()
        expires_at = timezone.now() + self.verification_token_lifetime
        
        verification_token = VerificationToken.objects.create(
            user=user,
            token=token,
            expires_at=expires_at
        )
        
        # TODO: Queue async email sending task
        # For now, the token is created and can be retrieved for testing
        
        return verification_token
    
    def get_verification_token(self, user_id: str) -> Optional[str]:
        """
        Get the latest verification token for a user.
        
        This is primarily for testing purposes.
        """
        token = VerificationToken.objects.filter(
            user_id=user_id,
            is_used=False
        ).order_by('-created_at').first()
        
        return token.token if token else None
    
    @transaction.atomic
    def verify_email(self, token: str) -> AuthResult:
        """
        Activate account via verification link.
        
        Requirements: 1.2
        
        Args:
            token: The verification token from the email link
            
        Returns:
            AuthResult with success status
        """
        if not token:
            return AuthResult.failure_result("Verification token is required")
        
        verification = VerificationToken.objects.filter(token=token).first()
        
        if not verification:
            return AuthResult.failure_result("Invalid verification token")
        
        if verification.is_used:
            return AuthResult.failure_result("Verification token has already been used")
        
        if verification.is_expired:
            return AuthResult.failure_result("Verification token has expired")
        
        # Mark token as used
        verification.is_used = True
        verification.save()
        
        # Activate user account
        user = verification.user
        user.is_verified = True
        user.save()
        
        return AuthResult.success_result(user_id=str(user.id))
    
    @transaction.atomic
    def login(
        self, 
        email: str, 
        password: str,
    ) -> AuthResult:
        """
        Authenticate user and return JWT access and refresh tokens.
        
        Requirements: 1.3, 1.4
        
        Args:
            email: User's email address
            password: User's password
            
        Returns:
            AuthResult with tokens on success, error on failure
        """
        # Validate email format
        email_valid, email_error = self._validate_email(email)
        if not email_valid:
            return AuthResult.failure_result("Invalid credentials")
        
        email = email.strip().lower()
        
        # Find user
        user = User.objects.filter(email=email).first()
        
        if not user:
            return AuthResult.failure_result("Invalid credentials")
        
        # Check password
        if not user.check_password(password):
            return AuthResult.failure_result("Invalid credentials")
        
        # Check if account is active
        if not user.is_active:
            return AuthResult.failure_result("Account is disabled")
        
        # Check if email is verified
        if not user.is_verified:
            return AuthResult.failure_result("Email not verified. Please check your email for verification link.")
        
        # Generate JWT tokens using SimpleJWT
        tokens = self._create_tokens_for_user(user)
        
        # Update last login
        user.last_login = timezone.now()
        user.save(update_fields=['last_login'])
        
        return AuthResult.success_result(
            user_id=str(user.id), 
            token=tokens.access_token,
            refresh_token=tokens.refresh_token
        )
    
    def validate_token(self, token: str) -> Optional[str]:
        """
        Validate JWT access token and return user_id if valid.
        
        Requirements: 1.6
        
        Args:
            token: JWT access token to validate
            
        Returns:
            User ID if token is valid, None otherwise
        """
        if not token:
            return None
        
        try:
            # Use SimpleJWT to validate the access token
            access_token = AccessToken(token)
            user_id = access_token.get('user_id')
            
            if not user_id:
                return None
            
            # Verify user exists and is active
            user = User.objects.filter(id=user_id, is_active=True).first()
            if not user:
                return None
            
            return str(user_id)
            
        except TokenError:
            return None
    
    def refresh_access_token(self, refresh_token: str) -> AuthResult:
        """
        Refresh the access token using a valid refresh token.
        
        Requirements: 1.6
        
        Args:
            refresh_token: The refresh token
            
        Returns:
            AuthResult with new tokens on success
        """
        if not refresh_token:
            return AuthResult.failure_result("Refresh token is required")
        
        try:
            # Use SimpleJWT to refresh the token
            refresh = RefreshToken(refresh_token)
            
            # Get user_id from the refresh token
            user_id = refresh.get('user_id')
            
            # Verify user exists and is active
            user = User.objects.filter(id=user_id, is_active=True).first()
            if not user:
                return AuthResult.failure_result("User not found or inactive")
            
            # Create new access token (and optionally rotate refresh token)
            new_access = str(refresh.access_token)
            
            # If ROTATE_REFRESH_TOKENS is True, blacklist old and create new
            if settings.SIMPLE_JWT.get('ROTATE_REFRESH_TOKENS', False):
                # Blacklist the old refresh token
                refresh.blacklist()
                # Create new refresh token
                new_refresh = RefreshToken.for_user(user)
                return AuthResult.success_result(
                    user_id=str(user_id),
                    token=str(new_refresh.access_token),
                    refresh_token=str(new_refresh)
                )
            
            return AuthResult.success_result(
                user_id=str(user_id),
                token=new_access,
                refresh_token=refresh_token
            )
            
        except TokenError as e:
            return AuthResult.failure_result(f"Invalid or expired refresh token: {str(e)}")
    
    @transaction.atomic
    def request_password_reset(self, email: str) -> bool:
        """
        Send password reset link valid for 24 hours.
        
        Requirements: 1.7
        
        Args:
            email: User's email address
            
        Returns:
            True if reset email was queued (always returns True for security)
        """
        email_valid, _ = self._validate_email(email)
        if not email_valid:
            # Return True to prevent email enumeration
            return True
        
        email = email.strip().lower()
        user = User.objects.filter(email=email).first()
        
        if not user:
            # Return True to prevent email enumeration
            return True
        
        # Invalidate existing reset tokens
        PasswordResetToken.objects.filter(user=user, is_used=False).update(is_used=True)
        
        # Create new reset token
        token = self._generate_token()
        expires_at = timezone.now() + self.password_reset_lifetime
        
        PasswordResetToken.objects.create(
            user=user,
            token=token,
            expires_at=expires_at
        )
        
        # TODO: Queue async email sending task
        
        return True
    
    def get_password_reset_token(self, user_id: str) -> Optional[str]:
        """
        Get the latest password reset token for a user.
        
        This is primarily for testing purposes.
        """
        token = PasswordResetToken.objects.filter(
            user_id=user_id,
            is_used=False
        ).order_by('-created_at').first()
        
        return token.token if token else None
    
    @transaction.atomic
    def reset_password(self, token: str, new_password: str) -> AuthResult:
        """
        Reset password using valid reset token.
        
        Requirements: 1.7
        
        Args:
            token: Password reset token
            new_password: New password to set
            
        Returns:
            AuthResult with success status
        """
        if not token:
            return AuthResult.failure_result("Reset token is required")
        
        # Validate new password
        password_valid, password_error = self._validate_password(new_password)
        if not password_valid:
            return AuthResult.failure_result(password_error)
        
        reset_token = PasswordResetToken.objects.filter(token=token).first()
        
        if not reset_token:
            return AuthResult.failure_result("Invalid reset token")
        
        if reset_token.is_used:
            return AuthResult.failure_result("Reset token has already been used")
        
        if reset_token.is_expired:
            return AuthResult.failure_result("Reset token has expired")
        
        # Mark token as used
        reset_token.is_used = True
        reset_token.save()
        
        # Update password
        user = reset_token.user
        user.set_password(new_password)
        user.save()
        
        # Blacklist all outstanding tokens for this user (security measure)
        self._blacklist_all_user_tokens(user)
        
        return AuthResult.success_result(user_id=str(user.id))
    
    def _blacklist_all_user_tokens(self, user: User) -> int:
        """
        Blacklist all outstanding tokens for a user.
        
        Used when password is reset or user is logged out from all devices.
        
        Args:
            user: The user whose tokens should be blacklisted
            
        Returns:
            Number of tokens blacklisted
        """
        count = 0
        outstanding_tokens = OutstandingToken.objects.filter(user=user)
        
        for outstanding in outstanding_tokens:
            # Check if not already blacklisted
            if not BlacklistedToken.objects.filter(token=outstanding).exists():
                BlacklistedToken.objects.create(token=outstanding)
                count += 1
        
        return count
    
    def oauth_callback(self, provider: str, code: str) -> AuthResult:
        """
        Handle OAuth callback and create/link account.
        
        Requirements: 1.5
        
        Args:
            provider: OAuth provider name (e.g., 'google')
            code: OAuth authorization code
            
        Returns:
            AuthResult with token on success
        """
        # TODO: Implement OAuth flow with actual provider APIs
        # This is a placeholder for the OAuth implementation
        return AuthResult.failure_result("OAuth not yet implemented")
    
    @transaction.atomic
    def logout(self, refresh_token: str) -> bool:
        """
        Logout by blacklisting the refresh token.
        
        Args:
            refresh_token: The refresh token to blacklist
            
        Returns:
            True if token was blacklisted successfully
        """
        if not refresh_token:
            return False
        
        try:
            token = RefreshToken(refresh_token)
            token.blacklist()
            return True
        except TokenError:
            return False
    
    @transaction.atomic
    def logout_all_devices(self, user_id: str) -> int:
        """
        Logout user from all devices by blacklisting all their tokens.
        
        Args:
            user_id: The user's ID
            
        Returns:
            Number of tokens blacklisted
        """
        user = User.objects.filter(id=user_id).first()
        if not user:
            return 0
        
        return self._blacklist_all_user_tokens(user)
    
    def cleanup_expired_tokens(self) -> Tuple[int, int]:
        """
        Remove expired verification and reset tokens.
        
        Returns:
            Tuple of (verification_tokens_deleted, reset_tokens_deleted)
        """
        now = timezone.now()
        
        verification_deleted, _ = VerificationToken.objects.filter(
            expires_at__lt=now
        ).delete()
        
        reset_deleted, _ = PasswordResetToken.objects.filter(
            expires_at__lt=now
        ).delete()
        
        return verification_deleted, reset_deleted
