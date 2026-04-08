"""
Dataclasses for credit-based AI architecture.

Defines ProviderResponse and related dataclasses for AI provider abstraction.
Requirements: 8.5
"""

from dataclasses import dataclass, field
from typing import Dict, Any, Optional


@dataclass
class ProviderResponse:
    """
    Standardized response from AI provider.
    
    Requirements: 8.5
    Used by all provider implementations to return consistent response format.
    """
    
    content: str
    tokens_used: int
    model_used: str
    latency_ms: int
    metadata: Dict[str, Any] = field(default_factory=dict)
    
    def __post_init__(self):
        """Validate fields after initialization."""
        if not self.content:
            raise ValueError("content cannot be empty")
        
        if self.tokens_used < 0:
            raise ValueError("tokens_used must be non-negative")
        
        if self.latency_ms < 0:
            raise ValueError("latency_ms must be non-negative")
        
        if not self.model_used:
            raise ValueError("model_used cannot be empty")
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for serialization."""
        return {
            'content': self.content,
            'tokens_used': self.tokens_used,
            'model_used': self.model_used,
            'latency_ms': self.latency_ms,
            'metadata': self.metadata,
        }
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'ProviderResponse':
        """Create from dictionary."""
        return cls(
            content=data['content'],
            tokens_used=data['tokens_used'],
            model_used=data['model_used'],
            latency_ms=data['latency_ms'],
            metadata=data.get('metadata', {}),
        )
    
    def get_content_length(self) -> int:
        """Get length of response content."""
        return len(self.content)
    
    def add_metadata(self, key: str, value: Any) -> None:
        """Add metadata entry."""
        self.metadata[key] = value
    
    def get_metadata(self, key: str, default: Any = None) -> Any:
        """Get metadata entry with optional default."""
        return self.metadata.get(key, default)


@dataclass
class ModelSelection:
    """
    Model selection result from ModelRouter.
    
    Contains primary model and fallback list for failure handling.
    Requirements: 6.7
    """
    
    primary_model: str
    fallback_models: list[str] = field(default_factory=list)
    selection_reason: Optional[str] = None
    brain_mode: Optional[str] = None
    operation_type: Optional[str] = None
    
    def __post_init__(self):
        """Validate fields after initialization."""
        if not self.primary_model:
            raise ValueError("primary_model cannot be empty")
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for logging."""
        return {
            'primary_model': self.primary_model,
            'fallback_models': self.fallback_models,
            'selection_reason': self.selection_reason,
            'brain_mode': self.brain_mode,
            'operation_type': self.operation_type,
        }
    
    def get_all_models(self) -> list[str]:
        """Get list of all models (primary + fallbacks)."""
        return [self.primary_model] + self.fallback_models


@dataclass
class CreditBalance:
    """
    User credit balance information.
    
    Requirements: 1.10, 4.5
    """
    
    monthly_credits: int
    remaining_credits: int
    used_credits: int
    purchased_credits: int
    last_reset_date: str
    next_reset_date: str
    days_until_reset: int
    usage_percentage: float
    
    def __post_init__(self):
        """Validate fields after initialization."""
        if self.monthly_credits < 0:
            raise ValueError("monthly_credits must be non-negative")
        
        if self.remaining_credits < 0:
            raise ValueError("remaining_credits must be non-negative")
        
        if self.used_credits < 0:
            raise ValueError("used_credits must be non-negative")
        
        if self.purchased_credits < 0:
            raise ValueError("purchased_credits must be non-negative")
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for API response."""
        return {
            'monthly_credits': self.monthly_credits,
            'remaining_credits': self.remaining_credits,
            'used_credits': self.used_credits,
            'purchased_credits': self.purchased_credits,
            'last_reset_date': self.last_reset_date,
            'next_reset_date': self.next_reset_date,
            'days_until_reset': self.days_until_reset,
            'usage_percentage': self.usage_percentage,
        }
    
    def is_exhausted(self) -> bool:
        """Check if credits are exhausted."""
        return self.remaining_credits == 0
    
    def is_low(self, threshold: float = 0.8) -> bool:
        """Check if credits are below threshold percentage."""
        return self.usage_percentage >= threshold * 100
    
    def has_sufficient_credits(self, required: int) -> bool:
        """Check if sufficient credits available."""
        return self.remaining_credits >= required


@dataclass
class CreditEstimate:
    """
    Credit cost estimate for a request.
    
    Requirements: 4.5
    """
    
    estimated_cost: int
    operation_type: str
    brain_mode: str
    estimated_tokens: int
    sufficient_credits: bool
    remaining_credits: int
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for API response."""
        return {
            'estimated_cost': self.estimated_cost,
            'operation_type': self.operation_type,
            'brain_mode': self.brain_mode,
            'estimated_tokens': self.estimated_tokens,
            'sufficient_credits': self.sufficient_credits,
            'remaining_credits': self.remaining_credits,
        }
