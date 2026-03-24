"""
Twin Suggestion Service.

Manages Twin workflow modification suggestions.
Requirements: 8.6
"""

import logging
from uuid import UUID
from datetime import timedelta
from typing import Optional

from django.core.exceptions import ValidationError
from django.db import transaction
from django.utils import timezone

from apps.automation.models import (
    TwinSuggestion,
    SuggestionStatus,
    Workflow,
)

logger = logging.getLogger(__name__)


class TwinSuggestionService:
    """Service for managing Twin workflow suggestions."""
    
    @staticmethod
    @transaction.atomic
    def create_suggestion(
        user,
        workflow_id: UUID,
        suggested_changes: dict,
        reasoning: str,
        cognitive_blend_value: int,
        based_on_pattern: str = '',
        expires_in_days: int = 7
    ) -> TwinSuggestion:
        """
        Create a new Twin workflow modification suggestion.
        
        Requirements: 8.6
        
        Args:
            user: User who owns the workflow
            workflow_id: ID of workflow to modify
            suggested_changes: Dictionary of proposed changes
            reasoning: Explanation for the suggestion
            cognitive_blend_value: Current cognitive blend value
            based_on_pattern: Description of learned pattern
            expires_in_days: Days until suggestion expires
            
        Returns:
            TwinSuggestion: Created suggestion
            
        Raises:
            ValidationError: If validation fails
        """
        # Get workflow
        try:
            workflow = Workflow.objects.get(
                id=workflow_id,
                user=user
            )
        except Workflow.DoesNotExist:
            raise ValidationError(f'Workflow {workflow_id} not found')
        
        # Validate suggested changes
        if not suggested_changes:
            raise ValidationError('Suggested changes cannot be empty')
        
        if not reasoning:
            raise ValidationError('Reasoning is required for Twin suggestions')
        
        # Calculate expiration
        expires_at = timezone.now() + timedelta(days=expires_in_days)
        
        # Create suggestion
        suggestion = TwinSuggestion.objects.create(
            workflow=workflow,
            user=user,
            suggested_changes=suggested_changes,
            reasoning=reasoning,
            cognitive_blend_value=cognitive_blend_value,
            based_on_pattern=based_on_pattern,
            expires_at=expires_at,
        )
        
        logger.info(
            f'Created Twin suggestion {suggestion.id} for workflow {workflow_id}: '
            f'{reasoning[:100]}'
        )
        
        return suggestion
    
    @staticmethod
    def get_pending_suggestions(user, workflow_id: Optional[UUID] = None):
        """
        Get pending suggestions for user.
        
        Args:
            user: User to get suggestions for
            workflow_id: Optional workflow ID to filter by
            
        Returns:
            QuerySet of pending TwinSuggestion objects
        """
        queryset = TwinSuggestion.objects.filter(
            user=user,
            status=SuggestionStatus.PENDING,
            expires_at__gt=timezone.now()
        ).select_related('workflow')
        
        if workflow_id:
            queryset = queryset.filter(workflow_id=workflow_id)
        
        return queryset.order_by('-created_at')
    
    @staticmethod
    def get_suggestion(suggestion_id: UUID, user) -> TwinSuggestion:
        """
        Get a specific suggestion.
        
        Args:
            suggestion_id: ID of suggestion
            user: User who owns the suggestion
            
        Returns:
            TwinSuggestion
            
        Raises:
            ValidationError: If not found
        """
        try:
            return TwinSuggestion.objects.select_related('workflow').get(
                id=suggestion_id,
                user=user
            )
        except TwinSuggestion.DoesNotExist:
            raise ValidationError(f'Suggestion {suggestion_id} not found')
    
    @staticmethod
    @transaction.atomic
    def approve_suggestion(
        suggestion_id: UUID,
        user,
        review_notes: str = ''
    ):
        """
        Approve a Twin suggestion and apply changes.
        
        Requirements: 8.6
        
        Args:
            suggestion_id: ID of suggestion to approve
            user: User approving the suggestion
            review_notes: Optional notes from user
            
        Returns:
            Workflow: Updated workflow
            
        Raises:
            ValidationError: If validation fails
        """
        suggestion = TwinSuggestionService.get_suggestion(suggestion_id, user)
        
        # Check if suggestion is still pending
        if suggestion.status != SuggestionStatus.PENDING:
            raise ValidationError(
                f'Suggestion is {suggestion.status}, cannot approve'
            )
        
        # Check if expired
        if suggestion.is_expired:
            suggestion.mark_expired()
            raise ValidationError('Suggestion has expired')
        
        # Approve and apply changes
        workflow = suggestion.approve(review_notes)
        
        logger.info(
            f'User {user.id} approved Twin suggestion {suggestion_id} '
            f'for workflow {workflow.id}'
        )
        
        return workflow
    
    @staticmethod
    @transaction.atomic
    def reject_suggestion(
        suggestion_id: UUID,
        user,
        review_notes: str = ''
    ):
        """
        Reject a Twin suggestion.
        
        Requirements: 8.6
        
        Args:
            suggestion_id: ID of suggestion to reject
            user: User rejecting the suggestion
            review_notes: Optional notes from user
            
        Raises:
            ValidationError: If validation fails
        """
        suggestion = TwinSuggestionService.get_suggestion(suggestion_id, user)
        
        # Check if suggestion is still pending
        if suggestion.status != SuggestionStatus.PENDING:
            raise ValidationError(
                f'Suggestion is {suggestion.status}, cannot reject'
            )
        
        # Reject
        suggestion.reject(review_notes)
        
        logger.info(
            f'User {user.id} rejected Twin suggestion {suggestion_id} '
            f'for workflow {suggestion.workflow.id}'
        )
    
    @staticmethod
    def cleanup_expired_suggestions():
        """
        Mark expired suggestions as expired.
        
        Should be called periodically (e.g., daily cron job).
        
        Returns:
            int: Number of suggestions marked as expired
        """
        return TwinSuggestion.cleanup_expired()
