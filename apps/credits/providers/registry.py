"""
Provider Registry for dynamic AI provider lookup.

Maintains a mapping of model names to provider instances and validates
provider availability on initialization. Enables the ModelRouter to
interact with providers through a unified interface without knowing
implementation details.

Requirements: 8.7, 8.8, 8.10
"""

import logging
from typing import Dict, Optional

from apps.credits.providers.base import AIProvider
from apps.credits.providers.cerebras import CerebrasService
from apps.credits.providers.gemini import GeminiService
from apps.credits.providers.mistral import MistralService
from apps.credits.exceptions import ProviderAPIError


logger = logging.getLogger(__name__)


class ProviderRegistry:
    """
    Registry for AI provider instances with dynamic lookup.
    
    Maintains a mapping of model names to provider instances and provides
    methods for retrieving providers by model name. Validates all providers
    are available on initialization.
    
    Requirements:
    - 8.7: ModelRouter interacts only with AIProvider interface
    - 8.8: Register all provider implementations for dynamic lookup
    - 8.10: Validate provider availability before routing requests
    """
    
    def __init__(self):
        """
        Initialize provider registry and register all providers.
        
        Creates instances of all provider services and maps model names
        to their corresponding provider instances. Validates that all
        providers are properly configured.
        
        Requirements: 8.8, 8.10
        """
        self._providers: Dict[str, AIProvider] = {}
        self._register_providers()
        self._validate_providers()
    
    def _register_providers(self) -> None:
        """
        Register all provider instances in the registry.
        
        Creates provider instances and maps model names to providers:
        - cerebras → CerebrasService
        - mistral → MistralService
        - gemini-2.5-flash → GeminiService(model="gemini-2.5-flash")
        - gemini-2.5-pro → GeminiService(model="gemini-2.5-pro")
        - gemini-3-pro → GeminiService(model="gemini-3-pro")
        - gemini-3.1-pro → GeminiService(model="gemini-3.1-pro")
        
        Requirements: 8.8
        """
        try:
            # Register Cerebras provider
            self._providers['cerebras'] = CerebrasService()
            logger.info("[ProviderRegistry] Registered CerebrasService for model: cerebras")
            
            # Register Mistral provider
            self._providers['mistral'] = MistralService()
            logger.info("[ProviderRegistry] Registered MistralService for model: mistral")
            
            # Register Gemini providers for each model variant
            gemini_models = [
                'gemini-2.5-flash',
                'gemini-2.5-pro',
                'gemini-3-pro',
                'gemini-3.1-pro'
            ]
            
            for model in gemini_models:
                self._providers[model] = GeminiService(model=model)
                logger.info(f"[ProviderRegistry] Registered GeminiService for model: {model}")
            
            logger.info(
                f"[ProviderRegistry] Successfully registered {len(self._providers)} providers"
            )
        
        except Exception as e:
            logger.error(
                f"[ProviderRegistry] Failed to register providers: {str(e)}",
                exc_info=True
            )
            raise ProviderAPIError(
                f"Provider registration failed: {str(e)}"
            )
    
    def _validate_providers(self) -> None:
        """
        Validate that all registered providers are available.
        
        Checks that each provider has required configuration (API keys)
        and logs warnings for providers that may not be fully configured.
        Does not fail initialization if providers are missing API keys,
        but logs warnings for visibility.
        
        Requirements: 8.10
        """
        logger.info("[ProviderRegistry] Validating provider availability...")
        
        validation_results = []
        
        for model_name, provider in self._providers.items():
            try:
                # Check if provider has API key configured
                if hasattr(provider, 'api_key'):
                    if not provider.api_key:
                        logger.warning(
                            f"[ProviderRegistry] Provider '{model_name}' has no API key configured. "
                            f"Requests to this provider will fail."
                        )
                        validation_results.append((model_name, False, "Missing API key"))
                    else:
                        logger.info(
                            f"[ProviderRegistry] Provider '{model_name}' is configured"
                        )
                        validation_results.append((model_name, True, "OK"))
                else:
                    # Provider doesn't have api_key attribute (unexpected)
                    logger.warning(
                        f"[ProviderRegistry] Provider '{model_name}' has no api_key attribute"
                    )
                    validation_results.append((model_name, False, "No api_key attribute"))
            
            except Exception as e:
                logger.error(
                    f"[ProviderRegistry] Validation failed for provider '{model_name}': {str(e)}",
                    exc_info=True
                )
                validation_results.append((model_name, False, str(e)))
        
        # Log summary
        configured_count = sum(1 for _, is_valid, _ in validation_results if is_valid)
        total_count = len(validation_results)
        
        logger.info(
            f"[ProviderRegistry] Validation complete: "
            f"{configured_count}/{total_count} providers fully configured"
        )
        
        # Log details of unconfigured providers
        unconfigured = [
            (name, reason) for name, is_valid, reason in validation_results if not is_valid
        ]
        if unconfigured:
            logger.warning(
                f"[ProviderRegistry] Unconfigured providers: "
                f"{', '.join(f'{name} ({reason})' for name, reason in unconfigured)}"
            )
    
    def get_provider(self, model_name: str) -> AIProvider:
        """
        Retrieve provider instance for the specified model name.
        
        Performs dynamic lookup of provider by model name and returns
        the corresponding AIProvider instance. Raises clear error if
        model is not registered.
        
        Args:
            model_name: Model identifier (e.g., 'cerebras', 'gemini-2.5-flash')
        
        Returns:
            AIProvider: Provider instance for the specified model
        
        Raises:
            ProviderAPIError: If model_name is not registered in the registry
        
        Requirements: 8.7, 8.8
        """
        if not model_name:
            raise ProviderAPIError("model_name cannot be empty")
        
        provider = self._providers.get(model_name)
        
        if provider is None:
            available_models = ', '.join(sorted(self._providers.keys()))
            error_message = (
                f"Model '{model_name}' is not registered in provider registry. "
                f"Available models: {available_models}"
            )
            logger.error(f"[ProviderRegistry] {error_message}")
            raise ProviderAPIError(error_message)
        
        logger.debug(
            f"[ProviderRegistry] Retrieved provider for model: {model_name} "
            f"(provider type: {provider.__class__.__name__})"
        )
        
        return provider
    
    def get_registered_models(self) -> list[str]:
        """
        Get list of all registered model names.
        
        Returns:
            list[str]: Sorted list of registered model names
        """
        return sorted(self._providers.keys())
    
    def is_model_registered(self, model_name: str) -> bool:
        """
        Check if a model is registered in the registry.
        
        Args:
            model_name: Model identifier to check
        
        Returns:
            bool: True if model is registered, False otherwise
        """
        return model_name in self._providers
    
    def __repr__(self) -> str:
        """String representation of the registry."""
        models = ', '.join(sorted(self._providers.keys()))
        return f"ProviderRegistry(models=[{models}])"


# Global registry instance
# This is initialized once when the module is imported
_registry: Optional[ProviderRegistry] = None


def get_registry() -> ProviderRegistry:
    """
    Get the global provider registry instance.
    
    Creates the registry on first call and returns the same instance
    on subsequent calls (singleton pattern).
    
    Returns:
        ProviderRegistry: Global provider registry instance
    """
    global _registry
    
    if _registry is None:
        logger.info("[ProviderRegistry] Initializing global provider registry")
        _registry = ProviderRegistry()
    
    return _registry
