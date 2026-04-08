"""
Rate limiting utilities using Redis sliding window algorithm.

Requirements: 12.1-12.7
"""

import time
import logging
from typing import Dict, Any, Tuple, Optional
from django.core.cache import cache
from django.conf import settings

logger = logging.getLogger(__name__)


class RateLimiter:
    """
    Redis-based rate limiter using sliding window algorithm.
    
    Enforces per-integration and global rate limits to prevent API quota exhaustion.
    Uses Redis sorted sets for efficient sliding window tracking.
    
    Requirements: 12.1-12.7
    """
    
    def __init__(self, redis_client=None):
        """
        Initialize rate limiter.
        
        Args:
            redis_client: Optional Redis client. If None, uses Django cache.
        """
        self.redis = redis_client or cache
    
    def check_rate_limit(
        self,
        integration_id: str,
        integration_type: Optional['IntegrationTypeModel'] = None,
        limit_per_minute: Optional[int] = None,
        global_limit: int = 100
    ) -> Tuple[bool, int]:
        """
        Check if request is within rate limits.
        
        Enforces both per-integration and global rate limits using sliding window.
        Uses integration_type.rate_limit_config if provided, otherwise falls back to defaults.
        
        Args:
            integration_id: Integration identifier
            integration_type: Optional IntegrationTypeModel to read rate limits from
            limit_per_minute: Per-integration limit (overrides integration_type config)
            global_limit: Global platform limit (default: 100)
            
        Returns:
            Tuple of (allowed, wait_seconds)
            - allowed: True if request is within limits
            - wait_seconds: Seconds to wait if rate limited (0 if allowed)
            
        Requirements: 12.1-12.5, 26.3
        """
        now = time.time()
        window = 60  # 1 minute window in seconds
        
        # Determine per-integration limit
        if limit_per_minute is None:
            if integration_type is not None:
                # Use rate limit from integration type config
                rate_config = integration_type.get_rate_limit_config()
                limit_per_minute = rate_config.get('messages_per_minute', 20)
            else:
                # Fall back to default
                limit_per_minute = 20
        
        # Check per-integration limit
        integration_key = f"rate_limit:integration:{integration_id}"
        integration_allowed, integration_wait = self._check_sliding_window(
            integration_key,
            limit_per_minute,
            window,
            now
        )
        
        if not integration_allowed:
            logger.warning(
                f"Rate limit exceeded for integration {integration_id}. "
                f"Wait {integration_wait} seconds."
            )
            self._log_rate_limit_violation(
                integration_id=integration_id,
                limit_type="per_integration",
                attempted_rate=limit_per_minute,
                timestamp=now
            )
            return False, integration_wait
        
        # Check global limit
        global_key = "rate_limit:global"
        global_allowed, global_wait = self._check_sliding_window(
            global_key,
            global_limit,
            window,
            now
        )
        
        if not global_allowed:
            logger.warning(
                f"Global rate limit exceeded. Wait {global_wait} seconds."
            )
            self._log_rate_limit_violation(
                integration_id=integration_id,
                limit_type="global",
                attempted_rate=global_limit,
                timestamp=now
            )
            return False, global_wait
        
        # Record this request in both windows
        self._record_request(integration_key, now, window)
        self._record_request(global_key, now, window)
        
        return True, 0
    
    def _check_sliding_window(
        self,
        key: str,
        limit: int,
        window: int,
        now: float
    ) -> Tuple[bool, int]:
        """
        Check sliding window rate limit using Redis sorted sets.
        
        Uses ZREMRANGEBYSCORE to remove old entries and ZCARD to count current requests.
        
        Args:
            key: Redis key for this rate limit window
            limit: Maximum requests allowed in window
            window: Time window in seconds
            now: Current timestamp
            
        Returns:
            Tuple of (allowed, wait_seconds)
            
        Requirements: 12.1, 12.2, 12.3
        """
        # Remove old entries outside the sliding window
        cutoff = now - window
        
        try:
            # Try to use Redis commands if available
            if hasattr(self.redis, 'zremrangebyscore'):
                self.redis.zremrangebyscore(key, 0, cutoff)
                count = self.redis.zcard(key)
            else:
                # Fallback for Django cache backend
                count = self._cache_sliding_window_count(key, cutoff, now)
        except Exception as e:
            logger.error(f"Error checking sliding window: {e}")
            # Fail open - allow request if Redis is unavailable
            return True, 0
        
        if count >= limit:
            # Get oldest request timestamp to calculate wait time
            try:
                if hasattr(self.redis, 'zrange'):
                    oldest = self.redis.zrange(key, 0, 0, withscores=True)
                    if oldest:
                        oldest_time = oldest[0][1]
                        wait_seconds = int(oldest_time + window - now) + 1
                        return False, wait_seconds
                else:
                    # Fallback calculation
                    wait_seconds = window
                    return False, wait_seconds
            except Exception as e:
                logger.error(f"Error calculating wait time: {e}")
                return False, window
            
            return False, window
        
        return True, 0
    
    def _record_request(self, key: str, timestamp: float, window: int):
        """
        Record a request in the sliding window.
        
        Adds timestamp to Redis sorted set and sets expiration.
        
        Args:
            key: Redis key for this rate limit window
            timestamp: Request timestamp
            window: Time window in seconds
            
        Requirements: 12.5
        """
        try:
            if hasattr(self.redis, 'zadd'):
                # Redis sorted set
                self.redis.zadd(key, {str(timestamp): timestamp})
                self.redis.expire(key, window + 10)  # Extra buffer for cleanup
            else:
                # Django cache fallback
                self._cache_record_request(key, timestamp, window)
        except Exception as e:
            logger.error(f"Error recording request: {e}")
    
    def get_rate_limit_status(
        self,
        integration_id: str,
        integration_type: Optional['IntegrationTypeModel'] = None,
        limit_per_minute: Optional[int] = None
    ) -> Dict[str, Any]:
        """
        Get current rate limit status for an integration.
        
        Returns current usage and remaining quota.
        Uses integration_type.rate_limit_config if provided, otherwise falls back to defaults.
        
        Args:
            integration_id: Integration identifier
            integration_type: Optional IntegrationTypeModel to read rate limits from
            limit_per_minute: Per-integration limit (overrides integration_type config)
            
        Returns:
            Dictionary with:
            - limit: Maximum requests per minute
            - current: Current request count in window
            - remaining: Remaining quota
            - reset_at: Timestamp when window resets
            
        Requirements: 12.6, 26.3
        """
        now = time.time()
        window = 60
        key = f"rate_limit:integration:{integration_id}"
        
        # Determine per-integration limit
        if limit_per_minute is None:
            if integration_type is not None:
                # Use rate limit from integration type config
                rate_config = integration_type.get_rate_limit_config()
                limit_per_minute = rate_config.get('messages_per_minute', 20)
            else:
                # Fall back to default
                limit_per_minute = 20
        
        # Remove old entries
        cutoff = now - window
        
        try:
            if hasattr(self.redis, 'zremrangebyscore'):
                self.redis.zremrangebyscore(key, 0, cutoff)
                current = self.redis.zcard(key)
            else:
                current = self._cache_sliding_window_count(key, cutoff, now)
        except Exception as e:
            logger.error(f"Error getting rate limit status: {e}")
            current = 0
        
        remaining = max(0, limit_per_minute - current)
        
        return {
            'limit': limit_per_minute,
            'current': current,
            'remaining': remaining,
            'reset_at': now + window
        }
    
    def _log_rate_limit_violation(
        self,
        integration_id: str,
        limit_type: str,
        attempted_rate: int,
        timestamp: float
    ):
        """
        Log rate limit violation for monitoring and debugging.
        
        Args:
            integration_id: Integration identifier
            limit_type: Type of limit exceeded (per_integration or global)
            attempted_rate: Rate that was attempted
            timestamp: Violation timestamp
            
        Requirements: 12.7
        """
        logger.warning(
            f"Rate limit violation - "
            f"integration_id={integration_id}, "
            f"limit_type={limit_type}, "
            f"attempted_rate={attempted_rate}, "
            f"timestamp={timestamp}"
        )
    
    # Django cache fallback methods
    
    def _cache_sliding_window_count(
        self,
        key: str,
        cutoff: float,
        now: float
    ) -> int:
        """
        Count requests in sliding window using Django cache.
        
        Fallback when Redis sorted sets are not available.
        """
        requests = cache.get(key, [])
        # Filter out old requests
        active_requests = [ts for ts in requests if ts > cutoff]
        # Update cache with filtered list
        cache.set(key, active_requests, timeout=70)
        return len(active_requests)
    
    def _cache_record_request(
        self,
        key: str,
        timestamp: float,
        window: int
    ):
        """
        Record request using Django cache.
        
        Fallback when Redis sorted sets are not available.
        """
        requests = cache.get(key, [])
        requests.append(timestamp)
        cache.set(key, requests, timeout=window + 10)
