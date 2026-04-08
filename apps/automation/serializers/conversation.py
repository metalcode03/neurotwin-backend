"""
Conversation serializers for API validation and response formatting.

Requirements: 15.1-15.2, 20.1-20.7
"""

from rest_framework import serializers
from apps.automation.models import Conversation, Message


class ConversationSerializer(serializers.ModelSerializer):
    """
    Serializer for Conversation model.
    
    Includes integration details and unread count.
    Requirements: 15.1-15.2, 20.3
    """
    
    unread_count = serializers.SerializerMethodField()
    integration_name = serializers.CharField(
        source='integration.integration_type.name',
        read_only=True
    )
    integration_type = serializers.CharField(
        source='integration.integration_type.type',
        read_only=True
    )
    
    class Meta:
        model = Conversation
        fields = [
            'id',
            'integration',
            'integration_name',
            'integration_type',
            'external_contact_id',
            'external_contact_name',
            'status',
            'last_message_at',
            'unread_count',
            'created_at',
            'updated_at'
        ]
        read_only_fields = [
            'id',
            'integration',
            'integration_name',
            'integration_type',
            'external_contact_id',
            'external_contact_name',
            'last_message_at',
            'unread_count',
            'created_at',
            'updated_at'
        ]
    
    def get_unread_count(self, obj: Conversation) -> int:
        """Calculate unread message count for conversation."""
        return obj.unread_count


class ConversationListSerializer(serializers.ModelSerializer):
    """
    Lightweight serializer for conversation list view.
    
    Returns only essential fields for list display.
    Requirements: 20.1-20.3
    """
    
    unread_count = serializers.SerializerMethodField()
    
    class Meta:
        model = Conversation
        fields = [
            'id',
            'external_contact_name',
            'last_message_at',
            'unread_count',
            'status'
        ]
        read_only_fields = fields
    
    def get_unread_count(self, obj: Conversation) -> int:
        """Calculate unread message count for conversation."""
        return obj.unread_count
