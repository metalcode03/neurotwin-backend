"""
AI Provider abstraction layer.

This module provides the abstract base class and concrete implementations
for AI model providers (Cerebras, Gemini, Mistral), as well as the
provider registry for dynamic lookup.

Requirements: 8.1-8.10
"""

from apps.credits.providers.base import AIProvider
from apps.credits.providers.cerebras import CerebrasService
from apps.credits.providers.gemini import GeminiService
from apps.credits.providers.mistral import MistralService
from apps.credits.providers.registry import ProviderRegistry, get_registry

__all__ = [
    'AIProvider',
    'CerebrasService',
    'GeminiService',
    'MistralService',
    'ProviderRegistry',
    'get_registry',
]
