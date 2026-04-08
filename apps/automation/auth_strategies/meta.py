"""
Meta Business API authentication strategy implementation.

Implements Meta-specific authentication for WhatsApp Business API
with long-lived tokens (60-day expiry) and business account details.

Requirements: 6.1-6.7
"""

import base64
import logging
from typing import List, Dict, Any
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


class MetaAuthStrategy(BaseAuthStrategy):
    """
    Meta Business API authentication strategy.
    
    Supports WhatsApp Business API with 60-day token expiry.
    Fetches business account details including WABA ID, phone number ID,
    and business ID during authentication.
    
    Requirements: 6.1-6.7
    - Generate Meta Business verification URL (6.1)
    - Exchange code for 60-day token (6.2)
    - Fetch business account details (6.4, 6.7)
    - Refresh tokens before expiry (6.5)
    - Revoke tokens on uninstall (6.6)
    - Validate required config fields (6.3)
    """
    
    GRAPH_API_VERSION = 'v18.0'
    TOKEN_EXPIRY_DAYS = 60
    
    def get_required_fields(self) -> List[str]:
        """
        Get required Meta configuration fields.
        
        Returns:
            List of required field names
            
        Requirements: 6.3
        """
        return [
            'app_id',
            'app_secret_encrypted',
            'config_id',
            'business_verification_url'
        ]
    
    def get_authorization_url(
        self,
        user_id: str,
        redirect_uri: str,
        state: str
    ) -> AuthorizationResult:
        """
        Generate Meta Business verification URL.
        
        Args:
            user_id: User identifier
            redirect_uri: Callback URL after authorization
            state: CSRF protection token
            
        Returns:
            AuthorizationResult with Meta authorization URL
            
        Requirements: 6.1
        """
        # Store session data
        cache_oauth_state(state, {
            'user_id': user_id,
            'integration_type_id': str(self.integration_type.id)
        })
        
        # Build Meta authorization URL
        params = {
            'app_id': self.auth_config['app_id'],
            'config_id': self.auth_config['config_id'],
            'redirect_uri': redirect_uri,
            'state': state,
            'response_type': 'code'
        }
        
        url = f"{self.auth_config['business_verification_url']}?{urlencode(params)}"
        
        logger.info(
            f"Generated Meta authorization URL for user {user_id}, "
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
        Exchange Meta authorization code for long-lived token.
        
        Args:
            code: Authorization code from Meta
            state: CSRF protection token
            redirect_uri: Original callback URL
            
        Returns:
            AuthenticationResult with token and business details
            
        Raises:
            ValidationError: If state is invalid or exchange fails
            
        Requirements: 6.2, 6.4, 6.7
        """
        # Validate state
        session_data = get_oauth_state(state, consume=True)
        if not session_data:
            raise ValidationError("Invalid or expired OAuth state")
        
        # Exchange code for access token
        token_url = f"https://graph.facebook.com/{self.GRAPH_API_VERSION}/oauth/access_token"
        
        # Get circuit breaker for Meta API
        breaker = CircuitBreakerRegistry.get_meta_breaker()
        
        try:
            # Wrap external API call with circuit breaker
            def make_token_request():
                response = httpx.get(
                    token_url,
                    params={
                        'client_id': self.auth_config['app_id'],
                        'client_secret': self._decrypt_app_secret(),
                        'code': code,
                        'redirect_uri': redirect_uri
                    },
                    timeout=30.0
                )
                response.raise_for_status()
                return response
            
            response = breaker.call(make_token_request)
            
        except CircuitBreakerOpenException as e:
            logger.error(f"Circuit breaker open for Meta token exchange: {str(e)}")
            raise ValidationError(
                f"Meta service temporarily unavailable. Please try again in a moment."
            )
        except httpx.HTTPStatusError as e:
            logger.error(
                f"Meta token exchange failed: {e.response.status_code} "
                f"{e.response.text}"
            )
            raise ValidationError(
                f"Meta authentication failed: {e.response.text}"
            )
        except httpx.RequestError as e:
            logger.error(f"Meta token exchange request failed: {str(e)}")
            raise ValidationError(
                f"Meta authentication failed: Network error"
            )
        
        tokens = response.json()
        access_token = tokens['access_token']
        
        # Fetch business account details
        business_data = self._fetch_business_details(access_token)
        
        # Calculate expiration (60 days)
        expires_at = timezone.now() + timedelta(days=self.TOKEN_EXPIRY_DAYS)
        
        logger.info(
            f"Meta authentication completed for "
            f"integration_type {self.integration_type.name}, "
            f"business_id {business_data['business_id']}"
        )
        
        return AuthenticationResult(
            access_token=access_token,
            refresh_token=None,  # Meta uses long-lived tokens
            expires_at=expires_at,
            metadata={
                'business_id': business_data['business_id'],
                'waba_id': business_data['waba_id'],
                'phone_number_id': business_data['phone_number_id'],
                'phone_numbers': business_data['phone_numbers']
            }
        )
    
    def refresh_credentials(self, integration) -> AuthenticationResult:
        """
        Refresh Meta long-lived token before 60-day expiry.
        
        Args:
            integration: Integration with expiring credentials
            
        Returns:
            AuthenticationResult with new token
            
        Raises:
            ValidationError: If refresh fails
            
        Requirements: 6.5
        """
        token_url = f"https://graph.facebook.com/{self.GRAPH_API_VERSION}/oauth/access_token"
        
        # Get circuit breaker for Meta API
        breaker = CircuitBreakerRegistry.get_meta_breaker()
        
        try:
            # Wrap external API call with circuit breaker
            def make_refresh_request():
                response = httpx.get(
                    token_url,
                    params={
                        'grant_type': 'fb_exchange_token',
                        'client_id': self.auth_config['app_id'],
                        'client_secret': self._decrypt_app_secret(),
                        'fb_exchange_token': integration.oauth_token
                    },
                    timeout=30.0
                )
                response.raise_for_status()
                return response
            
            response = breaker.call(make_refresh_request)
            
        except CircuitBreakerOpenException as e:
            logger.error(f"Circuit breaker open for Meta token refresh: {str(e)}")
            raise ValidationError(
                f"Meta service temporarily unavailable. Please try again in a moment."
            )
        except httpx.HTTPStatusError as e:
            logger.error(
                f"Meta token refresh failed: {e.response.status_code} "
                f"{e.response.text}"
            )
            raise ValidationError(
                f"Meta token refresh failed: {e.response.text}"
            )
        except httpx.RequestError as e:
            logger.error(f"Meta token refresh request failed: {str(e)}")
            raise ValidationError(
                f"Meta token refresh failed: Network error"
            )
        
        tokens = response.json()
        expires_at = timezone.now() + timedelta(days=self.TOKEN_EXPIRY_DAYS)
        
        logger.info(
            f"Meta credentials refreshed for integration {integration.id}"
        )
        
        return AuthenticationResult(
            access_token=tokens['access_token'],
            refresh_token=None,
            expires_at=expires_at,
            metadata={}
        )
    
    def revoke_credentials(self, integration) -> bool:
        """
        Revoke Meta access token.
        
        Args:
            integration: Integration to revoke
            
        Returns:
            True if revocation successful
            
        Requirements: 6.6
        """
        try:
            revoke_url = (
                f"https://graph.facebook.com/{self.GRAPH_API_VERSION}/"
                f"{self.auth_config['app_id']}/permissions"
            )
            response = httpx.delete(
                revoke_url,
                params={'access_token': integration.oauth_token},
                timeout=10.0
            )
            success = response.status_code in [200, 204]
            
            if success:
                logger.info(
                    f"Meta credentials revoked for integration {integration.id}"
                )
            else:
                logger.warning(
                    f"Meta revocation returned status {response.status_code} "
                    f"for integration {integration.id}"
                )
            
            return success
        except Exception as e:
            logger.error(
                f"Failed to revoke Meta token for integration {integration.id}: "
                f"{str(e)}"
            )
            return False
    
    def _fetch_business_details(self, access_token: str) -> Dict[str, Any]:
        """
        Fetch Meta business account details.
        
        Retrieves business_id, waba_id, phone_number_id, and phone numbers
        from Meta Graph API.
        
        Args:
            access_token: Meta access token
            
        Returns:
            Dictionary with business details
            
        Raises:
            ValidationError: If business details cannot be fetched
            
        Requirements: 6.4, 6.7
        """
        # Get circuit breaker for Meta API
        breaker = CircuitBreakerRegistry.get_meta_breaker()
        
        try:
            # Get business accounts
            def fetch_businesses():
                response = httpx.get(
                    f"https://graph.facebook.com/{self.GRAPH_API_VERSION}/me/businesses",
                    params={'access_token': access_token},
                    timeout=30.0
                )
                response.raise_for_status()
                return response
            
            response = breaker.call(fetch_businesses)
            businesses = response.json()['data']
            if not businesses:
                raise ValidationError("No business accounts found")
            
            business_id = businesses[0]['id']
            
            # Get WABA (WhatsApp Business Account)
            def fetch_wabas():
                response = httpx.get(
                    f"https://graph.facebook.com/{self.GRAPH_API_VERSION}/"
                    f"{business_id}/owned_whatsapp_business_accounts",
                    params={'access_token': access_token},
                    timeout=30.0
                )
                response.raise_for_status()
                return response
            
            response = breaker.call(fetch_wabas)
            wabas = response.json()['data']
            if not wabas:
                raise ValidationError("No WhatsApp Business Accounts found")
            
            waba_id = wabas[0]['id']
            
            # Get phone numbers
            def fetch_phone_numbers():
                response = httpx.get(
                    f"https://graph.facebook.com/{self.GRAPH_API_VERSION}/"
                    f"{waba_id}/phone_numbers",
                    params={'access_token': access_token},
                    timeout=30.0
                )
                response.raise_for_status()
                return response
            
            response = breaker.call(fetch_phone_numbers)
            phone_numbers = response.json()['data']
            if not phone_numbers:
                raise ValidationError("No phone numbers found")
            
            phone_number_id = phone_numbers[0]['id']
            
            logger.info(
                f"Fetched Meta business details: business_id={business_id}, "
                f"waba_id={waba_id}, phone_number_id={phone_number_id}"
            )
            
            return {
                'business_id': business_id,
                'waba_id': waba_id,
                'phone_number_id': phone_number_id,
                'phone_numbers': [p['display_phone_number'] for p in phone_numbers]
            }
        except CircuitBreakerOpenException as e:
            logger.error(f"Circuit breaker open for Meta business details: {str(e)}")
            raise ValidationError(
                f"Meta service temporarily unavailable. Please try again in a moment."
            )
        except httpx.HTTPStatusError as e:
            logger.error(
                f"Failed to fetch Meta business details: {e.response.status_code} "
                f"{e.response.text}"
            )
            raise ValidationError(
                f"Failed to fetch business details: {e.response.text}"
            )
        except httpx.RequestError as e:
            logger.error(f"Meta business details request failed: {str(e)}")
            raise ValidationError(
                f"Failed to fetch business details: Network error"
            )
    
    def _decrypt_app_secret(self) -> str:
        """
        Decrypt Meta app secret.
        
        Returns:
            Decrypted app secret
        """
        encrypted = self.auth_config['app_secret_encrypted']
        return TokenEncryption.decrypt(
            base64.b64decode(encrypted),
            auth_type='meta'
        )
