"""
Tests for caching layer.

Requirements: 17.1, 17.2, 17.3, 17.4, 17.5
"""

import pytest
from django.core.cache import cache
from django.contrib.auth import get_user_model

from apps.automation.models import IntegrationTypeModel, Integration, IntegrationCategory
from apps.automation.cache import MarketplaceCache
from apps.automation.services.marketplace import AppMarketplaceService

User = get_user_model()


@pytest.mark.django_db
class TestMarketplaceCache:
    """Test marketplace caching functionality."""
    
    def test_cache_active_types(self):
        """Test caching of active integration types."""
        # Create test integration type
        integration_type = IntegrationTypeModel.objects.create(
            type='test-integration',
            name='Test Integration',
            description='Test description',
            brief_description='Test brief',
            category=IntegrationCategory.COMMUNICATION
        )
        
        # Cache should be empty initially
        cached = MarketplaceCache.get_active_types()
        assert cached is None
        
        # Cache the IDs
        MarketplaceCache.cache_active_types([str(integration_type.id)])
        
        # Should now be cached
        cached = MarketplaceCache.get_active_types()
        assert cached is not None
        assert str(integration_type.id) in cached
        
        # Invalidate cache
        MarketplaceCache.invalidate_active_types()
        
        # Should be empty again
        cached = MarketplaceCache.get_active_types()
        assert cached is None
    
    def test_cache_user_installed(self, django_user_model):
        """Test caching of user's installed integrations."""
        # Create test user
        user = django_user_model.objects.create_user(
            email='test@example.com',
            password='testpass123'
        )
        
        # Create test integration type
        integration_type = IntegrationTypeModel.objects.create(
            type='test-integration',
            name='Test Integration',
            description='Test description',
            brief_description='Test brief',
            category=IntegrationCategory.COMMUNICATION
        )
        
        # Cache should be empty initially
        cached = MarketplaceCache.get_user_installed(user.id)
        assert cached is None
        
        # Cache the installed types
        installed_ids = {str(integration_type.id)}
        MarketplaceCache.cache_user_installed(user.id, installed_ids)
        
        # Should now be cached
        cached = MarketplaceCache.get_user_installed(user.id)
        assert cached is not None
        assert str(integration_type.id) in cached
        
        # Invalidate cache
        MarketplaceCache.invalidate_user_installed(user.id)
        
        # Should be empty again
        cached = MarketplaceCache.get_user_installed(user.id)
        assert cached is None
    
    def test_cache_oauth_config(self):
        """Test caching of OAuth configuration."""
        # Create test integration type with OAuth config
        integration_type = IntegrationTypeModel.objects.create(
            type='test-integration',
            name='Test Integration',
            description='Test description',
            brief_description='Test brief',
            category=IntegrationCategory.COMMUNICATION,
            oauth_config={
                'client_id': 'test_client_id',
                'authorization_url': 'https://example.com/oauth/authorize',
                'token_url': 'https://example.com/oauth/token',
                'scopes': ['read', 'write']
            }
        )
        
        # Cache should be empty initially
        cached = MarketplaceCache.get_oauth_config(str(integration_type.id))
        assert cached is None
        
        # Cache the OAuth config
        MarketplaceCache.cache_oauth_config(
            str(integration_type.id),
            integration_type.oauth_config
        )
        
        # Should now be cached
        cached = MarketplaceCache.get_oauth_config(str(integration_type.id))
        assert cached is not None
        assert cached['client_id'] == 'test_client_id'
        
        # Invalidate cache
        MarketplaceCache.invalidate_oauth_config(str(integration_type.id))
        
        # Should be empty again
        cached = MarketplaceCache.get_oauth_config(str(integration_type.id))
        assert cached is None


@pytest.mark.django_db
class TestCacheSignals:
    """Test cache invalidation signals."""
    
    def test_integration_type_save_invalidates_cache(self):
        """Test that saving IntegrationType invalidates caches."""
        # Pre-populate cache
        MarketplaceCache.cache_active_types(['test-id'])
        assert MarketplaceCache.get_active_types() is not None
        
        # Create integration type (should trigger signal)
        integration_type = IntegrationTypeModel.objects.create(
            type='test-integration',
            name='Test Integration',
            description='Test description',
            brief_description='Test brief',
            category=IntegrationCategory.COMMUNICATION
        )
        
        # Cache should be invalidated
        cached = MarketplaceCache.get_active_types()
        assert cached is None
    
    def test_integration_type_delete_invalidates_cache(self):
        """Test that deleting IntegrationType invalidates caches."""
        # Create integration type
        integration_type = IntegrationTypeModel.objects.create(
            type='test-integration',
            name='Test Integration',
            description='Test description',
            brief_description='Test brief',
            category=IntegrationCategory.COMMUNICATION
        )
        
        # Pre-populate cache
        MarketplaceCache.cache_active_types([str(integration_type.id)])
        assert MarketplaceCache.get_active_types() is not None
        
        # Delete integration type (should trigger signal)
        integration_type.delete()
        
        # Cache should be invalidated
        cached = MarketplaceCache.get_active_types()
        assert cached is None
    
    def test_integration_save_invalidates_user_cache(self, django_user_model):
        """Test that saving Integration invalidates user cache."""
        # Create test user
        user = django_user_model.objects.create_user(
            email='test@example.com',
            password='testpass123'
        )
        
        # Create integration type
        integration_type = IntegrationTypeModel.objects.create(
            type='test-integration',
            name='Test Integration',
            description='Test description',
            brief_description='Test brief',
            category=IntegrationCategory.COMMUNICATION
        )
        
        # Pre-populate cache
        MarketplaceCache.cache_user_installed(user.id, set())
        assert MarketplaceCache.get_user_installed(user.id) is not None
        
        # Create integration (should trigger signal)
        integration = Integration.objects.create(
            user=user,
            integration_type=integration_type
        )
        
        # Cache should be invalidated
        cached = MarketplaceCache.get_user_installed(user.id)
        assert cached is None
    
    def test_integration_delete_invalidates_user_cache(self, django_user_model):
        """Test that deleting Integration invalidates user cache."""
        # Create test user
        user = django_user_model.objects.create_user(
            email='test@example.com',
            password='testpass123'
        )
        
        # Create integration type
        integration_type = IntegrationTypeModel.objects.create(
            type='test-integration',
            name='Test Integration',
            description='Test description',
            brief_description='Test brief',
            category=IntegrationCategory.COMMUNICATION
        )
        
        # Create integration
        integration = Integration.objects.create(
            user=user,
            integration_type=integration_type
        )
        
        # Pre-populate cache
        MarketplaceCache.cache_user_installed(user.id, {str(integration_type.id)})
        assert MarketplaceCache.get_user_installed(user.id) is not None
        
        # Delete integration (should trigger signal)
        integration.delete()
        
        # Cache should be invalidated
        cached = MarketplaceCache.get_user_installed(user.id)
        assert cached is None
