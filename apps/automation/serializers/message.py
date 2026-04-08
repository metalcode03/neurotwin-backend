"""
Message serializers for API validation and response formatting.

Requirements: 15.3-15.7, 20.4-20.7, 21.1-21.7
"""

from rest_framework import serializers
from apps.automation.models import Message, MessageDirection, MessageStatus


class MessageSerializer(serializers.ModelSerializer):
    """
    Serializer for Message model.
    
    Includes all message fields and retry information.
    Requirements: 15.3-15.7
    """
    
    class Meta:
        model = Message
        fields = [
            'id',
            'conversation',
            'direction',
            'content',
            'status',
            'external_message_id',
            'retry_count',
            'last_retry_at',
            'metadata',
            'created_at',
            'updated_at'
        ]
        read_only_fields = [
            'id',
            'conversation',
            'direction',
            'status',
            'external_message_id',
            'retry_count',
            'last_retry_at',
            'created_at',
            'updated_at'
        ]


class MessageListSerializer(serializers.ModelSerializer):
    """
    Lightweight serializer for message list view.
    
    Returns only essential fields for list display.
    Requirements: 20.4-20.7
    """
    
    class Meta:
        model = Message
        fields = [
            'id',
            'direction',
            'content',
            'status',
            'created_at'
        ]
        read_only_fields = fields


class SendMessageSerializer(serializers.Serializer):
    """
    Serializer for sending outgoing messages.
    
    Validates content and optional metadata.
    Requirements: 21.1-21.7
    """
    
    content = serializers.CharField(
        required=True,
        allow_blank=False,
        max_length=4096,
        help_text="Message content to send"
    )
    
    metadata = serializers.JSONField(
        required=False,
        default=dict,
        help_text="Optional platform-specific metadata"
    )
    
    def validate_content(self, value: str) -> str:
        """Validate message content is not empty after stripping."""
        if not value.strip():
            raise serializers.ValidationError("Message content cannot be empty")
        return value.strip()
    
    def validate_metadata(self, value: dict) -> dict:
        """Validate metadata is a dictionary."""
        if not isinstance(value, dict):
            raise serializers.ValidationError("Metadata must be a JSON object")
        return value
