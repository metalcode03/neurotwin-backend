"""
Data classes for Cognitive Signature Model (CSM).

These dataclasses define the structured profile storing personality,
tone, habits, and decision patterns.

Requirements: 4.1
"""

from dataclasses import dataclass, field, asdict
from typing import List, Dict, Any, Optional
from datetime import datetime
import json


@dataclass
class PersonalityTraits:
    """
    Big Five personality traits model.
    
    All values are floats between 0.0 and 1.0.
    Requirements: 4.1
    """
    
    openness: float = 0.5  # 0.0 = conventional, 1.0 = inventive
    conscientiousness: float = 0.5  # 0.0 = careless, 1.0 = organized
    extraversion: float = 0.5  # 0.0 = introverted, 1.0 = extraverted
    agreeableness: float = 0.5  # 0.0 = challenging, 1.0 = friendly
    neuroticism: float = 0.5  # 0.0 = confident, 1.0 = nervous
    
    def __post_init__(self):
        """Validate all values are within bounds."""
        for attr in ['openness', 'conscientiousness', 'extraversion', 
                     'agreeableness', 'neuroticism']:
            value = getattr(self, attr)
            if not 0.0 <= value <= 1.0:
                raise ValueError(f"{attr} must be between 0.0 and 1.0, got {value}")
    
    def to_dict(self) -> Dict[str, float]:
        """Convert to dictionary."""
        return asdict(self)
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'PersonalityTraits':
        """Create from dictionary."""
        return cls(
            openness=float(data.get('openness', 0.5)),
            conscientiousness=float(data.get('conscientiousness', 0.5)),
            extraversion=float(data.get('extraversion', 0.5)),
            agreeableness=float(data.get('agreeableness', 0.5)),
            neuroticism=float(data.get('neuroticism', 0.5)),
        )


@dataclass
class TonePreferences:
    """
    Communication tone preferences.
    
    All values are floats between 0.0 and 1.0.
    Requirements: 4.1
    """
    
    formality: float = 0.5  # 0.0 = casual, 1.0 = formal
    warmth: float = 0.5  # 0.0 = distant, 1.0 = warm
    directness: float = 0.5  # 0.0 = indirect, 1.0 = direct
    humor_level: float = 0.3  # 0.0 = serious, 1.0 = humorous
    
    def __post_init__(self):
        """Validate all values are within bounds."""
        for attr in ['formality', 'warmth', 'directness', 'humor_level']:
            value = getattr(self, attr)
            if not 0.0 <= value <= 1.0:
                raise ValueError(f"{attr} must be between 0.0 and 1.0, got {value}")
    
    def to_dict(self) -> Dict[str, float]:
        """Convert to dictionary."""
        return asdict(self)
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'TonePreferences':
        """Create from dictionary."""
        return cls(
            formality=float(data.get('formality', 0.5)),
            warmth=float(data.get('warmth', 0.5)),
            directness=float(data.get('directness', 0.5)),
            humor_level=float(data.get('humor_level', 0.3)),
        )


@dataclass
class CommunicationHabits:
    """
    Communication style and habits.
    
    Requirements: 4.1
    """
    
    preferred_greeting: str = "Hello"
    sign_off_style: str = "Best regards"
    response_length: str = "moderate"  # "brief", "moderate", "detailed"
    emoji_usage: str = "minimal"  # "none", "minimal", "moderate", "frequent"
    
    VALID_RESPONSE_LENGTHS = ("brief", "moderate", "detailed")
    VALID_EMOJI_USAGE = ("none", "minimal", "moderate", "frequent")
    
    def __post_init__(self):
        """Validate enum-like fields."""
        if self.response_length not in self.VALID_RESPONSE_LENGTHS:
            raise ValueError(
                f"response_length must be one of {self.VALID_RESPONSE_LENGTHS}, "
                f"got {self.response_length}"
            )
        if self.emoji_usage not in self.VALID_EMOJI_USAGE:
            raise ValueError(
                f"emoji_usage must be one of {self.VALID_EMOJI_USAGE}, "
                f"got {self.emoji_usage}"
            )
    
    def to_dict(self) -> Dict[str, str]:
        """Convert to dictionary."""
        return asdict(self)
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'CommunicationHabits':
        """Create from dictionary."""
        return cls(
            preferred_greeting=str(data.get('preferred_greeting', 'Hello')),
            sign_off_style=str(data.get('sign_off_style', 'Best regards')),
            response_length=str(data.get('response_length', 'moderate')),
            emoji_usage=str(data.get('emoji_usage', 'minimal')),
        )


@dataclass
class DecisionStyle:
    """
    Decision-making style preferences.
    
    All values are floats between 0.0 and 1.0.
    Requirements: 4.1
    """
    
    risk_tolerance: float = 0.5  # 0.0 = conservative, 1.0 = aggressive
    speed_vs_accuracy: float = 0.5  # 0.0 = thorough, 1.0 = quick
    collaboration_preference: float = 0.5  # 0.0 = independent, 1.0 = collaborative
    
    def __post_init__(self):
        """Validate all values are within bounds."""
        for attr in ['risk_tolerance', 'speed_vs_accuracy', 'collaboration_preference']:
            value = getattr(self, attr)
            if not 0.0 <= value <= 1.0:
                raise ValueError(f"{attr} must be between 0.0 and 1.0, got {value}")
    
    def to_dict(self) -> Dict[str, float]:
        """Convert to dictionary."""
        return asdict(self)
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'DecisionStyle':
        """Create from dictionary."""
        return cls(
            risk_tolerance=float(data.get('risk_tolerance', 0.5)),
            speed_vs_accuracy=float(data.get('speed_vs_accuracy', 0.5)),
            collaboration_preference=float(data.get('collaboration_preference', 0.5)),
        )


@dataclass
class CSMProfileData:
    """
    Complete CSM profile data structure.
    
    This is the structured data stored in the JSONB profile_data field.
    Requirements: 4.1, 4.6
    """
    
    personality: PersonalityTraits = field(default_factory=PersonalityTraits)
    tone: TonePreferences = field(default_factory=TonePreferences)
    vocabulary_patterns: List[str] = field(default_factory=list)
    communication: CommunicationHabits = field(default_factory=CommunicationHabits)
    decision_style: DecisionStyle = field(default_factory=DecisionStyle)
    custom_rules: Dict[str, str] = field(default_factory=dict)
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for JSON serialization."""
        return {
            'personality': self.personality.to_dict(),
            'tone': self.tone.to_dict(),
            'vocabulary_patterns': self.vocabulary_patterns,
            'communication': self.communication.to_dict(),
            'decision_style': self.decision_style.to_dict(),
            'custom_rules': self.custom_rules,
        }
    
    def to_json(self) -> str:
        """
        Serialize CSM profile data to JSON string.
        
        Requirements: 4.6
        """
        return json.dumps(self.to_dict(), indent=2)
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'CSMProfileData':
        """Create from dictionary."""
        return cls(
            personality=PersonalityTraits.from_dict(data.get('personality', {})),
            tone=TonePreferences.from_dict(data.get('tone', {})),
            vocabulary_patterns=list(data.get('vocabulary_patterns', [])),
            communication=CommunicationHabits.from_dict(data.get('communication', {})),
            decision_style=DecisionStyle.from_dict(data.get('decision_style', {})),
            custom_rules=dict(data.get('custom_rules', {})),
        )
    
    @classmethod
    def from_json(cls, json_str: str) -> 'CSMProfileData':
        """
        Deserialize CSM profile data from JSON string.
        
        Requirements: 4.6
        """
        data = json.loads(json_str)
        return cls.from_dict(data)


@dataclass
class QuestionnaireResponse:
    """
    Response data from the onboarding questionnaire.
    
    Used to generate initial CSM profile.
    Requirements: 2.2, 4.1
    """
    
    communication_style: Dict[str, Any] = field(default_factory=dict)
    decision_patterns: Dict[str, Any] = field(default_factory=dict)
    preferences: Dict[str, Any] = field(default_factory=dict)
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary."""
        return {
            'communication_style': self.communication_style,
            'decision_patterns': self.decision_patterns,
            'preferences': self.preferences,
        }
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'QuestionnaireResponse':
        """Create from dictionary."""
        return cls(
            communication_style=dict(data.get('communication_style', {})),
            decision_patterns=dict(data.get('decision_patterns', {})),
            preferences=dict(data.get('preferences', {})),
        )
