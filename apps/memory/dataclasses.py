"""
Data classes for Memory app.

Defines Memory and MemoryQuery dataclasses for vector memory storage
and semantic retrieval.

Requirements: 5.1, 5.3, 5.7
"""

from dataclasses import dataclass, field, asdict
from typing import List, Dict, Any, Optional
from datetime import datetime
from enum import Enum
import json


class MemorySource(Enum):
    """
    Source types for memories.
    
    Tracks where the memory originated from.
    Requirements: 5.1
    """
    
    CONVERSATION = "conversation"
    ACTION = "action"
    FEEDBACK = "feedback"
    LEARNING = "learning"
    SYSTEM = "system"
    
    @classmethod
    def is_valid(cls, value: str) -> bool:
        """Check if a source value is valid."""
        return value in [s.value for s in cls]


@dataclass
class Memory:
    """
    A single memory entry with embedding.
    
    Stores user interactions as embeddings for semantic retrieval.
    Requirements: 5.1, 5.6
    """
    
    id: str
    user_id: str
    content: str
    embedding: List[float]
    source: str  # MemorySource value
    timestamp: datetime
    metadata: Dict[str, Any] = field(default_factory=dict)
    relevance_score: Optional[float] = None
    
    def __post_init__(self):
        """Validate memory fields."""
        if not self.id:
            raise ValueError("Memory id is required")
        if not self.user_id:
            raise ValueError("Memory user_id is required")
        if not self.content:
            raise ValueError("Memory content is required")
        if not MemorySource.is_valid(self.source):
            raise ValueError(f"Invalid memory source: {self.source}")
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for serialization."""
        return {
            'id': self.id,
            'user_id': self.user_id,
            'content': self.content,
            'embedding': self.embedding,
            'source': self.source,
            'timestamp': self.timestamp.isoformat() if isinstance(self.timestamp, datetime) else self.timestamp,
            'metadata': self.metadata,
            'relevance_score': self.relevance_score,
        }
    
    def to_json(self) -> str:
        """Serialize to JSON string."""
        return json.dumps(self.to_dict())
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'Memory':
        """Create from dictionary."""
        timestamp = data.get('timestamp')
        if isinstance(timestamp, str):
            timestamp = datetime.fromisoformat(timestamp)
        
        return cls(
            id=str(data['id']),
            user_id=str(data['user_id']),
            content=str(data['content']),
            embedding=list(data.get('embedding', [])),
            source=str(data.get('source', MemorySource.CONVERSATION.value)),
            timestamp=timestamp or datetime.now(),
            metadata=dict(data.get('metadata', {})),
            relevance_score=data.get('relevance_score'),
        )
    
    @classmethod
    def from_json(cls, json_str: str) -> 'Memory':
        """Deserialize from JSON string."""
        data = json.loads(json_str)
        return cls.from_dict(data)
    
    def has_valid_embedding(self) -> bool:
        """Check if the memory has a valid embedding."""
        return bool(self.embedding) and len(self.embedding) > 0
    
    def get_source_enum(self) -> MemorySource:
        """Get the source as MemorySource enum."""
        return MemorySource(self.source)


@dataclass
class MemoryQuery:
    """
    Query parameters for memory retrieval.
    
    Defines how to search and filter memories.
    Requirements: 5.3, 5.7
    """
    
    query_text: str
    max_results: int = 10
    min_relevance: float = 0.5
    recency_weight: float = 0.3
    source_filter: Optional[List[str]] = None
    time_range_start: Optional[datetime] = None
    time_range_end: Optional[datetime] = None
    
    def __post_init__(self):
        """Validate query parameters."""
        if not self.query_text:
            raise ValueError("Query text is required")
        if self.max_results < 1:
            raise ValueError("max_results must be at least 1")
        if not 0.0 <= self.min_relevance <= 1.0:
            raise ValueError("min_relevance must be between 0.0 and 1.0")
        if not 0.0 <= self.recency_weight <= 1.0:
            raise ValueError("recency_weight must be between 0.0 and 1.0")
        
        # Validate source filter
        if self.source_filter:
            for source in self.source_filter:
                if not MemorySource.is_valid(source):
                    raise ValueError(f"Invalid source in filter: {source}")
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary."""
        return {
            'query_text': self.query_text,
            'max_results': self.max_results,
            'min_relevance': self.min_relevance,
            'recency_weight': self.recency_weight,
            'source_filter': self.source_filter,
            'time_range_start': self.time_range_start.isoformat() if self.time_range_start else None,
            'time_range_end': self.time_range_end.isoformat() if self.time_range_end else None,
        }
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'MemoryQuery':
        """Create from dictionary."""
        time_start = data.get('time_range_start')
        time_end = data.get('time_range_end')
        
        if isinstance(time_start, str):
            time_start = datetime.fromisoformat(time_start)
        if isinstance(time_end, str):
            time_end = datetime.fromisoformat(time_end)
        
        return cls(
            query_text=str(data['query_text']),
            max_results=int(data.get('max_results', 10)),
            min_relevance=float(data.get('min_relevance', 0.5)),
            recency_weight=float(data.get('recency_weight', 0.3)),
            source_filter=data.get('source_filter'),
            time_range_start=time_start,
            time_range_end=time_end,
        )


@dataclass
class MemorySearchResult:
    """
    Result from a memory search operation.
    
    Contains the memories found and search metadata.
    """
    
    memories: List[Memory]
    total_found: int
    query: MemoryQuery
    search_time_ms: float = 0.0
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary."""
        return {
            'memories': [m.to_dict() for m in self.memories],
            'total_found': self.total_found,
            'query': self.query.to_dict(),
            'search_time_ms': self.search_time_ms,
        }


@dataclass
class EmbeddingConfig:
    """
    Configuration for embedding generation.
    
    Defines the embedding model and parameters.
    """
    
    model_name: str = "text-embedding-004"
    dimension: int = 768
    batch_size: int = 100
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary."""
        return {
            'model_name': self.model_name,
            'dimension': self.dimension,
            'batch_size': self.batch_size,
        }
