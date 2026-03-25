"""
Memory serializers for NeuroTwin platform.

Handles serialization and validation for memory REST API endpoints.
Requirements: 5.1, 5.3, 5.6
"""

from rest_framework import serializers
from django.utils import timezone
from typing import Dict, Any

from .models import MemoryRecord
from .dataclasses import MemorySource


class MemoryEntrySerializer(serializers.Serializer):
    """
    Serializer for memory entries in frontend format.
    
    Transforms MemoryRecord to the format expected by the frontend.
    Requirements: 5.1, 5.6
    """
    
    id = serializers.UUIDField(read_only=True)
    eventType = serializers.SerializerMethodField()
    timestamp = serializers.DateTimeField(source='created_at', read_only=True)
    description = serializers.CharField(source='content', read_only=True)
    source = serializers.CharField(read_only=True)
    metadata = serializers.JSONField(read_only=True, required=False)
    
    def get_eventType(self, obj: MemoryRecord) -> str:
        """
        Generate event type from source.
        
        Maps memory source to user-friendly event type.
        """
        source_to_event = {
            MemorySource.CONVERSATION.value: 'Conversation',
            MemorySource.ACTION.value: 'Action Taken',
            MemorySource.FEEDBACK.value: 'User Feedback',
            MemorySource.LEARNING.value: 'Learning Insight',
            MemorySource.SYSTEM.value: 'System Event',
        }
        return source_to_event.get(obj.source, 'Unknown Event')
    
    class Meta:
        fields = ['id', 'eventType', 'timestamp', 'description', 'source', 'metadata']


class MemoryDetailSerializer(MemoryEntrySerializer):
    """
    Extended serializer for detailed memory view.
    
    Includes additional fields for the detail endpoint.
    Requirements: 5.6
    """
    
    contentHash = serializers.CharField(source='content_hash', read_only=True)
    hasEmbedding = serializers.BooleanField(source='has_embedding', read_only=True)
    embeddingModel = serializers.CharField(source='embedding_model', read_only=True, allow_null=True)
    vectorId = serializers.CharField(source='vector_id', read_only=True, allow_null=True)
    updatedAt = serializers.DateTimeField(source='updated_at', read_only=True)
    
    class Meta:
        fields = MemoryEntrySerializer.Meta.fields + [
            'contentHash', 'hasEmbedding', 'embeddingModel', 'vectorId', 'updatedAt'
        ]


class MemorySearchSerializer(serializers.Serializer):
    """
    Serializer for memory search requests.
    
    Validates search query parameters.
    Requirements: 5.3
    """
    
    query = serializers.CharField(
        required=False,
        allow_blank=True,
        max_length=500,
        help_text='Search query text'
    )
    source = serializers.ChoiceField(
        choices=[s.value for s in MemorySource],
        required=False,
        allow_null=True,
        help_text='Filter by memory source'
    )
    limit = serializers.IntegerField(
        default=20,
        min_value=1,
        max_value=100,
        help_text='Maximum number of results'
    )
    offset = serializers.IntegerField(
        default=0,
        min_value=0,
        help_text='Pagination offset'
    )
    
    def validate_query(self, value: str) -> str:
        """Validate and clean search query."""
        if value:
            return value.strip()
        return value


class MemoryListResponseSerializer(serializers.Serializer):
    """
    Serializer for memory list response.
    
    Wraps memory entries with pagination metadata.
    """
    
    memories = MemoryEntrySerializer(many=True)
    total = serializers.IntegerField()
    hasMore = serializers.BooleanField()
    nextCursor = serializers.IntegerField(required=False, allow_null=True)


class MemoryCreateSerializer(serializers.Serializer):
    """
    Serializer for creating new memories.
    
    Used when manually adding memories or importing data.
    Requirements: 5.1
    """
    
    content = serializers.CharField(
        required=True,
        max_length=10000,
        help_text='Memory content text'
    )
    source = serializers.ChoiceField(
        choices=[s.value for s in MemorySource],
        default=MemorySource.CONVERSATION.value,
        help_text='Source of the memory'
    )
    metadata = serializers.JSONField(
        required=False,
        default=dict,
        help_text='Additional metadata'
    )
    
    def validate_content(self, value: str) -> str:
        """Validate memory content."""
        if not value or not value.strip():
            raise serializers.ValidationError("Memory content cannot be empty")
        return value.strip()
    
    def validate_metadata(self, value: Dict[str, Any]) -> Dict[str, Any]:
        """Validate metadata is a dictionary."""
        if not isinstance(value, dict):
            raise serializers.ValidationError("Metadata must be a JSON object")
        return value
