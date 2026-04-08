"""
Unit tests for RateLimiter class.

Requirements: 12.1-12.7, 34.1
"""

import time
import pytest
from unittest.mock import Mock, patch
from django.core.cache import cache
from apps.automation.utils.rate_limiter import RateLimiter


@pytest.fixture
def rate_limiter():
    """Create RateLimiter instance for testing."""
    return RateLimiter()


@pytest.fixture(autouse=True)
def clear_cache():
    """Clear cache before and after each test."""
    cache.clear()
    yield
    cache.clear()


class TestRateLimiter:
    """Test RateLimiter sliding window algorithm."""
    
    def test_check_rate_limit_allows_within_limit(self, rate_limiter):
        """Test that requests within limit are allowed."""
        integration_id = "test-integration-1"
        
        # Make 5 requests (well under limit of 20)
        for i in range(5):
            allowed, wait = rate_limiter.check_rate_limit(
                integration_id=integration_id,
                limit_per_minute=20
            )
            assert allowed is True
            assert wait == 0
    
    def test_check_rate_limit_blocks_over_limit(self, rate_limiter):
        """Test that requests over limit are blocked."""
        integration_id = "test-integration-2"
        limit = 5
        
        # Make requests up to limit
        for i in range(limit):
            allowed, wait = rate_limiter.check_rate_limit(
                integration_id=integration_id,
                limit_per_minute=limit
            )
            assert allowed is True
        
        # Next request should be blocked
        allowed, wait = rate_limiter.check_rate_limit(
            integration_id=integration_id,
            limit_per_minute=limit
        )
        assert allowed is False
        assert wait > 0
    
    def test_check_rate_limit_per_integration_isolation(self, rate_limiter):
        """Test that rate limits are isolated per integration."""
        integration_1 = "test-integration-3"
        integration_2 = "test-integration-4"
        limit = 5
        
        # Fill up integration_1 limit
        for i in range(limit):
            allowed, _ = rate_limiter.check_rate_limit(
                integration_id=integration_1,
                limit_per_minute=limit
            )
            assert allowed is True
        
        # integration_1 should be blocked
        allowed, _ = rate_limiter.check_rate_limit(
            integration_id=integration_1,
            limit_per_minute=limit
        )
        assert allowed is False
        
        # integration_2 should still be allowed
        allowed, _ = rate_limiter.check_rate_limit(
            integration_id=integration_2,
            limit_per_minute=limit
        )
        assert allowed is True
    
    def test_check_rate_limit_global_limit(self, rate_limiter):
        """Test that global rate limit is enforced."""
        global_limit = 10
        
        # Make requests from different integrations
        for i in range(global_limit):
            integration_id = f"test-integration-{i}"
            allowed, _ = rate_limiter.check_rate_limit(
                integration_id=integration_id,
                limit_per_minute=20,
                global_limit=global_limit
            )
            assert allowed is True
        
        # Next request from any integration should be blocked by global limit
        allowed, wait = rate_limiter.check_rate_limit(
            integration_id="test-integration-new",
            limit_per_minute=20,
            global_limit=global_limit
        )
        assert allowed is False
        assert wait > 0
    
    def test_get_rate_limit_status(self, rate_limiter):
        """Test rate limit status reporting."""
        integration_id = "test-integration-5"
        limit = 10
        
        # Make 3 requests
        for i in range(3):
            rate_limiter.check_rate_limit(
                integration_id=integration_id,
                limit_per_minute=limit
            )
        
        # Check status
        status = rate_limiter.get_rate_limit_status(
            integration_id=integration_id,
            limit_per_minute=limit
        )
        
        assert status['limit'] == limit
        assert status['current'] == 3
        assert status['remaining'] == 7
        assert 'reset_at' in status
    
    def test_get_rate_limit_status_empty(self, rate_limiter):
        """Test rate limit status for integration with no requests."""
        integration_id = "test-integration-6"
        limit = 20
        
        status = rate_limiter.get_rate_limit_status(
            integration_id=integration_id,
            limit_per_minute=limit
        )
        
        assert status['limit'] == limit
        assert status['current'] == 0
        assert status['remaining'] == limit
    
    def test_sliding_window_cleanup(self, rate_limiter):
        """Test that old requests are removed from sliding window."""
        integration_id = "test-integration-7"
        limit = 5
        
        # Mock time to simulate requests in the past
        with patch('time.time') as mock_time:
            # Make requests 70 seconds ago (outside 60-second window)
            mock_time.return_value = time.time() - 70
            for i in range(limit):
                rate_limiter.check_rate_limit(
                    integration_id=integration_id,
                    limit_per_minute=limit
                )
            
            # Move to current time
            mock_time.return_value = time.time()
            
            # Old requests should be cleaned up, new request should be allowed
            allowed, _ = rate_limiter.check_rate_limit(
                integration_id=integration_id,
                limit_per_minute=limit
            )
            assert allowed is True
    
    def test_rate_limit_wait_time_calculation(self, rate_limiter):
        """Test that wait time is calculated correctly."""
        integration_id = "test-integration-8"
        limit = 3
        
        # Fill up the limit
        for i in range(limit):
            rate_limiter.check_rate_limit(
                integration_id=integration_id,
                limit_per_minute=limit
            )
        
        # Check wait time
        allowed, wait = rate_limiter.check_rate_limit(
            integration_id=integration_id,
            limit_per_minute=limit
        )
        
        assert allowed is False
        assert wait > 0
        assert wait <= 60  # Should be within window duration
    
    @patch('apps.automation.utils.rate_limiter.logger')
    def test_rate_limit_violation_logging(self, mock_logger, rate_limiter):
        """Test that rate limit violations are logged."""
        integration_id = "test-integration-9"
        limit = 2
        
        # Fill up the limit
        for i in range(limit):
            rate_limiter.check_rate_limit(
                integration_id=integration_id,
                limit_per_minute=limit
            )
        
        # Trigger violation
        rate_limiter.check_rate_limit(
            integration_id=integration_id,
            limit_per_minute=limit
        )
        
        # Verify logging was called
        assert mock_logger.warning.called
        call_args = str(mock_logger.warning.call_args)
        assert integration_id in call_args
        assert "Rate limit exceeded" in call_args or "violation" in call_args.lower()
    
    def test_rate_limiter_with_redis_unavailable(self, rate_limiter):
        """Test that rate limiter fails open when Redis is unavailable."""
        integration_id = "test-integration-10"
        
        # Mock cache operations to simulate Redis failure
        with patch.object(cache, 'get') as mock_get:
            mock_get.side_effect = Exception("Redis connection failed")
            
            # Should fail open and allow request (graceful degradation)
            allowed, wait = rate_limiter.check_rate_limit(
                integration_id=integration_id,
                limit_per_minute=20
            )
            
            # Should fail open (allow request) when Redis is unavailable
            assert allowed is True
            assert wait == 0


class TestRateLimiterIntegration:
    """Integration tests for rate limiter with time-based scenarios."""
    
    def test_rate_limit_resets_after_window(self, rate_limiter):
        """Test that rate limit resets after time window expires."""
        integration_id = "test-integration-11"
        limit = 3
        
        with patch('time.time') as mock_time:
            start_time = 1000.0
            mock_time.return_value = start_time
            
            # Fill up the limit
            for i in range(limit):
                allowed, _ = rate_limiter.check_rate_limit(
                    integration_id=integration_id,
                    limit_per_minute=limit
                )
                assert allowed is True
            
            # Should be blocked
            allowed, _ = rate_limiter.check_rate_limit(
                integration_id=integration_id,
                limit_per_minute=limit
            )
            assert allowed is False
            
            # Move time forward 61 seconds (past window)
            mock_time.return_value = start_time + 61
            
            # Should be allowed again
            allowed, _ = rate_limiter.check_rate_limit(
                integration_id=integration_id,
                limit_per_minute=limit
            )
            assert allowed is True
    
    def test_rate_limit_partial_window_reset(self, rate_limiter):
        """Test sliding window behavior with partial resets."""
        integration_id = "test-integration-12"
        limit = 5
        
        with patch('time.time') as mock_time:
            start_time = 1000.0
            
            # Make 3 requests at start
            mock_time.return_value = start_time
            for i in range(3):
                rate_limiter.check_rate_limit(
                    integration_id=integration_id,
                    limit_per_minute=limit
                )
            
            # Make 2 more requests at 30 seconds
            mock_time.return_value = start_time + 30
            for i in range(2):
                allowed, _ = rate_limiter.check_rate_limit(
                    integration_id=integration_id,
                    limit_per_minute=limit
                )
                assert allowed is True
            
            # Should be at limit
            allowed, _ = rate_limiter.check_rate_limit(
                integration_id=integration_id,
                limit_per_minute=limit
            )
            assert allowed is False
            
            # Move to 61 seconds (first 3 requests should expire)
            mock_time.return_value = start_time + 61
            
            # Should have room for 3 more requests
            for i in range(3):
                allowed, _ = rate_limiter.check_rate_limit(
                    integration_id=integration_id,
                    limit_per_minute=limit
                )
                assert allowed is True
