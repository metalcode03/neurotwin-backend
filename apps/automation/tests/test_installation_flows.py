"""
Integration tests for complete installation flows.

Tests end-to-end OAuth, Meta, and API key installation flows with mocked providers.
Validates the complete journey from start_installation to integration creation.

Requirements: 20.6
"""

import pytest
import uuid
from unittest.mock import patch, AsyncMock
from datetime import timedelta
from django.utils import timezone
from django.contrib.auth import get_user_model

from apps.automation.services.installation import InstallationService
from apps.automation.models import (
    IntegrationTypeModel,
    Integration,
    InstallationSession,
    InstallationStatus
)
from apps.automation.utils.encryption import TokenEncryption
import base64

User = get_user_model()


@pytest.fixture
def user(db):
    """Create test user."""
    return User.objects.create_user(
        email='integration@example.com',
        password='testpass123'
    )


@pytest.fixture
def oauth_integration_type(db, user):
    """Create OAuth integration type."""
    client_secret = "oauth_secret"
    encrypted_secret = base64.b64encode(
        TokenEncryption.encrypt(client_secret)
    ).decode('utf-8')
    
    return IntegrationTypeModel.objects.create(
        type='gmail',
        name='Gmail',
        description='Gmail integration',
        brief_description='Connect Gmail',
        category='communication',
        auth_type='oauth',
        auth_config={
            'client_id': 'gmail_client_id',
            'client_secret_encrypted': encrypted_secret,
            'authorization_url': 'https://accounts.google.com/o/oauth2/v2/auth',
            'token_url': 'https://oauth2.googleapis.com/token',
            'revoke_url': 'https://oauth2.googleapis.com/revoke',
            'scopes': ['https://www.googleapis.com/auth/gmail.readonly']
        },
        created_by=user
    )


@pytest.fixture
def meta_integration_type(db, user):
    """Create Meta integration type."""
    app_secret = "meta_secret"
    encrypted_secret = base64.b64encode(
        TokenEncryption.encrypt(app_secret)
    ).decode('utf-8')
    
    return IntegrationTypeModel.objects.create(
        type='whatsapp',
        name='WhatsApp Business',
        description='WhatsApp Business integration',
        brief_description='Connect WhatsApp',
        category='communication',
        auth_type='meta',
        auth_config={
            'app_id': 'whatsapp_app_id',
            'app_secret_encrypted': encrypted_secret,
            'config_id': 'whatsapp_config_id',
            'business_verification_url': 'https://www.facebook.com/v18.0/dialog/oauth'
        },
        created_by=user
    )


@pytest.fixture
def api_key_integration_type(db, user):
    """Create API Key integration type."""
    return IntegrationTypeModel.objects.create(
        type='notion',
        name='Notion',
        description='Notion integration',
        brief_description='Connect Notion',
        category='productivity',
        auth_type='api_key',
        auth_config={
            'api_endpoint': 'https://api.notion.com/v1/users/me',
            'authentication_header_name': 'Authorization',
            'api_key_format_hint': 'Format: secret_...'
        },
        created_by=user
    )


@pytest.mark.django_db
class TestOAuthInstallationFlow:
    """Test complete OAuth installation flow end-to-end."""
    
    def test_start_oauth_installation(self, user, oauth_integration_type):
        """Test Phase 1: Starting OAuth installation."""
        result = InstallationService.start_installation(
            user=user,
            integration_type_id=str(oauth_integration_type.id)
        )
        
        # Verify response structure
        assert 'session_id' in result
        assert 'authorization_url' in result
        assert result['requires_redirect'] is True
        assert result['requires_api_key'] is False
        assert result['auth_type'] == 'oauth'
        
        # Verify authorization URL
        auth_url = result['authorization_url']
        assert auth_url.startswith('https://accounts.google.com/o/oauth2/v2/auth?')
        assert 'client_id=gmail_client_id' in auth_url
        assert 'response_type=code' in auth_url
        
        # Verify session created
        session = InstallationSession.objects.get(id=result['session_id'])
        assert session.user == user
        assert session.integration_type == oauth_integration_type
        assert session.status == InstallationStatus.OAUTH_SETUP
        assert session.oauth_state is not None
    
    @pytest.mark.asyncio
    async def test_complete_oauth_installation(self, user, oauth_integration_type):
        """Test Phase 2: Completing OAuth installation."""
        # Phase 1: Start installation
        start_result = InstallationService.start_installation(
            user=user,
            integration_type_id=str(oauth_integration_type.id)
        )
        
        session = InstallationSession.objects.get(id=start_result['session_id'])
        
        # Mock OAuth token exchange
        mock_token_data = {
            'access_token': 'gmail_access_token',
            'refresh_token': 'gmail_refresh_token',
            'expires_in': 3600,
            'scope': 'https://www.googleapis.com/auth/gmail.readonly'
        }
        
        with patch('apps.automation.services.auth_client.AuthClient.exchange_oauth_code',
                   new_callable=AsyncMock, return_value=mock_token_data):
            
            # Phase 2: Complete authentication
            integration = await InstallationService.complete_authentication_flow(
                session_id=str(session.id),
                authorization_code='test_auth_code',
                state=session.oauth_state
            )
        
        # Verify integration created
        assert integration.user == user
        assert integration.integration_type == oauth_integration_type
        assert integration.is_active is True
        assert integration.oauth_token_encrypted is not None
        assert integration.refresh_token_encrypted is not None
        assert integration.token_expires_at is not None
        
        # Verify session completed
        session.refresh_from_db()
        assert session.status == InstallationStatus.COMPLETED
        assert session.progress == 100
        assert session.completed_at is not None
        
        # Verify token decryption works
        decrypted_token = integration.oauth_token
        assert decrypted_token == 'gmail_access_token'
    
    @pytest.mark.asyncio
    async def test_oauth_installation_invalid_state(self, user, oauth_integration_type):
        """Test that invalid state parameter fails authentication."""
        # Start installation
        start_result = InstallationService.start_installation(
            user=user,
            integration_type_id=str(oauth_integration_type.id)
        )
        
        session = InstallationSession.objects.get(id=start_result['session_id'])
        
        # Try to complete with wrong state
        from django.core.exceptions import ValidationError
        with pytest.raises(ValidationError) as exc_info:
            await InstallationService.complete_authentication_flow(
                session_id=str(session.id),
                authorization_code='test_code',
                state='wrong_state_value'
            )
        
        assert 'Invalid state parameter' in str(exc_info.value)
        
        # Verify session marked as failed
        session.refresh_from_db()
        assert session.status == InstallationStatus.FAILED
    
    @pytest.mark.asyncio
    async def test_oauth_installation_network_failure(self, user, oauth_integration_type):
        """Test OAuth installation handles network failures gracefully."""
        # Start installation
        start_result = InstallationService.start_installation(
            user=user,
            integration_type_id=str(oauth_integration_type.id)
        )
        
        session = InstallationSession.objects.get(id=start_result['session_id'])
        
        # Mock network failure
        with patch('apps.automation.services.auth_client.AuthClient.exchange_oauth_code',
                   new_callable=AsyncMock, side_effect=Exception('Network timeout')):
            
            with pytest.raises(Exception) as exc_info:
                await InstallationService.complete_authentication_flow(
                    session_id=str(session.id),
                    authorization_code='test_code',
                    state=session.oauth_state
                )
            
            assert 'Network timeout' in str(exc_info.value)
        
        # Verify session marked as failed
        session.refresh_from_db()
        assert session.status == InstallationStatus.FAILED
        assert 'Network timeout' in session.error_message


@pytest.mark.django_db
class TestMetaInstallationFlow:
    """Test complete Meta installation flow end-to-end."""
    
    def test_start_meta_installation(self, user, meta_integration_type):
        """Test Phase 1: Starting Meta installation."""
        result = InstallationService.start_installation(
            user=user,
            integration_type_id=str(meta_integration_type.id)
        )
        
        # Verify response structure
        assert 'session_id' in result
        assert 'authorization_url' in result
        assert result['requires_redirect'] is True
        assert result['requires_api_key'] is False
        assert result['auth_type'] == 'meta'
        
        # Verify authorization URL
        auth_url = result['authorization_url']
        assert auth_url.startswith('https://www.facebook.com/v18.0/dialog/oauth?')
        assert 'app_id=whatsapp_app_id' in auth_url
        assert 'config_id=whatsapp_config_id' in auth_url
        
        # Verify session created
        session = InstallationSession.objects.get(id=result['session_id'])
        assert session.user == user
        assert session.integration_type == meta_integration_type
        assert session.status == InstallationStatus.OAUTH_SETUP
    
    @pytest.mark.asyncio
    async def test_complete_meta_installation(self, user, meta_integration_type):
        """Test Phase 2: Completing Meta installation with business details."""
        # Phase 1: Start installation
        start_result = InstallationService.start_installation(
            user=user,
            integration_type_id=str(meta_integration_type.id)
        )
        
        session = InstallationSession.objects.get(id=start_result['session_id'])
        
        # Mock Meta token exchange and business details
        mock_short_token = {'access_token': 'short_lived_token'}
        mock_long_token = {'access_token': 'long_lived_token', 'expires_in': 5184000}
        mock_business_data = {
            'business_id': 'meta_business_123',
            'business_name': 'Test Business',
            'waba_id': 'waba_456',
            'phone_number_id': 'phone_789'
        }
        
        with patch('apps.automation.services.auth_client.AuthClient.exchange_meta_code',
                   new_callable=AsyncMock, return_value=mock_short_token), \
             patch('apps.automation.services.auth_client.AuthClient.exchange_meta_long_lived_token',
                   new_callable=AsyncMock, return_value=mock_long_token), \
             patch('apps.automation.services.auth_client.AuthClient.get_meta_business_details',
                   new_callable=AsyncMock, return_value=mock_business_data):
            
            # Phase 2: Complete authentication
            integration = await InstallationService.complete_authentication_flow(
                session_id=str(session.id),
                authorization_code='meta_auth_code',
                state=session.oauth_state
            )
        
        # Verify integration created with Meta fields
        assert integration.user == user
        assert integration.integration_type == meta_integration_type
        assert integration.is_active is True
        assert integration.oauth_token_encrypted is not None
        assert integration.refresh_token_encrypted is None  # Meta doesn't use refresh tokens
        
        # Verify Meta-specific fields
        assert integration.meta_business_id == 'meta_business_123'
        assert integration.meta_waba_id == 'waba_456'
        assert integration.meta_phone_number_id == 'phone_789'
        assert 'business_name' in integration.meta_config
        
        # Verify session completed
        session.refresh_from_db()
        assert session.status == InstallationStatus.COMPLETED


@pytest.mark.django_db
class TestAPIKeyInstallationFlow:
    """Test complete API Key installation flow end-to-end."""
    
    def test_start_api_key_installation(self, user, api_key_integration_type):
        """Test Phase 1: Starting API Key installation (no redirect)."""
        result = InstallationService.start_installation(
            user=user,
            integration_type_id=str(api_key_integration_type.id)
        )
        
        # Verify response structure
        assert 'session_id' in result
        assert result['authorization_url'] is None  # No redirect for API key
        assert result['requires_redirect'] is False
        assert result['requires_api_key'] is True
        assert result['auth_type'] == 'api_key'
        
        # Verify session created
        session = InstallationSession.objects.get(id=result['session_id'])
        assert session.user == user
        assert session.integration_type == api_key_integration_type
        assert session.status == InstallationStatus.DOWNLOADING
    
    @pytest.mark.asyncio
    async def test_complete_api_key_installation(self, user, api_key_integration_type):
        """Test Phase 2: Completing API Key installation."""
        # Phase 1: Start installation
        start_result = InstallationService.start_installation(
            user=user,
            integration_type_id=str(api_key_integration_type.id)
        )
        
        session = InstallationSession.objects.get(id=start_result['session_id'])
        
        # Mock API key validation
        with patch('apps.automation.services.auth_client.AuthClient.validate_api_key',
                   new_callable=AsyncMock, return_value=True):
            
            # Phase 2: Complete authentication with API key
            integration = await InstallationService.complete_authentication_flow(
                session_id=str(session.id),
                authorization_code='',  # Not used for API key
                state=session.oauth_state,
                api_key='secret_notion_key_123'
            )
        
        # Verify integration created
        assert integration.user == user
        assert integration.integration_type == api_key_integration_type
        assert integration.is_active is True
        assert integration.oauth_token_encrypted is not None  # API key stored here
        assert integration.refresh_token_encrypted is None
        assert integration.token_expires_at is None  # API keys don't expire
        
        # Verify session completed
        session.refresh_from_db()
        assert session.status == InstallationStatus.COMPLETED
        
        # Verify API key decryption works
        decrypted_key = integration.oauth_token
        assert decrypted_key == 'secret_notion_key_123'
    
    @pytest.mark.asyncio
    async def test_api_key_installation_invalid_key(self, user, api_key_integration_type):
        """Test that invalid API key fails installation."""
        # Start installation
        start_result = InstallationService.start_installation(
            user=user,
            integration_type_id=str(api_key_integration_type.id)
        )
        
        session = InstallationSession.objects.get(id=start_result['session_id'])
        
        # Mock API key validation failure
        with patch('apps.automation.services.auth_client.AuthClient.validate_api_key',
                   new_callable=AsyncMock, return_value=False):
            
            from django.core.exceptions import ValidationError
            with pytest.raises(ValidationError) as exc_info:
                await InstallationService.complete_authentication_flow(
                    session_id=str(session.id),
                    authorization_code='',
                    state=session.oauth_state,
                    api_key='invalid_key'
                )
            
            assert 'Invalid API key' in str(exc_info.value)
        
        # Verify session marked as failed
        session.refresh_from_db()
        assert session.status == InstallationStatus.FAILED


@pytest.mark.django_db
class TestInstallationEdgeCases:
    """Test edge cases and error scenarios in installation flows."""
    
    def test_duplicate_installation_prevented(self, user, oauth_integration_type):
        """Test that duplicate installations are prevented."""
        # Create existing integration
        Integration.objects.create(
            user=user,
            integration_type=oauth_integration_type,
            oauth_token_encrypted=TokenEncryption.encrypt('existing_token'),
            is_active=True
        )
        
        # Try to install again
        from django.core.exceptions import ValidationError
        with pytest.raises(ValidationError) as exc_info:
            InstallationService.start_installation(
                user=user,
                integration_type_id=str(oauth_integration_type.id)
            )
        
        assert 'already installed' in str(exc_info.value)
    
    @pytest.mark.asyncio
    async def test_expired_session_rejected(self, user, oauth_integration_type):
        """Test that expired installation sessions are rejected."""
        # Create expired session
        session = InstallationSession.objects.create(
            user=user,
            integration_type=oauth_integration_type,
            oauth_state='test_state',
            status=InstallationStatus.OAUTH_SETUP,
            created_at=timezone.now() - timedelta(hours=2)  # Expired
        )
        
        from django.core.exceptions import ValidationError
        with pytest.raises(ValidationError) as exc_info:
            await InstallationService.complete_authentication_flow(
                session_id=str(session.id),
                authorization_code='test_code',
                state='test_state'
            )
        
        assert 'expired' in str(exc_info.value).lower()
    
    @pytest.mark.asyncio
    async def test_uninstall_integration_revokes_credentials(self, user, oauth_integration_type):
        """Test that uninstalling integration revokes credentials."""
        # Create integration
        integration = Integration.objects.create(
            user=user,
            integration_type=oauth_integration_type,
            oauth_token_encrypted=TokenEncryption.encrypt('test_token'),
            is_active=True
        )
        
        # Mock credential revocation
        with patch('apps.automation.services.auth_client.AuthClient.revoke_oauth_token',
                   new_callable=AsyncMock, return_value=True), \
             patch('apps.automation.services.workflow.WorkflowService.disable_workflows_for_integration',
                   return_value=2):
            
            result = await InstallationService.uninstall_integration(
                user=user,
                integration_id=str(integration.id)
            )
        
        # Verify result
        assert result['success'] is True
        assert result['disabled_workflows'] == 2
        
        # Verify integration deleted
        assert not Integration.objects.filter(id=integration.id).exists()
