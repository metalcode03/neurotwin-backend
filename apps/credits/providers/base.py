"""
AIProvider abstract base class.

Defines the interface that all AI provider implementations must follow.
This abstraction enables consistent error handling, logging, and easy
provider swapping without changing dependent code.

Requirements: 8.1, 8.5, 8.6
"""

from abc import ABC, abstractmethod
from typing import List, Optional, Dict, Any
import logging

from apps.credits.dataclasses import ProviderResponse


logger = logging.getLogger(__name__)


class AIProvider(ABC):
    """
    Abstract base class for AI model providers.
    
    All provider implementations (Cerebras, Gemini, Mistral) must extend
    this class and implement the abstract methods. This ensures consistent
    interfaces across all providers and enables the ModelRouter to interact
    with providers without knowing implementation details.
    
    Requirements:
    - 8.1: Define AIProvider abstract base class with generate_response and generate_embeddings methods
    - 8.5: Enforce consistent error handling across all implementations
    - 8.6: Enforce consistent logging format across all implementations
    """
    
    @abstractmethod
    def generate_response(
        self,
        messages: List[dict],
        max_tokens: int = 1000,
        temperature: float = 0.7
    ) -> ProviderResponse:
        """
        Generate AI response for the given messages.
        
        Args:
            messages: List of message dictionaries with 'role' and 'content' keys.
                     Example: [
                         {"role": "system", "content": "You are a helpful assistant"},
                         {"role": "user", "content": "Hello"}
                     ]
                     Supported roles: system, user, assistant
            max_tokens: Maximum number of tokens to generate (default: 1000)
            temperature: Sampling temperature for response generation (0.0-1.0, default: 0.7)
        
        Returns:
            ProviderResponse: Standardized response containing content, tokens_used,
                            model_used, latency_ms, and metadata
        
        Raises:
            ProviderAPIError: When the provider API returns an error
            ProviderTimeoutError: When the request times out
            ProviderAuthError: When authentication fails
            ProviderRateLimitError: When rate limit is exceeded
        
        Requirements: 8.1
        
        Note:
            Each provider implementation must translate the messages format
            into its own API-specific format. For example:
            - OpenAI-style APIs (Mistral, Cerebras): Pass messages directly
            - Gemini: Convert messages to a single formatted string
        """
        pass
    
    @abstractmethod
    def generate_embeddings(self, text: str) -> List[float]:
        """
        Generate vector embeddings for the given text.
        
        Args:
            text: The text to generate embeddings for
        
        Returns:
            List[float]: Vector embedding representation of the text
        
        Raises:
            ProviderAPIError: When the provider API returns an error
            ProviderTimeoutError: When the request times out
            ProviderAuthError: When authentication fails
        
        Requirements: 8.1
        """
        pass
    
    @abstractmethod
    def estimate_tokens(self, text: str) -> int:
        """
        Estimate the number of tokens in the given text.
        
        This is used for credit cost estimation before making actual API calls.
        Implementations should use provider-specific tokenization logic or
        approximations based on character/word count.
        
        Args:
            text: The text to estimate tokens for
        
        Returns:
            int: Estimated number of tokens
        
        Requirements: 8.1
        """
        pass
    
    def _log_request(
        self,
        operation: str,
        prompt_length: int,
        response_length: Optional[int] = None,
        latency_ms: Optional[int] = None,
        error: Optional[Exception] = None
    ) -> None:
        """
        Log provider request with consistent format.
        
        This method enforces consistent logging across all provider implementations.
        All providers should call this method for request logging.
        
        Args:
            operation: The operation being performed (e.g., 'generate_response', 'generate_embeddings')
            prompt_length: Length of the input prompt in characters
            response_length: Length of the response in characters (if successful)
            latency_ms: Request latency in milliseconds (if successful)
            error: Exception object if request failed
        
        Requirements: 8.6
        """
        provider_name = self.__class__.__name__
        
        if error:
            logger.error(
                f"[{provider_name}] {operation} failed | "
                f"prompt_length={prompt_length} | "
                f"error={error.__class__.__name__}: {str(error)}"
            )
        else:
            logger.info(
                f"[{provider_name}] {operation} succeeded | "
                f"prompt_length={prompt_length} | "
                f"response_length={response_length} | "
                f"latency_ms={latency_ms}"
            )
    
    def _sanitize_prompt(self, prompt: str, max_log_length: int = 200) -> str:
        """
        Sanitize prompt for logging by removing PII and truncating.
        
        This method helps enforce consistent PII handling across providers.
        Implementations should call this before logging prompts.
        
        Args:
            prompt: The prompt to sanitize
            max_log_length: Maximum length of sanitized prompt for logging
        
        Returns:
            str: Sanitized and truncated prompt safe for logging
        
        Requirements: 8.6
        """
        # Truncate long prompts
        if len(prompt) > max_log_length:
            sanitized = prompt[:max_log_length] + "..."
        else:
            sanitized = prompt
        
        # Basic PII patterns to redact (email, phone numbers)
        # Note: This is a simple implementation. Production systems should use
        # more sophisticated PII detection libraries.
        import re
        
        # Redact email addresses
        sanitized = re.sub(
            r'\b[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Z|a-z]{2,}\b',
            '[EMAIL]',
            sanitized
        )
        
        # Redact phone numbers (basic patterns)
        sanitized = re.sub(
            r'\b\d{3}[-.]?\d{3}[-.]?\d{4}\b',
            '[PHONE]',
            sanitized
        )
        
        return sanitized
    
    def _handle_error(self, error: Exception, operation: str) -> None:
        """
        Handle provider errors with consistent error handling.
        
        This method enforces consistent error handling across all provider implementations.
        Providers should call this method when catching exceptions.
        
        Args:
            error: The exception that occurred
            operation: The operation that failed
        
        Requirements: 8.5
        """
        from apps.credits.exceptions import (
            ProviderAPIError,
            ProviderTimeoutError,
            ProviderAuthError,
            ProviderRateLimitError
        )
        
        provider_name = self.__class__.__name__
        
        # Log the error
        logger.error(
            f"[{provider_name}] {operation} error: {error.__class__.__name__}: {str(error)}",
            exc_info=True
        )
        
        # Re-raise with provider context if not already a provider exception
        if not isinstance(error, (
            ProviderAPIError,
            ProviderTimeoutError,
            ProviderAuthError,
            ProviderRateLimitError
        )):
            raise ProviderAPIError(
                f"{provider_name} {operation} failed: {str(error)}"
            ) from error
        
        # Re-raise provider exceptions as-is
        raise error
