"""
Authentication models for NeuroTwin platform.

Defines custom User model with email-based authentication.
JWT token management is handled by djangorestframework-simplejwt.
Requirements: 1.1, 1.2, 1.3
"""

import uuid
from datetime import timedelta
from typing import Optional

from django.db import models
from django.contrib.auth.models import AbstractBaseUser, BaseUserManager, PermissionsMixin
from django.utils import timezone


class UserManager(BaseUserManager):
    """Custom user manager for email-based authentication."""
    
    def create_user(
        self, 
        email: str, 
        password: Optional[str] = None, 
        **extra_fields
    ) -> 'User':
        """Create and return a regular user with email and password."""
        if not email:
            raise ValueError('Email address is required')
        
        email = self.normalize_email(email)
        user = self.model(email=email, **extra_fields)
        
        if password:
            user.set_password(password)
        else:
            user.set_unusable_password()
        
        user.save(using=self._db)
        return user
    
    def create_superuser(
        self, 
        email: str, 
        password: str, 
        **extra_fields
    ) -> 'User':
        """Create and return a superuser."""
        extra_fields.setdefault('is_staff', True)
        extra_fields.setdefault('is_superuser', True)
        extra_fields.setdefault('is_verified', True)
        
        if extra_fields.get('is_staff') is not True:
            raise ValueError('Superuser must have is_staff=True')
        if extra_fields.get('is_superuser') is not True:
            raise ValueError('Superuser must have is_superuser=True')
        
        return self.create_user(email, password, **extra_fields)


class User(AbstractBaseUser, PermissionsMixin):
    """
    Custom User model with email-based authentication.
    
    Supports both password-based and OAuth authentication.
    JWT tokens are managed by djangorestframework-simplejwt.
    Requirements: 1.1, 1.2, 1.3, 1.5
    """
    
    id = models.UUIDField(
        primary_key=True, 
        default=uuid.uuid4, 
        editable=False
    )
    email = models.EmailField(
        unique=True, 
        max_length=255,
        db_index=True
    )
    
    # OAuth fields
    oauth_provider = models.CharField(
        max_length=50, 
        blank=True, 
        null=True,
        help_text='OAuth provider name (e.g., google)'
    )
    oauth_id = models.CharField(
        max_length=255, 
        blank=True, 
        null=True,
        help_text='OAuth provider user ID'
    )
    
    # Account status
    is_verified = models.BooleanField(
        default=False,
        help_text='Whether email has been verified'
    )
    is_active = models.BooleanField(default=True)
    is_staff = models.BooleanField(default=False)
    
    # Timestamps
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    objects = UserManager()
    
    USERNAME_FIELD = 'email'
    REQUIRED_FIELDS = []
    
    class Meta:
        db_table = 'users'
        verbose_name = 'user'
        verbose_name_plural = 'users'
        indexes = [
            models.Index(fields=['email']),
            models.Index(fields=['oauth_provider', 'oauth_id']),
        ]
    
    def __str__(self) -> str:
        return self.email


class VerificationToken(models.Model):
    """
    Token for email verification.
    
    Requirements: 1.1, 1.2
    """
    
    id = models.UUIDField(
        primary_key=True, 
        default=uuid.uuid4, 
        editable=False
    )
    user = models.ForeignKey(
        User, 
        on_delete=models.CASCADE, 
        related_name='verification_tokens'
    )
    token = models.CharField(
        max_length=64, 
        unique=True,
        db_index=True
    )
    expires_at = models.DateTimeField()
    is_used = models.BooleanField(default=False)
    created_at = models.DateTimeField(auto_now_add=True)
    
    class Meta:
        db_table = 'verification_tokens'
        indexes = [
            models.Index(fields=['token']),
        ]
    
    @property
    def is_expired(self) -> bool:
        """Check if the verification token has expired."""
        return timezone.now() > self.expires_at
    
    @property
    def is_valid(self) -> bool:
        """Check if the token is valid (not used and not expired)."""
        return not self.is_used and not self.is_expired


class PasswordResetToken(models.Model):
    """
    Token for password reset requests.
    
    Valid for 24 hours as per Requirements 1.7.
    """
    
    id = models.UUIDField(
        primary_key=True, 
        default=uuid.uuid4, 
        editable=False
    )
    user = models.ForeignKey(
        User, 
        on_delete=models.CASCADE, 
        related_name='password_reset_tokens'
    )
    token = models.CharField(
        max_length=64, 
        unique=True,
        db_index=True
    )
    expires_at = models.DateTimeField()
    is_used = models.BooleanField(default=False)
    created_at = models.DateTimeField(auto_now_add=True)
    
    class Meta:
        db_table = 'password_reset_tokens'
        indexes = [
            models.Index(fields=['token']),
        ]
    
    @property
    def is_expired(self) -> bool:
        """Check if the reset token has expired."""
        return timezone.now() > self.expires_at
    
    @property
    def is_valid(self) -> bool:
        """Check if the token is valid (not used and not expired)."""
        return not self.is_used and not self.is_expired
    
    @classmethod
    def get_expiry_duration(cls) -> timedelta:
        """Return the standard expiry duration (24 hours)."""
        return timedelta(hours=24)
