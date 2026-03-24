"""
OAuth client utility for handling OAuth 2.0 authorization flows.

Provides methods for building authorization URLs, exchanging codes for tokens,
and refreshing expired tokens.

Requirements: 4.4-4.6, 15.7
"""

import logging
from typing import Optional
from urllib.parse import urlencode

import httpx
from django.core.exceptions import ValidationError


logger = logging.getLogger(__name__)


class OAuthError(Exception):
    """Base exception for OAuth-related errors."""
    pass


class OAuthAuthorizationError(OAuthError):
    """Raised when OAuth authorization fails."""
    pass


class OAuthTokenExchangeError(OAuthError):
    """Raised when token exchange fails."""
    pass


class OAuthTokenRefreshError(OAuthError):
    """Raised when token refresh fails."""
    pass


class OAuthClient:
    """
    OAuth 2.0 client for handling authorization flows.
    
    Supports:
    - Building authorization URLs
    - Exchanging authorization codes for tokens
    - Refreshing expired access tokens
    
    Requirements: 4.4-4.6, 15.7
    """
    
    def __init__(
        self,
        client_id: str,
        client_secret: str,
        authorization_url: str,
        token_url: str,
        scopes: list[str],
        redirect_uri: str
    ):
        """
        Initialize OAuth client with provider configuration.
        
        Args:
            client_id: OAuth client ID
            client_secret: OAuth client secret
            authorization_url: Provider's authorization endpoint
            token_url: Provider's token endpoint
            scopes: List of OAuth scopes to request
            redirect_uri: Callback URL for OAuth redirect
            
        Raises:
            ValidationError: If URLs are not HTTPS
        """
        self.client_id = client_id
        self.client_secret = client_secret
        self.authorization_url = authorization_url
        self.token_url = token_url
        self.scopes = scopes
        self.redirect_uri = redirect_uri
        
        # Validate HTTPS URLs (Requirement 2.3) - allow HTTP in DEBUG mode
        from django.conf import settings as django_settings
        if not django_settings.DEBUG:
            if not authorization_url.startswith('https://'):
                raise ValidationError('Authorization URL must use HTTPS')
            if not token_url.startswith('https://'):
                raise ValidationError('Token URL must use HTTPS')
            if not redirect_uri.startswith('https://') and not redirect_uri.startswith('http://localhost'):
                raise ValidationError('Redirect URI must use HTTPS (or localhost for development)')
    
    def build_authorization_url(self, state: str, **extra_params) -> str:
        """
        Build OAuth authorization URL with required parameters.
        
        Args:
            state: CSRF protection state parameter
            **extra_params: Additional provider-specific parameters
            
        Returns:
            str: Complete authorization URL
            
        Requirements: 4.4
        """
        params = {
            'client_id': self.client_id,
            'redirect_uri': self.redirect_uri,
            'response_type': 'code',
            'scope': ' '.join(self.scopes),
            'state': state,
            'access_type': 'offline',  # Request refresh token
            **extra_params
        }
        
        query_string = urlencode(params)
        url = f"{self.authorization_url}?{query_string}"
        
        logger.info(
            f"Built authorization URL for client_id={self.client_id}, "
            f"scopes={self.scopes}, state={state[:8]}..."
        )
        
        return url
    
    async def exchange_code_for_tokens(
        self,
        authorization_code: str,
        **extra_params
    ) -> dict:
        """
        Exchange authorization code for access and refresh tokens.
        
        Args:
            authorization_code: Authorization code from OAuth callback
            **extra_params: Additional provider-specific parameters
            
        Returns:
            dict: Token response containing:
                - access_token: OAuth access token
                - refresh_token: OAuth refresh token (if available)
                - expires_in: Token expiration time in seconds
                - token_type: Token type (usually "Bearer")
                - scope: Granted scopes
                
        Raises:
            OAuthTokenExchangeError: If token exchange fails
            
        Requirements: 4.5-4.6
        """
        data = {
            'client_id': self.client_id,
            'client_secret': self.client_secret,
            'code': authorization_code,
            'redirect_uri': self.redirect_uri,
            'grant_type': 'authorization_code',
            **extra_params
        }
        
        try:
            async with httpx.AsyncClient(timeout=30.0) as client:
                response = await client.post(
                    self.token_url,
                    data=data,
                    headers={'Accept': 'application/json'}
                )
                
                if response.status_code != 200:
                    error_data = response.json() if response.headers.get('content-type', '').startswith('application/json') else {}
                    error_message = error_data.get('error_description', error_data.get('error', 'Unknown error'))
                    
                    logger.error(
                        f"Token exchange failed: status={response.status_code}, "
                        f"error={error_message}"
                    )
                    
                    raise OAuthTokenExchangeError(
                        f"Token exchange failed: {error_message}"
                    )
                
                token_data = response.json()
                
                # Validate required fields
                if 'access_token' not in token_data:
                    raise OAuthTokenExchangeError(
                        "Token response missing access_token"
                    )
                
                logger.info(
                    f"Successfully exchanged authorization code for tokens. "
                    f"Expires in: {token_data.get('expires_in', 'unknown')}s"
                )
                
                return token_data
                
        except httpx.HTTPError as e:
            logger.error(f"HTTP error during token exchange: {str(e)}")
            raise OAuthTokenExchangeError(
                f"Network error during token exchange: {str(e)}"
            )
        except Exception as e:
            if isinstance(e, OAuthTokenExchangeError):
                raise
            logger.error(f"Unexpected error during token exchange: {str(e)}")
            raise OAuthTokenExchangeError(
                f"Unexpected error during token exchange: {str(e)}"
            )
    
    async def refresh_token(
        self,
        refresh_token: str,
        **extra_params
    ) -> dict:
        """
        Refresh an expired access token using refresh token.
        
        Args:
            refresh_token: OAuth refresh token
            **extra_params: Additional provider-specific parameters
            
        Returns:
            dict: Token response containing new access_token and optionally new refresh_token
            
        Raises:
            OAuthTokenRefreshError: If token refresh fails
            
        Requirements: 15.7
        """
        data = {
            'client_id': self.client_id,
            'client_secret': self.client_secret,
            'refresh_token': refresh_token,
            'grant_type': 'refresh_token',
            **extra_params
        }
        
        try:
            async with httpx.AsyncClient(timeout=30.0) as client:
                response = await client.post(
                    self.token_url,
                    data=data,
                    headers={'Accept': 'application/json'}
                )
                
                if response.status_code != 200:
                    error_data = response.json() if response.headers.get('content-type', '').startswith('application/json') else {}
                    error_message = error_data.get('error_description', error_data.get('error', 'Unknown error'))
                    
                    logger.error(
                        f"Token refresh failed: status={response.status_code}, "
                        f"error={error_message}"
                    )
                    
                    raise OAuthTokenRefreshError(
                        f"Token refresh failed: {error_message}"
                    )
                
                token_data = response.json()
                
                # Validate required fields
                if 'access_token' not in token_data:
                    raise OAuthTokenRefreshError(
                        "Token response missing access_token"
                    )
                
                logger.info(
                    f"Successfully refreshed access token. "
                    f"Expires in: {token_data.get('expires_in', 'unknown')}s"
                )
                
                return token_data
                
        except httpx.HTTPError as e:
            logger.error(f"HTTP error during token refresh: {str(e)}")
            raise OAuthTokenRefreshError(
                f"Network error during token refresh: {str(e)}"
            )
        except Exception as e:
            if isinstance(e, OAuthTokenRefreshError):
                raise
            logger.error(f"Unexpected error during token refresh: {str(e)}")
            raise OAuthTokenRefreshError(
                f"Unexpected error during token refresh: {str(e)}"
            )
    
    @staticmethod
    def from_integration_type(integration_type, redirect_uri: str) -> 'OAuthClient':
        """
        Create OAuthClient from IntegrationType model instance.
        
        Args:
            integration_type: IntegrationType model instance
            redirect_uri: OAuth callback URL
            
        Returns:
            OAuthClient: Configured OAuth client
        """
        oauth_config = integration_type.oauth_config

        # Validate required OAuth config fields are present and non-empty
        required_fields = ['client_id', 'authorization_url', 'token_url']
        missing = [f for f in required_fields if not oauth_config.get(f)]
        if missing:
            raise ValidationError(
                f"Integration '{integration_type.name}' is missing OAuth config fields: "
                f"{', '.join(missing)}. Please configure the integration in the admin panel."
            )

        return OAuthClient(
            client_id=oauth_config.get('client_id', ''),
            client_secret=integration_type.oauth_client_secret,  # Uses decryption property
            authorization_url=oauth_config.get('authorization_url', ''),
            token_url=oauth_config.get('token_url', ''),
            scopes=integration_type.oauth_scopes,  # Uses property that handles list/string
            redirect_uri=redirect_uri
        )
