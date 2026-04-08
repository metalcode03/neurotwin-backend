"""
Unit tests for GeminiService provider.

Tests Gemini API integration, error handling, and response formatting.
"""

import pytest
from unittest.mock import Mock, patch, MagicMock
import os

from apps.credits.providers.gemini import GeminiService
from apps.credits.dataclasses import ProviderResponse
from apps.credits.exceptions import (
    ProviderAPIError,
    ProviderAuthError,
    ProviderTimeoutError,
    ProviderRateLimitError,
)


class TestGeminiServiceInitialization:
    """Test GeminiService initialization and configuration."""
    
    def test_init_with_default_model(self):
        """Test initialization with default model."""
        with patch('apps.credits.providers.gemini.genai.Client'):
            service = GeminiService()
            assert service.model == "gemini-2.5-flash"
            assert service.api_model_id == "gemini-2.5-flash-exp"
    
    def test_init_with_custom_model(self):
        """Test initialization with custom model."""
        with patch('apps.credits.providers.gemini.genai.Client'):
            service = GeminiService(model="gemini-3-pro")
            assert service.model == "gemini-3-pro"
            assert service.api_model_id == "gemini-exp-1206"
    
    def test_init_with_unsupported_model(self):
        """Test initialization with unsupported model raises ValueError."""
        with pytest.raises(ValueError) as exc_info:
            GeminiService(model="unsupported-model")
        
        assert "Unsupported model" in str(exc_info.value)
    
    def test_supported_models(self):
        """Test all supported models can be initialized."""
        supported = [
            "gemini-2.5-flash",
            "gemini-2.5-pro",
            "gemini-3-pro",
            "gemini-3.1-pro"
        ]
        
        with patch('apps.credits.providers.gemini.genai.Client'):
            for model in supported:
                service = GeminiService(model=model)
                assert service.model == model
                assert service.api_model_id in GeminiService.SUPPORTED_MODELS.values()


class TestGeminiServiceGenerateResponse:
    """Test generate_response method."""
    
    @patch('apps.credits.providers.gemini.genai.Client')
    def test_generate_response_success(self, mock_client_class):
        """Test successful response generation."""
        # Setup mock
        mock_client = Mock()
        mock_client_class.return_value = mock_client
        
        mock_response = Mock()
        mock_response.text = "This is a test response"
        mock_response.usage_metadata = Mock()
        mock_response.usage_metadata.total_token_count = 50
        
        mock_client.models.generate_content.return_value = mock_response
        
        # Test
        service = GeminiService()
        result = service.generate_response(
            prompt="Test prompt",
            system_prompt="Test system",
            max_tokens=100,
            temperature=0.8
        )
        
        # Assertions
        assert isinstance(result, ProviderResponse)
        assert result.content == "This is a test response"
        assert result.tokens_used == 50
        assert result.model_used == "gemini-2.5-flash"
        assert result.latency_ms >= 0  # Can be 0 in mocked tests
        assert result.metadata["provider"] == "gemini"
        
        # Verify API call
        mock_client.models.generate_content.assert_called_once()
        call_args = mock_client.models.generate_content.call_args
        assert call_args[1]['model'] == "gemini-2.5-flash-exp"
        assert call_args[1]['contents'] == "Test prompt"
        assert call_args[1]['config']['max_output_tokens'] == 100
        assert call_args[1]['config']['temperature'] == 0.8
        assert call_args[1]['config']['system_instruction'] == "Test system"
    
    @patch('apps.credits.providers.gemini.genai.Client')
    def test_generate_response_without_system_prompt(self, mock_client_class):
        """Test response generation without system prompt."""
        mock_client = Mock()
        mock_client_class.return_value = mock_client
        
        mock_response = Mock()
        mock_response.text = "Response"
        mock_response.usage_metadata = Mock()
        mock_response.usage_metadata.total_token_count = 10
        
        mock_client.models.generate_content.return_value = mock_response
        
        service = GeminiService()
        result = service.generate_response(prompt="Test")
        
        # Verify system_instruction not in config
        call_args = mock_client.models.generate_content.call_args
        assert 'system_instruction' not in call_args[1]['config']
    
    @patch('apps.credits.providers.gemini.genai.Client')
    def test_generate_response_auth_error(self, mock_client_class):
        """Test authentication error handling."""
        mock_client = Mock()
        mock_client_class.return_value = mock_client
        mock_client.models.generate_content.side_effect = Exception("401 auth failed")
        
        service = GeminiService()
        
        with pytest.raises(ProviderAuthError) as exc_info:
            service.generate_response(prompt="Test")
        
        assert "authentication failed" in str(exc_info.value).lower()
    
    @patch('apps.credits.providers.gemini.genai.Client')
    @patch('apps.credits.providers.gemini.time.sleep')
    def test_generate_response_rate_limit_retry(self, mock_sleep, mock_client_class):
        """Test rate limit error with retry logic."""
        mock_client = Mock()
        mock_client_class.return_value = mock_client
        
        # First two calls fail with rate limit, third succeeds
        mock_response = Mock()
        mock_response.text = "Success after retry"
        mock_response.usage_metadata = Mock()
        mock_response.usage_metadata.total_token_count = 20
        
        mock_client.models.generate_content.side_effect = [
            Exception("429 rate limit"),
            Exception("rate limit exceeded"),
            mock_response
        ]
        
        service = GeminiService()
        result = service.generate_response(prompt="Test")
        
        # Should succeed after retries
        assert result.content == "Success after retry"
        assert result.metadata["attempt"] == 3
        
        # Verify exponential backoff
        assert mock_sleep.call_count == 2
        mock_sleep.assert_any_call(1)  # First retry: 2^0 = 1s
        mock_sleep.assert_any_call(2)  # Second retry: 2^1 = 2s
    
    @patch('apps.credits.providers.gemini.genai.Client')
    @patch('apps.credits.providers.gemini.time.sleep')
    def test_generate_response_rate_limit_exhausted(self, mock_sleep, mock_client_class):
        """Test rate limit error when retries exhausted."""
        mock_client = Mock()
        mock_client_class.return_value = mock_client
        mock_client.models.generate_content.side_effect = Exception("429 rate limit")
        
        service = GeminiService()
        
        with pytest.raises(ProviderRateLimitError) as exc_info:
            service.generate_response(prompt="Test")
        
        assert "rate limit exceeded" in str(exc_info.value).lower()
        assert mock_sleep.call_count == 2  # max_retries - 1
    
    @patch('apps.credits.providers.gemini.genai.Client')
    def test_generate_response_timeout_error(self, mock_client_class):
        """Test timeout error handling."""
        mock_client = Mock()
        mock_client_class.return_value = mock_client
        mock_client.models.generate_content.side_effect = Exception("timeout occurred")
        
        service = GeminiService()
        
        with pytest.raises(ProviderTimeoutError) as exc_info:
            service.generate_response(prompt="Test")
        
        assert "timed out" in str(exc_info.value).lower()
    
    @patch('apps.credits.providers.gemini.genai.Client')
    def test_generate_response_no_client(self, mock_client_class):
        """Test error when client not initialized."""
        mock_client_class.side_effect = Exception("Client init failed")
        
        service = GeminiService()
        
        with pytest.raises(ProviderAPIError) as exc_info:
            service.generate_response(prompt="Test")
        
        assert "not initialized" in str(exc_info.value).lower()


class TestGeminiServiceEmbeddings:
    """Test generate_embeddings method."""
    
    @patch('apps.credits.providers.gemini.genai.Client')
    def test_generate_embeddings_success(self, mock_client_class):
        """Test successful embedding generation."""
        mock_client = Mock()
        mock_client_class.return_value = mock_client
        
        mock_response = Mock()
        mock_response.embedding = [0.1, 0.2, 0.3, 0.4]
        mock_client.models.embed_content.return_value = mock_response
        
        service = GeminiService()
        result = service.generate_embeddings("Test text")
        
        assert result == [0.1, 0.2, 0.3, 0.4]
        mock_client.models.embed_content.assert_called_once_with(
            model='text-embedding-004',
            content="Test text"
        )
    
    @patch('apps.credits.providers.gemini.genai.Client')
    def test_generate_embeddings_empty_text(self, mock_client_class):
        """Test embedding generation with empty text."""
        mock_client = Mock()
        mock_client_class.return_value = mock_client
        
        service = GeminiService()
        result = service.generate_embeddings("")
        
        assert result == []
        mock_client.models.embed_content.assert_not_called()
    
    @patch('apps.credits.providers.gemini.genai.Client')
    def test_generate_embeddings_auth_error(self, mock_client_class):
        """Test embedding generation with auth error."""
        mock_client = Mock()
        mock_client_class.return_value = mock_client
        mock_client.models.embed_content.side_effect = Exception("API key invalid")
        
        service = GeminiService()
        
        with pytest.raises(ProviderAuthError):
            service.generate_embeddings("Test")


class TestGeminiServiceTokenEstimation:
    """Test estimate_tokens method."""
    
    @patch('apps.credits.providers.gemini.genai.Client')
    def test_estimate_tokens(self, mock_client_class):
        """Test token estimation."""
        service = GeminiService()
        
        # Test various text lengths
        assert service.estimate_tokens("") == 1  # Minimum 1 token
        assert service.estimate_tokens("test") == 1  # 4 chars = 1 token
        assert service.estimate_tokens("test text") == 2  # 9 chars = 2 tokens
        assert service.estimate_tokens("a" * 100) == 25  # 100 chars = 25 tokens


class TestGeminiServiceHelperMethods:
    """Test helper methods."""
    
    @patch('apps.credits.providers.gemini.genai.Client')
    def test_extract_content_from_text_attribute(self, mock_client_class):
        """Test content extraction from response.text."""
        service = GeminiService()
        
        mock_response = Mock()
        mock_response.text = "Test content"
        
        content = service._extract_content(mock_response)
        assert content == "Test content"
    
    @patch('apps.credits.providers.gemini.genai.Client')
    def test_extract_content_from_candidates(self, mock_client_class):
        """Test content extraction from candidates."""
        service = GeminiService()
        
        mock_part = Mock()
        mock_part.text = "Candidate content"
        
        mock_content = Mock()
        mock_content.parts = [mock_part]
        
        mock_candidate = Mock()
        mock_candidate.content = mock_content
        
        mock_response = Mock()
        del mock_response.text  # No text attribute
        mock_response.candidates = [mock_candidate]
        
        content = service._extract_content(mock_response)
        assert content == "Candidate content"
    
    @patch('apps.credits.providers.gemini.genai.Client')
    def test_extract_tokens_from_usage_metadata(self, mock_client_class):
        """Test token extraction from usage_metadata."""
        service = GeminiService()
        
        mock_response = Mock()
        mock_response.text = "Test"
        mock_response.usage_metadata = Mock()
        mock_response.usage_metadata.total_token_count = 42
        
        tokens = service._extract_tokens(mock_response)
        assert tokens == 42
    
    @patch('apps.credits.providers.gemini.genai.Client')
    def test_extract_tokens_fallback_to_sum(self, mock_client_class):
        """Test token extraction fallback to sum of prompt and candidate tokens."""
        service = GeminiService()
        
        mock_response = Mock()
        mock_response.text = "Test"
        mock_response.usage_metadata = Mock()
        del mock_response.usage_metadata.total_token_count
        mock_response.usage_metadata.prompt_token_count = 10
        mock_response.usage_metadata.candidates_token_count = 20
        
        tokens = service._extract_tokens(mock_response)
        assert tokens == 30
    
    @patch('apps.credits.providers.gemini.genai.Client')
    def test_extract_tokens_fallback_to_estimate(self, mock_client_class):
        """Test token extraction fallback to estimation."""
        service = GeminiService()
        
        mock_response = Mock()
        mock_response.text = "Test content here"
        del mock_response.usage_metadata
        
        tokens = service._extract_tokens(mock_response)
        assert tokens > 0  # Should estimate from content
