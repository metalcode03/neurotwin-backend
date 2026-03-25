"""
Data classes for Twin app.

Defines AIModel enum and QuestionnaireResponse dataclass for Twin creation.
Requirements: 2.1, 2.3
"""

from dataclasses import dataclass, field
from typing import Dict, Any, List
from enum import Enum


class AIModel(Enum):
    """
    Available AI models for Twin.
    
    Requirements: 2.3
    - Free tier: Gemini-3 Flash, Qwen, Mistral
    - Paid tiers: Gemini-3 Pro
    """
    
    GEMINI_FLASH = "gemini-3-flash"
    QWEN = "qwen"
    MISTRAL = "mistral"
    GEMINI_PRO = "gemini-3-pro"
    
    @classmethod
    def free_tier_models(cls) -> List['AIModel']:
        """Return models available on free tier."""
        return [cls.GEMINI_FLASH, cls.QWEN, cls.MISTRAL]
    
    @classmethod
    def paid_tier_models(cls) -> List['AIModel']:
        """Return models available on paid tiers."""
        return [cls.GEMINI_PRO]
    
    @classmethod
    def all_models(cls) -> List['AIModel']:
        """Return all available models."""
        return list(cls)
    
    @classmethod
    def is_valid_model(cls, model_value: str) -> bool:
        """Check if a model value is valid."""
        return model_value in [m.value for m in cls]


@dataclass
class QuestionnaireResponse:
    """
    Response data from the onboarding questionnaire.
    
    Used to generate initial CSM profile during Twin creation.
    Requirements: 2.1, 2.2
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
    
    def is_complete(self) -> bool:
        """
        Check if the questionnaire response has minimum required data.
        
        Returns True if all three sections have at least some data.
        This is a lenient check - we just need non-empty dictionaries.
        """
        has_comm = bool(self.communication_style and len(self.communication_style) > 0)
        has_decision = bool(self.decision_patterns and len(self.decision_patterns) > 0)
        has_prefs = bool(self.preferences and len(self.preferences) > 0)
        
        return has_comm and has_decision and has_prefs


@dataclass
class OnboardingQuestionnaire:
    """
    The cognitive questionnaire presented during Twin creation.
    
    Requirements: 2.1
    """
    
    sections: List[Dict[str, Any]] = field(default_factory=list)
    
    @classmethod
    def get_default_questionnaire(cls) -> 'OnboardingQuestionnaire':
        """
        Return the default onboarding questionnaire.
        
        Covers communication style, decision patterns, and preferences.
        """
        return cls(sections=[
            {
                'id': 'communication_style',
                'title': 'Communication Style',
                'description': 'Help us understand how you communicate',
                'questions': [
                    {
                        'id': 'openness',
                        'text': 'How open are you to new ideas and experiences?',
                        'type': 'slider',
                        'min': 0.0,
                        'max': 1.0,
                        'default': 0.5,
                    },
                    {
                        'id': 'extraversion',
                        'text': 'How energized do you feel in social situations?',
                        'type': 'slider',
                        'min': 0.0,
                        'max': 1.0,
                        'default': 0.5,
                    },
                    {
                        'id': 'agreeableness',
                        'text': 'How important is harmony in your interactions?',
                        'type': 'slider',
                        'min': 0.0,
                        'max': 1.0,
                        'default': 0.5,
                    },
                    {
                        'id': 'formality',
                        'text': 'How formal is your communication style?',
                        'type': 'slider',
                        'min': 0.0,
                        'max': 1.0,
                        'default': 0.5,
                    },
                    {
                        'id': 'warmth',
                        'text': 'How warm and friendly is your tone?',
                        'type': 'slider',
                        'min': 0.0,
                        'max': 1.0,
                        'default': 0.5,
                    },
                    {
                        'id': 'directness',
                        'text': 'How direct are you in your communication?',
                        'type': 'slider',
                        'min': 0.0,
                        'max': 1.0,
                        'default': 0.5,
                    },
                    {
                        'id': 'preferred_greeting',
                        'text': 'What is your preferred greeting?',
                        'type': 'text',
                        'default': 'Hello',
                    },
                    {
                        'id': 'sign_off_style',
                        'text': 'How do you typically sign off messages?',
                        'type': 'text',
                        'default': 'Best regards',
                    },
                ],
            },
            {
                'id': 'decision_patterns',
                'title': 'Decision Making',
                'description': 'Help us understand how you make decisions',
                'questions': [
                    {
                        'id': 'conscientiousness',
                        'text': 'How organized and detail-oriented are you?',
                        'type': 'slider',
                        'min': 0.0,
                        'max': 1.0,
                        'default': 0.5,
                    },
                    {
                        'id': 'risk_tolerance',
                        'text': 'How comfortable are you with taking risks?',
                        'type': 'slider',
                        'min': 0.0,
                        'max': 1.0,
                        'default': 0.5,
                    },
                    {
                        'id': 'speed_vs_accuracy',
                        'text': 'Do you prefer quick decisions or thorough analysis?',
                        'type': 'slider',
                        'min': 0.0,
                        'max': 1.0,
                        'default': 0.5,
                    },
                    {
                        'id': 'collaboration_preference',
                        'text': 'Do you prefer working independently or collaboratively?',
                        'type': 'slider',
                        'min': 0.0,
                        'max': 1.0,
                        'default': 0.5,
                    },
                ],
            },
            {
                'id': 'preferences',
                'title': 'Personal Preferences',
                'description': 'Help us understand your preferences',
                'questions': [
                    {
                        'id': 'neuroticism',
                        'text': 'How sensitive are you to stress?',
                        'type': 'slider',
                        'min': 0.0,
                        'max': 1.0,
                        'default': 0.5,
                    },
                    {
                        'id': 'humor_level',
                        'text': 'How much humor do you like in communication?',
                        'type': 'slider',
                        'min': 0.0,
                        'max': 1.0,
                        'default': 0.3,
                    },
                    {
                        'id': 'response_length',
                        'text': 'What length of responses do you prefer?',
                        'type': 'select',
                        'options': ['brief', 'moderate', 'detailed'],
                        'default': 'moderate',
                    },
                    {
                        'id': 'emoji_usage',
                        'text': 'How often do you use emojis?',
                        'type': 'select',
                        'options': ['none', 'minimal', 'moderate', 'frequent'],
                        'default': 'minimal',
                    },
                    {
                        'id': 'vocabulary_patterns',
                        'text': 'What words or phrases do you commonly use?',
                        'type': 'text_list',
                        'default': [],
                        'required': False,
                    },
                ],
            },
        ])
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for API response."""
        return {
            'sections': self.sections,
        }
