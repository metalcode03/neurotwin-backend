"""
Circuit Breaker Registry

Manages circuit breaker instances for external API calls.
Provides pre-configured circuit breakers for OAuth, Meta, and API Key services.

Requirements: 32.3-32.4
"""

import logging
from typing import Dict
from .circuit_breaker import CircuitBreaker

logger = logging.getLogger(__name__)


class CircuitBreakerRegistry:
    """
    Registry for managing circuit breaker instances.
    
    Provides singleton circuit breakers for different external services
    to prevent cascading failures across the integration system.
    
    Requirements: 32.3-32.4
    """
    
    _breakers: Dict[str, CircuitBreaker] = {}
    
    @classmethod
    def get_oauth_breaker(cls, provider_name: str = "oauth") -> CircuitBreaker:
        """
        Get circuit breaker for OAuth provider calls.
        
        Args:
            provider_name: Name of OAuth provider (for logging)
            
        Returns:
            CircuitBreaker instance for OAuth calls
        """
        key = f"oauth_{provider_name}"
        if key not in cls._breakers:
            cls._breakers[key] = CircuitBreaker(
                name=f"OAuth-{provider_name}",
                failure_threshold=5,
                timeout=60,  # 60 seconds as per requirement 32.4
                success_threshold=2
            )
            logger.info(f"Created circuit breaker for OAuth provider: {provider_name}")
        return cls._breakers[key]
    
    @classmethod
    def get_meta_breaker(cls) -> CircuitBreaker:
        """
        Get circuit breaker for Meta API calls.
        
        Returns:
            CircuitBreaker instance for Meta calls
        """
        key = "meta"
        if key not in cls._breakers:
            cls._breakers[key] = CircuitBreaker(
                name="Meta-Graph-API",
                failure_threshold=5,
                timeout=60,  # 60 seconds as per requirement 32.4
                success_threshold=2
            )
            logger.info("Created circuit breaker for Meta Graph API")
        return cls._breakers[key]
    
    @classmethod
    def get_api_key_breaker(cls, service_name: str) -> CircuitBreaker:
        """
        Get circuit breaker for API key service calls.
        
        Args:
            service_name: Name of API key service (for logging)
            
        Returns:
            CircuitBreaker instance for API key calls
        """
        key = f"api_key_{service_name}"
        if key not in cls._breakers:
            cls._breakers[key] = CircuitBreaker(
                name=f"APIKey-{service_name}",
                failure_threshold=5,
                timeout=60,  # 60 seconds as per requirement 32.4
                success_threshold=2
            )
            logger.info(f"Created circuit breaker for API key service: {service_name}")
        return cls._breakers[key]
    
    @classmethod
    def get_breaker_status(cls) -> Dict[str, dict]:
        """
        Get status of all circuit breakers.
        
        Returns:
            Dictionary mapping breaker names to their status
        """
        return {
            name: breaker.get_status()
            for name, breaker in cls._breakers.items()
        }
    
    @classmethod
    def reset_all(cls):
        """Reset all circuit breakers to CLOSED state"""
        for name, breaker in cls._breakers.items():
            breaker.reset()
            logger.info(f"Reset circuit breaker: {name}")
