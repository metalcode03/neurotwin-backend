"""
Memory service for NeuroTwin platform.

Implements VectorMemoryEngine for semantic memory storage and retrieval.
Handles async embedding generation and vector database operations.

Requirements: 5.1, 5.2, 5.3, 5.4, 5.6, 5.7
"""

import hashlib
import time
from typing import List, Optional, Dict, Any
from datetime import datetime
from django.db import transaction
from django.utils import timezone
from asgiref.sync import sync_to_async

from .models import MemoryRecord, MemoryAccessLog
from .dataclasses import (
    Memory,
    MemoryQuery,
    MemorySearchResult,
    MemorySource,
)
from .vector_client import (
    get_vector_client,
    get_embedding_generator,
    VectorDBClient,
    EmbeddingGenerator,
)


class VectorMemoryEngine:
    """
    Manages semantic memory storage and retrieval.
    
    Provides async methods for storing interactions as embeddings
    and retrieving semantically relevant memories.
    
    Requirements: 5.1, 5.2, 5.3, 5.4, 5.6, 5.7
    """
    
    def __init__(
        self,
        vector_client: Optional[VectorDBClient] = None,
        embedding_generator: Optional[EmbeddingGenerator] = None
    ):
        """
        Initialize the VectorMemoryEngine.
        
        Args:
            vector_client: Optional custom vector DB client
            embedding_generator: Optional custom embedding generator
        """
        self._vector_client = vector_client or get_vector_client()
        self._embedding_generator = embedding_generator or get_embedding_generator()
    
    def _compute_content_hash(self, content: str) -> str:
        """
        Compute SHA-256 hash of content for deduplication.
        
        Args:
            content: The content to hash
            
        Returns:
            Hex string of the hash
        """
        return hashlib.sha256(content.encode('utf-8')).hexdigest()
    
    def _calculate_combined_score(
        self,
        relevance_score: float,
        timestamp: datetime,
        recency_weight: float
    ) -> float:
        """
        Calculate combined score from relevance and recency.
        
        Requirements: 5.7
        
        Args:
            relevance_score: Cosine similarity score (0-1)
            timestamp: When the memory was created
            recency_weight: Weight for recency (0-1)
            
        Returns:
            Combined score
        """
        # Calculate recency score (exponential decay)
        now = timezone.now()
        age_hours = (now - timestamp).total_seconds() / 3600
        
        # Decay factor: memories lose half their recency score every 24 hours
        recency_score = 0.5 ** (age_hours / 24)
        
        # Combine scores
        relevance_weight = 1.0 - recency_weight
        combined = (relevance_weight * relevance_score) + (recency_weight * recency_score)
        
        return combined
    
    async def store_memory(
        self,
        user_id: str,
        content: str,
        source: str,
        metadata: Optional[Dict[str, Any]] = None
    ) -> Memory:
        """
        Asynchronously generate embedding and store memory.
        
        Requirements: 5.1, 5.2
        
        Args:
            user_id: UUID of the user
            content: The text content to store
            source: Source of the memory (MemorySource value)
            metadata: Optional additional metadata
            
        Returns:
            The stored Memory
            
        Raises:
            ValueError: If content is empty or source is invalid
        """
        if not content or not content.strip():
            raise ValueError("Memory content cannot be empty")
        
        if not MemorySource.is_valid(source):
            raise ValueError(f"Invalid memory source: {source}")
        
        # Compute content hash for deduplication
        content_hash = self._compute_content_hash(content)
        
        # Check for duplicate
        exists = await sync_to_async(MemoryRecord.exists_by_hash)(user_id, content_hash)
        if exists:
            # Return existing memory instead of creating duplicate
            record = await sync_to_async(
                lambda: MemoryRecord.objects.filter(
                    user_id=user_id,
                    content_hash=content_hash
                ).first()
            )()
            
            if record:
                # Get embedding from vector store
                result = await self._vector_client.get(str(record.id))
                embedding = result[0] if result else []
                
                return record.to_memory_dataclass(embedding=embedding)
        
        # Generate embedding asynchronously
        embedding = await self._embedding_generator.generate(content)
        
        # Create database record
        @sync_to_async
        def create_record():
            return MemoryRecord.objects.create(
                user_id=user_id,
                content=content,
                content_hash=content_hash,
                source=source,
                metadata=metadata or {},
                has_embedding=True,
                embedding_model=self._embedding_generator.__class__.__name__,
            )
        
        record = await create_record()
        
        # Store in vector database
        vector_metadata = {
            'user_id': user_id,
            'source': source,
            'timestamp': record.created_at.isoformat(),
            'content_hash': content_hash,
            **(metadata or {}),
        }
        
        await self._vector_client.store(
            id=str(record.id),
            embedding=embedding,
            metadata=vector_metadata
        )
        
        # Update record with vector_id
        @sync_to_async
        def update_vector_id():
            record.vector_id = str(record.id)
            record.save(update_fields=['vector_id'])
        
        await update_vector_id()
        
        return Memory(
            id=str(record.id),
            user_id=user_id,
            content=content,
            embedding=embedding,
            source=source,
            timestamp=record.created_at,
            metadata=metadata or {},
        )
    
    async def retrieve_relevant(
        self,
        user_id: str,
        query: MemoryQuery
    ) -> List[Memory]:
        """
        Retrieve semantically relevant memories with timestamps.
        
        Requirements: 5.3, 5.6, 5.7
        
        Args:
            user_id: UUID of the user
            query: Query parameters
            
        Returns:
            List of relevant memories ordered by combined score
        """
        start_time = time.time()
        
        # Generate query embedding
        query_embedding = await self._embedding_generator.generate(query.query_text)
        
        # Search vector database
        search_results = await self._vector_client.search(
            query_embedding=query_embedding,
            user_id=user_id,
            limit=query.max_results * 2,  # Get more to filter
            min_score=query.min_relevance
        )
        
        memories = []
        
        for result in search_results:
            # Get the full record from database
            @sync_to_async
            def get_record():
                try:
                    return MemoryRecord.objects.get(id=result.id)
                except MemoryRecord.DoesNotExist:
                    return None
            
            record = await get_record()
            if not record:
                continue
            
            # Apply source filter
            if query.source_filter and record.source not in query.source_filter:
                continue
            
            # Apply time range filter
            if query.time_range_start and record.created_at < query.time_range_start:
                continue
            if query.time_range_end and record.created_at > query.time_range_end:
                continue
            
            # Calculate combined score
            combined_score = self._calculate_combined_score(
                relevance_score=result.score,
                timestamp=record.created_at,
                recency_weight=query.recency_weight
            )
            
            # Get embedding from vector store
            vector_data = await self._vector_client.get(str(record.id))
            embedding = vector_data[0] if vector_data else []
            
            memory = Memory(
                id=str(record.id),
                user_id=str(record.user_id),
                content=record.content,
                embedding=embedding,
                source=record.source,
                timestamp=record.created_at,
                metadata=record.metadata,
                relevance_score=combined_score,
            )
            
            memories.append(memory)
            
            # Log access
            @sync_to_async
            def log_access():
                MemoryAccessLog.objects.create(
                    memory=record,
                    access_type='retrieval',
                    context={'query': query.query_text}
                )
            
            await log_access()
        
        # Sort by combined score and limit
        memories.sort(key=lambda m: m.relevance_score or 0, reverse=True)
        memories = memories[:query.max_results]
        
        return memories
    
    async def validate_memory_exists(self, memory_id: str) -> bool:
        """
        Verify a memory actually exists before referencing.
        
        Requirements: 5.4
        
        This prevents the Twin from fabricating memories that don't exist.
        
        Args:
            memory_id: UUID of the memory to validate
            
        Returns:
            True if memory exists, False otherwise
        """
        # Check in PostgreSQL
        @sync_to_async
        def check_db():
            return MemoryRecord.objects.filter(id=memory_id).exists()
        
        db_exists = await check_db()
        
        if not db_exists:
            return False
        
        # Also verify in vector store
        vector_exists = await self._vector_client.exists(memory_id)
        
        # Log validation access
        @sync_to_async
        def log_validation():
            try:
                record = MemoryRecord.objects.get(id=memory_id)
                MemoryAccessLog.objects.create(
                    memory=record,
                    access_type='validation',
                    context={'validated': db_exists and vector_exists}
                )
            except MemoryRecord.DoesNotExist:
                pass
        
        await log_validation()
        
        return db_exists and vector_exists
    
    async def get_memory_with_source(self, memory_id: str) -> Optional[Memory]:
        """
        Get memory with source timestamp for validation.
        
        Requirements: 5.6
        
        Args:
            memory_id: UUID of the memory
            
        Returns:
            Memory with timestamp or None if not found
        """
        @sync_to_async
        def get_record():
            try:
                return MemoryRecord.objects.get(id=memory_id)
            except MemoryRecord.DoesNotExist:
                return None
        
        record = await get_record()
        
        if not record:
            return None
        
        # Get embedding from vector store
        vector_data = await self._vector_client.get(str(record.id))
        embedding = vector_data[0] if vector_data else []
        
        # Log access
        @sync_to_async
        def log_access():
            MemoryAccessLog.objects.create(
                memory=record,
                access_type='retrieval',
                context={'method': 'get_memory_with_source'}
            )
        
        await log_access()
        
        return Memory(
            id=str(record.id),
            user_id=str(record.user_id),
            content=record.content,
            embedding=embedding,
            source=record.source,
            timestamp=record.created_at,
            metadata=record.metadata,
        )
    
    async def delete_memory(self, memory_id: str) -> bool:
        """
        Delete a memory from both databases.
        
        Args:
            memory_id: UUID of the memory to delete
            
        Returns:
            True if deleted, False if not found
        """
        # Delete from vector store
        await self._vector_client.delete(memory_id)
        
        # Delete from PostgreSQL
        @sync_to_async
        def delete_record():
            deleted, _ = MemoryRecord.objects.filter(id=memory_id).delete()
            return deleted > 0
        
        return await delete_record()
    
    async def get_user_memory_count(self, user_id: str) -> int:
        """
        Get the total number of memories for a user.
        
        Args:
            user_id: UUID of the user
            
        Returns:
            Number of memories
        """
        @sync_to_async
        def count_records():
            return MemoryRecord.objects.filter(user_id=user_id).count()
        
        return await count_records()
    
    async def get_memories_by_source(
        self,
        user_id: str,
        source: str,
        limit: int = 100
    ) -> List[Memory]:
        """
        Get memories filtered by source.
        
        Args:
            user_id: UUID of the user
            source: Source to filter by
            limit: Maximum number of memories to return
            
        Returns:
            List of memories
        """
        @sync_to_async
        def get_records():
            return list(MemoryRecord.objects.filter(
                user_id=user_id,
                source=source
            ).order_by('-created_at')[:limit])
        
        records = await get_records()
        
        memories = []
        for record in records:
            vector_data = await self._vector_client.get(str(record.id))
            embedding = vector_data[0] if vector_data else []
            
            memories.append(Memory(
                id=str(record.id),
                user_id=str(record.user_id),
                content=record.content,
                embedding=embedding,
                source=record.source,
                timestamp=record.created_at,
                metadata=record.metadata,
            ))
        
        return memories
