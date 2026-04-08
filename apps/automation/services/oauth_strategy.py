"""
OAuth 2.0 Authentication Strategy

Implements OAuth 2.0 authorization code flow for standard OAuth providers
like Gmail, Slack, Google Calendar, etc.

Requirements: 4.1-4.7
"""

import base64
import logging
from datetime import timedelta
from typing import Optional, Dict, Any, List
from urllib.parse import urlencode

from django.core.exceptions import ValidationError
from django.utils import timezone

from apps.automation.services.auth_strategy import AuthStrategy

logger = logging.getLogger(__name__)


class OAuthStrategy(AuthStrategy):
    """
    OAuth 2.0 authentication strategy.
    
    Implements standard OAuth 2.0 authorization code flow.
    Supports providers like Gmail, Slack, Google Calendar, etc.
    
    Requirements: 4.1-4.7
    """
    
    def get_required_fields(self) -> List[str]:
        """Get required OAuth configuration fields."""
        return [
            'client_id',
            'client_secret_encrypted',
            'authorization_url',
            'token_url',
            'scopes'
        ]
    
    def validate_config(self) -> None:
        """Validate OAuth configuration including HTTPS URLs."""
        super().validate_config()
        
        # Validate HTTPS URLs (Requirement 4.7)
        for url_field in ['authorization_url', 'token_url']:
            url = self.auth_config.get(url_field, '')
            if not url.startswith('https://'):
                raise ValidationError(
                    f"{url_field} must use HTTPS protocol"
                )
    
    def get_authorization_url(self, state: str, redirect_uri: str) -> Optional[str]:
        """
        Build OAuth 2.0 authorization URL.
        
        Requirements: 4.2
        
        Args:
            state: CSRF protection state parameter
            redirect_uri: Callback URL after authorization
            
        Returns:
            Authorization URL string
        """
        params = {
            'client_id': self.auth_config['client_id'],
            'redirect_uri': redirect_uri,
            'response_type': 'code',
            'scope': ' '.join(self._get_scopes()),
            'state': state,
            'access_type': 'offline',  # Request refresh token
            'prompt': 'consent'
        }
        
        base_url = self.auth_config['authorization_url']
        return f"{base_url}?{urlencode(params)}"
    
    async def complete_authentication(
        self,
        authorization_code: str,
        state: str,
        redirect_uri: str,
        **kwargs
    ) -> Dict[str, Any]:
        """
        Exchange authorization code for access token.
        
        Requirements: 4.3
        
        Args:
            authorization_code: Authorization code from provider
            state: CSRF protection state parameter
            redirect_uri: Callback URL used in authorization
            **kwargs: Additional parameters
            
        Returns:
            Dictionary with encrypted tokens and expiration
        """
        from apps.automation.services.auth_client import AuthClient
        from apps.automation.utils.encryption import TokenEncryption
        
        client_secret = TokenEncryption.decrypt(
            base64.b64decode(self.auth_config['client_secret_encrypted'])
        )
        
        token_data = await AuthClient.exchange_oauth_code(
            token_url=self.auth_config['token_url'],
            client_id=self.auth_config['client_id'],
            client_secret=client_secret,
            code=authorization_code,
            redirect_uri=redirect_uri
        )
        
        # Encrypt tokens before returning
        access_token_encrypted = TokenEncryption.encrypt(token_data['access_token'])
        refresh_token_encrypted = None
        if 'refresh_token' in token_data:
            refresh_token_encrypted = TokenEncryption.encrypt(token_data['refresh_token'])
        
        return {
            'access_token_encrypted': access_token_encrypted,
            'refresh_token_encrypted': refresh_token_encrypted,
            'expires_at': timezone.now() + timedelta(seconds=token_data.get('expires_in', 3600)),
            'scopes': token_data.get('scope', '').split()
        }
    
    async def refresh_credentials(self, integration) -> Dict[str, Any]:
        """
        Refresh OAuth access token using refresh token.
        
        Requirements: 4.4
        
        Args:
            integration: Integration instance with current credentials
            
        Returns:
            Dictionary with refreshed credentials
        """
        from apps.automation.services.auth_client import AuthClient
        from apps.automation.utils.encryption import TokenEncryption
        
        if not integration.refresh_token:
            raise ValidationError("No refresh token available")
        
        client_secret = TokenEncryption.decrypt(
            base64.b64decode(self.auth_config['client_secret_encrypted'])
        )
        
        token_data = await AuthClient.refresh_oauth_token(
            token_url=self.auth_config['token_url'],
            client_id=self.auth_config['client_id'],
            client_secret=client_secret,
            refresh_token=integration.refresh_token
        )
        
        access_token_encrypted = TokenEncryption.encrypt(token_data['access_token'])
        
        return {
            'access_token_encrypted': access_token_encrypted,
            'expires_at': timezone.now() + timedelta(seconds=token_data.get('expires_in', 3600))
        }
    
    async def revoke_credentials(self, integration) -> bool:
        """
        Revoke OAuth tokens with provider.
        
        Requirements: 4.5
        
        Args:
            integration: Integration instance to revoke
            
        Returns:
            True if revocation successful, False otherwise
        """
        from apps.automation.services.auth_client import AuthClient
        
        revoke_url = self.auth_config.get('revoke_url')
        if not revoke_url:
            return True  # No revocation endpoint, consider success
        
        try:
            await AuthClient.revoke_oauth_token(
                revoke_url=revoke_url,
                token=integration.oauth_token
            )
            return True
        except Exception as e:
            logger.error(f"Failed to revoke OAuth token: {e}")
            return False
    
    def _get_scopes(self) -> List[str]:
        """Get scopes as list."""
        scopes = self.auth_config.get('scopes', [])
        if isinstance(scopes, str):
            return [s.strip() for s in scopes.split(',')]
        return scopes
