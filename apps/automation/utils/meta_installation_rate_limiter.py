"""
Meta installation rate limiting utilities.

Implements global rate limiting for Meta integration installations to prevent
exceeding Meta's onboarding quotas.

Requirements: 14.1-14.7
"""

import time
import logging
from typing import Tuple
from django.core.cache import cache
from django.conf import settings

logger = logging.getLogger(__name__)


class MetaInstallationRateLimiter:
    """
    Global rate limiter for Meta integration installations.
    
    Enforces a global limit of 5 Meta installations per minute across all users
    to prevent exceeding Meta's onboarding quotas. Admin users are exempted from
    this limit.
    
    Requirements: 14.1-14.7
    """
    
    # Global rate limit: 5 installations per minute
    INSTALLATIONS_PER_MINUTE = 5
    WINDOW_SECONDS = 60
    
    def __init__(self, redis_client=None):
        """
        Initialize Meta installation rate limiter.
        
        Args:
            redis_client: Optional Redis client. If None, uses Django cache.
        """
        self.redis = redis_client or cache
    
    def check_installation_limit(
        self,
        user_id: str,
        is_admin: bool = False
    ) -> Tuple[bool, int]:
        """
        Check if Meta installation is within global rate limit.
        
        Admin users are exempted from rate limiting.
        
        Args:
            user_id: User identifier attempting installation
            is_admin: Whether user has admin privileges
            
        Returns:
            Tuple of (allowed, wait_seconds)
            - allowed: True if installation is within limits
            - wait_seconds: Seconds to wait if rate limited (0 if allowed)
            
        Requirements: 14.1-14.5
        """
        # Exempt admin users from rate limiting
        if is_admin:
            logger.info(
                f"Meta installation rate limit exempted for admin user {user_id}"
            )
            return True, 0
        
        now = time.time()
        key = "rate_limit:meta_installation:global"
        
        # Check sliding window
        allowed, wait_seconds = self._check_sliding_window(
            key,
            self.INSTALLATIONS_PER_MINUTE,
            self.WINDOW_SECONDS,
            now
        )
        
        if not allowed:
            logger.warning(
                f"Meta installation rate limit exceeded. "
                f"User {user_id} must wait {wait_seconds} seconds."
            )
            self._log_rate_limit_violation(user_id, now)
            return False, wait_seconds
        
        # Record this installation attempt
        self._record_installation(key, now, self.WINDOW_SECONDS)
        
        logger.info(
            f"Meta installation allowed for user {user_id}. "
            f"Current rate: {self._get_current_count(key, now)} installations/minute"
        )
        
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
        
        Args:
            key: Redis key for this rate limit window
            limit: Maximum installations allowed in window
            window: Time window in seconds
            now: Current timestamp
            
        Returns:
            Tuple of (allowed, wait_seconds)
            
        Requirements: 14.1-14.2
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
            logger.error(f"Error checking Meta installation sliding window: {e}")
            # Fail open - allow installation if Redis is unavailable
            return True, 0
        
        if count >= limit:
            # Get oldest installation timestamp to calculate wait time
            try:
                if hasattr(self.redis, 'zrange'):
                    oldest = self.redis.zrange(key, 0, 0, withscores=True)
                    if oldest:
                        oldest_time = oldest[0][1]
                        wait_seconds = int(oldest_time + window - now) + 1
                        return False, wait_seconds
                else:
                    # Fallback calculation
                    return False, window
            except Exception as e:
                logger.error(f"Error calculating wait time: {e}")
                return False, window
            
            return False, window
        
        return True, 0
    
    def _record_installation(self, key: str, timestamp: float, window: int):
        """
        Record a Meta installation attempt in the sliding window.
        
        Args:
            key: Redis key for this rate limit window
            timestamp: Installation timestamp
            window: Time window in seconds
            
        Requirements: 14.2
        """
        try:
            if hasattr(self.redis, 'zadd'):
                # Redis sorted set
                self.redis.zadd(key, {str(timestamp): timestamp})
                self.redis.expire(key, window + 10)  # Extra buffer for cleanup
            else:
                # Django cache fallback
                self._cache_record_installation(key, timestamp, window)
        except Exception as e:
            logger.error(f"Error recording Meta installation: {e}")
    
    def _get_current_count(self, key: str, now: float) -> int:
        """
        Get current count of installations in the window.
        
        Args:
            key: Redis key for this rate limit window
            now: Current timestamp
            
        Returns:
            Current installation count
        """
        cutoff = now - self.WINDOW_SECONDS
        
        try:
            if hasattr(self.redis, 'zremrangebyscore'):
                self.redis.zremrangebyscore(key, 0, cutoff)
                return self.redis.zcard(key)
            else:
                return self._cache_sliding_window_count(key, cutoff, now)
        except Exception as e:
            logger.error(f"Error getting current Meta installation count: {e}")
            return 0
    
    def _log_rate_limit_violation(self, user_id: str, timestamp: float):
        """
        Log Meta installation rate limit violation.
        
        Args:
            user_id: User identifier
            timestamp: Violation timestamp
            
        Requirements: 14.6
        """
        logger.warning(
            f"Meta installation rate limit violation - "
            f"user_id={user_id}, "
            f"limit={self.INSTALLATIONS_PER_MINUTE}/minute, "
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
        Count installations in sliding window using Django cache.
        
        Fallback when Redis sorted sets are not available.
        """
        installations = cache.get(key, [])
        # Filter out old installations
        active_installations = [ts for ts in installations if ts > cutoff]
        # Update cache with filtered list
        cache.set(key, active_installations, timeout=70)
        return len(active_installations)
    
    def _cache_record_installation(
        self,
        key: str,
        timestamp: float,
        window: int
    ):
        """
        Record installation using Django cache.
        
        Fallback when Redis sorted sets are not available.
        """
        installations = cache.get(key, [])
        installations.append(timestamp)
        cache.set(key, installations, timeout=window + 10)
