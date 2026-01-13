"""
Core AI module for NeuroTwin platform.

Provides centralized AI model interaction including:
- Response generation with CSM and blend application
- Feature extraction for learning
- Embedding generation for memory

Requirements: 2.3, 4.2, 5.2, 6.1
"""

from .dataclasses import AIResponse, AIConfig, BlendMode
from .services import AIService

__all__ = [
    'AIResponse',
    'AIConfig',
    'BlendMode',
    'AIService',
]
