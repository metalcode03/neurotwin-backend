"""
Learning app models for NeuroTwin platform.

Defines LearningEvent model for tracking the learning loop:
User Action → Feature Extraction → Profile Update → Behavior Shift → Feedback Reinforcement

Requirements: 6.1, 6.2, 6.3, 6.4, 6.5, 6.6
"""

import uuid
from typing import Optional, Dict, Any, List

from django.db import models
from django.conf import settings
from django.utils import timezone

from .dataclasses import ExtractedFeatures, FeedbackType, ActionCategory


class LearningEvent(models.Model):
    """
    Records a learning event in the learning loop.
    
    Tracks user actions, extracted features, profile updates,
    and feedback for transparency and debugging.
    
    Requirements: 6.1, 6.2, 6.3, 6.4, 6.5
    """
    
    FEEDBACK_CHOICES = [
        (FeedbackType.POSITIVE.value, 'Positive'),
        (FeedbackType.NEGATIVE.value, 'Negative'),
        (FeedbackType.CORRECTION.value, 'Correction'),
    ]
    
    CATEGORY_CHOICES = [
        (ActionCategory.COMMUNICATION.value, 'Communication'),
        (ActionCategory.DECISION.value, 'Decision'),
        (ActionCategory.PREFERENCE.value, 'Preference'),
        (ActionCategory.INTERACTION.value, 'Interaction'),
        (ActionCategory.FEEDBACK.value, 'Feedback'),
    ]
    
    id = models.UUIDField(
        primary_key=True,
        default=uuid.uuid4,
        editable=False
    )
    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name='learning_events'
    )
    
    # Action details
    action_type = models.CharField(
        max_length=100,
        help_text='Type of user action that triggered learning'
    )
    action_category = models.CharField(
        max_length=20,
        choices=CATEGORY_CHOICES,
        default=ActionCategory.INTERACTION.value,
        help_text='Category of the action'
    )
    action_content = models.TextField(
        blank=True,
        default='',
        help_text='Content of the action (e.g., message text)'
    )
    action_context = models.JSONField(
        default=dict,
        help_text='Context in which the action occurred'
    )
    
    # Extracted features (JSONB)
    features = models.JSONField(
        default=dict,
        help_text='Features extracted from the action'
    )
    
    # Profile updates applied
    profile_updates = models.JSONField(
        default=dict,
        null=True,
        blank=True,
        help_text='Updates applied to CSM profile'
    )
    csm_version_before = models.PositiveIntegerField(
        null=True,
        blank=True,
        help_text='CSM version before this learning event'
    )
    csm_version_after = models.PositiveIntegerField(
        null=True,
        blank=True,
        help_text='CSM version after this learning event'
    )
    
    # Feedback (optional, applied later)
    feedback = models.CharField(
        max_length=20,
        choices=FEEDBACK_CHOICES,
        null=True,
        blank=True,
        help_text='User feedback on the Twin behavior'
    )
    feedback_content = models.TextField(
        blank=True,
        default='',
        help_text='Additional feedback content (e.g., correction text)'
    )
    feedback_applied_at = models.DateTimeField(
        null=True,
        blank=True,
        help_text='When feedback was applied'
    )
    
    # Processing status
    is_processed = models.BooleanField(
        default=False,
        help_text='Whether features have been extracted'
    )
    is_profile_updated = models.BooleanField(
        default=False,
        help_text='Whether profile has been updated'
    )
    processing_error = models.TextField(
        blank=True,
        default='',
        help_text='Error message if processing failed'
    )
    
    # Timestamps
    created_at = models.DateTimeField(auto_now_add=True)
    processed_at = models.DateTimeField(
        null=True,
        blank=True,
        help_text='When feature extraction completed'
    )
    
    class Meta:
        db_table = 'learning_events'
        verbose_name = 'Learning Event'
        verbose_name_plural = 'Learning Events'
        ordering = ['-created_at']
        indexes = [
            models.Index(fields=['user', '-created_at']),
            models.Index(fields=['user', 'action_type']),
            models.Index(fields=['user', 'is_processed']),
            models.Index(fields=['user', 'feedback']),
        ]
    
    def __str__(self) -> str:
        return f"Learning Event: {self.action_type} for {self.user.email}"
    
    def get_features(self) -> Optional[ExtractedFeatures]:
        """
        Get the extracted features as an ExtractedFeatures dataclass.
        
        Returns:
            ExtractedFeatures instance or None if not processed
        """
        if not self.features:
            return None
        return ExtractedFeatures.from_dict(self.features)
    
    def set_features(self, features: ExtractedFeatures) -> None:
        """
        Set the extracted features from an ExtractedFeatures dataclass.
        
        Args:
            features: ExtractedFeatures instance to store
        """
        self.features = features.to_dict()
    
    def get_feedback_type(self) -> Optional[FeedbackType]:
        """
        Get the feedback type as a FeedbackType enum.
        
        Returns:
            FeedbackType enum or None if no feedback
        """
        if not self.feedback:
            return None
        return FeedbackType(self.feedback)
    
    def set_feedback(
        self,
        feedback_type: FeedbackType,
        content: str = ''
    ) -> None:
        """
        Set feedback on this learning event.
        
        Args:
            feedback_type: Type of feedback
            content: Optional feedback content (e.g., correction)
        """
        self.feedback = feedback_type.value
        self.feedback_content = content
        self.feedback_applied_at = timezone.now()
    
    @classmethod
    def get_recent_for_user(
        cls,
        user_id: str,
        limit: int = 100
    ) -> List['LearningEvent']:
        """
        Get recent learning events for a user.
        
        Args:
            user_id: UUID of the user
            limit: Maximum number of events to return
            
        Returns:
            List of recent LearningEvent instances
        """
        return list(
            cls.objects.filter(user_id=user_id)
            .order_by('-created_at')[:limit]
        )
    
    @classmethod
    def get_unprocessed_for_user(cls, user_id: str) -> List['LearningEvent']:
        """
        Get unprocessed learning events for a user.
        
        Args:
            user_id: UUID of the user
            
        Returns:
            List of unprocessed LearningEvent instances
        """
        return list(
            cls.objects.filter(
                user_id=user_id,
                is_processed=False
            ).order_by('created_at')
        )
    
    @classmethod
    def get_by_action_type(
        cls,
        user_id: str,
        action_type: str,
        limit: int = 50
    ) -> List['LearningEvent']:
        """
        Get learning events by action type for a user.
        
        Args:
            user_id: UUID of the user
            action_type: Type of action to filter by
            limit: Maximum number of events to return
            
        Returns:
            List of matching LearningEvent instances
        """
        return list(
            cls.objects.filter(
                user_id=user_id,
                action_type=action_type
            ).order_by('-created_at')[:limit]
        )
