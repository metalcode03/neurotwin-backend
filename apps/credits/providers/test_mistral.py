"""
Unit tests for MistralService provider.

Tests error handling, retry logic, and request logging.
Requirements: 8.2, 8.5, 8.6
"""

import pytest
from unittest.mock import Mock, patch, MagicMock
import httpx

from apps.credits.providers.mistral import MistralService
from apps.credits.exceptions import (
    ProviderAPIError,
    ProviderTimeoutError,
    ProviderAuthError,
    ProviderRateLimitError,
)


class TestMistralService:
    """Test suite for MistralService provider."""
    
    def setup_method(self):
        """Set up test fixtures."""
        self.service = MistralService()
    
    @patch.dict('os.environ', {'MISTRAL_API_KEY': 'test-key-123'})
    def test_initialization(self):
        """Test service initializes with correct configuration."""
        service = MistralService()
        assert service.api_key == 'test-key-123'
        assert service.base_url == "https://api.mistral.ai/v1"
        assert service.timeout == 30
        assert service.max_retries == 3
        assert service.model == "mistral-small-latest"
    
    @patch('apps.credits.providers.mistral.httpx.Client')
    def test_generate_response_success(self, mock_client):
        """Test successful response generation."""
        # Mock successful API response
        mock_response = Mock()
        mock_response.json.return_value = {
            "choices": [
                {
                    "message": {
                        "content": "This is a test summarization"
                    }
                }
            ],
            "usage": {
                "total_tokens": 30
            }
        }
        mock_response.raise_for_status = Mock()
        
        mock_client_instance = MagicMock()
        mock_client_instance.__enter__.return_value.post.return_value = mock_response
        mock_client.return_value = mock_client_instance
        
        # Execute
        result = self.service.generate_response(
            prompt="Summarize this text",
            system_prompt="You are a summarization assistant",
            max_tokens=100,
            temperature=0.7
        )
        
        # Verify
        assert result.content == "This is a test summarization"
        assert result.tokens_used == 30
        assert result.model_used == "mistral-small-latest"
        assert result.latency_ms >= 0  # Can be 0 in mocked tests
        assert result.metadata["provider"] == "mistral"
    
    @patch('apps.credits.providers.mistral.httpx.Client')
    def test_generate_response_timeout(self, mock_client):
        """Test timeout error handling."""
        # Mock timeout
        mock_client_instance = MagicMock()
        mock_client_instance.__enter__.return_value.post.side_effect = httpx.TimeoutException("Timeout")
        mock_client.return_value = mock_client_instance
        
        # Execute and verify
        with pytest.raises(ProviderTimeoutError) as exc_info:
            self.service.generate_response(prompt="Test")
        
        assert "timed out" in str(exc_info.value).lower()
    
    @patch('apps.credits.providers.mistral.httpx.Client')
    def test_generate_response_auth_error(self, mock_client):
        """Test authentication error handling."""
        # Mock 401 error
        mock_response = Mock()
        mock_response.status_code = 401
        mock_response.json.return_value = {"error": {"message": "Invalid API key"}}
        
        mock_client_instance = MagicMock()
        mock_client_instance.__enter__.return_value.post.side_effect = httpx.HTTPStatusError(
            "401 Unauthorized",
            request=Mock(),
            response=mock_response
        )
        mock_client.return_value = mock_client_instance
        
        # Execute and verify
        with pytest.raises(ProviderAuthError) as exc_info:
            self.service.generate_response(prompt="Test")
        
        assert "authentication failed" in str(exc_info.value).lower()
    
    @patch('apps.credits.providers.mistral.httpx.Client')
    @patch('time.sleep')  # Mock sleep to speed up test
    def test_generate_response_rate_limit_retry(self, mock_sleep, mock_client):
        """Test exponential backoff for rate limit errors."""
        # Mock 429 error twice, then success
        mock_response_429 = Mock()
        mock_response_429.status_code = 429
        mock_response_429.json.return_value = {"error": {"message": "Rate limit"}}
        
        mock_response_success = Mock()
        mock_response_success.json.return_value = {
            "choices": [{"message": {"content": "Success after retry"}}],
            "usage": {"total_tokens": 15}
        }
        mock_response_success.raise_for_status = Mock()
        
        mock_client_instance = MagicMock()
        post_mock = mock_client_instance.__enter__.return_value.post
        post_mock.side_effect = [
            httpx.HTTPStatusError("429", request=Mock(), response=mock_response_429),
            httpx.HTTPStatusError("429", request=Mock(), response=mock_response_429),
            mock_response_success
        ]
        mock_client.return_value = mock_client_instance
        
        # Execute
        result = self.service.generate_response(prompt="Test")
        
        # Verify retries occurred
        assert post_mock.call_count == 3
        assert mock_sleep.call_count == 2
        # Verify exponential backoff: 1s, 2s
        mock_sleep.assert_any_call(1)
        mock_sleep.assert_any_call(2)
        assert result.content == "Success after retry"
        assert result.metadata["attempt"] == 3
    
    @patch('apps.credits.providers.mistral.httpx.Client')
    @patch('time.sleep')
    def test_generate_response_rate_limit_exhausted(self, mock_sleep, mock_client):
        """Test rate limit error after max retries."""
        # Mock 429 error for all attempts
        mock_response = Mock()
        mock_response.status_code = 429
        mock_response.json.return_value = {"error": {"message": "Rate limit"}}
        
        mock_client_instance = MagicMock()
        mock_client_instance.__enter__.return_value.post.side_effect = httpx.HTTPStatusError(
            "429",
            request=Mock(),
            response=mock_response
        )
        mock_client.return_value = mock_client_instance
        
        # Execute and verify
        with pytest.raises(ProviderRateLimitError) as exc_info:
            self.service.generate_response(prompt="Test")
        
        assert "rate limit exceeded" in str(exc_info.value).lower()
        assert exc_info.value.status_code == 429
    
    @patch('apps.credits.providers.mistral.httpx.Client')
    def test_generate_response_server_error(self, mock_client):
        """Test server error handling."""
        # Mock 500 error
        mock_response = Mock()
        mock_response.status_code = 500
        mock_response.text = "Internal server error"
        mock_response.json.side_effect = Exception("Not JSON")
        
        mock_client_instance = MagicMock()
        mock_client_instance.__enter__.return_value.post.side_effect = httpx.HTTPStatusError(
            "500",
            request=Mock(),
            response=mock_response
        )
        mock_client.return_value = mock_client_instance
        
        # Execute and verify
        with pytest.raises(ProviderAPIError) as exc_info:
            self.service.generate_response(prompt="Test")
        
        assert exc_info.value.status_code == 500
    
    def test_estimate_tokens(self):
        """Test token estimation."""
        # Test various text lengths
        assert self.service.estimate_tokens("") == 1  # Minimum 1
        assert self.service.estimate_tokens("test") == 1  # 4 chars = 1 token
        assert self.service.estimate_tokens("a" * 100) == 25  # 100 chars = 25 tokens
        assert self.service.estimate_tokens("a" * 1000) == 250  # 1000 chars = 250 tokens
    
    def test_generate_embeddings_not_implemented(self):
        """Test embeddings raise NotImplementedError."""
        with pytest.raises(NotImplementedError) as exc_info:
            self.service.generate_embeddings("test text")
        
        assert "not yet supported" in str(exc_info.value).lower()
    
    def test_sanitize_prompt_removes_pii(self):
        """Test prompt sanitization removes PII."""
        prompt_with_email = "Contact me at john.doe@example.com for details"
        sanitized = self.service._sanitize_prompt(prompt_with_email)
        assert "[EMAIL]" in sanitized
        assert "john.doe@example.com" not in sanitized
        
        prompt_with_phone = "Call me at 555-123-4567"
        sanitized = self.service._sanitize_prompt(prompt_with_phone)
        assert "[PHONE]" in sanitized
        assert "555-123-4567" not in sanitized
    
    def test_sanitize_prompt_truncates_long_text(self):
        """Test prompt sanitization truncates long text."""
        long_prompt = "a" * 300
        sanitized = self.service._sanitize_prompt(long_prompt, max_log_length=200)
        assert len(sanitized) <= 203  # 200 + "..."
        assert sanitized.endswith("...")
    
    @patch('apps.credits.providers.mistral.httpx.Client')
    def test_generate_response_with_system_prompt(self, mock_client):
        """Test response generation with system prompt."""
        # Mock successful API response
        mock_response = Mock()
        mock_response.json.return_value = {
            "choices": [{"message": {"content": "Summarized content"}}],
            "usage": {"total_tokens": 20}
        }
        mock_response.raise_for_status = Mock()
        
        mock_client_instance = MagicMock()
        post_mock = mock_client_instance.__enter__.return_value.post
        post_mock.return_value = mock_response
        mock_client.return_value = mock_client_instance
        
        # Execute
        result = self.service.generate_response(
            prompt="Summarize this",
            system_prompt="You are a helpful assistant"
        )
        
        # Verify system prompt was included in request
        call_args = post_mock.call_args
        payload = call_args[1]['json']
        assert len(payload['messages']) == 2
        assert payload['messages'][0]['role'] == 'system'
        assert payload['messages'][0]['content'] == "You are a helpful assistant"
        assert payload['messages'][1]['role'] == 'user'
        assert result.content == "Summarized content"
