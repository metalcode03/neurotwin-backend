"""
Data classes for the Learning Loop system.

Defines ExtractedFeatures, FeedbackType, and related structures
for the learning loop processing.

Requirements: 6.1, 6.2, 6.3, 6.4, 6.5
"""

from dataclasses import dataclass, field, asdict
from typing import List, Dict, Any, Optional
from datetime import datetime
from enum import Enum
import json


class FeedbackType(Enum):
    """
    Types of user feedback on Twin actions.
    
    Requirements: 6.4
    """
    POSITIVE = "positive"  # User approves the action/response
    NEGATIVE = "negative"  # User disapproves the action/response
    CORRECTION = "correction"  # User provides corrected version


class ActionCategory(Enum):
    """
    Categories of user actions for feature extraction.
    
    Requirements: 6.1
    """
    COMMUNICATION = "communication"  # Messages, emails, chats
    DECISION = "decision"  # Choices, approvals, rejections
    PREFERENCE = "preference"  # Settings, customizations
    INTERACTION = "interaction"  # UI interactions, navigation
    FEEDBACK = "feedback"  # Explicit feedback on Twin behavior


@dataclass
class ExtractedFeatures:
    """
    Features extracted from a user action for profile updating.
    
    Requirements: 6.1, 6.2
    """
    
    action_type: str  # The type of action performed
    category: ActionCategory = ActionCategory.INTERACTION
    context: Dict[str, Any] = field(default_factory=dict)
    patterns: List[str] = field(default_factory=list)
    sentiment: float = 0.0  # -1.0 to 1.0
    confidence: float = 1.0  # 0.0 to 1.0, how confident we are in extraction
    
    # Extracted profile update suggestions
    personality_signals: Dict[str, float] = field(default_factory=dict)
    tone_signals: Dict[str, float] = field(default_factory=dict)
    vocabulary_additions: List[str] = field(default_factory=list)
    decision_signals: Dict[str, float] = field(default_factory=dict)
    
    def __post_init__(self):
        """Validate extracted features."""
        if not -1.0 <= self.sentiment <= 1.0:
            raise ValueError(f"sentiment must be between -1.0 and 1.0, got {self.sentiment}")
        if not 0.0 <= self.confidence <= 1.0:
            raise ValueError(f"confidence must be between 0.0 and 1.0, got {self.confidence}")
        if isinstance(self.category, str):
            self.category = ActionCategory(self.category)
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for JSON serialization."""
        return {
            'action_type': self.action_type,
            'category': self.category.value,
            'context': self.context,
            'patterns': self.patterns,
            'sentiment': self.sentiment,
            'confidence': self.confidence,
            'personality_signals': self.personality_signals,
            'tone_signals': self.tone_signals,
            'vocabulary_additions': self.vocabulary_additions,
            'decision_signals': self.decision_signals,
        }
    
    def to_json(self) -> str:
        """Serialize to JSON string."""
        return json.dumps(self.to_dict())
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'ExtractedFeatures':
        """Create from dictionary."""
        category = data.get('category', 'interaction')
        if isinstance(category, str):
            category = ActionCategory(category)
        
        return cls(
            action_type=str(data.get('action_type', 'unknown')),
            category=category,
            context=dict(data.get('context', {})),
            patterns=list(data.get('patterns', [])),
            sentiment=float(data.get('sentiment', 0.0)),
            confidence=float(data.get('confidence', 1.0)),
            personality_signals=dict(data.get('personality_signals', {})),
            tone_signals=dict(data.get('tone_signals', {})),
            vocabulary_additions=list(data.get('vocabulary_additions', [])),
            decision_signals=dict(data.get('decision_signals', {})),
        )
    
    @classmethod
    def from_json(cls, json_str: str) -> 'ExtractedFeatures':
        """Deserialize from JSON string."""
        data = json.loads(json_str)
        return cls.from_dict(data)


@dataclass
class ProfileUpdateResult:
    """
    Result of applying extracted features to a CSM profile.
    
    Requirements: 6.2, 6.3
    """
    
    success: bool
    updated_fields: List[str] = field(default_factory=list)
    new_version: Optional[int] = None
    error: Optional[str] = None
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary."""
        return {
            'success': self.success,
            'updated_fields': self.updated_fields,
            'new_version': self.new_version,
            'error': self.error,
        }


@dataclass
class FeedbackResult:
    """
    Result of applying user feedback.
    
    Requirements: 6.4
    """
    
    success: bool
    reinforcement_applied: bool = False
    correction_applied: bool = False
    profile_updated: bool = False
    error: Optional[str] = None
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary."""
        return {
            'success': self.success,
            'reinforcement_applied': self.reinforcement_applied,
            'correction_applied': self.correction_applied,
            'profile_updated': self.profile_updated,
            'error': self.error,
        }


@dataclass
class UserAction:
    """
    Represents a user action to be processed by the learning loop.
    
    Requirements: 6.1
    """
    
    action_type: str
    content: str = ""
    context: Dict[str, Any] = field(default_factory=dict)
    metadata: Dict[str, Any] = field(default_factory=dict)
    timestamp: Optional[datetime] = None
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary."""
        return {
            'action_type': self.action_type,
            'content': self.content,
            'context': self.context,
            'metadata': self.metadata,
            'timestamp': self.timestamp.isoformat() if self.timestamp else None,
        }
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'UserAction':
        """Create from dictionary."""
        timestamp = data.get('timestamp')
        if isinstance(timestamp, str):
            timestamp = datetime.fromisoformat(timestamp)
        
        return cls(
            action_type=str(data.get('action_type', 'unknown')),
            content=str(data.get('content', '')),
            context=dict(data.get('context', {})),
            metadata=dict(data.get('metadata', {})),
            timestamp=timestamp,
        )
