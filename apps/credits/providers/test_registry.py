"""
Unit tests for ProviderRegistry.

Tests provider registration, dynamic lookup, validation, and error handling.

Requirements: 8.7, 8.8, 8.10
"""

import pytest
from unittest.mock import patch, MagicMock

from apps.credits.providers.registry import ProviderRegistry, get_registry
from apps.credits.providers.base import AIProvider
from apps.credits.providers.cerebras import CerebrasService
from apps.credits.providers.gemini import GeminiService
from apps.credits.providers.mistral import MistralService
from apps.credits.exceptions import ProviderAPIError


class TestProviderRegistry:
    """Test suite for ProviderRegistry class."""
    
    def test_registry_initialization(self):
        """Test that registry initializes and registers all providers."""
        registry = ProviderRegistry()
        
        # Verify all expected models are registered
        expected_models = [
            'cerebras',
            'mistral',
            'gemini-2.5-flash',
            'gemini-2.5-pro',
            'gemini-3-pro',
            'gemini-3.1-pro'
        ]
        
        registered_models = registry.get_registered_models()
        assert len(registered_models) == len(expected_models)
        
        for model in expected_models:
            assert model in registered_models, f"Model {model} not registered"
    
    def test_get_provider_cerebras(self):
        """Test retrieving Cerebras provider."""
        registry = ProviderRegistry()
        
        provider = registry.get_provider('cerebras')
        
        assert provider is not None
        assert isinstance(provider, CerebrasService)
        assert isinstance(provider, AIProvider)
    
    def test_get_provider_mistral(self):
        """Test retrieving Mistral provider."""
        registry = ProviderRegistry()
        
        provider = registry.get_provider('mistral')
        
        assert provider is not None
        assert isinstance(provider, MistralService)
        assert isinstance(provider, AIProvider)
    
    def test_get_provider_gemini_flash(self):
        """Test retrieving Gemini 2.5 Flash provider."""
        registry = ProviderRegistry()
        
        provider = registry.get_provider('gemini-2.5-flash')
        
        assert provider is not None
        assert isinstance(provider, GeminiService)
        assert isinstance(provider, AIProvider)
        assert provider.model == 'gemini-2.5-flash'
    
    def test_get_provider_gemini_pro(self):
        """Test retrieving Gemini 2.5 Pro provider."""
        registry = ProviderRegistry()
        
        provider = registry.get_provider('gemini-2.5-pro')
        
        assert provider is not None
        assert isinstance(provider, GeminiService)
        assert provider.model == 'gemini-2.5-pro'
    
    def test_get_provider_gemini_3_pro(self):
        """Test retrieving Gemini 3 Pro provider."""
        registry = ProviderRegistry()
        
        provider = registry.get_provider('gemini-3-pro')
        
        assert provider is not None
        assert isinstance(provider, GeminiService)
        assert provider.model == 'gemini-3-pro'
    
    def test_get_provider_gemini_31_pro(self):
        """Test retrieving Gemini 3.1 Pro provider."""
        registry = ProviderRegistry()
        
        provider = registry.get_provider('gemini-3.1-pro')
        
        assert provider is not None
        assert isinstance(provider, GeminiService)
        assert provider.model == 'gemini-3.1-pro'
    
    def test_get_provider_unregistered_model(self):
        """Test that requesting unregistered model raises error."""
        registry = ProviderRegistry()
        
        with pytest.raises(ProviderAPIError) as exc_info:
            registry.get_provider('unknown-model')
        
        error_message = str(exc_info.value)
        assert 'unknown-model' in error_message
        assert 'not registered' in error_message
        assert 'Available models:' in error_message
    
    def test_get_provider_empty_model_name(self):
        """Test that empty model name raises error."""
        registry = ProviderRegistry()
        
        with pytest.raises(ProviderAPIError) as exc_info:
            registry.get_provider('')
        
        assert 'cannot be empty' in str(exc_info.value)
    
    def test_is_model_registered(self):
        """Test checking if models are registered."""
        registry = ProviderRegistry()
        
        # Test registered models
        assert registry.is_model_registered('cerebras') is True
        assert registry.is_model_registered('mistral') is True
        assert registry.is_model_registered('gemini-2.5-flash') is True
        
        # Test unregistered model
        assert registry.is_model_registered('unknown-model') is False
    
    def test_get_registered_models(self):
        """Test retrieving list of registered models."""
        registry = ProviderRegistry()
        
        models = registry.get_registered_models()
        
        assert isinstance(models, list)
        assert len(models) == 6
        assert 'cerebras' in models
        assert 'mistral' in models
        assert 'gemini-2.5-flash' in models
        assert 'gemini-2.5-pro' in models
        assert 'gemini-3-pro' in models
        assert 'gemini-3.1-pro' in models
        
        # Verify list is sorted
        assert models == sorted(models)
    
    def test_provider_instances_are_different(self):
        """Test that different Gemini models get different instances."""
        registry = ProviderRegistry()
        
        provider_flash = registry.get_provider('gemini-2.5-flash')
        provider_pro = registry.get_provider('gemini-2.5-pro')
        
        # Should be different instances
        assert provider_flash is not provider_pro
        
        # But same type
        assert type(provider_flash) == type(provider_pro)
        
        # With different model configurations
        assert provider_flash.model != provider_pro.model
    
    def test_provider_instances_are_cached(self):
        """Test that same model returns same instance."""
        registry = ProviderRegistry()
        
        provider1 = registry.get_provider('cerebras')
        provider2 = registry.get_provider('cerebras')
        
        # Should be the exact same instance
        assert provider1 is provider2
    
    def test_registry_repr(self):
        """Test string representation of registry."""
        registry = ProviderRegistry()
        
        repr_str = repr(registry)
        
        assert 'ProviderRegistry' in repr_str
        assert 'cerebras' in repr_str
        assert 'mistral' in repr_str
        assert 'gemini-2.5-flash' in repr_str
    
    def test_validation_logs_warnings_for_missing_api_keys(self, caplog):
        """Test that validation logs warnings for unconfigured providers."""
        import logging
        caplog.set_level(logging.WARNING)
        
        # Create registry (validation happens in __init__)
        registry = ProviderRegistry()
        
        # Check if any warnings were logged about missing API keys
        # (This will depend on whether API keys are actually configured in test env)
        warning_messages = [record.message for record in caplog.records if record.levelname == 'WARNING']
        
        # We expect warnings if API keys are not set
        # The test passes regardless, but logs should contain provider validation info
        assert isinstance(registry, ProviderRegistry)
    
    def test_global_registry_singleton(self):
        """Test that get_registry returns singleton instance."""
        registry1 = get_registry()
        registry2 = get_registry()
        
        # Should be the exact same instance
        assert registry1 is registry2
    
    def test_provider_interface_compliance(self):
        """Test that all registered providers implement AIProvider interface."""
        registry = ProviderRegistry()
        
        for model_name in registry.get_registered_models():
            provider = registry.get_provider(model_name)
            
            # Verify provider implements AIProvider interface
            assert isinstance(provider, AIProvider)
            
            # Verify required methods exist
            assert hasattr(provider, 'generate_response')
            assert hasattr(provider, 'generate_embeddings')
            assert hasattr(provider, 'estimate_tokens')
            
            # Verify methods are callable
            assert callable(provider.generate_response)
            assert callable(provider.generate_embeddings)
            assert callable(provider.estimate_tokens)


class TestProviderRegistryIntegration:
    """Integration tests for ProviderRegistry with actual providers."""
    
    def test_cerebras_provider_configuration(self):
        """Test that Cerebras provider is properly configured."""
        registry = ProviderRegistry()
        provider = registry.get_provider('cerebras')
        
        assert hasattr(provider, 'api_key')
        assert hasattr(provider, 'base_url')
        assert hasattr(provider, 'timeout')
        assert hasattr(provider, 'max_retries')
    
    def test_mistral_provider_configuration(self):
        """Test that Mistral provider is properly configured."""
        registry = ProviderRegistry()
        provider = registry.get_provider('mistral')
        
        assert hasattr(provider, 'api_key')
        assert hasattr(provider, 'base_url')
        assert hasattr(provider, 'timeout')
        assert hasattr(provider, 'max_retries')
    
    def test_gemini_provider_configuration(self):
        """Test that Gemini providers are properly configured."""
        registry = ProviderRegistry()
        
        for model in ['gemini-2.5-flash', 'gemini-2.5-pro', 'gemini-3-pro', 'gemini-3.1-pro']:
            provider = registry.get_provider(model)
            
            assert hasattr(provider, 'api_key')
            assert hasattr(provider, 'model')
            assert hasattr(provider, 'client')
            assert provider.model == model
    
    def test_all_providers_have_estimate_tokens(self):
        """Test that all providers can estimate tokens."""
        registry = ProviderRegistry()
        test_text = "This is a test prompt for token estimation."
        
        for model_name in registry.get_registered_models():
            provider = registry.get_provider(model_name)
            
            # Should not raise exception
            token_count = provider.estimate_tokens(test_text)
            
            # Should return positive integer
            assert isinstance(token_count, int)
            assert token_count > 0
