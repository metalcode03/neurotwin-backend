"""
Enums for credit-based AI architecture.

Defines BrainMode and OperationType enums for intelligent model routing.
Requirements: 3.1, 5.1
"""

from enum import Enum
from typing import List


class BrainMode(Enum):
    """
    User-facing AI intelligence level abstraction.
    
    Requirements: 5.1
    - BRAIN: Default mode - fast and efficient (FREE tier+)
    - BRAIN_PRO: Advanced mode - higher reasoning (PRO tier+)
    - BRAIN_GEN: Genius mode - maximum intelligence (EXECUTIVE tier)
    """
    
    BRAIN = "brain"
    BRAIN_PRO = "brain_pro"
    BRAIN_GEN = "brain_gen"
    
    @classmethod
    def all_modes(cls) -> List['BrainMode']:
        """Return all available brain modes."""
        return list(cls)
    
    @classmethod
    def is_valid_mode(cls, mode_value: str) -> bool:
        """Check if a brain mode value is valid."""
        return mode_value in [m.value for m in cls]
    
    @classmethod
    def from_string(cls, mode_value: str) -> 'BrainMode':
        """
        Convert string to BrainMode enum.
        
        Raises ValueError if mode_value is invalid.
        """
        for mode in cls:
            if mode.value == mode_value:
                return mode
        raise ValueError(f"Invalid brain mode: {mode_value}")
    
    def get_display_name(self) -> str:
        """Get user-friendly display name."""
        display_names = {
            self.BRAIN: "Brain - Balanced",
            self.BRAIN_PRO: "Brain Pro - Advanced",
            self.BRAIN_GEN: "Brain Gen - Genius",
        }
        return display_names[self]
    
    def get_description(self) -> str:
        """Get mode description."""
        descriptions = {
            self.BRAIN: "Fast and efficient",
            self.BRAIN_PRO: "Higher reasoning quality",
            self.BRAIN_GEN: "Maximum intelligence",
        }
        return descriptions[self]


class OperationType(Enum):
    """
    Classification of AI request complexity.
    
    Requirements: 3.1
    Used for credit cost calculation and model routing.
    """
    
    SIMPLE_RESPONSE = "simple_response"
    LONG_RESPONSE = "long_response"
    SUMMARIZATION = "summarization"
    COMPLEX_REASONING = "complex_reasoning"
    AUTOMATION = "automation"
    
    @classmethod
    def all_types(cls) -> List['OperationType']:
        """Return all available operation types."""
        return list(cls)
    
    @classmethod
    def is_valid_type(cls, type_value: str) -> bool:
        """Check if an operation type value is valid."""
        return type_value in [t.value for t in cls]
    
    @classmethod
    def from_string(cls, type_value: str) -> 'OperationType':
        """
        Convert string to OperationType enum.
        
        Raises ValueError if type_value is invalid.
        """
        for op_type in cls:
            if op_type.value == type_value:
                return op_type
        raise ValueError(f"Invalid operation type: {type_value}")
    
    def get_display_name(self) -> str:
        """Get user-friendly display name."""
        display_names = {
            self.SIMPLE_RESPONSE: "Simple Response",
            self.LONG_RESPONSE: "Long Response",
            self.SUMMARIZATION: "Summarization",
            self.COMPLEX_REASONING: "Complex Reasoning",
            self.AUTOMATION: "Automation",
        }
        return display_names[self]
