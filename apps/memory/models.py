"""
Memory models for NeuroTwin platform.

Defines MemoryRecord model for tracking memory metadata in PostgreSQL.
The actual embeddings are stored in a vector database.

Requirements: 5.1, 5.6
"""

import uuid
from typing import Optional, List, Dict, Any

from django.db import models
from django.conf import settings
from django.utils import timezone

from .dataclasses import Memory, MemorySource


class MemoryRecord(models.Model):
    """
    PostgreSQL record for memory metadata.
    
    Stores memory metadata and references to vector database entries.
    The actual embeddings are stored in the vector database for
    efficient similarity search.
    
    Requirements: 5.1, 5.6
    """
    
    SOURCE_CHOICES = [
        (MemorySource.CONVERSATION.value, 'Conversation'),
        (MemorySource.ACTION.value, 'Action'),
        (MemorySource.FEEDBACK.value, 'Feedback'),
        (MemorySource.LEARNING.value, 'Learning'),
        (MemorySource.SYSTEM.value, 'System'),
    ]
    
    id = models.UUIDField(
        primary_key=True,
        default=uuid.uuid4,
        editable=False
    )
    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name='memories',
        help_text='The user this memory belongs to'
    )
    content = models.TextField(
        help_text='The text content of the memory'
    )
    content_hash = models.CharField(
        max_length=64,
        db_index=True,
        help_text='SHA-256 hash of content for deduplication'
    )
    source = models.CharField(
        max_length=20,
        choices=SOURCE_CHOICES,
        default=MemorySource.CONVERSATION.value,
        help_text='Source of the memory'
    )
    metadata = models.JSONField(
        default=dict,
        help_text='Additional metadata for the memory'
    )
    
    # Vector database reference
    vector_id = models.CharField(
        max_length=255,
        blank=True,
        null=True,
        help_text='ID in the vector database'
    )
    has_embedding = models.BooleanField(
        default=False,
        help_text='Whether embedding has been generated'
    )
    embedding_model = models.CharField(
        max_length=100,
        blank=True,
        null=True,
        help_text='Model used to generate embedding'
    )
    
    # Timestamps
    created_at = models.DateTimeField(
        default=timezone.now,
        help_text='When the memory was created'
    )
    updated_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        db_table = 'memory_records'
        verbose_name = 'Memory Record'
        verbose_name_plural = 'Memory Records'
        ordering = ['-created_at']
        indexes = [
            models.Index(fields=['user', '-created_at']),
            models.Index(fields=['user', 'source']),
            models.Index(fields=['content_hash']),
            models.Index(fields=['has_embedding']),
        ]
    
    def __str__(self) -> str:
        content_preview = self.content[:50] + '...' if len(self.content) > 50 else self.content
        return f"Memory: {content_preview}"
    
    def get_source_enum(self) -> MemorySource:
        """Get the source as MemorySource enum."""
        return MemorySource(self.source)
    
    def to_memory_dataclass(self, embedding: List[float] = None, relevance_score: float = None) -> Memory:
        """
        Convert to Memory dataclass.
        
        Args:
            embedding: Optional embedding vector (from vector DB)
            relevance_score: Optional relevance score from search
            
        Returns:
            Memory dataclass instance
        """
        return Memory(
            id=str(self.id),
            user_id=str(self.user_id),
            content=self.content,
            embedding=embedding or [],
            source=self.source,
            timestamp=self.created_at,
            metadata=self.metadata,
            relevance_score=relevance_score,
        )
    
    @classmethod
    def get_for_user(
        cls,
        user_id: str,
        source: Optional[str] = None,
        limit: int = 100
    ) -> List['MemoryRecord']:
        """
        Get memories for a user.
        
        Args:
            user_id: UUID of the user
            source: Optional source filter
            limit: Maximum number of records to return
            
        Returns:
            List of MemoryRecord instances
        """
        queryset = cls.objects.filter(user_id=user_id)
        
        if source:
            queryset = queryset.filter(source=source)
        
        return list(queryset[:limit])
    
    @classmethod
    def exists_by_hash(cls, user_id: str, content_hash: str) -> bool:
        """
        Check if a memory with the given hash exists for the user.
        
        Args:
            user_id: UUID of the user
            content_hash: SHA-256 hash of the content
            
        Returns:
            True if memory exists, False otherwise
        """
        return cls.objects.filter(
            user_id=user_id,
            content_hash=content_hash
        ).exists()


class MemoryAccessLog(models.Model):
    """
    Log of memory access operations.
    
    Tracks when memories are read for audit and debugging.
    Requirements: 5.6
    """
    
    id = models.UUIDField(
        primary_key=True,
        default=uuid.uuid4,
        editable=False
    )
    memory = models.ForeignKey(
        MemoryRecord,
        on_delete=models.CASCADE,
        related_name='access_logs'
    )
    accessed_at = models.DateTimeField(default=timezone.now)
    access_type = models.CharField(
        max_length=20,
        choices=[
            ('retrieval', 'Retrieval'),
            ('validation', 'Validation'),
            ('export', 'Export'),
        ],
        default='retrieval'
    )
    context = models.JSONField(
        default=dict,
        help_text='Context of the access (query, etc.)'
    )
    
    class Meta:
        db_table = 'memory_access_logs'
        verbose_name = 'Memory Access Log'
        verbose_name_plural = 'Memory Access Logs'
        ordering = ['-accessed_at']
        indexes = [
            models.Index(fields=['memory', '-accessed_at']),
        ]
    
    def __str__(self) -> str:
        return f"Access to {self.memory_id} at {self.accessed_at}"
