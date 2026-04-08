"""
Authentication strategy factory.

Factory pattern implementation for creating appropriate authentication
strategy instances based on integration type configuration.

Requirements: 8.1-8.7
"""

import logging
from typing import Dict, Type

from django.core.exceptions import ValidationError

from .base import BaseAuthStrategy
from .oauth import OAuthStrategy
from .meta import MetaAuthStrategy
from .api_key import APIKeyStrategy


logger = logging.getLogger(__name__)


class AuthStrategyFactory:
    """
    Factory for creating authentication strategy instances.
    
    Uses registry pattern to map auth_type values to strategy classes,
    allowing dynamic extension of supported authentication methods.
    
    Requirements: 8.1-8.7
    - Create strategy based on auth_type (8.1, 8.2, 8.3, 8.4)
    - Raise error for unrecognized auth_type (8.5)
    - Support dynamic registration (8.6)
    - Pass auth_config to strategy (8.7)
    """
    
    # Registry mapping auth_type to strategy class
    _registry: Dict[str, Type[BaseAuthStrategy]] = {
        'oauth': OAuthStrategy,
        'meta': MetaAuthStrategy,
        'api_key': APIKeyStrategy,
    }
    
    @classmethod
    def create_strategy(cls, integration_type) -> BaseAuthStrategy:
        """
        Create appropriate authentication strategy.
        
        Looks up the strategy class based on integration_type.auth_type
        and instantiates it with the integration_type configuration.
        
        Args:
            integration_type: IntegrationTypeModel instance
            
        Returns:
            Instantiated authentication strategy
            
        Raises:
            ValidationError: If auth_type is not recognized
            
        Requirements: 8.1, 8.2, 8.3, 8.4, 8.5, 8.7
        """
        auth_type = integration_type.auth_type
        
        # Look up strategy class in registry
        strategy_class = cls._registry.get(auth_type)
        
        if not strategy_class:
            supported_types = ', '.join(cls._registry.keys())
            error_msg = (
                f"Unknown auth_type: '{auth_type}'. "
                f"Supported types: {supported_types}"
            )
            logger.error(
                f"Failed to create strategy for integration_type "
                f"{integration_type.id}: {error_msg}"
            )
            raise ValidationError(error_msg)
        
        # Instantiate strategy with integration_type
        try:
            strategy = strategy_class(integration_type)
            logger.info(
                f"Created {strategy_class.__name__} for "
                f"integration_type {integration_type.name} (id={integration_type.id})"
            )
            return strategy
        except Exception as e:
            logger.error(
                f"Failed to instantiate {strategy_class.__name__} for "
                f"integration_type {integration_type.id}: {str(e)}"
            )
            raise
    
    @classmethod
    def register_strategy(
        cls,
        auth_type: str,
        strategy_class: Type[BaseAuthStrategy]
    ):
        """
        Register a new authentication strategy.
        
        Allows dynamic extension of supported auth types by registering
        custom strategy implementations at runtime.
        
        Args:
            auth_type: Authentication type identifier
            strategy_class: Strategy class to register
            
        Requirements: 8.6
        """
        if not issubclass(strategy_class, BaseAuthStrategy):
            raise ValueError(
                f"Strategy class must inherit from BaseAuthStrategy, "
                f"got {strategy_class.__name__}"
            )
        
        cls._registry[auth_type] = strategy_class
        logger.info(
            f"Registered {strategy_class.__name__} for auth_type '{auth_type}'"
        )
    
    @classmethod
    def get_supported_auth_types(cls) -> list[str]:
        """
        Get list of supported authentication types.
        
        Returns:
            List of registered auth_type identifiers
        """
        return list(cls._registry.keys())
    
    @classmethod
    def is_auth_type_supported(cls, auth_type: str) -> bool:
        """
        Check if an auth_type is supported.
        
        Args:
            auth_type: Authentication type to check
            
        Returns:
            True if auth_type is registered, False otherwise
        """
        return auth_type in cls._registry
