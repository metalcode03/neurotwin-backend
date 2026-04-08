"""
OAuth 2.0 authentication strategy implementation.

Implements OAuth 2.0 authorization code flow with PKCE support
for secure authentication with third-party providers.

Requirements: 5.1-5.7
"""

import os
import base64
import hashlib
import logging
from typing import List, Optional
from urllib.parse import urlencode
from datetime import timedelta

import httpx
from django.utils import timezone
from django.core.exceptions import ValidationError

from .base import BaseAuthStrategy, AuthorizationResult, AuthenticationResult
from ..utils.encryption import TokenEncryption
from ..utils.oauth_state import cache_oauth_state, get_oauth_state
from ..utils.circuit_breaker_registry import CircuitBreakerRegistry
from ..utils.circuit_breaker import CircuitBreakerOpenException


logger = logging.getLogger(__name__)


class OAuthStrategy(BaseAuthStrategy):
    """
    OAuth 2.0 authentication strategy with PKCE support.
    
    Implements the OAuth 2.0 authorization code flow with PKCE
    (Proof Key for Code Exchange) for enhanced security.
    
    Requirements: 5.1-5.7
    - Generate authorization URL with PKCE (5.1)
    - Exchange code for tokens (5.2)
    - Refresh expired tokens (5.3)
    - Revoke tokens on uninstall (5.4)
    - Validate required config fields (5.5)
    - Enforce HTTPS URLs (5.6)
    - Store encrypted tokens (5.7)
    """
    
    def get_required_fields(self) -> List[str]:
        """
        Get required OAuth configuration fields.
        
        Returns:
            List of required field names
            
        Requirements: 5.5
        """
        return [
            'client_id',
            'client_secret_encrypted',
            'authorization_url',
            'token_url',
            'scopes'
        ]
    
    def get_authorization_url(
        self,
        user_id: str,
        redirect_uri: str,
        state: str
    ) -> AuthorizationResult:
        """
        Generate OAuth authorization URL with PKCE.
        
        Args:
            user_id: User identifier
            redirect_uri: Callback URL after authorization
            state: CSRF protection token
            
        Returns:
            AuthorizationResult with authorization URL
            
        Raises:
            ValidationError: If authorization_url is not HTTPS
            
        Requirements: 5.1, 5.6
        """
        # Validate HTTPS
        if not self.auth_config['authorization_url'].startswith('https://'):
            raise ValidationError(
                "OAuth authorization URL must use HTTPS protocol"
            )
        
        # Generate PKCE parameters
        code_verifier = self._generate_code_verifier()
        code_challenge = self._generate_code_challenge(code_verifier)
        
        # Build authorization URL parameters
        params = {
            'client_id': self.auth_config['client_id'],
            'redirect_uri': redirect_uri,
            'response_type': 'code',
            'state': state,
            'scope': ' '.join(self._get_scopes()),
            'code_challenge': code_challenge,
            'code_challenge_method': 'S256',
        }
        
        # Store code_verifier in cache for later use
        cache_oauth_state(state, {
            'code_verifier': code_verifier,
            'user_id': user_id,
            'integration_type_id': str(self.integration_type.id)
        })
        
        url = f"{self.auth_config['authorization_url']}?{urlencode(params)}"
        
        logger.info(
            f"Generated OAuth authorization URL for user {user_id}, "
            f"integration_type {self.integration_type.name}"
        )
        
        return AuthorizationResult(
            url=url,
            state=state,
            session_id=state
        )
    
    def complete_authentication(
        self,
        code: Optional[str] = None,
        state: Optional[str] = None,
        redirect_uri: Optional[str] = None,
        **kwargs
    ) -> AuthenticationResult:
        """
        Exchange OAuth authorization code for access tokens.
        
        Args:
            code: Authorization code from provider
            state: CSRF protection token
            redirect_uri: Original callback URL
            
        Returns:
            AuthenticationResult with tokens
            
        Raises:
            ValidationError: If state is invalid or token exchange fails
            
        Requirements: 5.2, 5.6, 5.7
        """
        # Validate token_url uses HTTPS
        if not self.auth_config['token_url'].startswith('https://'):
            raise ValidationError(
                "OAuth token URL must use HTTPS protocol"
            )
        
        # Retrieve code_verifier from cache
        session_data = get_oauth_state(state, consume=True)
        if not session_data:
            raise ValidationError("Invalid or expired OAuth state")
        
        code_verifier = session_data['code_verifier']
        
        # Exchange code for tokens
        token_data = {
            'grant_type': 'authorization_code',
            'code': code,
            'redirect_uri': redirect_uri,
            'client_id': self.auth_config['client_id'],
            'client_secret': self._decrypt_client_secret(),
            'code_verifier': code_verifier
        }
        
        # Get circuit breaker for this OAuth provider
        breaker = CircuitBreakerRegistry.get_oauth_breaker(
            self.integration_type.name
        )
        
        try:
            # Wrap external API call with circuit breaker
            def make_token_request():
                response = httpx.post(
                    self.auth_config['token_url'],
                    data=token_data,
                    timeout=30.0
                )
                response.raise_for_status()
                return response
            
            response = breaker.call(make_token_request)
            
        except CircuitBreakerOpenException as e:
            logger.error(f"Circuit breaker open for OAuth token exchange: {str(e)}")
            raise ValidationError(
                f"OAuth service temporarily unavailable. Please try again in a moment."
            )
        except httpx.HTTPStatusError as e:
            logger.error(
                f"OAuth token exchange failed: {e.response.status_code} "
                f"{e.response.text}"
            )
            raise ValidationError(
                f"OAuth authentication failed: {e.response.text}"
            )
        except httpx.RequestError as e:
            logger.error(f"OAuth token exchange request failed: {str(e)}")
            raise ValidationError(
                f"OAuth authentication failed: Network error"
            )
        
        tokens = response.json()
        
        # Calculate expiration time
        expires_in = tokens.get('expires_in', 3600)
        expires_at = timezone.now() + timedelta(seconds=expires_in)
        
        logger.info(
            f"OAuth authentication completed for "
            f"integration_type {self.integration_type.name}"
        )
        
        return AuthenticationResult(
            access_token=tokens['access_token'],
            refresh_token=tokens.get('refresh_token'),
            expires_at=expires_at,
            metadata={}
        )
    
    def refresh_credentials(self, integration) -> AuthenticationResult:
        """
        Refresh OAuth tokens using refresh_token.
        
        Args:
            integration: Integration with expired credentials
            
        Returns:
            AuthenticationResult with new tokens
            
        Raises:
            ValidationError: If refresh fails or no refresh_token
            
        Requirements: 5.3, 5.7
        """
        if not integration.refresh_token:
            raise ValidationError("No refresh token available")
        
        token_data = {
            'grant_type': 'refresh_token',
            'refresh_token': integration.refresh_token,
            'client_id': self.auth_config['client_id'],
            'client_secret': self._decrypt_client_secret()
        }
        
        # Get circuit breaker for this OAuth provider
        breaker = CircuitBreakerRegistry.get_oauth_breaker(
            self.integration_type.name
        )
        
        try:
            # Wrap external API call with circuit breaker
            def make_refresh_request():
                response = httpx.post(
                    self.auth_config['token_url'],
                    data=token_data,
                    timeout=30.0
                )
                response.raise_for_status()
                return response
            
            response = breaker.call(make_refresh_request)
            
        except CircuitBreakerOpenException as e:
            logger.error(f"Circuit breaker open for OAuth token refresh: {str(e)}")
            raise ValidationError(
                f"OAuth service temporarily unavailable. Please try again in a moment."
            )
        except httpx.HTTPStatusError as e:
            logger.error(
                f"OAuth token refresh failed: {e.response.status_code} "
                f"{e.response.text}"
            )
            raise ValidationError(
                f"OAuth token refresh failed: {e.response.text}"
            )
        except httpx.RequestError as e:
            logger.error(f"OAuth token refresh request failed: {str(e)}")
            raise ValidationError(
                f"OAuth token refresh failed: Network error"
            )
        
        tokens = response.json()
        
        # Calculate expiration time
        expires_in = tokens.get('expires_in', 3600)
        expires_at = timezone.now() + timedelta(seconds=expires_in)
        
        # Use new refresh_token if provided, otherwise keep existing
        new_refresh_token = tokens.get('refresh_token', integration.refresh_token)
        
        logger.info(
            f"OAuth credentials refreshed for integration {integration.id}"
        )
        
        return AuthenticationResult(
            access_token=tokens['access_token'],
            refresh_token=new_refresh_token,
            expires_at=expires_at,
            metadata={}
        )
    
    def revoke_credentials(self, integration) -> bool:
        """
        Revoke OAuth tokens with provider.
        
        Args:
            integration: Integration to revoke
            
        Returns:
            True if revocation successful
            
        Requirements: 5.4
        """
        revoke_url = self.auth_config.get('revoke_url')
        if not revoke_url:
            logger.info(
                f"No revoke_url configured for {self.integration_type.name}, "
                "skipping revocation"
            )
            return True
        
        try:
            response = httpx.post(
                revoke_url,
                data={
                    'token': integration.oauth_token,
                    'client_id': self.auth_config['client_id'],
                    'client_secret': self._decrypt_client_secret()
                },
                timeout=10.0
            )
            success = response.status_code in [200, 204]
            
            if success:
                logger.info(
                    f"OAuth credentials revoked for integration {integration.id}"
                )
            else:
                logger.warning(
                    f"OAuth revocation returned status {response.status_code} "
                    f"for integration {integration.id}"
                )
            
            return success
        except Exception as e:
            logger.error(
                f"Failed to revoke OAuth token for integration {integration.id}: "
                f"{str(e)}"
            )
            return False
    
    def _get_scopes(self) -> List[str]:
        """
        Get OAuth scopes as list.
        
        Returns:
            List of scope strings
        """
        scopes = self.auth_config.get('scopes', [])
        if isinstance(scopes, str):
            return [s.strip() for s in scopes.split(',') if s.strip()]
        return scopes
    
    def _decrypt_client_secret(self) -> str:
        """
        Decrypt OAuth client secret.
        
        Returns:
            Decrypted client secret
        """
        encrypted = self.auth_config['client_secret_encrypted']
        return TokenEncryption.decrypt(
            base64.b64decode(encrypted),
            auth_type='oauth'
        )
    
    def _generate_code_verifier(self) -> str:
        """
        Generate PKCE code verifier.
        
        Returns:
            Base64 URL-safe encoded random string
        """
        return base64.urlsafe_b64encode(
            os.urandom(32)
        ).decode('utf-8').rstrip('=')
    
    def _generate_code_challenge(self, verifier: str) -> str:
        """
        Generate PKCE code challenge from verifier.
        
        Args:
            verifier: Code verifier string
            
        Returns:
            Base64 URL-safe encoded SHA256 hash
        """
        digest = hashlib.sha256(verifier.encode('utf-8')).digest()
        return base64.urlsafe_b64encode(digest).decode('utf-8').rstrip('=')
