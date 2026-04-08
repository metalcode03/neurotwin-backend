"""
Base authentication strategy interface.

Defines the abstract base class for all authentication strategies,
ensuring consistent interface across OAuth, Meta, and API Key implementations.

Requirements: 4.1-4.6
"""

from abc import ABC, abstractmethod
from dataclasses import dataclass
from datetime import datetime
from typing import Dict, List, Optional, Tuple, Any

from django.core.exceptions import ValidationError


@dataclass
class AuthorizationResult:
    """
    Result of get_authorization_url operation.
    
    Attributes:
        url: Authorization URL to redirect user to
        state: CSRF protection token
        session_id: Session identifier for tracking
    """
    url: Optional[str]
    state: str
    session_id: str


@dataclass
class AuthenticationResult:
    """
    Result of complete_authentication operation.
    
    Attributes:
        access_token: Access token for API calls
        refresh_token: Optional refresh token for token renewal
        expires_at: Token expiration timestamp
        metadata: Additional platform-specific data
    """
    access_token: str
    refresh_token: Optional[str]
    expires_at: Optional[datetime]
    metadata: Dict[str, Any]


class BaseAuthStrategy(ABC):
    """
    Abstract base class for authentication strategies.
    
    All authentication strategies (OAuth, Meta, API Key) must implement
    this interface to ensure consistent behavior across the platform.
    
    Requirements: 4.1-4.6
    - Define abstract methods for auth lifecycle (4.1)
    - Validate configuration on instantiation (4.4)
    - Provide required fields specification (4.3)
    - Raise ValidationError on invalid config (4.6)
    """
    
    def __init__(self, integration_type):
        """
        Initialize authentication strategy.
        
        Args:
            integration_type: IntegrationTypeModel instance
            
        Raises:
            ValidationError: If auth_config is invalid
        """
        self.integration_type = integration_type
        self.auth_config = integration_type.auth_config
        self._validate_config()
    
    @abstractmethod
    def get_authorization_url(
        self,
        user_id: str,
        redirect_uri: str,
        state: str
    ) -> AuthorizationResult:
        """
        Generate authorization URL for user to grant permissions.
        
        For OAuth/Meta: Returns URL to redirect user to provider
        For API Key: Returns None (no redirect needed)
        
        Args:
            user_id: User identifier
            redirect_uri: Callback URL after authorization
            state: CSRF protection token
            
        Returns:
            AuthorizationResult with URL and session info
            
        Requirements: 4.1
        """
        pass
    
    @abstractmethod
    def complete_authentication(
        self,
        code: Optional[str] = None,
        state: Optional[str] = None,
        redirect_uri: Optional[str] = None,
        **kwargs
    ) -> AuthenticationResult:
        """
        Exchange authorization code for access tokens.
        
        For OAuth/Meta: Exchange code for tokens
        For API Key: Validate and store API key
        
        Args:
            code: Authorization code from provider (OAuth/Meta)
            state: CSRF protection token (OAuth/Meta)
            redirect_uri: Original callback URL (OAuth/Meta)
            **kwargs: Additional strategy-specific parameters
            
        Returns:
            AuthenticationResult with tokens and metadata
            
        Requirements: 4.1
        """
        pass
    
    @abstractmethod
    def refresh_credentials(self, integration) -> AuthenticationResult:
        """
        Refresh expired credentials.
        
        For OAuth: Use refresh_token to get new access_token
        For Meta: Exchange token before 60-day expiry
        For API Key: No-op (API keys don't expire)
        
        Args:
            integration: Integration instance with expired credentials
            
        Returns:
            AuthenticationResult with new tokens
            
        Requirements: 4.1
        """
        pass
    
    @abstractmethod
    def revoke_credentials(self, integration) -> bool:
        """
        Revoke credentials with provider.
        
        Called during integration uninstallation to clean up
        provider-side access.
        
        Args:
            integration: Integration instance to revoke
            
        Returns:
            True if revocation successful, False otherwise
            
        Requirements: 4.1
        """
        pass
    
    def validate_config(self) -> Tuple[bool, List[str]]:
        """
        Validate auth_config structure.
        
        Checks that all required fields are present in auth_config.
        
        Returns:
            Tuple of (is_valid, list of error messages)
            
        Requirements: 4.2
        """
        required_fields = self.get_required_fields()
        missing = [f for f in required_fields if f not in self.auth_config]
        
        if missing:
            return False, [f"Missing required field: {f}" for f in missing]
        
        return True, []
    
    @abstractmethod
    def get_required_fields(self) -> List[str]:
        """
        Get list of required auth_config fields.
        
        Each strategy defines its own required configuration fields.
        
        Returns:
            List of required field names
            
        Requirements: 4.3
        """
        pass
    
    def _validate_config(self):
        """
        Internal validation called during initialization.
        
        Raises:
            ValidationError: If auth_config is invalid
            
        Requirements: 4.4, 4.6
        """
        is_valid, errors = self.validate_config()
        if not is_valid:
            raise ValidationError(
                f"Invalid auth_config for {self.integration_type.name}: "
                f"{', '.join(errors)}"
            )
