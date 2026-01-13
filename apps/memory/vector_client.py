"""
Vector database client configuration for Memory app.

Provides an abstraction layer for vector database operations.
Currently implements an in-memory store for development/testing,
with interface ready for production vector DB integration.

Requirements: 5.1, 5.2, 5.3
"""

import os
import math
import hashlib
from abc import ABC, abstractmethod
from typing import List, Dict, Any, Optional, Tuple
from datetime import datetime
from dataclasses import dataclass
import threading

from .dataclasses import Memory, MemoryQuery, EmbeddingConfig


@dataclass
class VectorSearchResult:
    """Result from a vector similarity search."""
    
    id: str
    score: float
    metadata: Dict[str, Any]


class VectorDBClient(ABC):
    """
    Abstract base class for vector database clients.
    
    Defines the interface for vector storage and retrieval.
    """
    
    @abstractmethod
    async def store(
        self,
        id: str,
        embedding: List[float],
        metadata: Dict[str, Any]
    ) -> bool:
        """Store an embedding with metadata."""
        pass
    
    @abstractmethod
    async def search(
        self,
        query_embedding: List[float],
        user_id: str,
        limit: int = 10,
        min_score: float = 0.0
    ) -> List[VectorSearchResult]:
        """Search for similar embeddings."""
        pass
    
    @abstractmethod
    async def delete(self, id: str) -> bool:
        """Delete an embedding by ID."""
        pass
    
    @abstractmethod
    async def exists(self, id: str) -> bool:
        """Check if an embedding exists."""
        pass
    
    @abstractmethod
    async def get(self, id: str) -> Optional[Tuple[List[float], Dict[str, Any]]]:
        """Get an embedding and its metadata by ID."""
        pass


class InMemoryVectorClient(VectorDBClient):
    """
    In-memory vector database client for development and testing.
    
    Stores embeddings in memory with basic cosine similarity search.
    Thread-safe implementation.
    """
    
    def __init__(self):
        """Initialize the in-memory store."""
        self._store: Dict[str, Tuple[List[float], Dict[str, Any]]] = {}
        self._lock = threading.RLock()
    
    def _cosine_similarity(self, a: List[float], b: List[float]) -> float:
        """
        Calculate cosine similarity between two vectors.
        
        Args:
            a: First vector
            b: Second vector
            
        Returns:
            Cosine similarity score (0.0 to 1.0)
        """
        if len(a) != len(b) or len(a) == 0:
            return 0.0
        
        dot_product = sum(x * y for x, y in zip(a, b))
        norm_a = math.sqrt(sum(x * x for x in a))
        norm_b = math.sqrt(sum(x * x for x in b))
        
        if norm_a == 0 or norm_b == 0:
            return 0.0
        
        return dot_product / (norm_a * norm_b)
    
    async def store(
        self,
        id: str,
        embedding: List[float],
        metadata: Dict[str, Any]
    ) -> bool:
        """
        Store an embedding with metadata.
        
        Args:
            id: Unique identifier for the embedding
            embedding: The embedding vector
            metadata: Associated metadata
            
        Returns:
            True if stored successfully
        """
        with self._lock:
            self._store[id] = (embedding, metadata)
        return True
    
    async def search(
        self,
        query_embedding: List[float],
        user_id: str,
        limit: int = 10,
        min_score: float = 0.0
    ) -> List[VectorSearchResult]:
        """
        Search for similar embeddings.
        
        Args:
            query_embedding: The query vector
            user_id: Filter by user ID
            limit: Maximum results to return
            min_score: Minimum similarity score
            
        Returns:
            List of search results sorted by score
        """
        results = []
        
        with self._lock:
            for id, (embedding, metadata) in self._store.items():
                # Filter by user_id
                if metadata.get('user_id') != user_id:
                    continue
                
                # Calculate similarity
                score = self._cosine_similarity(query_embedding, embedding)
                
                if score >= min_score:
                    results.append(VectorSearchResult(
                        id=id,
                        score=score,
                        metadata=metadata
                    ))
        
        # Sort by score descending
        results.sort(key=lambda x: x.score, reverse=True)
        
        return results[:limit]
    
    async def delete(self, id: str) -> bool:
        """
        Delete an embedding by ID.
        
        Args:
            id: The embedding ID to delete
            
        Returns:
            True if deleted, False if not found
        """
        with self._lock:
            if id in self._store:
                del self._store[id]
                return True
            return False
    
    async def exists(self, id: str) -> bool:
        """
        Check if an embedding exists.
        
        Args:
            id: The embedding ID to check
            
        Returns:
            True if exists, False otherwise
        """
        with self._lock:
            return id in self._store
    
    async def get(self, id: str) -> Optional[Tuple[List[float], Dict[str, Any]]]:
        """
        Get an embedding and its metadata by ID.
        
        Args:
            id: The embedding ID
            
        Returns:
            Tuple of (embedding, metadata) or None if not found
        """
        with self._lock:
            return self._store.get(id)
    
    def clear(self) -> None:
        """Clear all stored embeddings (for testing)."""
        with self._lock:
            self._store.clear()
    
    def count(self) -> int:
        """Get the number of stored embeddings."""
        with self._lock:
            return len(self._store)


class EmbeddingGenerator(ABC):
    """
    Abstract base class for embedding generators.
    
    Defines the interface for generating embeddings from text.
    """
    
    @abstractmethod
    async def generate(self, text: str) -> List[float]:
        """Generate an embedding for the given text."""
        pass
    
    @abstractmethod
    async def generate_batch(self, texts: List[str]) -> List[List[float]]:
        """Generate embeddings for multiple texts."""
        pass
    
    @property
    @abstractmethod
    def dimension(self) -> int:
        """Return the embedding dimension."""
        pass


class MockEmbeddingGenerator(EmbeddingGenerator):
    """
    Mock embedding generator for development and testing.
    
    Generates deterministic embeddings based on text hash.
    """
    
    def __init__(self, dimension: int = 768):
        """
        Initialize the mock generator.
        
        Args:
            dimension: The embedding dimension
        """
        self._dimension = dimension
    
    def _text_to_embedding(self, text: str) -> List[float]:
        """
        Generate a deterministic embedding from text.
        
        Uses SHA-256 hash to create reproducible embeddings.
        """
        # Create hash of text
        text_hash = hashlib.sha256(text.encode()).hexdigest()
        
        # Convert hash to floats
        embedding = []
        for i in range(0, min(len(text_hash), self._dimension * 2), 2):
            # Convert each pair of hex chars to a float between -1 and 1
            value = int(text_hash[i:i+2], 16) / 255.0 * 2 - 1
            embedding.append(value)
        
        # Pad or truncate to dimension
        while len(embedding) < self._dimension:
            # Extend by repeating the pattern
            idx = len(embedding) % len(text_hash)
            value = int(text_hash[idx:idx+2] if idx + 2 <= len(text_hash) else text_hash[idx:], 16) / 255.0 * 2 - 1
            embedding.append(value)
        
        embedding = embedding[:self._dimension]
        
        # Normalize the vector
        norm = math.sqrt(sum(x * x for x in embedding))
        if norm > 0:
            embedding = [x / norm for x in embedding]
        
        return embedding
    
    async def generate(self, text: str) -> List[float]:
        """
        Generate an embedding for the given text.
        
        Args:
            text: The text to embed
            
        Returns:
            Embedding vector
        """
        return self._text_to_embedding(text)
    
    async def generate_batch(self, texts: List[str]) -> List[List[float]]:
        """
        Generate embeddings for multiple texts.
        
        Args:
            texts: List of texts to embed
            
        Returns:
            List of embedding vectors
        """
        return [self._text_to_embedding(text) for text in texts]
    
    @property
    def dimension(self) -> int:
        """Return the embedding dimension."""
        return self._dimension


# Global instances for dependency injection
_vector_client: Optional[VectorDBClient] = None
_embedding_generator: Optional[EmbeddingGenerator] = None


def get_vector_client() -> VectorDBClient:
    """
    Get the configured vector database client.
    
    Returns:
        VectorDBClient instance
    """
    global _vector_client
    
    if _vector_client is None:
        # Default to in-memory client for development
        # In production, this would be configured based on settings
        _vector_client = InMemoryVectorClient()
    
    return _vector_client


def set_vector_client(client: VectorDBClient) -> None:
    """
    Set the vector database client (for testing/configuration).
    
    Args:
        client: VectorDBClient instance to use
    """
    global _vector_client
    _vector_client = client


def get_embedding_generator() -> EmbeddingGenerator:
    """
    Get the configured embedding generator.
    
    Returns:
        EmbeddingGenerator instance
    """
    global _embedding_generator
    
    if _embedding_generator is None:
        # Default to mock generator for development
        # In production, this would use the actual AI service
        _embedding_generator = MockEmbeddingGenerator()
    
    return _embedding_generator


def set_embedding_generator(generator: EmbeddingGenerator) -> None:
    """
    Set the embedding generator (for testing/configuration).
    
    Args:
        generator: EmbeddingGenerator instance to use
    """
    global _embedding_generator
    _embedding_generator = generator


def reset_clients() -> None:
    """Reset all clients to None (for testing)."""
    global _vector_client, _embedding_generator
    _vector_client = None
    _embedding_generator = None
