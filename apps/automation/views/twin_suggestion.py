"""
Twin Suggestion API Views.

Requirements: 8.6
"""

import logging
from uuid import UUID

from rest_framework import viewsets, status
from rest_framework.decorators import action
from rest_framework.response import Response
from rest_framework.permissions import IsAuthenticated
from django.core.exceptions import ValidationError

from apps.automation.models import TwinSuggestion
from apps.automation.serializers.twin_suggestion import (
    TwinSuggestionSerializer,
    CreateTwinSuggestionSerializer,
    ReviewTwinSuggestionSerializer,
)
from apps.automation.services.twin_suggestion import TwinSuggestionService

logger = logging.getLogger(__name__)


class TwinSuggestionViewSet(viewsets.ReadOnlyModelViewSet):
    """
    ViewSet for Twin workflow suggestions.
    
    Provides endpoints for:
    - Listing pending suggestions
    - Retrieving suggestion details
    - Approving suggestions
    - Rejecting suggestions
    
    Requirements: 8.6
    """
    
    serializer_class = TwinSuggestionSerializer
    permission_classes = [IsAuthenticated]
    
    def get_queryset(self):
        """Get suggestions for current user."""
        user = self.request.user
        workflow_id = self.request.query_params.get('workflow_id')
        
        if workflow_id:
            try:
                workflow_uuid = UUID(workflow_id)
                return TwinSuggestionService.get_pending_suggestions(
                    user,
                    workflow_id=workflow_uuid
                )
            except (ValueError, ValidationError):
                return TwinSuggestion.objects.none()
        
        return TwinSuggestionService.get_pending_suggestions(user)
    
    def create(self, request):
        """
        Create a new Twin suggestion.
        
        This endpoint is typically called by the Twin AI system,
        not directly by users.
        """
        serializer = CreateTwinSuggestionSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        
        try:
            suggestion = TwinSuggestionService.create_suggestion(
                user=request.user,
                workflow_id=serializer.validated_data['workflow_id'],
                suggested_changes=serializer.validated_data['suggested_changes'],
                reasoning=serializer.validated_data['reasoning'],
                cognitive_blend_value=serializer.validated_data['cognitive_blend_value'],
                based_on_pattern=serializer.validated_data.get('based_on_pattern', ''),
                expires_in_days=serializer.validated_data.get('expires_in_days', 7),
            )
            
            response_serializer = TwinSuggestionSerializer(suggestion)
            return Response(
                response_serializer.data,
                status=status.HTTP_201_CREATED
            )
        
        except ValidationError as e:
            return Response(
                {'error': str(e)},
                status=status.HTTP_400_BAD_REQUEST
            )
    
    @action(detail=True, methods=['post'])
    def review(self, request, pk=None):
        """
        Review a Twin suggestion (approve or reject).
        
        POST /api/v1/twin-suggestions/{id}/review/
        Body: {
            "action": "approve" | "reject",
            "review_notes": "optional notes"
        }
        """
        serializer = ReviewTwinSuggestionSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        
        action_type = serializer.validated_data['action']
        review_notes = serializer.validated_data.get('review_notes', '')
        
        try:
            if action_type == 'approve':
                workflow = TwinSuggestionService.approve_suggestion(
                    suggestion_id=pk,
                    user=request.user,
                    review_notes=review_notes
                )
                
                return Response({
                    'status': 'approved',
                    'message': 'Suggestion approved and applied to workflow',
                    'workflow_id': str(workflow.id),
                    'workflow_name': workflow.name,
                })
            
            else:  # reject
                TwinSuggestionService.reject_suggestion(
                    suggestion_id=pk,
                    user=request.user,
                    review_notes=review_notes
                )
                
                return Response({
                    'status': 'rejected',
                    'message': 'Suggestion rejected',
                })
        
        except ValidationError as e:
            return Response(
                {'error': str(e)},
                status=status.HTTP_400_BAD_REQUEST
            )
    
    @action(detail=False, methods=['get'])
    def pending(self, request):
        """
        Get all pending suggestions for the user.
        
        GET /api/v1/twin-suggestions/pending/
        """
        suggestions = self.get_queryset()
        serializer = self.get_serializer(suggestions, many=True)
        return Response(serializer.data)
    
    @action(detail=False, methods=['post'])
    def cleanup_expired(self, request):
        """
        Cleanup expired suggestions.
        
        This endpoint is typically called by a scheduled task.
        """
        count = TwinSuggestionService.cleanup_expired_suggestions()
        return Response({
            'message': f'Marked {count} suggestions as expired',
            'count': count,
        })
