"""
Data classes for the AI service.

Defines AIResponse, AIConfig, and related structures for AI model interaction.

Requirements: 2.3, 4.2, 4.3, 4.4, 4.5
"""

from dataclasses import dataclass, field
from typing import List, Dict, Any, Optional
from enum import Enum
import json


class BlendMode(Enum):
    """
    Cognitive blend modes based on blend value ranges.
    
    Requirements: 4.3, 4.4, 4.5
    - 0-30%: AI_LOGIC - Pure AI logic with minimal personality mimicry
    - 31-70%: BALANCED - Balanced blend of user personality + AI reasoning
    - 71-100%: PERSONALITY_HEAVY - Heavy personality mimicry, requires confirmation
    """
    AI_LOGIC = "ai_logic"
    BALANCED = "balanced"
    PERSONALITY_HEAVY = "personality_heavy"
    
    @classmethod
    def from_blend_value(cls, blend: int) -> 'BlendMode':
        """
        Determine blend mode from blend value (0-100).
        
        Requirements: 4.3, 4.4, 4.5
        
        Args:
            blend: Cognitive blend value (0-100)
            
        Returns:
            BlendMode corresponding to the blend value
            
        Raises:
            ValueError: If blend is not between 0 and 100
        """
        if not 0 <= blend <= 100:
            raise ValueError(f"Blend must be between 0 and 100, got {blend}")
        
        if blend <= 30:
            return cls.AI_LOGIC
        elif blend <= 70:
            return cls.BALANCED
        else:
            return cls.PERSONALITY_HEAVY
    
    def requires_confirmation(self) -> bool:
        """
        Check if this blend mode requires user confirmation for actions.
        
        Requirements: 4.5
        
        Returns:
            True if confirmation is required (PERSONALITY_HEAVY mode)
        """
        return self == BlendMode.PERSONALITY_HEAVY
    
    def get_personality_weight(self, blend: int) -> float:
        """
        Get the personality weight for response generation.
        
        Args:
            blend: Cognitive blend value (0-100)
            
        Returns:
            Personality weight (0.0 - 1.0)
        """
        return blend / 100.0


class AIModel(Enum):
    """
    Available AI models for Twin.
    
    Requirements: 2.3, 18.2
    - Free tier: Cerebras, Gemini 2.5 Flash, Mistral
    - Paid tiers: Gemini 2.5 Pro, Gemini 3 Pro, Gemini 3.1 Pro
    """
    CEREBRAS = "cerebras"
    GEMINI_FLASH = "gemini-2.5-flash"
    GEMINI_PRO_25 = "gemini-2.5-pro"
    GEMINI_PRO_3 = "gemini-3-pro"
    GEMINI_PRO_31 = "gemini-3.1-pro"
    MISTRAL = "mistral"
    
    @classmethod
    def free_tier_models(cls) -> List['AIModel']:
        """Return models available on free tier."""
        return [cls.CEREBRAS, cls.GEMINI_FLASH, cls.MISTRAL]
    
    @classmethod
    def paid_tier_models(cls) -> List['AIModel']:
        """Return models available on paid tiers."""
        return [cls.GEMINI_PRO_25, cls.GEMINI_PRO_3, cls.GEMINI_PRO_31]
    
    @classmethod
    def is_valid_model(cls, model_value: str) -> bool:
        """Check if a model value is valid."""
        return model_value in [m.value for m in cls]
    
    def get_model_id(self) -> str:
        """Get the actual model ID for API calls."""
        model_mapping = {
            AIModel.CEREBRAS: "llama-3.3-70b",
            AIModel.GEMINI_FLASH: "gemini-2.5-flash",
            AIModel.GEMINI_PRO_25: "gemini-2.5-pro",
            AIModel.GEMINI_PRO_3: "gemini-3-pro",
            AIModel.GEMINI_PRO_31: "gemini-3.1-pro",
            AIModel.MISTRAL: "mistral-large",
        }
        return model_mapping.get(self, self.value)


@dataclass
class AIResponse:
    """
    Response from AI model generation.
    
    Contains the generated content along with metadata about
    the generation process.
    """
    content: str
    model_used: str
    tokens_used: int
    reasoning_chain: Optional[str] = None
    blend_mode: Optional[BlendMode] = None
    blend_value: Optional[int] = None
    requires_confirmation: bool = False
    metadata: Dict[str, Any] = field(default_factory=dict)
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for serialization."""
        return {
            'content': self.content,
            'model_used': self.model_used,
            'tokens_used': self.tokens_used,
            'reasoning_chain': self.reasoning_chain,
            'blend_mode': self.blend_mode.value if self.blend_mode else None,
            'blend_value': self.blend_value,
            'requires_confirmation': self.requires_confirmation,
            'metadata': self.metadata,
        }
    
    def to_json(self) -> str:
        """Serialize to JSON string."""
        return json.dumps(self.to_dict())
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'AIResponse':
        """Create from dictionary."""
        blend_mode = None
        if data.get('blend_mode'):
            blend_mode = BlendMode(data['blend_mode'])
        
        return cls(
            content=str(data.get('content', '')),
            model_used=str(data.get('model_used', '')),
            tokens_used=int(data.get('tokens_used', 0)),
            reasoning_chain=data.get('reasoning_chain'),
            blend_mode=blend_mode,
            blend_value=data.get('blend_value'),
            requires_confirmation=bool(data.get('requires_confirmation', False)),
            metadata=dict(data.get('metadata', {})),
        )


@dataclass
class AIConfig:
    """
    Configuration for AI service.
    
    Defines model settings and generation parameters.
    """
    default_model: AIModel = AIModel.GEMINI_FLASH
    max_tokens: int = 2048
    temperature: float = 0.7
    embedding_model: str = "text-embedding-004"
    embedding_dimension: int = 768
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary."""
        return {
            'default_model': self.default_model.value,
            'max_tokens': self.max_tokens,
            'temperature': self.temperature,
            'embedding_model': self.embedding_model,
            'embedding_dimension': self.embedding_dimension,
        }


@dataclass
class BlendedProfile:
    """
    CSM profile with cognitive blend applied.
    
    Contains the blended personality and tone settings
    ready for response generation.
    
    Requirements: 4.2, 4.3, 4.4, 4.5
    """
    mode: BlendMode
    blend_value: int
    personality_weight: float
    requires_confirmation: bool
    personality: Dict[str, float]
    tone: Dict[str, float]
    communication: Dict[str, str]
    decision_style: Dict[str, float]
    vocabulary_patterns: List[str]
    custom_rules: Dict[str, str]
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary."""
        return {
            'mode': self.mode.value,
            'blend_value': self.blend_value,
            'personality_weight': self.personality_weight,
            'requires_confirmation': self.requires_confirmation,
            'personality': self.personality,
            'tone': self.tone,
            'communication': self.communication,
            'decision_style': self.decision_style,
            'vocabulary_patterns': self.vocabulary_patterns,
            'custom_rules': self.custom_rules,
        }
    
    def get_system_prompt_additions(self) -> str:
        """
        Generate system prompt additions based on blended profile.
        
        Returns personality and tone instructions for the AI model.
        """
        lines = []
        
        # Add personality instructions based on blend mode
        if self.mode == BlendMode.AI_LOGIC:
            lines.append("Respond with clear, logical reasoning. Minimize personality mimicry.")
        elif self.mode == BlendMode.BALANCED:
            lines.append("Balance logical reasoning with the user's communication style.")
        else:  # PERSONALITY_HEAVY
            lines.append("Closely mimic the user's personality and communication patterns.")
        
        # Add tone instructions
        if self.tone.get('formality', 0.5) > 0.7:
            lines.append("Use formal language and professional tone.")
        elif self.tone.get('formality', 0.5) < 0.3:
            lines.append("Use casual, conversational language.")
        
        if self.tone.get('warmth', 0.5) > 0.7:
            lines.append("Be warm and friendly in responses.")
        
        if self.tone.get('directness', 0.5) > 0.7:
            lines.append("Be direct and concise.")
        elif self.tone.get('directness', 0.5) < 0.3:
            lines.append("Be diplomatic and considerate in phrasing.")
        
        if self.tone.get('humor_level', 0.3) > 0.5:
            lines.append("Include appropriate humor when suitable.")
        
        # Add communication preferences
        response_length = self.communication.get('response_length', 'moderate')
        if response_length == 'brief':
            lines.append("Keep responses brief and to the point.")
        elif response_length == 'detailed':
            lines.append("Provide detailed, comprehensive responses.")
        
        # Add vocabulary patterns if any
        if self.vocabulary_patterns:
            patterns = ', '.join(self.vocabulary_patterns[:5])
            lines.append(f"Incorporate these vocabulary patterns when appropriate: {patterns}")
        
        return '\n'.join(lines)
