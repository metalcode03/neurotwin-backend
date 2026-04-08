"""
API Key Authentication Strategy

For integrations that use simple API key authentication
without OAuth flows.

Requirements: 6.1-6.9
"""

import logging
from typing import Optional, Dict, Any, List

from django.core.exceptions import ValidationError

from apps.automation.services.auth_strategy import AuthStrategy

logger = logging.getLogger(__name__)


class APIKeyStrategy(AuthStrategy):
    """
    API Key authentication strategy.
    
    For integrations that use simple API key authentication
    without OAuth flows.
    
    Requirements: 6.1-6.9
    """
    
    def get_required_fields(self) -> List[str]:
        """Get required API key configuration fields."""
        return [
            'api_endpoint',
            'authentication_header_name'
        ]
    
    def get_authorization_url(self, state: str, redirect_uri: str) -> Optional[str]:
        """
        API key auth doesn't require redirect.
        
        Requirements: 6.2
        
        Args:
            state: CSRF protection state parameter (unused)
            redirect_uri: Callback URL (unused)
            
        Returns:
            None (no redirect needed for API key auth)
        """
        return None
    
    async def complete_authentication(
        self,
        authorization_code: str,
        state: str,
        redirect_uri: str,
        **kwargs
    ) -> Dict[str, Any]:
        """
        Validate and store API key.
        
        Requirements: 6.3, 6.6, 6.9
        
        Args:
            authorization_code: Unused for API key auth
            state: CSRF protection state parameter (unused)
            redirect_uri: Callback URL (unused)
            **kwargs: Must contain 'api_key' parameter
            
        Returns:
            Dictionary with encrypted API key
        """
        from apps.automation.services.auth_client import AuthClient
        from apps.automation.utils.encryption import TokenEncryption
        
        api_key = kwargs.get('api_key')
        if not api_key:
            raise ValidationError("API key is required")
        
        # Validate API key by making test request (Requirement 6.9)
        is_valid = await AuthClient.validate_api_key(
            api_endpoint=self.auth_config['api_endpoint'],
            api_key=api_key,
            header_name=self.auth_config['authentication_header_name']
        )
        
        if not is_valid:
            raise ValidationError("Invalid API key")
        
        # Encrypt API key (Requirement 6.6)
        api_key_encrypted = TokenEncryption.encrypt(api_key)
        
        return {
            'access_token_encrypted': api_key_encrypted,
            'refresh_token_encrypted': None,
            'expires_at': None,  # API keys don't expire
            'scopes': []
        }
    
    async def refresh_credentials(self, integration) -> Dict[str, Any]:
        """
        API keys don't need refresh (no-op).
        
        Requirements: 6.7
        
        Args:
            integration: Integration instance (unused)
            
        Returns:
            Empty dictionary (no refresh needed)
        """
        return {}
    
    async def revoke_credentials(self, integration) -> bool:
        """
        API keys are manually revoked (no-op).
        
        Requirements: 6.8
        
        Args:
            integration: Integration instance (unused)
            
        Returns:
            True (manual revocation, always succeeds)
        """
        return True
