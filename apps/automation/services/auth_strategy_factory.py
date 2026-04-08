"""
Authentication Strategy Factory

Factory for creating authentication strategy instances based on integration type.
Uses the Strategy pattern with a registry for extensibility.

Requirements: 7.1-7.7, 19.3
"""

import logging
from typing import Dict, Type

from django.core.exceptions import ValidationError

from apps.automation.services.auth_strategy import AuthStrategy
from apps.automation.services.oauth_strategy import OAuthStrategy
from apps.automation.services.meta_strategy import MetaStrategy
from apps.automation.services.api_key_strategy import APIKeyStrategy

logger = logging.getLogger(__name__)


class AuthStrategyFactory:
    """
    Factory for creating authentication strategy instances.
    
    Uses the integration type's auth_type field to determine
    which strategy class to instantiate. Supports dynamic
    registration for extensibility.
    
    Requirements: 7.1-7.7, 19.3
    """
    
    # Strategy registry mapping auth_type to strategy class
    _strategy_registry: Dict[str, Type[AuthStrategy]] = {
        'oauth': OAuthStrategy,
        'meta': MetaStrategy,
        'api_key': APIKeyStrategy,
    }
    
    @classmethod
    def create_strategy(cls, integration_type) -> AuthStrategy:
        """
        Create appropriate authentication strategy for integration type.
        
        Args:
            integration_type: IntegrationTypeModel instance
            
        Returns:
            Concrete AuthStrategy instance (OAuthStrategy, MetaStrategy, or APIKeyStrategy)
            
        Raises:
            ValidationError: If auth_type is unrecognized
            
        Requirements: 7.1, 7.2, 7.3, 7.4, 7.6
        """
        auth_type = integration_type.auth_type
        
        strategy_class = cls._strategy_registry.get(auth_type)
        
        if not strategy_class:
            supported_types = ', '.join(cls._strategy_registry.keys())
            error_msg = (
                f"Unrecognized auth_type: '{auth_type}'. "
                f"Supported types: {supported_types}"
            )
            logger.error(
                f"Failed to create strategy for integration type {integration_type.id}: "
                f"{error_msg}"
            )
            raise ValidationError(error_msg)
        
        # Instantiate strategy with integration type
        strategy = strategy_class(integration_type)
        
        logger.debug(
            f"Created {strategy_class.__name__} for integration type "
            f"{integration_type.name} (auth_type={auth_type})"
        )
        
        return strategy
    
    @classmethod
    def register_strategy(cls, auth_type: str, strategy_class: Type[AuthStrategy]) -> None:
        """
        Register a new authentication strategy.
        
        Enables extensibility for future auth types (e.g., SAML, JWT, custom).
        
        Args:
            auth_type: Authentication type identifier (e.g., 'saml', 'jwt')
            strategy_class: Strategy class to register (must extend AuthStrategy)
            
        Raises:
            TypeError: If strategy_class doesn't extend AuthStrategy
            
        Requirements: 7.5, 7.7, 19.3
        """
        # Validate that strategy_class extends AuthStrategy
        if not issubclass(strategy_class, AuthStrategy):
            raise TypeError(
                f"Strategy class {strategy_class.__name__} must extend AuthStrategy"
            )
        
        cls._strategy_registry[auth_type] = strategy_class
        
        logger.info(
            f"Registered new authentication strategy: {auth_type} -> "
            f"{strategy_class.__name__}"
        )
    
    @classmethod
    def get_supported_auth_types(cls) -> list[str]:
        """
        Get list of supported authentication types.
        
        Returns:
            List of registered auth_type identifiers
        """
        return list(cls._strategy_registry.keys())
    
    @classmethod
    def is_auth_type_supported(cls, auth_type: str) -> bool:
        """
        Check if an auth_type is supported.
        
        Args:
            auth_type: Authentication type identifier
            
        Returns:
            True if auth_type is registered, False otherwise
        """
        return auth_type in cls._strategy_registry
