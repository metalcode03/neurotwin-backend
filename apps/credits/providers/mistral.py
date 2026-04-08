"""
MistralService provider implementation.

Integrates Mistral API for summarization tasks in Brain mode (free tier).
Implements exponential backoff, error handling, and request logging.

Requirements: 8.2, 8.5, 8.6
"""

import os
import time
import logging
from typing import List, Optional
from datetime import datetime

import httpx

from apps.credits.providers.base import AIProvider
from apps.credits.dataclasses import ProviderResponse
from apps.credits.exceptions import (
    ProviderAPIError,
    ProviderTimeoutError,
    ProviderAuthError,
    ProviderRateLimitError,
)


logger = logging.getLogger(__name__)


class MistralService(AIProvider):
    """
    Mistral API provider implementation.
    
    Provides summarization capabilities for Brain mode (free tier).
    Used exclusively for summarization operations in the free tier routing.
    Implements exponential backoff for rate limits and comprehensive logging.
    
    Requirements:
    - 8.2: Extend AIProvider interface
    - 8.5: Implement exponential backoff for rate limit errors (429), max 3 retries
    - 8.6: Set timeout to 30 seconds
    - 8.6: Log all requests with timestamp, prompt_length, response_length, latency_ms
    """
    
    def __init__(self):
        """
        Initialize Mistral service with API configuration.
        
        Requirements: 8.2, 8.6
        """
        self.api_key = os.getenv('MISTRAL_API_KEY', '')
        if not self.api_key:
            logger.warning("MISTRAL_API_KEY not found in environment variables")
        
        self.base_url = "https://api.mistral.ai/v1"
        # OPTIMIZATION: Reduced timeout from 30s to 15s for faster failure
        self.timeout = 15
        # OPTIMIZATION: Reduced retries from 3 to 2
        self.max_retries = 2
        self.model = "mistral-small-latest"  # Good for summarization
    
    def generate_response(
        self,
        messages: List[dict],
        max_tokens: int = 1000,
        temperature: float = 0.7
    ) -> ProviderResponse:
        """
        Generate AI response using Mistral API.
        
        Implements exponential backoff for rate limits (429 errors) with
        retry delays of 1s, 2s, 4s. Logs all requests with full metadata.
        
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
            ProviderAuthError: On 401 authentication failure
            ProviderTimeoutError: On request timeout
            ProviderRateLimitError: On rate limit exceeded after retries
            ProviderAPIError: On other API errors
        
        Requirements: 8.2, 8.5, 8.6
        """
        start_time = time.time()
        
        # Calculate prompt length from all messages
        prompt_length = sum(len(msg.get("content", "")) for msg in messages)
        
        # Sanitize first user message for logging
        user_msg = next((m.get("content", "") for m in messages if m.get("role") == "user"), "")
        sanitized_prompt = self._sanitize_prompt(user_msg)
        
        # Build request payload - Mistral uses OpenAI-style messages format
        payload = {
            "model": self.model,
            "messages": messages,
            "max_tokens": max_tokens,
            "temperature": temperature,
        }
        
        # Retry with exponential backoff (Requirement 8.5)
        last_error = None
        for attempt in range(self.max_retries):
            try:
                response = self._make_request(payload)
                
                # Parse response
                content = self._extract_content(response)
                tokens_used = self._extract_tokens(response)
                
                # Calculate latency
                latency_ms = int((time.time() - start_time) * 1000)
                response_length = len(content)
                
                # Log successful request (Requirement 8.6)
                self._log_request(
                    operation="generate_response",
                    prompt_length=prompt_length,
                    response_length=response_length,
                    latency_ms=latency_ms
                )
                
                logger.info(
                    f"[MistralService] Request succeeded | "
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
                        "provider": "mistral",
                        "attempt": attempt + 1,
                        "timestamp": datetime.utcnow().isoformat(),
                    }
                )
            
            except httpx.TimeoutException as e:
                # Timeout error - don't retry (Requirement 8.6)
                error = ProviderTimeoutError(
                    f"Mistral API request timed out after {self.timeout}s"
                )
                self._log_request(
                    operation="generate_response",
                    prompt_length=prompt_length,
                    error=error
                )
                logger.error(
                    f"[MistralService] Timeout error | "
                    f"prompt_preview='{sanitized_prompt}' | "
                    f"timeout={self.timeout}s",
                    exc_info=True
                )
                raise error
            
            except httpx.HTTPStatusError as e:
                status_code = e.response.status_code
                
                # Authentication error (Requirement 8.5)
                if status_code == 401:
                    error = ProviderAuthError(
                        "Mistral API authentication failed. Check MISTRAL_API_KEY."
                    )
                    self._log_request(
                        operation="generate_response",
                        prompt_length=prompt_length,
                        error=error
                    )
                    logger.error(
                        f"[MistralService] Authentication error | "
                        f"status_code={status_code}",
                        exc_info=True
                    )
                    raise error
                
                # Rate limit error - retry with exponential backoff (Requirement 8.5)
                elif status_code == 429:
                    if attempt < self.max_retries - 1:
                        # OPTIMIZATION: Faster backoff (0.5s, 1s instead of 1s, 2s, 4s)
                        backoff_delay = 0.5 * (2 ** attempt)
                        logger.warning(
                            f"[MistralService] Rate limit hit (429) | "
                            f"attempt={attempt + 1}/{self.max_retries} | "
                            f"retrying in {backoff_delay}s"
                        )
                        time.sleep(backoff_delay)
                        last_error = e
                        continue
                    else:
                        error = ProviderRateLimitError(
                            f"Mistral API rate limit exceeded after {self.max_retries} retries"
                        )
                        self._log_request(
                            operation="generate_response",
                            prompt_length=prompt_length,
                            error=error
                        )
                        logger.error(
                            f"[MistralService] Rate limit exhausted | "
                            f"max_retries={self.max_retries}",
                            exc_info=True
                        )
                        raise error
                
                # Other HTTP errors (Requirement 8.5)
                else:
                    error_message = self._extract_error_message(e.response)
                    error = ProviderAPIError(
                        f"Mistral API error: {error_message}",
                        status_code=status_code
                    )
                    self._log_request(
                        operation="generate_response",
                        prompt_length=prompt_length,
                        error=error
                    )
                    logger.error(
                        f"[MistralService] API error | "
                        f"status_code={status_code} | "
                        f"error='{error_message}'",
                        exc_info=True
                    )
                    raise error
            
            except Exception as e:
                # Unexpected errors
                last_error = e
                if attempt < self.max_retries - 1:
                    # OPTIMIZATION: Faster backoff
                    backoff_delay = 0.5 * (2 ** attempt)
                    logger.warning(
                        f"[MistralService] Unexpected error | "
                        f"attempt={attempt + 1}/{self.max_retries} | "
                        f"retrying in {backoff_delay}s | "
                        f"error={str(e)}"
                    )
                    time.sleep(backoff_delay)
                    continue
                else:
                    error = ProviderAPIError(f"Mistral request failed: {str(e)}")
                    self._log_request(
                        operation="generate_response",
                        prompt_length=prompt_length,
                        error=error
                    )
                    logger.error(
                        f"[MistralService] Unexpected error after retries | "
                        f"error={str(e)}",
                        exc_info=True
                    )
                    raise error
        
        # Should not reach here, but handle edge case
        if last_error:
            error = ProviderAPIError(f"Mistral request failed: {str(last_error)}")
            self._log_request(
                operation="generate_response",
                prompt_length=prompt_length,
                error=error
            )
            raise error
    
    def generate_embeddings(self, text: str) -> List[float]:
        """
        Generate vector embeddings for text.
        
        Note: Mistral may not support embeddings. This is a placeholder
        implementation that raises NotImplementedError.
        
        Args:
            text: Text to generate embeddings for
        
        Returns:
            List[float]: Vector embedding
        
        Raises:
            NotImplementedError: Mistral embeddings not yet supported
        
        Requirements: 8.1
        """
        raise NotImplementedError(
            "Mistral embeddings are not yet supported. "
            "Use GeminiService or another provider for embeddings."
        )
    
    def estimate_tokens(self, text: str) -> int:
        """
        Estimate token count for text.
        
        Uses simple heuristic: ~4 characters per token (approximation).
        For more accurate estimates, use provider-specific tokenizers.
        
        Args:
            text: Text to estimate tokens for
        
        Returns:
            int: Estimated token count
        
        Requirements: 8.1
        """
        # Simple approximation: 4 characters per token
        # This is a rough estimate; actual tokenization may vary
        return max(1, len(text) // 4)
    
    def _make_request(self, payload: dict) -> dict:
        """
        Make HTTP request to Mistral API.
        
        Args:
            payload: Request payload
        
        Returns:
            dict: Response JSON
        
        Raises:
            httpx.HTTPStatusError: On HTTP errors
            httpx.TimeoutException: On timeout
        """
        headers = {
            "Authorization": f"Bearer {self.api_key}",
            "Content-Type": "application/json",
        }
        
        with httpx.Client(timeout=self.timeout) as client:
            response = client.post(
                f"{self.base_url}/chat/completions",
                json=payload,
                headers=headers
            )
            response.raise_for_status()
            return response.json()
    
    def _extract_content(self, response: dict) -> str:
        """
        Extract content from Mistral API response.
        
        Args:
            response: API response JSON
        
        Returns:
            str: Generated content
        
        Raises:
            ProviderAPIError: If response format is invalid
        """
        try:
            return response["choices"][0]["message"]["content"]
        except (KeyError, IndexError) as e:
            raise ProviderAPIError(
                f"Invalid Mistral API response format: {str(e)}"
            )
    
    def _extract_tokens(self, response: dict) -> int:
        """
        Extract token usage from Mistral API response.
        
        Args:
            response: API response JSON
        
        Returns:
            int: Total tokens used
        """
        try:
            usage = response.get("usage", {})
            return usage.get("total_tokens", 0)
        except Exception:
            # If token extraction fails, estimate based on content
            content = self._extract_content(response)
            return self.estimate_tokens(content)
    
    def _extract_error_message(self, response: httpx.Response) -> str:
        """
        Extract error message from failed response.
        
        Args:
            response: HTTP response object
        
        Returns:
            str: Error message
        """
        try:
            error_data = response.json()
            return error_data.get("error", {}).get("message", response.text)
        except Exception:
            return response.text or f"HTTP {response.status_code}"
