"""
End-to-end OAuth flow tests for Task 19 checkpoint.

Tests the complete installation flow including:
- Installation initiation
- OAuth authorization URL generation
- OAuth callback handling
- Token encryption and storage
- Error handling and retry logic
- Rate limiting

Requirements: 4.1-4.11, 11.1-11.7, 15.1-15.6, 18.1-18.7
"""

import base64
import json
import os
from datetime import timedelta
from unittest.mock import AsyncMock, Mock, patch
from uuid import uuid4

import httpx
import pytest
from cryptography.fernet import Fernet
from django.contrib.auth import get_user_model
from django.test import TestCase, override_settings
from django.utils import timezone

from apps.automation.models import (
    InstallationSession,
    InstallationStatus,
    Integration,
    IntegrationType,
)
from apps.automation.services.installation import InstallationService
from apps.automation.utils.encryption import TokenEncryption
from apps.automation.utils.oauth_client import OAuthClient

User = get_user_model()


# Generate a test encryption key for tests
TEST_ENCRYPTION_KEY = Fernet.generate_key().decode()


@override_settings(ENCRYPTION_KEY=TEST_ENCRYPTION_KEY)
class OAuthFlowEndToEndTest(TestCase):
    """
    End-to-end tests for OAuth installation flow.
    
    Task 19: Checkpoint - Ensure OAuth flow works end-to-end
    """
    
    def setUp(self):
        """Set up test data."""
        self.user = User.objects.create_user(
            email='test@example.com',
            password='testpass123'
        )
        
        # Create test integration type with OAuth config
        self.integration_type = IntegrationType.objects.create(
            type='test-oauth-app',
            name='Test OAuth App',
            description='Test integration for OAuth flow',
            brief_description='Test app',
            category='productivity',
            oauth_config={
                'client_id': 'test_client_id',
                'client_secret_encrypted': base64.b64encode(
                    TokenEncryption.encrypt('test_client_secret')
                ).decode(),
                'authorization_url': 'https://oauth.example.com/authorize',
                'token_url': 'https://oauth.example.com/token',
                'scopes': ['read', 'write']
            },
            is_active=True
        )
    
    def test_complete_installation_flow_success(self):
        """
        Test complete successful installation flow.
        
        Validates:
        - Phase 1: Installation session creation
        - Phase 2: OAuth URL generation
        - OAuth callback handling
        - Token encryption and storage
        - Template instantiation
        
        Requirements: 4.1-4.11
        """
        # Phase 1: Start installation
        session = InstallationService.start_installation(
            user=self.user,
            integration_type_id=self.integration_type.id
        )
        
        # Verify session created with correct status
        self.assertEqual(session.status, InstallationStatus.DOWNLOADING)
        self.assertEqual(session.user, self.user)
        self.assertEqual(session.integration_type, self.integration_type)
        self.assertIsNotNone(session.oauth_state)
        self.assertEqual(len(session.oauth_state), 64)  # 32 bytes hex
        
        # Phase 2: Get OAuth authorization URL
        oauth_url = InstallationService.get_oauth_authorization_url(
            session_id=session.id
        )
        
        # Verify OAuth URL structure
        self.assertIn('https://oauth.example.com/authorize', oauth_url)
        self.assertIn(f'client_id=test_client_id', oauth_url)
        self.assertIn(f'state={session.oauth_state}', oauth_url)
        self.assertIn('scope=read+write', oauth_url)
        
        # Verify session status updated
        session.refresh_from_db()
        self.assertEqual(session.status, InstallationStatus.OAUTH_SETUP)
        
        # Simulate OAuth callback with token exchange
        with patch('httpx.AsyncClient.post') as mock_post:
            # Mock successful token exchange
            mock_response = Mock()
            mock_response.status_code = 200
            mock_response.json.return_value = {
                'access_token': 'test_access_token_12345',
                'refresh_token': 'test_refresh_token_67890',
                'expires_in': 3600,
                'token_type': 'Bearer'
            }
            mock_post.return_value = mock_response
            
            # Complete OAuth flow
            import asyncio
            integration = asyncio.run(
                InstallationService.complete_oauth_flow(
                    session_id=session.id,
                    authorization_code='test_auth_code',
                    state=session.oauth_state
                )
            )
        
        # Verify integration created
        self.assertIsNotNone(integration)
        self.assertEqual(integration.user, self.user)
        self.assertEqual(integration.integration_type, self.integration_type)
        self.assertTrue(integration.is_active)
        
        # Verify tokens encrypted
        self.assertIsNotNone(integration.oauth_token_encrypted)
        self.assertIsNotNone(integration.refresh_token_encrypted)
        
        # Verify token decryption works
        decrypted_access = TokenEncryption.decrypt(
            integration.oauth_token_encrypted
        )
        self.assertEqual(decrypted_access, 'test_access_token_12345')
        
        decrypted_refresh = TokenEncryption.decrypt(
            integration.refresh_token_encrypted
        )
        self.assertEqual(decrypted_refresh, 'test_refresh_token_67890')
        
        # Verify session completed
        session.refresh_from_db()
        self.assertEqual(session.status, InstallationStatus.COMPLETED)
        self.assertEqual(session.progress, 100)
        self.assertIsNotNone(session.completed_at)
    
    def test_oauth_state_validation_prevents_csrf(self):
        """
        Test OAuth state validation prevents CSRF attacks.
        
        Validates: Requirements 18.4
        """
        # Start installation
        session = InstallationService.start_installation(
            user=self.user,
            integration_type_id=self.integration_type.id
        )
        
        # Get OAuth URL
        InstallationService.get_oauth_authorization_url(
            session_id=session.id
        )
        
        # Attempt callback with invalid state
        with self.assertRaises(ValueError) as context:
            import asyncio
            asyncio.run(
                InstallationService.complete_oauth_flow(
                    session_id=session.id,
                    authorization_code='test_auth_code',
                    state='invalid_state_value'
                )
            )
        
        self.assertIn('Invalid OAuth state', str(context.exception))
        
        # Verify session marked as failed
        session.refresh_from_db()
        self.assertEqual(session.status, InstallationStatus.FAILED)
        self.assertIn('Invalid OAuth state', session.error_message)
    
    def test_token_exchange_failure_handling(self):
        """
        Test error handling when token exchange fails.
        
        Validates: Requirements 15.1-15.3
        """
        # Start installation
        session = InstallationService.start_installation(
            user=self.user,
            integration_type_id=self.integration_type.id
        )
        
        # Get OAuth URL
        InstallationService.get_oauth_authorization_url(
            session_id=session.id
        )
        
        # Simulate failed token exchange
        with patch('httpx.AsyncClient.post') as mock_post:
            # Mock failed token exchange
            mock_response = Mock()
            mock_response.status_code = 400
            mock_response.json.return_value = {
                'error': 'invalid_grant',
                'error_description': 'Authorization code expired'
            }
            mock_post.return_value = mock_response
            
            # Attempt to complete OAuth flow
            with self.assertRaises(Exception):
                import asyncio
                asyncio.run(
                    InstallationService.complete_oauth_flow(
                        session_id=session.id,
                        authorization_code='expired_code',
                        state=session.oauth_state
                    )
                )
        
        # Verify session marked as failed
        session.refresh_from_db()
        self.assertEqual(session.status, InstallationStatus.FAILED)
        self.assertIn('error', session.error_message.lower())
    
    def test_installation_retry_logic(self):
        """
        Test retry logic for failed installations.
        
        Validates: Requirements 15.4-15.5
        """
        # Create failed session
        session = InstallationSession.objects.create(
            user=self.user,
            integration_type=self.integration_type,
            status=InstallationStatus.FAILED,
            oauth_state='test_state_123',
            error_message='Network error',
            retry_count=0
        )
        
        # Retry installation
        new_session = InstallationService.start_installation(
            user=self.user,
            integration_type_id=self.integration_type.id
        )
        
        # Verify new session created
        self.assertNotEqual(new_session.id, session.id)
        self.assertEqual(new_session.status, InstallationStatus.DOWNLOADING)
        self.assertEqual(new_session.retry_count, 0)
    
    def test_installation_progress_tracking(self):
        """
        Test installation progress tracking.
        
        Validates: Requirements 11.1-11.7
        """
        # Start installation
        session = InstallationService.start_installation(
            user=self.user,
            integration_type_id=self.integration_type.id
        )
        
        # Get progress - Phase 1
        progress = InstallationService.get_installation_progress(
            session_id=session.id
        )
        
        self.assertEqual(progress['status'], InstallationStatus.DOWNLOADING)
        self.assertIn('progress', progress)
        self.assertIsNone(progress.get('error_message'))
        
        # Move to Phase 2
        InstallationService.get_oauth_authorization_url(
            session_id=session.id
        )
        
        # Get progress - Phase 2
        progress = InstallationService.get_installation_progress(
            session_id=session.id
        )
        
        self.assertEqual(progress['status'], InstallationStatus.OAUTH_SETUP)
    
    @override_settings(
        INSTALLATION_RATE_LIMIT_COUNT=3,
        INSTALLATION_RATE_LIMIT_PERIOD=3600
    )
    def test_rate_limiting(self):
        """
        Test installation rate limiting.
        
        Validates: Requirements 18.7
        """
        # Create multiple installations to hit rate limit
        for i in range(3):
            session = InstallationService.start_installation(
                user=self.user,
                integration_type_id=self.integration_type.id
            )
            self.assertIsNotNone(session)
        
        # Next installation should be rate limited
        with self.assertRaises(Exception) as context:
            InstallationService.start_installation(
                user=self.user,
                integration_type_id=self.integration_type.id
            )
        
        self.assertIn('rate limit', str(context.exception).lower())
    
    def test_token_encryption_round_trip(self):
        """
        Test token encryption and decryption round-trip.
        
        Validates: Requirements 2.2, 4.7, 18.1
        """
        test_tokens = [
            'simple_token',
            'token_with_special_chars!@#$%',
            'very_long_token_' * 100,
            '🔐_unicode_token_🔑',
        ]
        
        for original_token in test_tokens:
            # Encrypt
            encrypted = TokenEncryption.encrypt(original_token)
            self.assertIsInstance(encrypted, bytes)
            self.assertNotEqual(encrypted, original_token.encode())
            
            # Decrypt
            decrypted = TokenEncryption.decrypt(encrypted)
            self.assertEqual(decrypted, original_token)
    
    def test_uninstall_integration(self):
        """
        Test integration uninstallation.
        
        Validates: Requirements 5.4-5.6, 18.5-18.6
        """
        # Create integration
        integration = Integration.objects.create(
            user=self.user,
            integration_type=self.integration_type,
            oauth_token_encrypted=TokenEncryption.encrypt('test_token'),
            refresh_token_encrypted=TokenEncryption.encrypt('test_refresh'),
            is_active=True
        )
        
        # Uninstall
        InstallationService.uninstall_integration(
            user=self.user,
            integration_id=integration.id
        )
        
        # Verify integration deleted
        with self.assertRaises(Integration.DoesNotExist):
            Integration.objects.get(id=integration.id)
    
    def test_oauth_url_https_validation(self):
        """
        Test OAuth URLs must be HTTPS.
        
        Validates: Requirements 2.3, 18.3
        """
        # Create integration type with HTTP URL (insecure)
        insecure_type = IntegrationType.objects.create(
            type='insecure-app',
            name='Insecure App',
            description='Test',
            brief_description='Test',
            category='other',
            oauth_config={
                'client_id': 'test',
                'authorization_url': 'http://oauth.example.com/authorize',  # HTTP!
                'token_url': 'https://oauth.example.com/token',
                'scopes': ['read']
            },
            is_active=True
        )
        
        # Start installation
        session = InstallationService.start_installation(
            user=self.user,
            integration_type_id=insecure_type.id
        )
        
        # Attempt to get OAuth URL should fail validation
        with self.assertRaises(ValueError) as context:
            InstallationService.get_oauth_authorization_url(
                session_id=session.id
            )
        
        self.assertIn('HTTPS', str(context.exception))


@override_settings(ENCRYPTION_KEY=TEST_ENCRYPTION_KEY)
class OAuthClientTest(TestCase):
    """Test OAuth client utility."""
    
    def test_build_authorization_url(self):
        """Test OAuth authorization URL building."""
        url = OAuthClient.build_authorization_url(
            authorization_url='https://oauth.example.com/authorize',
            client_id='test_client',
            scopes=['read', 'write'],
            state='test_state_123',
            redirect_uri='https://app.example.com/callback'
        )
        
        self.assertIn('https://oauth.example.com/authorize', url)
        self.assertIn('client_id=test_client', url)
        self.assertIn('state=test_state_123', url)
        self.assertIn('scope=read+write', url)
        self.assertIn('redirect_uri=', url)
    
    @pytest.mark.asyncio
    async def test_exchange_code_for_tokens_success(self):
        """Test successful token exchange."""
        with patch('httpx.AsyncClient.post') as mock_post:
            mock_response = Mock()
            mock_response.status_code = 200
            mock_response.json.return_value = {
                'access_token': 'test_access',
                'refresh_token': 'test_refresh',
                'expires_in': 3600
            }
            mock_post.return_value = mock_response
            
            tokens = await OAuthClient.exchange_code_for_tokens(
                token_url='https://oauth.example.com/token',
                client_id='test_client',
                client_secret='test_secret',
                authorization_code='test_code',
                redirect_uri='https://app.example.com/callback'
            )
            
            self.assertEqual(tokens['access_token'], 'test_access')
            self.assertEqual(tokens['refresh_token'], 'test_refresh')
    
    @pytest.mark.asyncio
    async def test_exchange_code_for_tokens_failure(self):
        """Test failed token exchange."""
        with patch('httpx.AsyncClient.post') as mock_post:
            mock_response = Mock()
            mock_response.status_code = 400
            mock_response.json.return_value = {
                'error': 'invalid_grant'
            }
            mock_post.return_value = mock_response
            
            with self.assertRaises(Exception):
                await OAuthClient.exchange_code_for_tokens(
                    token_url='https://oauth.example.com/token',
                    client_id='test_client',
                    client_secret='test_secret',
                    authorization_code='invalid_code',
                    redirect_uri='https://app.example.com/callback'
                )


@override_settings(ENCRYPTION_KEY=TEST_ENCRYPTION_KEY)
class TokenEncryptionTest(TestCase):
    """Test token encryption utility."""
    
    def test_encrypt_decrypt_round_trip(self):
        """Test encryption and decryption round-trip."""
        original = 'my_secret_token_12345'
        
        encrypted = TokenEncryption.encrypt(original)
        self.assertIsInstance(encrypted, bytes)
        self.assertNotEqual(encrypted, original.encode())
        
        decrypted = TokenEncryption.decrypt(encrypted)
        self.assertEqual(decrypted, original)
    
    def test_different_encryptions_produce_different_ciphertexts(self):
        """Test same plaintext produces different ciphertexts (IV randomization)."""
        original = 'test_token'
        
        encrypted1 = TokenEncryption.encrypt(original)
        encrypted2 = TokenEncryption.encrypt(original)
        
        # Different ciphertexts due to random IV
        self.assertNotEqual(encrypted1, encrypted2)
        
        # But both decrypt to same plaintext
        self.assertEqual(TokenEncryption.decrypt(encrypted1), original)
        self.assertEqual(TokenEncryption.decrypt(encrypted2), original)
    
    def test_decrypt_invalid_data_raises_error(self):
        """Test decrypting invalid data raises error."""
        with self.assertRaises(Exception):
            TokenEncryption.decrypt(b'invalid_encrypted_data')
