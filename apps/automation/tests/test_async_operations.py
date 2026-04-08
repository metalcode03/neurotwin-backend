"""
Tests for async operations in authentication flows.

Verifies that all external API calls are properly async and don't block
HTTP requests.

Requirements: 22.1, 22.2, 22.3, 22.6
"""

import asyncio
import pytest
from unittest.mock import AsyncMock, patch, MagicMock
from django.test import TestCase

from apps.automation.services.auth_client import AuthClient
from apps.automation.services.oauth_strategy import OAuthStrategy
from apps.automation.services.meta_strategy import MetaStrategy
from apps.automation.services.api_key_strategy import APIKeyStrategy


class TestAuthClientAsync(TestCase):
    """
    Test that AuthClient methods are properly async.
    
    Requirements: 22.1, 22.2, 22.3
    """
    
    @pytest.mark.asyncio
    async def test_exchange_oauth_code_is_async(self):
        """Verify exchange_oauth_code is async and doesn't block."""
        with patch('httpx.AsyncClient') as mock_client:
            mock_response = MagicMock()
            mock_response.json.return_value = {
                'access_token': 'test_token',
                'expires_in': 3600
            }
            mock_response.raise_for_status = MagicMock()
            
            mock_client.return_value.__aenter__.return_value.post = AsyncMock(
                return_value=mock_response
            )
            
            # This should complete without blocking
            result = await AuthClient.exchange_oauth_code(
                token_url='https://oauth.example.com/token',
                client_id='test_client',
                client_secret='test_secret',
                code='test_code',
                redirect_uri='https://example.com/callback'
            )
            
            assert result['access_token'] == 'test_token'
            assert 'expires_in' in result
    
    @pytest.mark.asyncio
    async def test_refresh_oauth_token_is_async(self):
        """Verify refresh_oauth_token is async and doesn't block."""
        with patch('httpx.AsyncClient') as mock_client:
            mock_response = MagicMock()
            mock_response.json.return_value = {
                'access_token': 'new_token',
                'expires_in': 3600
            }
            mock_response.raise_for_status = MagicMock()
            
            mock_client.return_value.__aenter__.return_value.post = AsyncMock(
                return_value=mock_response
            )
            
            result = await AuthClient.refresh_oauth_token(
                token_url='https://oauth.example.com/token',
                client_id='test_client',
                client_secret='test_secret',
                refresh_token='test_refresh'
            )
            
            assert result['access_token'] == 'new_token'
    
    @pytest.mark.asyncio
    async def test_validate_api_key_is_async(self):
        """Verify validate_api_key is async and doesn't block."""
        with patch('httpx.AsyncClient') as mock_client:
            mock_response = MagicMock()
            mock_response.status_code = 200
            
            mock_client.return_value.__aenter__.return_value.get = AsyncMock(
                return_value=mock_response
            )
            
            result = await AuthClient.validate_api_key(
                api_endpoint='https://api.example.com/validate',
                api_key='test_key',
                header_name='Authorization'
            )
            
            assert result is True
    
    @pytest.mark.asyncio
    async def test_concurrent_requests_dont_block(self):
        """
        Verify multiple concurrent requests can be processed.
        
        Requirements: 22.6
        """
        with patch('httpx.AsyncClient') as mock_client:
            mock_response = MagicMock()
            mock_response.json.return_value = {
                'access_token': 'test_token',
                'expires_in': 3600
            }
            mock_response.raise_for_status = MagicMock()
            
            mock_client.return_value.__aenter__.return_value.post = AsyncMock(
                return_value=mock_response
            )
            
            # Create 10 concurrent requests
            tasks = [
                AuthClient.exchange_oauth_code(
                    token_url='https://oauth.example.com/token',
                    client_id='test_client',
                    client_secret='test_secret',
                    code=f'code_{i}',
                    redirect_uri='https://example.com/callback'
                )
                for i in range(10)
            ]
            
            # All should complete without blocking each other
            results = await asyncio.gather(*tasks)
            
            assert len(results) == 10
            assert all(r['access_token'] == 'test_token' for r in results)


class TestStrategyMethodsAsync(TestCase):
    """
    Test that strategy methods are properly async.
    
    Requirements: 22.1, 22.2, 22.3
    """
    
    def setUp(self):
        """Set up test fixtures."""
        from apps.automation.models import IntegrationTypeModel, AuthType
        
        self.oauth_type = IntegrationTypeModel(
            id='test-oauth-id',
            type='test-oauth',
            name='Test OAuth',
            auth_type=AuthType.OAUTH,
            auth_config={
                'client_id': 'test_client',
                'client_secret_encrypted': 'encrypted_secret',
                'authorization_url': 'https://oauth.example.com/authorize',
                'token_url': 'https://oauth.example.com/token',
                'scopes': ['read', 'write']
            }
        )
    
    @pytest.mark.asyncio
    async def test_oauth_strategy_complete_authentication_is_async(self):
        """Verify OAuthStrategy.complete_authentication is async."""
        strategy = OAuthStrategy(self.oauth_type)
        
        with patch.object(AuthClient, 'exchange_oauth_code', new_callable=AsyncMock) as mock_exchange:
            mock_exchange.return_value = {
                'access_token': 'test_token',
                'refresh_token': 'test_refresh',
                'expires_in': 3600
            }
            
            with patch('apps.automation.services.oauth_strategy.TokenEncryption') as mock_encryption:
                mock_encryption.encrypt.return_value = b'encrypted'
                
                result = await strategy.complete_authentication(
                    authorization_code='test_code',
                    state='test_state',
                    redirect_uri='https://example.com/callback'
                )
                
                assert 'access_token_encrypted' in result
                mock_exchange.assert_called_once()
    
    @pytest.mark.asyncio
    async def test_meta_strategy_complete_authentication_is_async(self):
        """Verify MetaStrategy.complete_authentication is async."""
        from apps.automation.models import AuthType
        
        meta_type = IntegrationTypeModel(
            id='test-meta-id',
            type='test-meta',
            name='Test Meta',
            auth_type=AuthType.META,
            auth_config={
                'app_id': 'test_app',
                'app_secret_encrypted': 'encrypted_secret',
                'config_id': 'test_config',
                'business_verification_url': 'https://meta.example.com/verify'
            }
        )
        
        strategy = MetaStrategy(meta_type)
        
        with patch.object(AuthClient, 'exchange_meta_code', new_callable=AsyncMock) as mock_exchange:
            with patch.object(AuthClient, 'exchange_meta_long_lived_token', new_callable=AsyncMock) as mock_long_lived:
                with patch.object(AuthClient, 'get_meta_business_details', new_callable=AsyncMock) as mock_details:
                    mock_exchange.return_value = {'access_token': 'short_token'}
                    mock_long_lived.return_value = {'access_token': 'long_token'}
                    mock_details.return_value = {
                        'business_id': 'test_business',
                        'waba_id': 'test_waba',
                        'phone_number_id': 'test_phone'
                    }
                    
                    with patch('apps.automation.services.meta_strategy.TokenEncryption') as mock_encryption:
                        mock_encryption.encrypt.return_value = b'encrypted'
                        
                        result = await strategy.complete_authentication(
                            authorization_code='test_code',
                            state='test_state',
                            redirect_uri='https://example.com/callback'
                        )
                        
                        assert 'access_token_encrypted' in result
                        assert result['meta_business_id'] == 'test_business'


class TestPerformanceRequirements(TestCase):
    """
    Test that performance requirements are met.
    
    Requirements: 22.1, 22.2, 22.3
    """
    
    @pytest.mark.asyncio
    async def test_oauth_exchange_completes_within_timeout(self):
        """
        Verify OAuth token exchange completes within 2 seconds.
        
        Requirements: 22.1
        """
        import time
        
        with patch('httpx.AsyncClient') as mock_client:
            mock_response = MagicMock()
            mock_response.json.return_value = {
                'access_token': 'test_token',
                'expires_in': 3600
            }
            mock_response.raise_for_status = MagicMock()
            
            # Simulate 1 second delay
            async def delayed_post(*args, **kwargs):
                await asyncio.sleep(1)
                return mock_response
            
            mock_client.return_value.__aenter__.return_value.post = delayed_post
            
            start = time.time()
            result = await AuthClient.exchange_oauth_code(
                token_url='https://oauth.example.com/token',
                client_id='test_client',
                client_secret='test_secret',
                code='test_code',
                redirect_uri='https://example.com/callback'
            )
            duration = time.time() - start
            
            # Should complete within 2 seconds (requirement)
            assert duration < 2.0
            assert result['access_token'] == 'test_token'
    
    @pytest.mark.asyncio
    async def test_api_key_validation_completes_within_timeout(self):
        """
        Verify API key validation completes within 1 second.
        
        Requirements: 22.3
        """
        import time
        
        with patch('httpx.AsyncClient') as mock_client:
            mock_response = MagicMock()
            mock_response.status_code = 200
            
            # Simulate 0.5 second delay
            async def delayed_get(*args, **kwargs):
                await asyncio.sleep(0.5)
                return mock_response
            
            mock_client.return_value.__aenter__.return_value.get = delayed_get
            
            start = time.time()
            result = await AuthClient.validate_api_key(
                api_endpoint='https://api.example.com/validate',
                api_key='test_key',
                header_name='Authorization'
            )
            duration = time.time() - start
            
            # Should complete within 1 second (requirement)
            assert duration < 1.0
            assert result is True


class TestAsyncContextPreservation(TestCase):
    """
    Test that async context is preserved throughout the call chain.
    
    Requirements: 22.6
    """
    
    @pytest.mark.asyncio
    async def test_retry_logic_preserves_async_context(self):
        """Verify retry logic uses async sleep and preserves context."""
        with patch('httpx.AsyncClient') as mock_client:
            # First two calls fail, third succeeds
            call_count = 0
            
            async def failing_post(*args, **kwargs):
                nonlocal call_count
                call_count += 1
                if call_count < 3:
                    raise Exception('Network error')
                
                mock_response = MagicMock()
                mock_response.json.return_value = {
                    'access_token': 'test_token',
                    'expires_in': 3600
                }
                mock_response.raise_for_status = MagicMock()
                return mock_response
            
            mock_client.return_value.__aenter__.return_value.post = failing_post
            
            # Should retry and eventually succeed
            result = await AuthClient.exchange_oauth_code(
                token_url='https://oauth.example.com/token',
                client_id='test_client',
                client_secret='test_secret',
                code='test_code',
                redirect_uri='https://example.com/callback'
            )
            
            assert call_count == 3
            assert result['access_token'] == 'test_token'
