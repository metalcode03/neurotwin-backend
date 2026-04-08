"""
Authentication Strategy Base Class

Defines the interface for all authentication strategies in the multi-auth system.
Each concrete strategy (OAuth, Meta, API Key) implements this interface.

Requirements: 3.1, 3.2, 3.3, 3.4, 3.5
"""

from abc import ABC, abstractmethod
from typing import Optional, Dict, Any, List
from django.core.exceptions import ValidationError


class AuthStrategy(ABC):
    """
    Base class for authentication strategies.
    
    Defines the interface that all authentication strategies must implement.
    Each strategy handles a specific authentication method (OAuth, Meta, API Key).
    
    Requirements: 3.1-3.5
    """
    
    def __init__(self, integration_type):
        """
        Initialize the strategy with integration type configuration.
        
        Args:
            integration_type: IntegrationTypeModel instance with auth_config
        """
        self.integration_type = integration_type
        self.auth_config = integration_type.auth_config
        self.validate_config()
    
    @abstractmethod
    def get_authorization_url(self, state: str, redirect_uri: str) -> Optional[str]:
        """
        Get the authorization URL for user redirect.
        
        Args:
            state: CSRF protection state parameter
            redirect_uri: Callback URL after authorization
            
        Returns:
            Authorization URL string, or None if no redirect needed (e.g., API key)
        """
        pass
    
    @abstractmethod
    async def complete_authentication(
        self,
        authorization_code: str,
        state: str,
        redirect_uri: str,
        **kwargs
    ) -> Dict[str, Any]:
        """
        Complete the authentication flow and retrieve credentials.
        
        Args:
            authorization_code: Authorization code from provider
            state: CSRF protection state parameter
            redirect_uri: Callback URL used in authorization
            **kwargs: Additional auth-type-specific parameters
            
        Returns:
            Dictionary containing:
                - access_token_encrypted: Encrypted access token
                - refresh_token_encrypted: Encrypted refresh token (if applicable)
                - expires_at: Token expiration datetime
                - Additional auth-type-specific fields
        """
        pass
    
    @abstractmethod
    async def refresh_credentials(self, integration) -> Dict[str, Any]:
        """
        Refresh expired credentials.
        
        Args:
            integration: Integration instance with current credentials
            
        Returns:
            Dictionary with refreshed credentials
        """
        pass
    
    @abstractmethod
    async def revoke_credentials(self, integration) -> bool:
        """
        Revoke credentials with the provider.
        
        Args:
            integration: Integration instance to revoke
            
        Returns:
            True if revocation successful, False otherwise
        """
        pass
    
    def validate_config(self) -> None:
        """
        Validate that auth_config contains all required fields.
        
        Raises:
            ValidationError: If required fields are missing or invalid
        """
        required_fields = self.get_required_fields()
        missing_fields = [
            field for field in required_fields
            if field not in self.auth_config
        ]
        
        if missing_fields:
            raise ValidationError(
                f"Missing required fields for {self.__class__.__name__}: "
                f"{', '.join(missing_fields)}"
            )
    
    @abstractmethod
    def get_required_fields(self) -> List[str]:
        """
        Get list of required fields in auth_config.
        
        Returns:
            List of required field names
        """
        pass
