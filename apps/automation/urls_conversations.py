"""
URL configuration for conversation and message endpoints.

Requirements: 20.1-20.7, 21.1-21.7, 23.6
"""

from django.urls import path
from .views import (
    ConversationListView,
    MessageListView,
    SendMessageView,
    IntegrationHealthView,
)

app_name = 'conversations'

urlpatterns = [
    # Conversation endpoints
    path(
        'integrations/<uuid:integration_id>/conversations/',
        ConversationListView.as_view(),
        name='conversation-list'
    ),
    
    # Message endpoints
    path(
        'conversations/<uuid:conversation_id>/messages/',
        MessageListView.as_view(),
        name='message-list'
    ),
    path(
        'conversations/<uuid:conversation_id>/messages/',
        SendMessageView.as_view(),
        name='message-send'
    ),
    
    # Integration health endpoint
    path(
        'integrations/<uuid:integration_id>/health/',
        IntegrationHealthView.as_view(),
        name='integration-health'
    ),
]
