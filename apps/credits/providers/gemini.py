"""
GeminiService provider implementation.

Integrates Google Gemini API for AI inference across Brain modes.
Supports multiple Gemini model versions with unified interface.

Requirements: 8.3, 8.4
"""

import os
import time
import logging
import threading
from typing import List, Optional, Dict, Set
from datetime import datetime

from google import genai
from google.genai.types import HttpOptions

from apps.credits.providers.base import AIProvider
from apps.credits.dataclasses import ProviderResponse
from apps.credits.exceptions import (
    ProviderAPIError,
    ProviderTimeoutError,
    ProviderAuthError,
    ProviderRateLimitError,
)


logger = logging.getLogger(__name__)


class GeminiService(AIProvider):
    """
    Google Gemini API provider implementation.
    
    Provides AI inference for Brain, Brain Pro, and Brain Gen modes.
    Supports multiple Gemini model versions through model parameter.
    
    Requirements:
    - 8.3: Implement Gemini_Service extending AIProvider
    - 8.4: Support model parameter for Gemini 2.5 Flash, 2.5 Pro, 3 Pro, 3.1 Pro
    """
    
    # Model mapping: external name -> preferred API model names (in priority order)
    # The system will try each model in order until one works
    SUPPORTED_MODELS = {
        'gemini-2.5-flash': ['gemini-2.5-flash', 'gemini-2.0-flash', 'gemini-1.5-flash'],
        'gemini-2.5-pro': ['gemini-2.5-pro', 'gemini-1.5-pro'],
        'gemini-3-pro': ['gemini-3-pro-preview', 'gemini-2.5-pro', 'gemini-1.5-pro'],
        'gemini-3.1-pro': ['gemini-3.1-pro-preview', 'gemini-3-pro-preview', 'gemini-2.5-pro'],
    }
    
    # Cache for available models (class-level to share across instances)
    _available_models_cache: Optional[Set[str]] = None
    _cache_timestamp: Optional[float] = None
    _cache_ttl: int = 3600  # Cache for 1 hour
    
    # Singleton client instance (shared across all instances)
    _client_instance: Optional[genai.Client] = None
    _client_lock = threading.Lock()
    
    def __init__(self, model: str = "gemini-2.5-flash"):
        """
        Initialize Gemini service with API configuration.
        
        Args:
            model: Gemini model identifier (default: gemini-2.5-flash)
                   Supported: gemini-2.5-flash, gemini-2.5-pro, 
                             gemini-3-pro, gemini-3.1-pro
        
        Raises:
            ValueError: If model is not supported
        
        Requirements: 8.3, 8.4
        """
        if model not in self.SUPPORTED_MODELS:
            raise ValueError(
                f"Unsupported model: {model}. "
                f"Supported models: {', '.join(self.SUPPORTED_MODELS.keys())}"
            )
        
        self.model = model
        self.api_model_candidates = self.SUPPORTED_MODELS[model]
        self.api_key = os.getenv('GOOGLE_API_KEY', '')
        
        if not self.api_key:
            logger.warning("GOOGLE_API_KEY not found in environment variables")
        
        # Use singleton client instance (OPTIMIZATION: avoid repeated initialization)
        self.client = self._get_or_create_client()
        
        # Determine which model to actually use (with caching)
        self.api_model_id = self._select_available_model()
        
        # OPTIMIZATION: Reduced timeout from 30s to 10s for faster failure
        self.timeout = 10
        # OPTIMIZATION: Reduced retries from 3 to 2
        self.max_retries = 2
    
    @classmethod
    def _get_or_create_client(cls) -> Optional[genai.Client]:
        """
        Get or create singleton Gemini client instance.
        
        OPTIMIZATION: Reuses client across all instances to avoid repeated initialization.
        Thread-safe using lock.
        
        Returns:
            genai.Client instance or None if initialization fails
        """
        if cls._client_instance is not None:
            return cls._client_instance
        
        with cls._client_lock:
            # Double-check after acquiring lock
            if cls._client_instance is not None:
                return cls._client_instance
            
            api_key = os.getenv('GOOGLE_API_KEY', '')
            if not api_key:
                logger.warning("GOOGLE_API_KEY not found, client not initialized")
                return None
            
            try:
                cls._client_instance = genai.Client(
                    api_key=api_key,
                    http_options=HttpOptions(api_version='v1')
                )
                logger.info("[GeminiService] Initialized singleton client with API v1")
                return cls._client_instance
            except Exception as e:
                logger.error(f"Failed to initialize Gemini client: {str(e)}")
                return None
    
    def _select_available_model(self) -> str:
        """
        Select the first available model from candidates.
        
        Queries the API to get available models and selects the first
        candidate that exists and supports generateContent.
        
        Returns:
            str: Selected model name
        
        Raises:
            ProviderAPIError: If no suitable model is found
        """
        if not self.client:
            # Fallback to first candidate if client not initialized
            logger.warning(
                f"[GeminiService] Client not initialized, using first candidate: "
                f"{self.api_model_candidates[0]}"
            )
            return self.api_model_candidates[0]
        
        try:
            # Get available models (with caching)
            available_models = self._get_available_models()
            
            # Try each candidate in order
            for candidate in self.api_model_candidates:
                if candidate in available_models:
                    logger.info(
                        f"[GeminiService] Selected model '{candidate}' for {self.model}"
                    )
                    return candidate
            
            # No exact match found, log available models and use first candidate
            logger.warning(
                f"[GeminiService] None of the candidates {self.api_model_candidates} "
                f"found in available models. Available models: {list(available_models)[:10]}. "
                f"Using first candidate: {self.api_model_candidates[0]}"
            )
            return self.api_model_candidates[0]
        
        except Exception as e:
            logger.warning(
                f"[GeminiService] Failed to query available models: {str(e)}. "
                f"Using first candidate: {self.api_model_candidates[0]}"
            )
            return self.api_model_candidates[0]
    
    def _get_available_models(self) -> Set[str]:
        """
        Get list of available models from Gemini API with caching.
        
        Returns:
            Set[str]: Set of available model names that support generateContent
        """
        # Check cache
        current_time = time.time()
        if (
            self._available_models_cache is not None 
            and self._cache_timestamp is not None
            and (current_time - self._cache_timestamp) < self._cache_ttl
        ):
            return self._available_models_cache
        
        try:
            # List all models
            models_response = self.client.models.list()
            
            available_models = set()
            for model in models_response:
                # Extract model name (remove 'models/' prefix if present)
                model_name = model.name
                if model_name.startswith('models/'):
                    model_name = model_name.replace('models/', '')
                
                # Check if model supports generateContent
                if hasattr(model, 'supported_generation_methods'):
                    if 'generateContent' in model.supported_generation_methods:
                        available_models.add(model_name)
                else:
                    # If no method info, assume it supports generateContent
                    available_models.add(model_name)
            
            # Update cache
            GeminiService._available_models_cache = available_models
            GeminiService._cache_timestamp = current_time
            
            logger.info(
                f"[GeminiService] Cached {len(available_models)} available models: "
                f"{list(available_models)[:10]}"
            )
            
            return available_models
        
        except Exception as e:
            logger.error(f"[GeminiService] Failed to list models: {str(e)}")
            # Return empty set on error
            return set()
    
    def generate_response(
        self,
        messages: List[dict],
        max_tokens: int = 1000,
        temperature: float = 0.7
    ) -> ProviderResponse:
        """
        Generate AI response using Gemini API.
        
        Implements retry logic with exponential backoff for rate limits.
        Logs all requests with full metadata.
        
        Args:
            messages: List of message dicts with 'role' and 'content' keys
                     Example: [
                         {"role": "system", "content": "You are helpful"},
                         {"role": "user", "content": "Hello"}
                     ]
            max_tokens: Maximum tokens to generate (default: 1000)
            temperature: Sampling temperature 0.0-1.0 (default: 0.7)
        
        Returns:
            ProviderResponse: Standardized response with content, tokens, latency
        
        Raises:
            ProviderAuthError: On authentication failure
            ProviderTimeoutError: On request timeout
            ProviderRateLimitError: On rate limit exceeded
            ProviderAPIError: On other API errors
        
        Requirements: 8.3, 8.4
        """
        if not self.client:
            raise ProviderAPIError(
                "Gemini client not initialized. Check GOOGLE_API_KEY."
            )
        
        start_time = time.time()
        
        # Convert messages to Gemini format
        contents = self._format_messages_for_gemini(messages)
        prompt_length = len(contents)
        
        # Sanitize prompt for logging
        sanitized_prompt = self._sanitize_prompt(contents)
        
        # OPTIMIZATION: Dynamic max_tokens based on operation type
        # Reduce token generation for shorter responses
        optimized_max_tokens = min(max_tokens, 500) if max_tokens <= 500 else max_tokens
        
        # Build configuration
        config = {
            'max_output_tokens': optimized_max_tokens,
            'temperature': temperature,
        }
        
        # OPTIMIZATION: Reduced retry with faster backoff
        last_error = None
        for attempt in range(self.max_retries):
            try:
                # Generate response using Google GenAI SDK
                response = self.client.models.generate_content(
                    model=self.api_model_id,
                    contents=contents,
                    config=config
                )
                
                # Extract content and metadata
                content = self._extract_content(response)
                tokens_used = self._extract_tokens(response)
                
                # Calculate latency
                latency_ms = int((time.time() - start_time) * 1000)
                response_length = len(content)
                
                # Log successful request
                self._log_request(
                    operation="generate_response",
                    prompt_length=prompt_length,
                    response_length=response_length,
                    latency_ms=latency_ms
                )
                
                logger.info(
                    f"[GeminiService] Request succeeded | "
                    f"model={self.model} | "
                    f"prompt_preview='{sanitized_prompt}' | "
                    f"tokens_used={tokens_used} | "
                    f"latency_ms={latency_ms}"
                )
                
                return ProviderResponse(
                    content=content,
                    tokens_used=tokens_used,
                    model_used=self.model,
                    latency_ms=latency_ms,
                    metadata={
                        "provider": "gemini",
                        "api_model_id": self.api_model_id,
                        "attempt": attempt + 1,
                        "timestamp": datetime.utcnow().isoformat(),
                    }
                )
            
            except Exception as e:
                error_str = str(e).lower()
                
                # Handle authentication errors
                if 'auth' in error_str or 'api key' in error_str or '401' in error_str:
                    error = ProviderAuthError(
                        "Gemini API authentication failed. Check GOOGLE_API_KEY."
                    )
                    self._log_request(
                        operation="generate_response",
                        prompt_length=prompt_length,
                        error=error
                    )
                    logger.error(
                        f"[GeminiService] Authentication error | "
                        f"model={self.model}",
                        exc_info=True
                    )
                    raise error
                
                # Handle rate limit errors with retry
                elif 'rate limit' in error_str or '429' in error_str or 'quota' in error_str:
                    if attempt < self.max_retries - 1:
                        # OPTIMIZATION: Faster backoff (0.5s, 1s instead of 1s, 2s, 4s)
                        backoff_delay = 0.5 * (2 ** attempt)
                        logger.warning(
                            f"[GeminiService] Rate limit hit | "
                            f"model={self.model} | "
                            f"attempt={attempt + 1}/{self.max_retries} | "
                            f"retrying in {backoff_delay}s"
                        )
                        time.sleep(backoff_delay)
                        last_error = e
                        continue
                    else:
                        error = ProviderRateLimitError(
                            f"Gemini API rate limit exceeded after {self.max_retries} retries"
                        )
                        self._log_request(
                            operation="generate_response",
                            prompt_length=prompt_length,
                            error=error
                        )
                        logger.error(
                            f"[GeminiService] Rate limit exhausted | "
                            f"model={self.model} | "
                            f"max_retries={self.max_retries}",
                            exc_info=True
                        )
                        raise error
                
                # Handle timeout errors
                elif 'timeout' in error_str or 'timed out' in error_str:
                    error = ProviderTimeoutError(
                        f"Gemini API request timed out after {self.timeout}s"
                    )
                    self._log_request(
                        operation="generate_response",
                        prompt_length=prompt_length,
                        error=error
                    )
                    logger.error(
                        f"[GeminiService] Timeout error | "
                        f"model={self.model} | "
                        f"timeout={self.timeout}s",
                        exc_info=True
                    )
                    raise error
                
                # Handle other errors with retry
                else:
                    last_error = e
                    if attempt < self.max_retries - 1:
                        # OPTIMIZATION: Faster backoff
                        backoff_delay = 0.5 * (2 ** attempt)
                        logger.warning(
                            f"[GeminiService] API error | "
                            f"model={self.model} | "
                            f"attempt={attempt + 1}/{self.max_retries} | "
                            f"retrying in {backoff_delay}s | "
                            f"error={str(e)}"
                        )
                        time.sleep(backoff_delay)
                        continue
                    else:
                        error = ProviderAPIError(
                            f"Gemini API error: {str(e)}"
                        )
                        self._log_request(
                            operation="generate_response",
                            prompt_length=prompt_length,
                            error=error
                        )
                        logger.error(
                            f"[GeminiService] API error after retries | "
                            f"model={self.model} | "
                            f"error={str(e)}",
                            exc_info=True
                        )
                        raise error
        
        # Should not reach here, but handle edge case
        if last_error:
            error = ProviderAPIError(f"Gemini request failed: {str(last_error)}")
            self._log_request(
                operation="generate_response",
                prompt_length=prompt_length,
                error=error
            )
            raise error
    
    def generate_embeddings(self, text: str) -> List[float]:
        """
        Generate vector embeddings for text using Gemini.
        
        Args:
            text: Text to generate embeddings for
        
        Returns:
            List[float]: Vector embedding
        
        Raises:
            ProviderAPIError: On API errors
            ProviderAuthError: On authentication failure
        
        Requirements: 8.1
        """
        if not self.client:
            raise ProviderAPIError(
                "Gemini client not initialized. Check GOOGLE_API_KEY."
            )
        
        if not text or not text.strip():
            return []
        
        try:
            # Use Gemini embedding model
            response = self.client.models.embed_content(
                model='text-embedding-004',  # Gemini embedding model
                content=text
            )
            
            embedding = response.embedding
            
            logger.info(
                f"[GeminiService] Embeddings generated | "
                f"text_length={len(text)} | "
                f"embedding_dim={len(embedding)}"
            )
            
            return embedding
        
        except Exception as e:
            error_str = str(e).lower()
            
            if 'auth' in error_str or 'api key' in error_str:
                raise ProviderAuthError(
                    "Gemini API authentication failed for embeddings"
                )
            else:
                raise ProviderAPIError(
                    f"Gemini embeddings generation failed: {str(e)}"
                )
    
    def _format_messages_for_gemini(self, messages: List[dict]) -> str:
        """
        Convert messages array to Gemini-compatible format.
        
        OPTIMIZATION: Simplified format without verbose markers to reduce prompt size.
        
        Args:
            messages: List of message dicts with 'role' and 'content'
        
        Returns:
            str: Formatted string for Gemini API
        """
        formatted = []
        
        for msg in messages:
            role = msg.get("role", "user")
            content = msg.get("content", "")
            
            if role == "system":
                # System messages become instructions at the top (no verbose markers)
                formatted.append(content)
            elif role == "user":
                formatted.append(f"User: {content}")
            elif role == "assistant":
                formatted.append(f"Assistant: {content}")
        
        return "\n\n".join(formatted)
    
    def estimate_tokens(self, text: str) -> int:
        """
        Estimate token count for text.
        
        Uses simple heuristic: ~4 characters per token (approximation).
        For more accurate estimates, use Gemini's count_tokens API.
        
        Args:
            text: Text to estimate tokens for
        
        Returns:
            int: Estimated token count
        
        Requirements: 8.1
        """
        # Simple approximation: 4 characters per token
        # This is a rough estimate; actual tokenization may vary
        return max(1, len(text) // 4)
    
    def _extract_content(self, response) -> str:
        """
        Extract content from Gemini API response.
        
        Args:
            response: Gemini API response object
        
        Returns:
            str: Generated content
        
        Raises:
            ProviderAPIError: If response format is invalid
        """
        try:
            # Gemini response has .text attribute
            if hasattr(response, 'text'):
                return response.text
            
            # Fallback: try to extract from candidates
            if hasattr(response, 'candidates') and response.candidates:
                candidate = response.candidates[0]
                if hasattr(candidate, 'content'):
                    content = candidate.content
                    if hasattr(content, 'parts') and content.parts:
                        return content.parts[0].text
            
            raise ProviderAPIError("Unable to extract content from Gemini response")
        
        except AttributeError as e:
            raise ProviderAPIError(
                f"Invalid Gemini API response format: {str(e)}"
            )
    
    def _extract_tokens(self, response) -> int:
        """
        Extract token usage from Gemini API response.
        
        Args:
            response: Gemini API response object
        
        Returns:
            int: Total tokens used
        """
        try:
            # Try to get usage metadata
            if hasattr(response, 'usage_metadata'):
                usage = response.usage_metadata
                if hasattr(usage, 'total_token_count'):
                    return usage.total_token_count
                # Fallback: sum prompt and candidate tokens
                prompt_tokens = getattr(usage, 'prompt_token_count', 0)
                candidate_tokens = getattr(usage, 'candidates_token_count', 0)
                return prompt_tokens + candidate_tokens
            
            # If no usage metadata, estimate from content
            content = self._extract_content(response)
            return self.estimate_tokens(content)
        
        except Exception:
            # If token extraction fails, return 0
            logger.warning(
                f"[GeminiService] Failed to extract token count, returning 0"
            )
            return 0
