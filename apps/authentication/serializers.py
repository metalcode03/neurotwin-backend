"""
Authentication API serializers.

Requirements: 1.1-1.7, 13.2
"""

from rest_framework import serializers


class RegisterSerializer(serializers.Serializer):
    """Serializer for user registration."""
    
    email = serializers.EmailField(
        required=True,
        help_text="User's email address"
    )
    password = serializers.CharField(
        required=True,
        min_length=8,
        write_only=True,
        help_text="Password (minimum 8 characters)"
    )


class VerifyEmailSerializer(serializers.Serializer):
    """Serializer for email verification."""
    
    token = serializers.CharField(
        required=True,
        help_text="Verification token from email"
    )


class LoginSerializer(serializers.Serializer):
    """Serializer for user login."""
    
    email = serializers.EmailField(
        required=True,
        help_text="User's email address"
    )
    password = serializers.CharField(
        required=True,
        write_only=True,
        help_text="User's password"
    )


class TokenResponseSerializer(serializers.Serializer):
    """Serializer for token response."""
    
    user_id = serializers.UUIDField(read_only=True)
    access_token = serializers.CharField(read_only=True)
    refresh_token = serializers.CharField(read_only=True)


class RefreshTokenSerializer(serializers.Serializer):
    """Serializer for token refresh."""
    
    refresh_token = serializers.CharField(
        required=True,
        help_text="Refresh token"
    )


class PasswordResetRequestSerializer(serializers.Serializer):
    """Serializer for password reset request."""
    
    email = serializers.EmailField(
        required=True,
        help_text="User's email address"
    )


class PasswordResetSerializer(serializers.Serializer):
    """Serializer for password reset."""
    
    token = serializers.CharField(
        required=True,
        help_text="Password reset token"
    )
    new_password = serializers.CharField(
        required=True,
        min_length=8,
        write_only=True,
        help_text="New password (minimum 8 characters)"
    )


class OAuthCallbackSerializer(serializers.Serializer):
    """Serializer for OAuth callback."""
    
    code = serializers.CharField(
        required=True,
        help_text="OAuth authorization code"
    )
    state = serializers.CharField(
        required=False,
        help_text="OAuth state parameter"
    )


class LogoutSerializer(serializers.Serializer):
    """Serializer for logout."""
    
    refresh_token = serializers.CharField(
        required=True,
        help_text="Refresh token to invalidate"
    )
