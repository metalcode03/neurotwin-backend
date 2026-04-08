"""
Unit tests for CerebrasService provider.

Tests error handling, retry logic, and request logging.
Requirements: 7.2-7.9, 8.2
"""

import pytest
from unittest.mock import Mock, patch, MagicMock
import httpx

from apps.credits.providers.cerebras import CerebrasService
from apps.credits.exceptions import (
    CerebrasAPIError,
    CerebrasTimeoutError,
    CerebrasAuthError,
)


class TestCerebrasService:
    """Test suite for CerebrasService provider."""
    
    def setup_method(self):
        """Set up test fixtures."""
        self.service = CerebrasService()
    
    @patch.dict('os.environ', {'CEREBRAS_API_KEY': 'test-key-123'})
    def test_initialization(self):
        """Test service initializes with correct configuration."""
        service = CerebrasService()
        assert service.api_key == 'test-key-123'
        assert service.base_url == "https://api.cerebras.ai/v1"
        assert service.timeout == 30
        assert service.max_retries == 3
    
    @patch('apps.credits.providers.cerebras.httpx.Client')
    def test_generate_response_success(self, mock_client):
        """Test successful response generation."""
        # Mock successful API response
        mock_response = Mock()
        mock_response.json.return_value = {
            "choices": [
                {
                    "message": {
                        "content": "This is a test response"
                    }
                }
            ],
            "usage": {
                "total_tokens": 25
            }
        }
        mock_response.raise_for_status = Mock()
        
        mock_client_instance = MagicMock()
        mock_client_instance.__enter__.return_value.post.return_value = mock_response
        mock_client.return_value = mock_client_instance
        
        # Execute
        result = self.service.generate_response(
            prompt="Test prompt",
            system_prompt="Test system",
            max_tokens=100,
            temperature=0.7
        )
        
        # Verify
        assert result.content == "This is a test response"
        assert result.tokens_used == 25
        assert result.model_used == "llama3.1-8b"
        assert result.latency_ms >= 0  # Can be 0 in mocked tests
        assert result.metadata["provider"] == "cerebras"
    
    @patch('apps.credits.providers.cerebras.httpx.Client')
    def test_generate_response_timeout(self, mock_client):
        """Test timeout error handling."""
        # Mock timeout
        mock_client_instance = MagicMock()
        mock_client_instance.__enter__.return_value.post.side_effect = httpx.TimeoutException("Timeout")
        mock_client.return_value = mock_client_instance
        
        # Execute and verify
        with pytest.raises(CerebrasTimeoutError) as exc_info:
            self.service.generate_response(prompt="Test")
        
        assert "timed out" in str(exc_info.value).lower()
    
    @patch('apps.credits.providers.cerebras.httpx.Client')
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
        with pytest.raises(CerebrasAuthError) as exc_info:
            self.service.generate_response(prompt="Test")
        
        assert "authentication failed" in str(exc_info.value).lower()
    
    @patch('apps.credits.providers.cerebras.httpx.Client')
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
            "usage": {"total_tokens": 10}
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
    
    @patch('apps.credits.providers.cerebras.httpx.Client')
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
        with pytest.raises(CerebrasAPIError) as exc_info:
            self.service.generate_response(prompt="Test")
        
        assert "rate limit exceeded" in str(exc_info.value).lower()
        assert exc_info.value.status_code == 429
    
    @patch('apps.credits.providers.cerebras.httpx.Client')
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
        with pytest.raises(CerebrasAPIError) as exc_info:
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
