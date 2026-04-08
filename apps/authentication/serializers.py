"""
Authentication API serializers.

Requirements: 1.1-1.7, 13.2
"""

from rest_framework import serializers
from .user_settings_models import BrainMode


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



class UserSettingsSerializer(serializers.Serializer):
    """
    Serializer for user settings.
    
    Requirements: 15.7
    """
    
    brain_mode = serializers.ChoiceField(
        choices=BrainMode.choices,
        default=BrainMode.BRAIN,
        help_text='Preferred Brain mode for AI requests'
    )
    cognitive_blend = serializers.IntegerField(
        read_only=True,
        help_text='Cognitive blend value from Twin (0-100)'
    )
    notification_preferences = serializers.JSONField(
        default=dict,
        help_text='User notification preferences'
    )
    subscription_tier = serializers.CharField(
        read_only=True,
        help_text='User subscription tier'
    )


class UpdateUserSettingsSerializer(serializers.Serializer):
    """
    Serializer for updating user settings.
    
    Requirements: 15.8, 15.9, 15.10
    """
    
    brain_mode = serializers.ChoiceField(
        choices=BrainMode.choices,
        required=True,
        help_text='Preferred Brain mode for AI requests'
    )
    
    def validate_brain_mode(self, value):
        """
        Validate brain_mode against user's subscription tier.
        
        Requirements: 5.6, 5.7, 5.10
        """
        from apps.subscription.models import SubscriptionTier
        
        # Get user from context
        user = self.context.get('user')
        if not user:
            raise serializers.ValidationError('User context is required')
        
        # Get user's subscription tier
        try:
            subscription = user.subscription
            tier = subscription.tier
        except AttributeError:
            # No subscription, default to FREE
            tier = SubscriptionTier.FREE
        
        # Define tier requirements for each brain mode
        tier_requirements = {
            BrainMode.BRAIN: [
                SubscriptionTier.FREE,
                SubscriptionTier.PRO,
                SubscriptionTier.TWIN_PLUS,
                SubscriptionTier.EXECUTIVE
            ],
            BrainMode.BRAIN_PRO: [
                SubscriptionTier.PRO,
                SubscriptionTier.TWIN_PLUS,
                SubscriptionTier.EXECUTIVE
            ],
            BrainMode.BRAIN_GEN: [
                SubscriptionTier.EXECUTIVE
            ]
        }
        
        # Validate brain_mode against tier
        allowed_tiers = tier_requirements.get(value, [])
        if tier not in allowed_tiers:
            required_tier_names = {
                BrainMode.BRAIN_PRO: 'PRO',
                BrainMode.BRAIN_GEN: 'EXECUTIVE'
            }
            required = required_tier_names.get(value, 'UNKNOWN')
            raise serializers.ValidationError(
                f'Brain mode {dict(BrainMode.choices).get(value)} requires {required} tier or higher. '
                f'Your current tier is {tier}.'
            )
        
        return value

class UserProfileSerializer(serializers.ModelSerializer):
    """Serializer for user profile."""
    class Meta:
        from .models import User
        model = User
        fields = [
            'id', 'email', 'username', 'display_name', 'bio', 'profile_image', 
            'phone_number', 'whatsapp_number', 'use_default_for_whatsapp',
            'created_at', 'updated_at'
        ]
        read_only_fields = ['id', 'email', 'created_at', 'updated_at']


class ProfileImageSerializer(serializers.Serializer):
    """Serializer for profile image upload."""
    image = serializers.ImageField(required=True)


class ChangePasswordSerializer(serializers.Serializer):
    """Serializer for changing password."""
    current_password = serializers.CharField(
        required=True, 
        write_only=True,
        help_text="Current password"
    )
    new_password = serializers.CharField(
        required=True, 
        min_length=8, 
        write_only=True,
        help_text="New password (minimum 8 characters)"
    )
