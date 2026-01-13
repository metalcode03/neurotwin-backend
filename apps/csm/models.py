"""
CSM (Cognitive Signature Model) models for NeuroTwin platform.

Defines CSMProfile model with JSONB profile_data for storing
personality, tone, habits, and decision patterns with version tracking.

Requirements: 4.1, 4.6, 4.7
"""

import uuid
from typing import Optional, Dict, Any

from django.db import models
from django.conf import settings
from django.utils import timezone

from .dataclasses import CSMProfileData


class CSMProfile(models.Model):
    """
    Cognitive Signature Model profile.
    
    Stores structured data including personality traits, tone preferences,
    vocabulary patterns, communication habits, and decision-making style.
    
    Uses JSONB for profile_data to allow flexible schema evolution.
    Supports versioning for rollback capability.
    
    Requirements: 4.1, 4.6, 4.7
    """
    
    id = models.UUIDField(
        primary_key=True,
        default=uuid.uuid4,
        editable=False
    )
    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name='csm_profiles'
    )
    version = models.PositiveIntegerField(
        default=1,
        help_text='Version number for this profile snapshot'
    )
    profile_data = models.JSONField(
        default=dict,
        help_text='JSONB storage for CSM profile data'
    )
    is_current = models.BooleanField(
        default=True,
        db_index=True,
        help_text='Whether this is the current active profile version'
    )
    
    # Timestamps
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        db_table = 'csm_profiles'
        verbose_name = 'CSM Profile'
        verbose_name_plural = 'CSM Profiles'
        ordering = ['-version']
        indexes = [
            models.Index(fields=['user', '-version']),
            models.Index(fields=['user', 'is_current']),
        ]
        constraints = [
            models.UniqueConstraint(
                fields=['user', 'version'],
                name='unique_user_version'
            ),
        ]
    
    def __str__(self) -> str:
        return f"CSM Profile for {self.user.email} (v{self.version})"
    
    def get_profile_data(self) -> CSMProfileData:
        """
        Get the profile data as a CSMProfileData dataclass.
        
        Returns:
            CSMProfileData instance with all profile fields
        """
        return CSMProfileData.from_dict(self.profile_data)
    
    def set_profile_data(self, data: CSMProfileData) -> None:
        """
        Set the profile data from a CSMProfileData dataclass.
        
        Args:
            data: CSMProfileData instance to store
        """
        self.profile_data = data.to_dict()
    
    def to_json(self) -> str:
        """
        Serialize the profile to JSON string.
        
        Requirements: 4.6
        
        Returns:
            JSON string representation of the profile data
        """
        return self.get_profile_data().to_json()
    
    @classmethod
    def from_json(cls, user, json_str: str, version: int = 1) -> 'CSMProfile':
        """
        Create a CSMProfile from JSON string.
        
        Requirements: 4.6
        
        Args:
            user: User instance to associate with the profile
            json_str: JSON string containing profile data
            version: Version number for this profile
            
        Returns:
            New CSMProfile instance (not saved)
        """
        profile_data = CSMProfileData.from_json(json_str)
        return cls(
            user=user,
            version=version,
            profile_data=profile_data.to_dict(),
        )
    
    @classmethod
    def get_current_for_user(cls, user_id: str) -> Optional['CSMProfile']:
        """
        Get the current active profile for a user.
        
        Args:
            user_id: UUID of the user
            
        Returns:
            Current CSMProfile or None if not found
        """
        return cls.objects.filter(
            user_id=user_id,
            is_current=True
        ).first()
    
    @classmethod
    def get_version_for_user(cls, user_id: str, version: int) -> Optional['CSMProfile']:
        """
        Get a specific version of the profile for a user.
        
        Args:
            user_id: UUID of the user
            version: Version number to retrieve
            
        Returns:
            CSMProfile at specified version or None if not found
        """
        return cls.objects.filter(
            user_id=user_id,
            version=version
        ).first()
    
    @classmethod
    def get_latest_version_number(cls, user_id: str) -> int:
        """
        Get the latest version number for a user's profiles.
        
        Args:
            user_id: UUID of the user
            
        Returns:
            Latest version number, or 0 if no profiles exist
        """
        result = cls.objects.filter(user_id=user_id).aggregate(
            max_version=models.Max('version')
        )
        return result['max_version'] or 0


class CSMChangeLog(models.Model):
    """
    Audit log for CSM profile changes.
    
    Tracks all changes to CSM profiles for transparency and debugging.
    Requirements: 4.7, 6.6
    """
    
    id = models.UUIDField(
        primary_key=True,
        default=uuid.uuid4,
        editable=False
    )
    profile = models.ForeignKey(
        CSMProfile,
        on_delete=models.CASCADE,
        related_name='change_logs'
    )
    from_version = models.PositiveIntegerField(
        null=True,
        blank=True,
        help_text='Previous version (null for initial creation)'
    )
    to_version = models.PositiveIntegerField(
        help_text='New version after change'
    )
    change_type = models.CharField(
        max_length=20,
        choices=[
            ('create', 'Created'),
            ('update', 'Updated'),
            ('rollback', 'Rolled Back'),
        ],
        default='update'
    )
    change_summary = models.JSONField(
        default=dict,
        help_text='Summary of what changed'
    )
    changed_at = models.DateTimeField(default=timezone.now)
    
    class Meta:
        db_table = 'csm_change_logs'
        verbose_name = 'CSM Change Log'
        verbose_name_plural = 'CSM Change Logs'
        ordering = ['-changed_at']
        indexes = [
            models.Index(fields=['profile', '-changed_at']),
        ]
    
    def __str__(self) -> str:
        if self.from_version:
            return f"CSM Change: v{self.from_version} -> v{self.to_version} ({self.change_type})"
        return f"CSM Change: Created v{self.to_version}"
