"""
Unit tests for authentication strategy implementations.

Tests OAuthStrategy, MetaStrategy, and APIKeyStrategy with mocked external providers.
Validates token encryption/decryption, error handling, and network failure scenarios.

Requirements: 20.1, 20.2, 20.3, 20.4
"""

import pytest
import base64
from unittest.mock import Mock, AsyncMock, patch, MagicMock
from datetime import timedelta
from django.utils import timezone
from django.core.exceptions import ValidationError
from django.contrib.auth import get_user_model

from apps.automation.services.oauth_strategy import OAuthStrategy
from apps.automation.services.meta_strategy import MetaStrategy
from apps.automation.services.api_key_strategy import APIKeyStrategy
from apps.automation.services.auth_strategy_factory import AuthStrategyFactory
from apps.automation.models import IntegrationTypeModel, Integration
from apps.automation.utils.encryption import TokenEncryption

User = get_user_model()


@pytest.fixture
def user(db):
    """Create test user."""
    return User.objects.create_user(
        email='test@example.com',
        password='testpass123'
    )


@pytest.fixture
def oauth_integration_type(db, user):
    """Create OAuth integration type for testing."""
    # Create encrypted client secret
    client_secret = "test_client_secret"
    encrypted_secret = base64.b64encode(
        TokenEncryption.encrypt(client_secret)
    ).decode('utf-8')
    
    return IntegrationTypeModel.objects.create(
        type='test-oauth',
        name='Test OAuth',
        description='Test OAuth integration',
        brief_description='Test OAuth',
        category='communication',
        auth_type='oauth',
        auth_config={
            'client_id': 'test_client_id',
            'client_secret_encrypted': encrypted_secret,
            'authorization_url': 'https://provider.com/oauth/authorize',
            'token_url': 'https://provider.com/oauth/token',
            'revoke_url': 'https://provider.com/oauth/revoke',
            'scopes': ['read', 'write']
        },
        created_by=user
    )


@pytest.fixture
def meta_integration_type(db, user):
    """Create Meta integration type for testing."""
    # Create encrypted app secret
    app_secret = "test_app_secret"
    encrypted_secret = base64.b64encode(
        TokenEncryption.encrypt(app_secret)
    ).decode('utf-8')
    
    return IntegrationTypeModel.objects.create(
        type='test-meta',
        name='Test Meta',
        description='Test Meta integration',
        brief_description='Test Meta',
        category='communication',
        auth_type='meta',
        auth_config={
            'app_id': 'test_app_id',
            'app_secret_encrypted': encrypted_secret,
            'config_id': 'test_config_id',
            'business_verification_url': 'https://facebook.com/v18.0/dialog/oauth'
        },
        created_by=user
    )


@pytest.fixture
def api_key_integration_type(db, user):
    """Create API Key integration type for testing."""
    return IntegrationTypeModel.objects.create(
        type='test-api-key',
        name='Test API Key',
        description='Test API Key integration',
        brief_description='Test API Key',
        category='productivity',
        auth_type='api_key',
        auth_config={
            'api_endpoint': 'https://api.example.com/validate',
            'authentication_header_name': 'X-API-Key',
            'api_key_format_hint': 'Format: sk_live_...'
        },
        created_by=user
    )


@pytest.fixture
def oauth_integration(db, user, oauth_integration_type):
    """Create OAuth integration for testing."""
    access_token = "test_access_token"
    refresh_token = "test_refresh_token"
    
    integration = Integration.objects.create(
        user=user,
        integration_type=oauth_integration_type,
        oauth_token_encrypted=TokenEncryption.encrypt(access_token),
        refresh_token_encrypted=TokenEncryption.encrypt(refresh_token),
        token_expires_at=timezone.now() + timedelta(hours=1),
        scopes=['read', 'write'],
        is_active=True
    )
    return integration


class TestOAuthStrategy:
    """Test suite for OAuthStrategy."""
    
    def test_get_required_fields(self, oauth_integration_type):
        """Test that OAuthStrategy returns correct required fields."""
        strategy = OAuthStrategy(oauth_integration_type)
        required = strategy.get_required_fields()
        
        assert 'client_id' in required
        assert 'client_secret_encrypted' in required
        assert 'authorization_url' in required
        assert 'token_url' in required
        assert 'scopes' in required
    
    def test_validate_config_success(self, oauth_integration_type):
        """Test that valid OAuth config passes validation."""
        strategy = OAuthStrategy(oauth_integration_type)
        # Should not raise
        strategy.validate_config()
    
    def test_validate_config_missing_fields(self, oauth_integration_type):
        """Test that missing required fields raises ValidationError."""
        oauth_integration_type.auth_config = {'client_id': 'test'}
        
        with pytest.raises(ValidationError) as exc_info:
            OAuthStrategy(oauth_integration_type)
        
        assert 'Missing required fields' in str(exc_info.value)
    
    def test_validate_config_non_https_url(self, oauth_integration_type):
        """Test that non-HTTPS URLs raise ValidationError."""
        oauth_integration_type.auth_config['authorization_url'] = 'http://insecure.com/oauth'
        
        with pytest.raises(ValidationError) as exc_info:
            OAuthStrategy(oauth_integration_type)
        
        assert 'must use HTTPS' in str(exc_info.value)
    
    def test_get_authorization_url(self, oauth_integration_type):
        """Test OAuth authorization URL generation."""
        strategy = OAuthStrategy(oauth_integration_type)
        
        state = 'test_state_123'
        redirect_uri = 'https://app.example.com/callback'
        
        url = strategy.get_authorization_url(state, redirect_uri)
        
        assert url.startswith('https://provider.com/oauth/authorize?')
        assert 'client_id=test_client_id' in url
        assert f'state={state}' in url
        assert f'redirect_uri={redirect_uri}' in url
        assert 'response_type=code' in url
        assert 'scope=read+write' in url
    
    @pytest.mark.asyncio
    async def test_complete_authentication_success(self, oauth_integration_type):
        """Test successful OAuth code exchange."""
        strategy = OAuthStrategy(oauth_integration_type)
        
        mock_token_data = {
            'access_token': 'new_access_token',
            'refresh_token': 'new_refresh_token',
            'expires_in': 3600,
            'scope': 'read write'
        }
        
        with patch('apps.automation.services.auth_client.AuthClient.exchange_oauth_code', 
                   new_callable=AsyncMock, return_value=mock_token_data):
            
            result = await strategy.complete_authentication(
                authorization_code='test_code',
                state='test_state',
                redirect_uri='https://app.example.com/callback'
            )
        
        assert 'access_token_encrypted' in result
        assert 'refresh_token_encrypted' in result
        assert 'expires_at' in result
        assert 'scopes' in result
        assert result['scopes'] == ['read', 'write']
    
    @pytest.mark.asyncio
    async def test_complete_authentication_network_failure(self, oauth_integration_type):
        """Test OAuth code exchange with network failure."""
        strategy = OAuthStrategy(oauth_integration_type)
        
        with patch('apps.automation.services.auth_client.AuthClient.exchange_oauth_code',
                   new_callable=AsyncMock, side_effect=Exception('Network error')):
            
            with pytest.raises(Exception) as exc_info:
                await strategy.complete_authentication(
                    authorization_code='test_code',
                    state='test_state',
                    redirect_uri='https://app.example.com/callback'
                )
            
            assert 'Network error' in str(exc_info.value)
    
    @pytest.mark.asyncio
    async def test_refresh_credentials_success(self, oauth_integration):
        """Test successful OAuth token refresh."""
        strategy = OAuthStrategy(oauth_integration.integration_type)
        
        mock_token_data = {
            'access_token': 'refreshed_access_token',
            'expires_in': 3600
        }
        
        with patch('apps.automation.services.auth_client.AuthClient.refresh_oauth_token',
                   new_callable=AsyncMock, return_value=mock_token_data):
            
            result = await strategy.refresh_credentials(oauth_integration)
        
        assert 'access_token_encrypted' in result
        assert 'expires_at' in result
    
    @pytest.mark.asyncio
    async def test_refresh_credentials_no_refresh_token(self, oauth_integration):
        """Test refresh fails when no refresh token available."""
        strategy = OAuthStrategy(oauth_integration.integration_type)
        oauth_integration.refresh_token_encrypted = None
        
        with pytest.raises(ValidationError) as exc_info:
            await strategy.refresh_credentials(oauth_integration)
        
        assert 'No refresh token available' in str(exc_info.value)
    
    @pytest.mark.asyncio
    async def test_revoke_credentials_success(self, oauth_integration):
        """Test successful OAuth token revocation."""
        strategy = OAuthStrategy(oauth_integration.integration_type)
        
        with patch('apps.automation.services.auth_client.AuthClient.revoke_oauth_token',
                   new_callable=AsyncMock, return_value=True):
            
            result = await strategy.revoke_credentials(oauth_integration)
        
        assert result is True
    
    @pytest.mark.asyncio
    async def test_revoke_credentials_no_revoke_url(self, oauth_integration):
        """Test revocation succeeds when no revoke_url configured."""
        strategy = OAuthStrategy(oauth_integration.integration_type)
        oauth_integration.integration_type.auth_config.pop('revoke_url')
        
        result = await strategy.revoke_credentials(oauth_integration)
        
        assert result is True
    
    def test_token_encryption_decryption(self, oauth_integration):
        """Test that tokens are properly encrypted and decrypted."""
        original_token = "test_access_token"
        
        # Token should be encrypted in database
        assert oauth_integration.oauth_token_encrypted is not None
        
        # Decryption should return original token
        decrypted = oauth_integration.oauth_token
        assert decrypted == original_token


class TestMetaStrategy:
    """Test suite for MetaStrategy."""
    
    def test_get_required_fields(self, meta_integration_type):
        """Test that MetaStrategy returns correct required fields."""
        strategy = MetaStrategy(meta_integration_type)
        required = strategy.get_required_fields()
        
        assert 'app_id' in required
        assert 'app_secret_encrypted' in required
        assert 'config_id' in required
        assert 'business_verification_url' in required
    
    def test_validate_config_success(self, meta_integration_type):
        """Test that valid Meta config passes validation."""
        strategy = MetaStrategy(meta_integration_type)
        # Should not raise
        strategy.validate_config()
    
    def test_get_authorization_url(self, meta_integration_type):
        """Test Meta authorization URL generation."""
        strategy = MetaStrategy(meta_integration_type)
        
        state = 'test_state_123'
        redirect_uri = 'https://app.example.com/meta/callback'
        
        url = strategy.get_authorization_url(state, redirect_uri)
        
        assert url.startswith('https://facebook.com/v18.0/dialog/oauth?')
        assert 'app_id=test_app_id' in url
        assert 'config_id=test_config_id' in url
        assert f'state={state}' in url
        assert f'redirect_uri={redirect_uri}' in url
    
    @pytest.mark.asyncio
    async def test_complete_authentication_success(self, meta_integration_type):
        """Test successful Meta authentication flow."""
        strategy = MetaStrategy(meta_integration_type)
        
        mock_short_token = {'access_token': 'short_lived_token'}
        mock_long_token = {'access_token': 'long_lived_token', 'expires_in': 5184000}
        mock_business_data = {
            'business_id': 'test_business_123',
            'waba_id': 'test_waba_456',
            'phone_number_id': 'test_phone_789'
        }
        
        with patch('apps.automation.services.auth_client.AuthClient.exchange_meta_code',
                   new_callable=AsyncMock, return_value=mock_short_token), \
             patch('apps.automation.services.auth_client.AuthClient.exchange_meta_long_lived_token',
                   new_callable=AsyncMock, return_value=mock_long_token), \
             patch('apps.automation.services.auth_client.AuthClient.get_meta_business_details',
                   new_callable=AsyncMock, return_value=mock_business_data):
            
            result = await strategy.complete_authentication(
                authorization_code='test_code',
                state='test_state',
                redirect_uri='https://app.example.com/meta/callback'
            )
        
        assert 'access_token_encrypted' in result
        assert result['refresh_token_encrypted'] is None  # Meta doesn't use refresh tokens
        assert 'expires_at' in result
        assert result['meta_business_id'] == 'test_business_123'
        assert result['meta_waba_id'] == 'test_waba_456'
        assert result['meta_phone_number_id'] == 'test_phone_789'
    
    @pytest.mark.asyncio
    async def test_refresh_credentials_success(self, user, meta_integration_type):
        """Test successful Meta token refresh."""
        strategy = MetaStrategy(meta_integration_type)
        
        # Create Meta integration
        integration = Integration.objects.create(
            user=user,
            integration_type=meta_integration_type,
            oauth_token_encrypted=TokenEncryption.encrypt('current_token'),
            token_expires_at=timezone.now() + timedelta(days=30),
            meta_business_id='test_business_123',
            is_active=True
        )
        
        mock_token_data = {
            'access_token': 'new_long_lived_token',
            'expires_in': 5184000
        }
        
        with patch('apps.automation.services.auth_client.AuthClient.exchange_meta_long_lived_token',
                   new_callable=AsyncMock, return_value=mock_token_data):
            
            result = await strategy.refresh_credentials(integration)
        
        assert 'access_token_encrypted' in result
        assert 'expires_at' in result
    
    @pytest.mark.asyncio
    async def test_revoke_credentials_success(self, user, meta_integration_type):
        """Test successful Meta token revocation."""
        strategy = MetaStrategy(meta_integration_type)
        
        integration = Integration.objects.create(
            user=user,
            integration_type=meta_integration_type,
            oauth_token_encrypted=TokenEncryption.encrypt('test_token'),
            meta_business_id='test_business_123',
            is_active=True
        )
        
        with patch('apps.automation.services.auth_client.AuthClient.revoke_meta_token',
                   new_callable=AsyncMock, return_value=True):
            
            result = await strategy.revoke_credentials(integration)
        
        assert result is True


class TestAPIKeyStrategy:
    """Test suite for APIKeyStrategy."""
    
    def test_get_required_fields(self, api_key_integration_type):
        """Test that APIKeyStrategy returns correct required fields."""
        strategy = APIKeyStrategy(api_key_integration_type)
        required = strategy.get_required_fields()
        
        assert 'api_endpoint' in required
        assert 'authentication_header_name' in required
    
    def test_validate_config_success(self, api_key_integration_type):
        """Test that valid API Key config passes validation."""
        strategy = APIKeyStrategy(api_key_integration_type)
        # Should not raise
        strategy.validate_config()
    
    def test_get_authorization_url_returns_none(self, api_key_integration_type):
        """Test that API Key strategy returns None for authorization URL."""
        strategy = APIKeyStrategy(api_key_integration_type)
        
        url = strategy.get_authorization_url('state', 'redirect_uri')
        
        assert url is None
    
    @pytest.mark.asyncio
    async def test_complete_authentication_success(self, api_key_integration_type):
        """Test successful API key validation and storage."""
        strategy = APIKeyStrategy(api_key_integration_type)
        
        with patch('apps.automation.services.auth_client.AuthClient.validate_api_key',
                   new_callable=AsyncMock, return_value=True):
            
            result = await strategy.complete_authentication(
                authorization_code='',  # Not used for API key
                state='',  # Not used for API key
                redirect_uri='',  # Not used for API key
                api_key='sk_live_test_key_123'
            )
        
        assert 'access_token_encrypted' in result
        assert result['refresh_token_encrypted'] is None
        assert result['expires_at'] is None  # API keys don't expire
        assert result['scopes'] == []
    
    @pytest.mark.asyncio
    async def test_complete_authentication_missing_api_key(self, api_key_integration_type):
        """Test that missing API key raises ValidationError."""
        strategy = APIKeyStrategy(api_key_integration_type)
        
        with pytest.raises(ValidationError) as exc_info:
            await strategy.complete_authentication(
                authorization_code='',
                state='',
                redirect_uri=''
                # api_key not provided
            )
        
        assert 'API key is required' in str(exc_info.value)
    
    @pytest.mark.asyncio
    async def test_complete_authentication_invalid_key(self, api_key_integration_type):
        """Test that invalid API key raises ValidationError."""
        strategy = APIKeyStrategy(api_key_integration_type)
        
        with patch('apps.automation.services.auth_client.AuthClient.validate_api_key',
                   new_callable=AsyncMock, return_value=False):
            
            with pytest.raises(ValidationError) as exc_info:
                await strategy.complete_authentication(
                    authorization_code='',
                    state='',
                    redirect_uri='',
                    api_key='invalid_key'
                )
            
            assert 'Invalid API key' in str(exc_info.value)
    
    @pytest.mark.asyncio
    async def test_refresh_credentials_noop(self, user, api_key_integration_type):
        """Test that API key refresh is a no-op."""
        strategy = APIKeyStrategy(api_key_integration_type)
        
        integration = Integration.objects.create(
            user=user,
            integration_type=api_key_integration_type,
            oauth_token_encrypted=TokenEncryption.encrypt('sk_live_test_key'),
            is_active=True
        )
        
        result = await strategy.refresh_credentials(integration)
        
        assert result == {}
    
    @pytest.mark.asyncio
    async def test_revoke_credentials_noop(self, user, api_key_integration_type):
        """Test that API key revocation is a no-op."""
        strategy = APIKeyStrategy(api_key_integration_type)
        
        integration = Integration.objects.create(
            user=user,
            integration_type=api_key_integration_type,
            oauth_token_encrypted=TokenEncryption.encrypt('sk_live_test_key'),
            is_active=True
        )
        
        result = await strategy.revoke_credentials(integration)
        
        assert result is True


class TestAuthStrategyFactory:
    """Test suite for AuthStrategyFactory."""
    
    def test_create_oauth_strategy(self, oauth_integration_type):
        """Test factory creates OAuthStrategy for oauth auth_type."""
        strategy = AuthStrategyFactory.create_strategy(oauth_integration_type)
        
        assert isinstance(strategy, OAuthStrategy)
        assert strategy.integration_type == oauth_integration_type
    
    def test_create_meta_strategy(self, meta_integration_type):
        """Test factory creates MetaStrategy for meta auth_type."""
        strategy = AuthStrategyFactory.create_strategy(meta_integration_type)
        
        assert isinstance(strategy, MetaStrategy)
        assert strategy.integration_type == meta_integration_type
    
    def test_create_api_key_strategy(self, api_key_integration_type):
        """Test factory creates APIKeyStrategy for api_key auth_type."""
        strategy = AuthStrategyFactory.create_strategy(api_key_integration_type)
        
        assert isinstance(strategy, APIKeyStrategy)
        assert strategy.integration_type == api_key_integration_type
    
    def test_create_strategy_unrecognized_type(self, oauth_integration_type):
        """Test factory raises ValidationError for unrecognized auth_type."""
        oauth_integration_type.auth_type = 'unknown_type'
        
        with pytest.raises(ValidationError) as exc_info:
            AuthStrategyFactory.create_strategy(oauth_integration_type)
        
        assert 'Unrecognized auth_type' in str(exc_info.value)
        assert 'unknown_type' in str(exc_info.value)
    
    def test_register_custom_strategy(self, oauth_integration_type):
        """Test that custom strategies can be registered."""
        class CustomStrategy(OAuthStrategy):
            pass
        
        AuthStrategyFactory.register_strategy('custom', CustomStrategy)
        oauth_integration_type.auth_type = 'custom'
        
        strategy = AuthStrategyFactory.create_strategy(oauth_integration_type)
        
        assert isinstance(strategy, CustomStrategy)


class TestTokenEncryption:
    """Test suite for token encryption/decryption."""
    
    def test_encrypt_decrypt_roundtrip(self):
        """Test that encryption and decryption produce original value."""
        original = "test_secret_token_12345"
        
        encrypted = TokenEncryption.encrypt(original)
        decrypted = TokenEncryption.decrypt(encrypted)
        
        assert decrypted == original
    
    def test_encrypted_value_differs_from_original(self):
        """Test that encrypted value is different from original."""
        original = "test_secret_token"
        
        encrypted = TokenEncryption.encrypt(original)
        
        assert encrypted != original.encode()
    
    def test_decrypt_invalid_data_raises_error(self):
        """Test that decrypting invalid data raises an error."""
        invalid_data = b"not_encrypted_data"
        
        with pytest.raises(Exception):
            TokenEncryption.decrypt(invalid_data)
    
    def test_multiple_encryptions_produce_different_values(self):
        """Test that encrypting same value twice produces different ciphertexts."""
        original = "test_token"
        
        encrypted1 = TokenEncryption.encrypt(original)
        encrypted2 = TokenEncryption.encrypt(original)
        
        # Different ciphertexts (due to random IV)
        assert encrypted1 != encrypted2
        
        # But both decrypt to same value
        assert TokenEncryption.decrypt(encrypted1) == original
        assert TokenEncryption.decrypt(encrypted2) == original
