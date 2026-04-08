"""
AuthClient for handling authentication flows across all auth types.

Provides HTTP client methods for OAuth 2.0, Meta Business, and API Key authentication.
Includes retry logic, exponential backoff, and comprehensive logging.

Requirements: 11.1-11.8
"""

import logging
import asyncio
from typing import Dict, Any, Optional
from urllib.parse import urlencode

import httpx
from django.core.exceptions import ValidationError


logger = logging.getLogger(__name__)


class AuthClientError(Exception):
    """Base exception for authentication client errors."""
    pass


class OAuthError(AuthClientError):
    """OAuth-specific errors."""
    pass


class MetaError(AuthClientError):
    """Meta-specific errors."""
    pass


class APIKeyError(AuthClientError):
    """API Key-specific errors."""
    pass


class AuthClient:
    """
    Generalized authentication client for all auth types.
    
    Handles HTTP requests for OAuth 2.0, Meta Business, and API Key authentication
    with retry logic, exponential backoff, and security validation.
    
    Requirements: 11.1-11.8
    """
    
    # Retry configuration
    MAX_RETRIES = 3
    INITIAL_BACKOFF = 1.0  # seconds
    MAX_BACKOFF = 10.0  # seconds
    TIMEOUT = 30.0  # seconds
    
    @classmethod
    def _validate_https_url(cls, url: str, url_name: str) -> None:
        """
        Validate that URL uses HTTPS protocol.
        
        Args:
            url: URL to validate
            url_name: Name of URL for error messages
            
        Raises:
            ValidationError: If URL doesn't use HTTPS
            
        Requirements: 11.7
        """
        from django.conf import settings
        
        # Allow HTTP in DEBUG mode or for localhost
        if settings.DEBUG or url.startswith('http://localhost') or url.startswith('http://127.0.0.1'):
            return
        
        if not url.startswith('https://'):
            raise ValidationError(
                f"{url_name} must use HTTPS protocol for security"
            )
    
    @classmethod
    def _sanitize_params(cls, params: Dict[str, Any]) -> Dict[str, Any]:
        """
        Sanitize parameters for logging by removing secrets.
        
        Args:
            params: Parameters dictionary
            
        Returns:
            Sanitized parameters safe for logging
            
        Requirements: 11.8
        """
        sensitive_keys = {
            'client_secret', 'app_secret', 'api_key', 'access_token',
            'refresh_token', 'code', 'token', 'password', 'secret'
        }
        
        sanitized = {}
        for key, value in params.items():
            if any(sensitive in key.lower() for sensitive in sensitive_keys):
                sanitized[key] = '***REDACTED***'
            else:
                sanitized[key] = value
        
        return sanitized
    
    @classmethod
    async def _retry_with_backoff(
        cls,
        func,
        *args,
        **kwargs
    ) -> Any:
        """
        Execute function with exponential backoff retry logic.
        
        Args:
            func: Async function to execute
            *args: Positional arguments for function
            **kwargs: Keyword arguments for function
            
        Returns:
            Function result
            
        Raises:
            AuthClientError: If all retries fail
            
        Requirements: 11.1, 11.2
        """
        backoff = cls.INITIAL_BACKOFF
        last_exception = None
        
        for attempt in range(cls.MAX_RETRIES):
            try:
                return await func(*args, **kwargs)
            except httpx.HTTPStatusError as e:
                # Don't retry client errors (4xx)
                if 400 <= e.response.status_code < 500:
                    raise
                last_exception = e
            except httpx.HTTPError as e:
                last_exception = e
            
            if attempt < cls.MAX_RETRIES - 1:
                logger.warning(
                    f"Request failed (attempt {attempt + 1}/{cls.MAX_RETRIES}), "
                    f"retrying in {backoff}s: {str(last_exception)}"
                )
                await asyncio.sleep(backoff)
                backoff = min(backoff * 2, cls.MAX_BACKOFF)
        
        raise AuthClientError(
            f"Request failed after {cls.MAX_RETRIES} attempts: {str(last_exception)}"
        )
    
    # ==================== OAuth 2.0 Methods ====================
    
    @classmethod
    async def exchange_oauth_code(
        cls,
        token_url: str,
        client_id: str,
        client_secret: str,
        code: str,
        redirect_uri: str,
        **extra_params
    ) -> Dict[str, Any]:
        """
        Exchange OAuth authorization code for access token.
        
        Args:
            token_url: OAuth token endpoint
            client_id: OAuth client ID
            client_secret: OAuth client secret
            code: Authorization code
            redirect_uri: Callback URL
            **extra_params: Additional provider-specific parameters
            
        Returns:
            Token response dictionary
            
        Raises:
            OAuthError: If token exchange fails
            
        Requirements: 11.1, 11.2
        """
        cls._validate_https_url(token_url, "OAuth token URL")
        
        data = {
            'client_id': client_id,
            'client_secret': client_secret,
            'code': code,
            'redirect_uri': redirect_uri,
            'grant_type': 'authorization_code',
            **extra_params
        }
        
        logger.info(
            f"Exchanging OAuth code for tokens: "
            f"token_url={token_url}, params={cls._sanitize_params(data)}"
        )
        
        async def _exchange():
            async with httpx.AsyncClient(timeout=cls.TIMEOUT) as client:
                response = await client.post(
                    token_url,
                    data=data,
                    headers={'Accept': 'application/json'}
                )
                response.raise_for_status()
                return response.json()
        
        try:
            token_data = await cls._retry_with_backoff(_exchange)
            
            if 'access_token' not in token_data:
                raise OAuthError("Token response missing access_token")
            
            logger.info(
                f"Successfully exchanged OAuth code. "
                f"Expires in: {token_data.get('expires_in', 'unknown')}s"
            )
            
            return token_data
            
        except httpx.HTTPStatusError as e:
            error_data = {}
            try:
                error_data = e.response.json()
            except Exception:
                pass
            
            error_message = error_data.get(
                'error_description',
                error_data.get('error', str(e))
            )
            
            logger.error(
                f"OAuth code exchange failed: status={e.response.status_code}, "
                f"error={error_message}"
            )
            
            raise OAuthError(f"Token exchange failed: {error_message}")
        
        except Exception as e:
            if isinstance(e, (OAuthError, AuthClientError)):
                raise
            logger.error(f"Unexpected error during OAuth code exchange: {str(e)}")
            raise OAuthError(f"Token exchange failed: {str(e)}")
    
    @classmethod
    async def refresh_oauth_token(
        cls,
        token_url: str,
        client_id: str,
        client_secret: str,
        refresh_token: str,
        **extra_params
    ) -> Dict[str, Any]:
        """
        Refresh OAuth access token using refresh token.
        
        Args:
            token_url: OAuth token endpoint
            client_id: OAuth client ID
            client_secret: OAuth client secret
            refresh_token: OAuth refresh token
            **extra_params: Additional provider-specific parameters
            
        Returns:
            Token response dictionary
            
        Raises:
            OAuthError: If token refresh fails
            
        Requirements: 11.2, 11.3
        """
        cls._validate_https_url(token_url, "OAuth token URL")
        
        data = {
            'client_id': client_id,
            'client_secret': client_secret,
            'refresh_token': refresh_token,
            'grant_type': 'refresh_token',
            **extra_params
        }
        
        logger.info(
            f"Refreshing OAuth token: "
            f"token_url={token_url}, params={cls._sanitize_params(data)}"
        )
        
        async def _refresh():
            async with httpx.AsyncClient(timeout=cls.TIMEOUT) as client:
                response = await client.post(
                    token_url,
                    data=data,
                    headers={'Accept': 'application/json'}
                )
                response.raise_for_status()
                return response.json()
        
        try:
            token_data = await cls._retry_with_backoff(_refresh)
            
            if 'access_token' not in token_data:
                raise OAuthError("Token response missing access_token")
            
            logger.info(
                f"Successfully refreshed OAuth token. "
                f"Expires in: {token_data.get('expires_in', 'unknown')}s"
            )
            
            return token_data
            
        except httpx.HTTPStatusError as e:
            error_data = {}
            try:
                error_data = e.response.json()
            except Exception:
                pass
            
            error_message = error_data.get(
                'error_description',
                error_data.get('error', str(e))
            )
            
            logger.error(
                f"OAuth token refresh failed: status={e.response.status_code}, "
                f"error={error_message}"
            )
            
            raise OAuthError(f"Token refresh failed: {error_message}")
        
        except Exception as e:
            if isinstance(e, (OAuthError, AuthClientError)):
                raise
            logger.error(f"Unexpected error during OAuth token refresh: {str(e)}")
            raise OAuthError(f"Token refresh failed: {str(e)}")
    
    @classmethod
    async def revoke_oauth_token(
        cls,
        revoke_url: str,
        token: str,
        client_id: Optional[str] = None,
        client_secret: Optional[str] = None,
        **extra_params
    ) -> bool:
        """
        Revoke OAuth token with provider.
        
        Args:
            revoke_url: OAuth revocation endpoint
            token: Token to revoke
            client_id: Optional OAuth client ID
            client_secret: Optional OAuth client secret
            **extra_params: Additional provider-specific parameters
            
        Returns:
            True if revocation successful
            
        Raises:
            OAuthError: If revocation fails
            
        Requirements: 11.4
        """
        cls._validate_https_url(revoke_url, "OAuth revoke URL")
        
        data = {
            'token': token,
            **extra_params
        }
        
        if client_id:
            data['client_id'] = client_id
        if client_secret:
            data['client_secret'] = client_secret
        
        logger.info(
            f"Revoking OAuth token: "
            f"revoke_url={revoke_url}, params={cls._sanitize_params(data)}"
        )
        
        try:
            async with httpx.AsyncClient(timeout=cls.TIMEOUT) as client:
                response = await client.post(
                    revoke_url,
                    data=data,
                    headers={'Accept': 'application/json'}
                )
                
                # Some providers return 200, others return 204
                if response.status_code in (200, 204):
                    logger.info("Successfully revoked OAuth token")
                    return True
                
                response.raise_for_status()
                return True
                
        except httpx.HTTPError as e:
            logger.error(f"OAuth token revocation failed: {str(e)}")
            raise OAuthError(f"Token revocation failed: {str(e)}")
    
    # ==================== Meta Business Methods ====================
    
    @classmethod
    async def exchange_meta_code(
        cls,
        app_id: str,
        app_secret: str,
        code: str,
        redirect_uri: str
    ) -> Dict[str, Any]:
        """
        Exchange Meta authorization code for short-lived access token.
        
        Args:
            app_id: Meta app ID
            app_secret: Meta app secret
            code: Authorization code
            redirect_uri: Callback URL
            
        Returns:
            Token response dictionary
            
        Raises:
            MetaError: If token exchange fails
            
        Requirements: 11.5
        """
        token_url = "https://graph.facebook.com/v18.0/oauth/access_token"
        
        params = {
            'client_id': app_id,
            'client_secret': app_secret,
            'code': code,
            'redirect_uri': redirect_uri
        }
        
        logger.info(
            f"Exchanging Meta code for short-lived token: "
            f"params={cls._sanitize_params(params)}"
        )
        
        async def _exchange():
            async with httpx.AsyncClient(timeout=cls.TIMEOUT) as client:
                response = await client.get(
                    token_url,
                    params=params
                )
                response.raise_for_status()
                return response.json()
        
        try:
            token_data = await cls._retry_with_backoff(_exchange)
            
            if 'access_token' not in token_data:
                raise MetaError("Token response missing access_token")
            
            logger.info("Successfully exchanged Meta code for short-lived token")
            
            return token_data
            
        except httpx.HTTPStatusError as e:
            error_data = {}
            try:
                error_data = e.response.json()
            except Exception:
                pass
            
            error_message = error_data.get(
                'error',
                {}).get('message', str(e))
            
            logger.error(
                f"Meta code exchange failed: status={e.response.status_code}, "
                f"error={error_message}"
            )
            
            raise MetaError(f"Meta token exchange failed: {error_message}")
        
        except Exception as e:
            if isinstance(e, (MetaError, AuthClientError)):
                raise
            logger.error(f"Unexpected error during Meta code exchange: {str(e)}")
            raise MetaError(f"Meta token exchange failed: {str(e)}")
    
    @classmethod
    async def exchange_meta_long_lived_token(
        cls,
        app_id: str,
        app_secret: str,
        short_lived_token: str
    ) -> Dict[str, Any]:
        """
        Exchange Meta short-lived token for long-lived token (60 days).
        
        Args:
            app_id: Meta app ID
            app_secret: Meta app secret
            short_lived_token: Short-lived access token
            
        Returns:
            Token response dictionary with long-lived token
            
        Raises:
            MetaError: If token exchange fails
            
        Requirements: 11.6
        """
        token_url = "https://graph.facebook.com/v18.0/oauth/access_token"
        
        params = {
            'grant_type': 'fb_exchange_token',
            'client_id': app_id,
            'client_secret': app_secret,
            'fb_exchange_token': short_lived_token
        }
        
        logger.info(
            f"Exchanging Meta short-lived token for long-lived token: "
            f"params={cls._sanitize_params(params)}"
        )
        
        async def _exchange():
            async with httpx.AsyncClient(timeout=cls.TIMEOUT) as client:
                response = await client.get(
                    token_url,
                    params=params
                )
                response.raise_for_status()
                return response.json()
        
        try:
            token_data = await cls._retry_with_backoff(_exchange)
            
            if 'access_token' not in token_data:
                raise MetaError("Token response missing access_token")
            
            logger.info(
                f"Successfully exchanged for long-lived token. "
                f"Expires in: {token_data.get('expires_in', 'unknown')}s"
            )
            
            return token_data
            
        except httpx.HTTPStatusError as e:
            error_data = {}
            try:
                error_data = e.response.json()
            except Exception:
                pass
            
            error_message = error_data.get(
                'error',
                {}).get('message', str(e))
            
            logger.error(
                f"Meta long-lived token exchange failed: "
                f"status={e.response.status_code}, error={error_message}"
            )
            
            raise MetaError(f"Long-lived token exchange failed: {error_message}")
        
        except Exception as e:
            if isinstance(e, (MetaError, AuthClientError)):
                raise
            logger.error(
                f"Unexpected error during Meta long-lived token exchange: {str(e)}"
            )
            raise MetaError(f"Long-lived token exchange failed: {str(e)}")
    
    @classmethod
    async def get_meta_business_details(
        cls,
        access_token: str
    ) -> Dict[str, Any]:
        """
        Retrieve Meta business account details.
        
        Args:
            access_token: Meta access token
            
        Returns:
            Business details dictionary containing:
                - business_id: Meta Business ID
                - waba_id: WhatsApp Business Account ID (if available)
                - phone_number_id: Phone number ID (if available)
                
        Raises:
            MetaError: If request fails
            
        Requirements: 11.7
        """
        # Get business accounts
        business_url = "https://graph.facebook.com/v18.0/me/businesses"
        
        params = {
            'access_token': access_token,
            'fields': 'id,name'
        }
        
        logger.info(
            f"Retrieving Meta business details: "
            f"params={cls._sanitize_params(params)}"
        )
        
        try:
            async with httpx.AsyncClient(timeout=cls.TIMEOUT) as client:
                # Get business accounts
                response = await client.get(business_url, params=params)
                response.raise_for_status()
                business_data = response.json()
                
                if not business_data.get('data'):
                    raise MetaError("No business accounts found")
                
                business_id = business_data['data'][0]['id']
                
                # Get WhatsApp Business Accounts
                waba_url = f"https://graph.facebook.com/v18.0/{business_id}/owned_whatsapp_business_accounts"
                waba_params = {
                    'access_token': access_token,
                    'fields': 'id,name'
                }
                
                waba_response = await client.get(waba_url, params=waba_params)
                waba_response.raise_for_status()
                waba_data = waba_response.json()
                
                result = {
                    'business_id': business_id,
                    'business_name': business_data['data'][0].get('name'),
                    'waba_id': None,
                    'phone_number_id': None
                }
                
                # Get phone numbers if WABA exists
                if waba_data.get('data'):
                    waba_id = waba_data['data'][0]['id']
                    result['waba_id'] = waba_id
                    
                    phone_url = f"https://graph.facebook.com/v18.0/{waba_id}/phone_numbers"
                    phone_params = {
                        'access_token': access_token,
                        'fields': 'id,display_phone_number,verified_name'
                    }
                    
                    phone_response = await client.get(phone_url, params=phone_params)
                    phone_response.raise_for_status()
                    phone_data = phone_response.json()
                    
                    if phone_data.get('data'):
                        result['phone_number_id'] = phone_data['data'][0]['id']
                        result['phone_numbers'] = phone_data['data']
                
                logger.info(
                    f"Successfully retrieved Meta business details: "
                    f"business_id={business_id}, waba_id={result.get('waba_id')}"
                )
                
                return result
                
        except httpx.HTTPStatusError as e:
            error_data = {}
            try:
                error_data = e.response.json()
            except Exception:
                pass
            
            error_message = error_data.get(
                'error',
                {}).get('message', str(e))
            
            logger.error(
                f"Failed to retrieve Meta business details: "
                f"status={e.response.status_code}, error={error_message}"
            )
            
            raise MetaError(f"Failed to retrieve business details: {error_message}")
        
        except Exception as e:
            if isinstance(e, (MetaError, AuthClientError)):
                raise
            logger.error(
                f"Unexpected error retrieving Meta business details: {str(e)}"
            )
            raise MetaError(f"Failed to retrieve business details: {str(e)}")
    
    @classmethod
    async def revoke_meta_token(
        cls,
        access_token: str
    ) -> bool:
        """
        Revoke Meta access token.
        
        Args:
            access_token: Meta access token to revoke
            
        Returns:
            True if revocation successful
            
        Raises:
            MetaError: If revocation fails
            
        Requirements: 11.8
        """
        revoke_url = "https://graph.facebook.com/v18.0/me/permissions"
        
        params = {
            'access_token': access_token
        }
        
        logger.info(
            f"Revoking Meta token: params={cls._sanitize_params(params)}"
        )
        
        try:
            async with httpx.AsyncClient(timeout=cls.TIMEOUT) as client:
                response = await client.delete(
                    revoke_url,
                    params=params
                )
                response.raise_for_status()
                
                logger.info("Successfully revoked Meta token")
                return True
                
        except httpx.HTTPError as e:
            logger.error(f"Meta token revocation failed: {str(e)}")
            raise MetaError(f"Token revocation failed: {str(e)}")
    
    # ==================== API Key Methods ====================
    
    @classmethod
    async def validate_api_key(
        cls,
        api_endpoint: str,
        api_key: str,
        header_name: str = 'Authorization',
        header_format: str = 'Bearer {key}'
    ) -> bool:
        """
        Validate API key by making test request.
        
        Args:
            api_endpoint: API endpoint to test
            api_key: API key to validate
            header_name: Header name for API key (default: Authorization)
            header_format: Format string for header value (default: Bearer {key})
            
        Returns:
            True if API key is valid
            
        Raises:
            APIKeyError: If validation fails
            
        Requirements: 11.8
        """
        cls._validate_https_url(api_endpoint, "API endpoint")
        
        headers = {
            header_name: header_format.format(key=api_key)
        }
        
        logger.info(
            f"Validating API key: endpoint={api_endpoint}, "
            f"header={header_name}"
        )
        
        try:
            async with httpx.AsyncClient(timeout=cls.TIMEOUT) as client:
                response = await client.get(
                    api_endpoint,
                    headers=headers
                )
                
                # Consider 2xx and 3xx as valid
                if 200 <= response.status_code < 400:
                    logger.info("API key validation successful")
                    return True
                
                # 401/403 means invalid key
                if response.status_code in (401, 403):
                    logger.warning(
                        f"API key validation failed: status={response.status_code}"
                    )
                    return False
                
                # Other errors
                response.raise_for_status()
                return True
                
        except httpx.HTTPError as e:
            logger.error(f"API key validation request failed: {str(e)}")
            raise APIKeyError(f"API key validation failed: {str(e)}")
