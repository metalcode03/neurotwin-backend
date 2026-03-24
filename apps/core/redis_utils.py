"""
Redis Utility Functions
Centralized Redis operations for NeuroTwin platform

Requirements:
- 17.1: Cache frequently accessed cognitive profiles
- 17.2: Session management
- 17.3: Rate limiting
- 18.7: API rate limiting
"""

from typing import Any, Optional, Callable
from django.core.cache import cache
from django.utils import timezone
from django_redis import get_redis_connection
import json
import logging

logger = logging.getLogger(__name__)


class CacheKeys:
    """Centralized cache key definitions."""
    
    # Cognitive Signature Model
    CSM_PROFILE = 'csm:profile:{user_id}'
    CSM_BLEND = 'csm:blend:{user_id}'
    
    # User Session
    USER_SESSION = 'session:{user_id}'
    USER_PREFERENCES = 'preferences:{user_id}'
    
    # Integration & Automation
    INTEGRATION_TYPES = 'integration_types:{category}'
    USER_INSTALLATIONS = 'installations:{user_id}'
    WORKFLOW_CONFIG = 'workflow:{workflow_id}'
    
    # OAuth
    OAUTH_STATE = 'oauth_state:{state}'
    OAUTH_TOKEN = 'oauth_token:{user_id}:{integration_id}'
    
    # Rate Limiting
    RATE_LIMIT = 'rate_limit:{action}:{user_id}'
    
    # Memory & Learning
    MEMORY_CACHE = 'memory:{user_id}:{memory_id}'
    LEARNING_STATS = 'learning:stats:{user_id}'


class CacheTTL:
    """Centralized TTL definitions (in seconds)."""
    
    MINUTE_1 = 60
    MINUTE_5 = 300
    MINUTE_10 = 600
    MINUTE_30 = 1800
    HOUR_1 = 3600
    HOUR_6 = 21600
    HOUR_12 = 43200
    DAY_1 = 86400
    WEEK_1 = 604800


def get_cached(
    key: str,
    fetch_func: Callable,
    timeout: int = CacheTTL.MINUTE_5,
    force_refresh: bool = False
) -> Any:
    """
    Get value from cache or fetch and cache it.
    
    Args:
        key: Cache key
        fetch_func: Function to fetch data if cache miss
        timeout: Cache timeout in seconds
        force_refresh: Force refresh from source
    
    Returns:
        Cached or fetched value
    """
    if not force_refresh:
        value = cache.get(key)
        if value is not None:
            logger.debug(f"Cache hit: {key}")
            return value
    
    logger.debug(f"Cache miss: {key}")
    value = fetch_func()
    cache.set(key, value, timeout=timeout)
    return value


def invalidate_pattern(pattern: str) -> int:
    """
    Invalidate all cache keys matching pattern.
    
    Args:
        pattern: Redis key pattern (e.g., 'user:123:*')
    
    Returns:
        Number of keys deleted
    """
    try:
        redis_conn = get_redis_connection('default')
        # Add key prefix
        full_pattern = f'neurotwin:{pattern}'
        keys = redis_conn.keys(full_pattern)
        
        if keys:
            count = redis_conn.delete(*keys)
            logger.info(f"Invalidated {count} keys matching pattern: {pattern}")
            return count
        return 0
    except Exception as e:
        logger.error(f"Failed to invalidate pattern {pattern}: {e}")
        return 0


def check_rate_limit(
    user_id: int,
    action: str,
    limit: int,
    window: int
) -> tuple[bool, int]:
    """
    Check if user has exceeded rate limit.
    
    Requirements: 18.7 - Rate limiting
    
    Args:
        user_id: User identifier
        action: Action being rate limited
        limit: Maximum number of actions allowed
        window: Time window in seconds
    
    Returns:
        Tuple of (allowed: bool, remaining: int)
    """
    cache_key = CacheKeys.RATE_LIMIT.format(action=action, user_id=user_id)
    
    try:
        # Get current count
        count = cache.get(cache_key, 0)
        
        if count >= limit:
            logger.warning(f"Rate limit exceeded for user {user_id}, action {action}")
            return False, 0
        
        # Increment counter
        if count == 0:
            # First request - set with expiry
            cache.set(cache_key, 1, timeout=window)
        else:
            # Subsequent request - increment
            cache.incr(cache_key)
        
        remaining = limit - (count + 1)
        return True, remaining
        
    except Exception as e:
        logger.error(f"Rate limit check failed: {e}")
        # Fail open - allow request if Redis is down
        return True, limit


def reset_rate_limit(user_id: int, action: str) -> None:
    """Reset rate limit counter for user and action."""
    cache_key = CacheKeys.RATE_LIMIT.format(action=action, user_id=user_id)
    cache.delete(cache_key)
    logger.info(f"Reset rate limit for user {user_id}, action {action}")


def cache_cognitive_profile(user_id: int, profile_data: dict) -> None:
    """
    Cache cognitive profile data.
    
    Requirements: 17.1 - Cache frequently accessed cognitive profiles
    """
    cache_key = CacheKeys.CSM_PROFILE.format(user_id=user_id)
    cache.set(cache_key, profile_data, timeout=CacheTTL.MINUTE_5)
    logger.debug(f"Cached cognitive profile for user {user_id}")


def get_cognitive_profile(user_id: int) -> Optional[dict]:
    """Get cached cognitive profile."""
    cache_key = CacheKeys.CSM_PROFILE.format(user_id=user_id)
    return cache.get(cache_key)


def invalidate_cognitive_profile(user_id: int) -> None:
    """Invalidate cognitive profile cache."""
    cache_key = CacheKeys.CSM_PROFILE.format(user_id=user_id)
    cache.delete(cache_key)
    logger.info(f"Invalidated cognitive profile cache for user {user_id}")


def cache_user_session(user_id: int, session_data: dict) -> None:
    """
    Cache user session data.
    
    Requirements: 17.2 - Session management
    """
    cache_key = CacheKeys.USER_SESSION.format(user_id=user_id)
    cache.set(cache_key, session_data, timeout=CacheTTL.HOUR_1)
    logger.debug(f"Cached session for user {user_id}")


def get_user_session(user_id: int) -> Optional[dict]:
    """Get cached user session."""
    cache_key = CacheKeys.USER_SESSION.format(user_id=user_id)
    return cache.get(cache_key)


def invalidate_user_session(user_id: int) -> None:
    """Invalidate user session cache."""
    cache_key = CacheKeys.USER_SESSION.format(user_id=user_id)
    cache.delete(cache_key)
    logger.info(f"Invalidated session cache for user {user_id}")


def cache_oauth_state(state: str, data: dict, timeout: int = CacheTTL.MINUTE_10) -> None:
    """
    Cache OAuth state token.
    
    Requirements: 18.4 - OAuth flow state management
    """
    cache_key = CacheKeys.OAUTH_STATE.format(state=state)
    cache.set(cache_key, data, timeout=timeout)
    logger.debug(f"Cached OAuth state: {state}")


def get_oauth_state(state: str, consume: bool = True) -> Optional[dict]:
    """
    Get and optionally consume OAuth state token.
    
    Args:
        state: OAuth state token
        consume: If True, delete after retrieval (one-time use)
    """
    cache_key = CacheKeys.OAUTH_STATE.format(state=state)
    data = cache.get(cache_key)
    
    if data and consume:
        cache.delete(cache_key)
        logger.debug(f"Consumed OAuth state: {state}")
    
    return data


def cache_integration_types(category: Optional[str], types: list) -> None:
    """Cache integration types listing."""
    cache_key = CacheKeys.INTEGRATION_TYPES.format(category=category or 'all')
    cache.set(cache_key, types, timeout=CacheTTL.MINUTE_5)
    logger.debug(f"Cached integration types for category: {category or 'all'}")


def get_integration_types(category: Optional[str]) -> Optional[list]:
    """Get cached integration types."""
    cache_key = CacheKeys.INTEGRATION_TYPES.format(category=category or 'all')
    return cache.get(cache_key)


def invalidate_integration_types() -> None:
    """Invalidate all integration types caches."""
    invalidate_pattern('integration_types:*')


def cache_user_installations(user_id: int, installations: list) -> None:
    """Cache user's installed integrations."""
    cache_key = CacheKeys.USER_INSTALLATIONS.format(user_id=user_id)
    cache.set(cache_key, installations, timeout=CacheTTL.MINUTE_1)
    logger.debug(f"Cached installations for user {user_id}")


def get_user_installations(user_id: int) -> Optional[list]:
    """Get cached user installations."""
    cache_key = CacheKeys.USER_INSTALLATIONS.format(user_id=user_id)
    return cache.get(cache_key)


def invalidate_user_installations(user_id: int) -> None:
    """Invalidate user installations cache."""
    cache_key = CacheKeys.USER_INSTALLATIONS.format(user_id=user_id)
    cache.delete(cache_key)
    logger.info(f"Invalidated installations cache for user {user_id}")


def get_cache_stats() -> dict:
    """
    Get cache statistics.
    
    Returns:
        Dictionary with cache statistics
    """
    try:
        redis_conn = get_redis_connection('default')
        info = redis_conn.info()
        
        return {
            'connected_clients': info.get('connected_clients', 0),
            'used_memory_human': info.get('used_memory_human', 'N/A'),
            'total_commands_processed': info.get('total_commands_processed', 0),
            'keyspace_hits': info.get('keyspace_hits', 0),
            'keyspace_misses': info.get('keyspace_misses', 0),
            'hit_rate': calculate_hit_rate(
                info.get('keyspace_hits', 0),
                info.get('keyspace_misses', 0)
            ),
        }
    except Exception as e:
        logger.error(f"Failed to get cache stats: {e}")
        return {}


def calculate_hit_rate(hits: int, misses: int) -> float:
    """Calculate cache hit rate percentage."""
    total = hits + misses
    if total == 0:
        return 0.0
    return round((hits / total) * 100, 2)


def test_redis_connection() -> bool:
    """
    Test Redis connection.
    
    Returns:
        True if connection successful, False otherwise
    """
    try:
        redis_conn = get_redis_connection('default')
        redis_conn.ping()
        logger.info("✓ Redis connection successful")
        return True
    except Exception as e:
        logger.error(f"✗ Redis connection failed: {e}")
        return False


def clear_all_cache() -> None:
    """
    Clear all cache (use with caution).
    
    WARNING: This will clear ALL cached data.
    """
    try:
        cache.clear()
        logger.warning("Cleared all cache data")
    except Exception as e:
        logger.error(f"Failed to clear cache: {e}")


def get_cache_size() -> int:
    """
    Get approximate number of keys in cache.
    
    Returns:
        Number of keys with 'neurotwin:' prefix
    """
    try:
        redis_conn = get_redis_connection('default')
        keys = redis_conn.keys('neurotwin:*')
        return len(keys)
    except Exception as e:
        logger.error(f"Failed to get cache size: {e}")
        return 0
