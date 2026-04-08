"""
Meta Business Authentication Strategy

Implements Meta's embedded signup flow for WhatsApp Business API
and Instagram integrations.

Requirements: 5.1-5.8
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


class MetaStrategy(AuthStrategy):
    """
    Meta Business authentication strategy.
    
    Implements Meta's embedded signup flow for WhatsApp Business API
    and Instagram integrations.
    
    Requirements: 5.1-5.8
    """
    
    def get_required_fields(self) -> List[str]:
        """Get required Meta configuration fields."""
        return [
            'app_id',
            'app_secret_encrypted',
            'config_id',
            'business_verification_url'
        ]
    
    def get_authorization_url(self, state: str, redirect_uri: str) -> Optional[str]:
        """
        Build Meta Business verification URL.
        
        Requirements: 5.2
        
        Args:
            state: CSRF protection state parameter
            redirect_uri: Callback URL after authorization
            
        Returns:
            Meta Business verification URL
        """
        params = {
            'app_id': self.auth_config['app_id'],
            'config_id': self.auth_config['config_id'],
            'redirect_uri': redirect_uri,
            'state': state,
            'response_type': 'code'
        }
        
        base_url = self.auth_config['business_verification_url']
        return f"{base_url}?{urlencode(params)}"
    
    async def complete_authentication(
        self,
        authorization_code: str,
        state: str,
        redirect_uri: str,
        **kwargs
    ) -> Dict[str, Any]:
        """
        Exchange Meta authorization code for long-lived access token.
        
        Requirements: 5.3, 5.5, 5.8
        
        Args:
            authorization_code: Authorization code from Meta
            state: CSRF protection state parameter
            redirect_uri: Callback URL used in authorization
            **kwargs: Additional parameters
            
        Returns:
            Dictionary with encrypted tokens, Meta-specific fields, and expiration
        """
        from apps.automation.services.auth_client import AuthClient
        from apps.automation.utils.encryption import TokenEncryption
        
        app_secret = TokenEncryption.decrypt(
            base64.b64decode(self.auth_config['app_secret_encrypted'])
        )
        
        # Exchange code for short-lived token
        token_data = await AuthClient.exchange_meta_code(
            app_id=self.auth_config['app_id'],
            app_secret=app_secret,
            code=authorization_code,
            redirect_uri=redirect_uri
        )
        
        short_lived_token = token_data['access_token']
        
        # Exchange short-lived for long-lived token (60 days)
        long_lived_data = await AuthClient.exchange_meta_long_lived_token(
            app_id=self.auth_config['app_id'],
            app_secret=app_secret,
            short_lived_token=short_lived_token
        )
        
        # Retrieve business account details
        business_data = await AuthClient.get_meta_business_details(
            access_token=long_lived_data['access_token']
        )
        
        # Encrypt token
        access_token_encrypted = TokenEncryption.encrypt(long_lived_data['access_token'])
        
        return {
            'access_token_encrypted': access_token_encrypted,
            'refresh_token_encrypted': None,  # Meta uses long-lived tokens
            'expires_at': timezone.now() + timedelta(days=60),
            'meta_business_id': business_data['business_id'],
            'meta_waba_id': business_data.get('waba_id'),
            'meta_phone_number_id': business_data.get('phone_number_id'),
            'meta_config': business_data
        }
    
    async def refresh_credentials(self, integration) -> Dict[str, Any]:
        """
        Refresh Meta long-lived token.
        
        Requirements: 5.6
        
        Args:
            integration: Integration instance with current credentials
            
        Returns:
            Dictionary with refreshed credentials
        """
        from apps.automation.services.auth_client import AuthClient
        from apps.automation.utils.encryption import TokenEncryption
        
        app_secret = TokenEncryption.decrypt(
            base64.b64decode(self.auth_config['app_secret_encrypted'])
        )
        
        # Exchange current token for new long-lived token
        token_data = await AuthClient.exchange_meta_long_lived_token(
            app_id=self.auth_config['app_id'],
            app_secret=app_secret,
            short_lived_token=integration.oauth_token
        )
        
        access_token_encrypted = TokenEncryption.encrypt(token_data['access_token'])
        
        return {
            'access_token_encrypted': access_token_encrypted,
            'expires_at': timezone.now() + timedelta(days=60)
        }
    
    async def revoke_credentials(self, integration) -> bool:
        """
        Revoke Meta access token.
        
        Requirements: 5.7
        
        Args:
            integration: Integration instance to revoke
            
        Returns:
            True if revocation successful, False otherwise
        """
        from apps.automation.services.auth_client import AuthClient
        
        try:
            await AuthClient.revoke_meta_token(
                access_token=integration.oauth_token
            )
            return True
        except Exception as e:
            logger.error(f"Failed to revoke Meta token: {e}")
            return False
