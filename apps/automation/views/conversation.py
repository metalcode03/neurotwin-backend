"""
Conversation API views.

Handles listing conversations for integrations.
Requirements: 20.1-20.7
"""

from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework import status
from rest_framework.permissions import IsAuthenticated
from rest_framework.pagination import PageNumberPagination
from django.shortcuts import get_object_or_404

from apps.automation.models import Integration, Conversation
from apps.automation.serializers import ConversationListSerializer


class ConversationPagination(PageNumberPagination):
    """Pagination for conversation list."""
    page_size = 20
    page_size_query_param = 'page_size'
    max_page_size = 100


class ConversationListView(APIView):
    """
    List conversations for an integration.
    
    GET /api/v1/integrations/{id}/conversations/
    
    Requirements: 20.1-20.7
    """
    
    permission_classes = [IsAuthenticated]
    pagination_class = ConversationPagination
    
    def get(self, request, integration_id):
        """
        List conversations for the specified integration.
        
        Returns conversations ordered by last_message_at descending.
        Uses select_related to avoid N+1 queries.
        """
        # Verify user owns the integration
        integration = get_object_or_404(
            Integration,
            id=integration_id,
            user=request.user
        )
        
        # Query conversations with optimization
        conversations = Conversation.objects.filter(
            integration=integration
        ).select_related(
            'integration',
            'integration__integration_type'
        ).order_by('-last_message_at')
        
        # Apply pagination
        paginator = self.pagination_class()
        paginated_conversations = paginator.paginate_queryset(
            conversations,
            request
        )
        
        # Serialize
        serializer = ConversationListSerializer(
            paginated_conversations,
            many=True
        )
        
        return paginator.get_paginated_response(serializer.data)
