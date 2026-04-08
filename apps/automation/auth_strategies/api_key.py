"""
API Key authentication strategy implementation.

Implements simple API key authentication for services that don't
require OAuth flows. Validates keys by making test requests.

Requirements: 7.1-7.7
"""

import logging
from typing import List, Optional

import httpx
from django.core.exceptions import ValidationError

from .base import BaseAuthStrategy, AuthorizationResult, AuthenticationResult
from ..utils.circuit_breaker_registry import CircuitBreakerRegistry
from ..utils.circuit_breaker import CircuitBreakerOpenException


logger = logging.getLogger(__name__)


class APIKeyStrategy(BaseAuthStrategy):
    """
    Simple API key authentication strategy.
    
    For services that use API key authentication instead of OAuth.
    Validates keys by making test requests to the configured endpoint.
    
    Requirements: 7.1-7.7
    - No authorization URL needed (7.1)
    - Validate API key with test request (7.2, 7.4)
    - Store encrypted API key (7.5)
    - No refresh needed (7.6)
    - No revocation needed (7.7)
    - Validate required config fields (7.3)
    """
    
    def get_required_fields(self) -> List[str]:
        """
        Get required API Key configuration fields.
        
        Returns:
            List of required field names
            
        Requirements: 7.3
        """
        return [
            'api_endpoint',
            'authentication_header_name'
        ]
    
    def get_authorization_url(
        self,
        user_id: str,
        redirect_uri: str,
        state: str
    ) -> AuthorizationResult:
        """
        API Key auth doesn't require redirect.
        
        Returns None to indicate frontend should show API key input form.
        
        Args:
            user_id: User identifier
            redirect_uri: Not used for API key auth
            state: CSRF protection token
            
        Returns:
            AuthorizationResult with url=None
            
        Requirements: 7.1
        """
        logger.info(
            f"API Key authentication initiated for user {user_id}, "
            f"integration_type {self.integration_type.name}"
        )
        
        return AuthorizationResult(
            url=None,  # No redirect needed
            state=state,
            session_id=state
        )
    
    def complete_authentication(
        self,
        code: Optional[str] = None,
        state: Optional[str] = None,
        redirect_uri: Optional[str] = None,
        api_key: Optional[str] = None,
        **kwargs
    ) -> AuthenticationResult:
        """
        Validate and store API key.
        
        Makes a test request to validate the API key works.
        
        Args:
            api_key: API key to validate
            state: CSRF protection token (optional)
            code: Not used for API key auth
            redirect_uri: Not used for API key auth
            
        Returns:
            AuthenticationResult with API key as access_token
            
        Raises:
            ValidationError: If API key is invalid
            
        Requirements: 7.2, 7.4, 7.5
        """
        if not api_key:
            raise ValidationError("API key is required")
        
        # Validate API key by making test request
        is_valid = self._validate_api_key(api_key)
        if not is_valid:
            raise ValidationError(
                "Invalid API key. Please verify the key and try again."
            )
        
        logger.info(
            f"API Key authentication completed for "
            f"integration_type {self.integration_type.name}"
        )
        
        return AuthenticationResult(
            access_token=api_key,
            refresh_token=None,  # API keys don't have refresh tokens
            expires_at=None,  # API keys don't expire
            metadata={}
        )
    
    def refresh_credentials(self, integration) -> AuthenticationResult:
        """
        API keys don't need refresh.
        
        Returns the existing API key unchanged.
        
        Args:
            integration: Integration with API key
            
        Returns:
            AuthenticationResult with existing API key
            
        Requirements: 7.6
        """
        logger.debug(
            f"API Key refresh called for integration {integration.id} "
            "(no-op, API keys don't expire)"
        )
        
        return AuthenticationResult(
            access_token=integration.api_key,
            refresh_token=None,
            expires_at=None,
            metadata={}
        )
    
    def revoke_credentials(self, integration) -> bool:
        """
        API keys are manually revoked by user.
        
        No automatic revocation is performed. Users must revoke
        keys through the service provider's interface.
        
        Args:
            integration: Integration to revoke
            
        Returns:
            True (always succeeds as no action needed)
            
        Requirements: 7.7
        """
        logger.info(
            f"API Key revocation called for integration {integration.id} "
            "(no-op, manual revocation required)"
        )
        return True
    
    def _validate_api_key(self, api_key: str) -> bool:
        """
        Validate API key with test request.
        
        Makes a test request to the configured api_endpoint with the
        API key in the specified header to verify it works.
        
        Args:
            api_key: API key to validate
            
        Returns:
            True if API key is valid, False otherwise
            
        Requirements: 7.4
        """
        # Get circuit breaker for this API key service
        breaker = CircuitBreakerRegistry.get_api_key_breaker(
            self.integration_type.name
        )
        
        try:
            # Build headers with API key
            headers = {
                self.auth_config['authentication_header_name']: api_key
            }
            
            # Add any additional headers from config
            additional_headers = self.auth_config.get('additional_headers', {})
            headers.update(additional_headers)
            
            # Wrap external API call with circuit breaker
            def make_validation_request():
                response = httpx.get(
                    self.auth_config['api_endpoint'],
                    headers=headers,
                    timeout=10.0
                )
                return response
            
            response = breaker.call(make_validation_request)
            
            # Consider 200 and 204 as success
            is_valid = response.status_code in [200, 204]
            
            if is_valid:
                logger.info(
                    f"API key validation successful for "
                    f"integration_type {self.integration_type.name}"
                )
            else:
                logger.warning(
                    f"API key validation failed with status {response.status_code} "
                    f"for integration_type {self.integration_type.name}"
                )
            
            return is_valid
            
        except CircuitBreakerOpenException as e:
            logger.error(
                f"Circuit breaker open for API key validation "
                f"({self.integration_type.name}): {str(e)}"
            )
            return False
        except httpx.TimeoutException:
            logger.error(
                f"API key validation timed out for "
                f"integration_type {self.integration_type.name}"
            )
            return False
        except httpx.RequestError as e:
            logger.error(
                f"API key validation request failed for "
                f"integration_type {self.integration_type.name}: {str(e)}"
            )
            return False
        except Exception as e:
            logger.error(
                f"API key validation failed with unexpected error for "
                f"integration_type {self.integration_type.name}: {str(e)}"
            )
            return False
