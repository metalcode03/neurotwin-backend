"""
Message API views.

Handles listing and sending messages within conversations.
Requirements: 20.4-20.7, 21.1-21.7
"""

from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework import status
from rest_framework.permissions import IsAuthenticated
from rest_framework.pagination import PageNumberPagination
from django.shortcuts import get_object_or_404
from django.utils import timezone

from apps.automation.models import (
    Conversation,
    Message,
    MessageDirection,
    MessageStatus
)
from apps.automation.serializers import (
    MessageListSerializer,
    MessageSerializer,
    SendMessageSerializer
)
from apps.automation.utils.rate_limiter import RateLimiter
from apps.automation.services.message_delivery import MessageDeliveryService


class MessagePagination(PageNumberPagination):
    """Pagination for message list."""
    page_size = 50
    page_size_query_param = 'page_size'
    max_page_size = 200


class MessageListView(APIView):
    """
    List messages in a conversation.
    
    GET /api/v1/conversations/{id}/messages/
    
    Requirements: 20.4-20.7
    """
    
    permission_classes = [IsAuthenticated]
    pagination_class = MessagePagination
    
    def get(self, request, conversation_id):
        """
        List messages for the specified conversation.
        
        Returns messages ordered by created_at ascending.
        Verifies user owns the integration via conversation.
        """
        # Get conversation and verify ownership
        conversation = get_object_or_404(
            Conversation.objects.select_related(
                'integration',
                'integration__user'
            ),
            id=conversation_id
        )
        
        # Verify user owns the integration
        if conversation.integration.user != request.user:
            return Response(
                {'error': 'You do not have permission to access this conversation'},
                status=status.HTTP_403_FORBIDDEN
            )
        
        # Query messages with optimization
        messages = Message.objects.filter(
            conversation=conversation
        ).select_related(
            'conversation'
        ).order_by('created_at')
        
        # Apply pagination
        paginator = self.pagination_class()
        paginated_messages = paginator.paginate_queryset(
            messages,
            request
        )
        
        # Serialize
        serializer = MessageListSerializer(
            paginated_messages,
            many=True
        )
        
        return paginator.get_paginated_response(serializer.data)


class SendMessageView(APIView):
    """
    Send a message in a conversation.
    
    POST /api/v1/conversations/{id}/messages/
    
    Requirements: 21.1-21.7
    """
    
    permission_classes = [IsAuthenticated]
    
    def post(self, request, conversation_id):
        """
        Send an outgoing message.
        
        Validates content, checks rate limits, creates message,
        and enqueues for asynchronous delivery.
        """
        # Get conversation and verify ownership
        conversation = get_object_or_404(
            Conversation.objects.select_related(
                'integration',
                'integration__user',
                'integration__integration_type'
            ),
            id=conversation_id
        )
        
        # Verify user owns the integration
        if conversation.integration.user != request.user:
            return Response(
                {'error': 'You do not have permission to send messages in this conversation'},
                status=status.HTTP_403_FORBIDDEN
            )
        
        # Validate request data
        serializer = SendMessageSerializer(data=request.data)
        if not serializer.is_valid():
            return Response(
                serializer.errors,
                status=status.HTTP_400_BAD_REQUEST
            )
        
        content = serializer.validated_data['content']
        metadata = serializer.validated_data.get('metadata', {})
        
        # Check rate limit
        rate_limiter = RateLimiter()
        integration = conversation.integration
        
        # Get rate limit config from integration type
        rate_limit_config = integration.integration_type.rate_limit_config or {}
        messages_per_minute = rate_limit_config.get('messages_per_minute', 20)
        
        allowed, wait_seconds = rate_limiter.check_rate_limit(
            integration_id=str(integration.id),
            limit_per_minute=messages_per_minute
        )
        
        if not allowed:
            return Response(
                {
                    'error': 'Rate limit exceeded',
                    'retry_after': wait_seconds,
                    'message': f'Please try again in {wait_seconds} seconds'
                },
                status=status.HTTP_429_TOO_MANY_REQUESTS,
                headers={'Retry-After': str(wait_seconds)}
            )
        
        # Create message with pending status
        message = Message.objects.create(
            conversation=conversation,
            direction=MessageDirection.OUTBOUND,
            content=content,
            status=MessageStatus.PENDING,
            metadata=metadata
        )
        
        # Enqueue for asynchronous sending
        from apps.automation.tasks.message_tasks import send_outgoing_message
        send_outgoing_message.delay(str(message.id))
        
        # Return created message immediately
        response_serializer = MessageSerializer(message)
        return Response(
            response_serializer.data,
            status=status.HTTP_201_CREATED
        )
