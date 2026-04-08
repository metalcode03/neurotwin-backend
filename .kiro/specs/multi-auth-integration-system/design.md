# Design Document: Multi-Auth Integration System

## Overview

The Multi-Auth Integration System refactors NeuroTwin's integration authentication architecture to support multiple authentication strategies beyond OAuth 2.0. Currently, the system assumes all integrations use OAuth, but platforms like Meta (WhatsApp/Instagram) require different authentication flows, and some integrations use simple API keys. This design enables the platform to support OAuth, Meta Business authentication, API key authentication, and future authentication methods while maintaining backward compatibility with existing OAuth integrations.

### Key Design Goals

1. **Extensibility**: Support multiple authentication strategies through a pluggable architecture
2. **Backward Compatibility**: Seamlessly migrate existing OAuth integrations without data loss
3. **Security**: Maintain encryption for all credentials with proper key management
4. **Type Safety**: Provide type-safe configuration parsing and validation
5. **Flexibility**: Enable future authentication methods without refactoring

### System Context

This refactoring impacts several NeuroTwin subsystems:
- **Integration Management**: Core authentication and credential storage
- **Installation Flow**: Two-phase installation process for different auth types
- **Webhook Infrastructure**: Meta webhook handling for real-time events
- **Admin Interface**: Configuration management for integration types
- **API Layer**: Endpoints for installation, callback handling, and management

## Architecture

### High-Level Architecture

```
┌─────────────────────────────────────────────────────────────────┐
│                         Frontend Layer                          │
│  ┌──────────────────┐              ┌──────────────────────┐    │
│  │  App Marketplace │              │ Installation Flow    │    │
│  │   (/apps)        │              │   (OAuth/Meta/API)   │    │
│  └────────┬─────────┘              └──────────┬───────────┘    │
└───────────┼────────────────────────────────────┼────────────────┘
            │                                    │
            │ REST API (JWT Auth)                │
            │                                    │
┌───────────┼────────────────────────────────────┼────────────────┐
│           │         Backend Layer              │                │
│  ┌────────▼─────────┐              ┌──────────▼───────────┐    │
│  │ Installation API │              │  Webhook API         │    │
│  │  - Start install │              │  - Meta webhooks     │    │
│  │  - OAuth callback│              │  - Signature verify  │    │
│  │  - Meta callback │              │  - Event routing     │    │
│  │  - API key setup │              └──────────────────────┘    │
│  └────────┬─────────┘                                           │
│           │                                                     │
│  ┌────────▼────────────────────────────────────────────────┐   │
│  │              Service Layer                              │   │
│  │  ┌──────────────────────────────────────────────────┐  │   │
│  │  │         AuthStrategyFactory                      │  │   │
│  │  │  - create_strategy(integration_type)             │  │   │
│  │  └──────────────┬───────────────────────────────────┘  │   │
│  │                 │                                       │   │
│  │     ┌───────────┼───────────┬───────────────┐          │   │
│  │     │           │           │               │          │   │
│  │  ┌──▼────┐  ┌──▼────┐  ┌──▼────┐      ┌───▼──────┐   │   │
│  │  │OAuth  │  │Meta   │  │APIKey │      │Future    │   │   │
│  │  │Strategy│ │Strategy│ │Strategy│     │Strategies│   │   │
│  │  └───────┘  └───────┘  └───────┘      └──────────┘   │   │
│  │                                                        │   │
│  │  - InstallationService                                │   │
│  │  - AuthClient (HTTP client for all auth types)       │   │
│  │  - AuthConfigParser/Serializer                       │   │
│  │  - TokenEncryption                                    │   │
│  └────────┬───────────────────────────────────────────────┘   │
│           │                                                     │
│  ┌────────▼────────────────────────────────────────────────┐   │
│  │              Data Layer                                 │   │
│  │  - IntegrationTypeModel (auth_type, auth_config)       │   │
│  │  - Integration (oauth_token, meta_*, api_key)          │   │
│  │  - InstallationSession (status, oauth_state)           │   │
│  └─────────────────────────────────────────────────────────┘   │
└─────────────────────────────────────────────────────────────────┘
```

### Architectural Patterns

1. **Strategy Pattern**: Different authentication methods implemented as concrete strategies
2. **Factory Pattern**: AuthStrategyFactory creates appropriate strategy instances
3. **Adapter Pattern**: AuthClient abstracts HTTP operations for all auth types
4. **Template Method Pattern**: Base AuthStrategy defines common flow, subclasses customize
5. **Service Layer Pattern**: Business logic isolated in service classes

### Key Architectural Decisions

**Decision 1: Strategy Pattern for Authentication**
- **Choice**: Use Strategy pattern with AuthStrategy base class and concrete implementations
- **Rationale**: Enables adding new auth methods without modifying existing code (Open/Closed Principle)
- **Trade-off**: More classes to maintain, but gains flexibility and testability

**Decision 2: Rename oauth_config to auth_config**
- **Choice**: Rename field to be auth-type agnostic
- **Rationale**: OAuth-specific naming limits extensibility
- **Trade-off**: Requires migration, but improves semantic clarity

**Decision 3: JSON Storage for auth_config**
- **Choice**: Store configuration as flexible JSON instead of fixed columns
- **Rationale**: Different auth types need different configuration fields
- **Trade-off**: Less type safety at database level, but gains flexibility

**Decision 4: Separate Meta Callback Endpoint**
- **Choice**: Create dedicated /api/v1/integrations/meta/callback/ endpoint
- **Rationale**: Meta has different callback parameters than standard OAuth
- **Trade-off**: More endpoints to maintain, but clearer separation of concerns

**Decision 5: Generalize OAuthClient to AuthClient**
- **Choice**: Rename and extend to support all auth types
- **Rationale**: Avoid code duplication for HTTP operations
- **Trade-off**: Single class with more responsibilities, but reduces duplication

## Components and Interfaces

### Backend Components

#### 1. AuthStrategy Base Class

Abstract base class defining the authentication strategy interface.

```python
from abc import ABC, abstractmethod
from typing import Optional, Dict, Any, List
from apps.automation.models import IntegrationTypeModel, Integration


class AuthStrategy(ABC):
    """
    Base class for authentication strategies.
    
    Defines the interface that all authentication strategies must implement.
    Each strategy handles a specific authentication method (OAuth, Meta, API Key).
    
    Requirements: 3.1-3.5
    """
    
    def __init__(self, integration_type: IntegrationTypeModel):
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
                - access_token: Encrypted access token
                - refresh_token: Encrypted refresh token (if applicable)
                - expires_at: Token expiration datetime
                - Additional auth-type-specific fields
        """
        pass
    
    @abstractmethod
    async def refresh_credentials(self, integration: Integration) -> Dict[str, Any]:
        """
        Refresh expired credentials.
        
        Args:
            integration: Integration instance with current credentials
            
        Returns:
            Dictionary with refreshed credentials
        """
        pass
    
    @abstractmethod
    async def revoke_credentials(self, integration: Integration) -> bool:
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
```

#### 2. OAuthStrategy Implementation

OAuth 2.0 authentication strategy for standard OAuth providers.

```python
import httpx
from urllib.parse import urlencode
from typing import Optional, Dict, Any, List
from django.core.exceptions import ValidationError


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
        """
        from apps.automation.services.auth_client import AuthClient
        
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
    
    async def refresh_credentials(self, integration: Integration) -> Dict[str, Any]:
        """
        Refresh OAuth access token using refresh token.
        
        Requirements: 4.4
        """
        from apps.automation.services.auth_client import AuthClient
        
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
    
    async def revoke_credentials(self, integration: Integration) -> bool:
        """
        Revoke OAuth tokens with provider.
        
        Requirements: 4.5
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
```

#### 3. MetaStrategy Implementation

Meta Business authentication strategy for WhatsApp and Instagram.

```python
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
        """
        from apps.automation.services.auth_client import AuthClient
        
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
    
    async def refresh_credentials(self, integration: Integration) -> Dict[str, Any]:
        """
        Refresh Meta long-lived token.
        
        Requirements: 5.6
        """
        from apps.automation.services.auth_client import AuthClient
        
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
    
    async def revoke_credentials(self, integration: Integration) -> bool:
        """
        Revoke Meta access token.
        
        Requirements: 5.7
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
```

#### 4. APIKeyStrategy Implementation

Simple API key authentication strategy.

```python
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
        """
        from apps.automation.services.auth_client import AuthClient
        
        api_key = kwargs.get('api_key')
        if not api_key:
            raise ValidationError("API key is required")
        
        # Validate API key by making test request
        is_valid = await AuthClient.validate_api_key(
            api_endpoint=self.auth_config['api_endpoint'],
            api_key=api_key,
            header_name=self.auth_config['authentication_header_name']
        )
        
        if not is_valid:
            raise ValidationError("Invalid API key")
        
        # Encrypt API key
        api_key_encrypted = TokenEncryption.encrypt(api_key)
        
        return {
            'access_token_encrypted': api_key_encrypted,
            'refresh_token_encrypted': None,
            'expires_at': None,  # API keys don't expire
            'scopes': []
        }
    
    async def refresh_credentials(self, integration: Integration) -> Dict[str, Any]:
        """
        API keys don't need refresh (no-op).
        
        Requirements: 6.7
        """
        return {}
    
    async def revoke_credentials(self, integration: Integration) -> bool:
        """
        API keys are manually revoked (no-op).
        
        Requirements: 6.8
        """
        return True
```

#### 5. AuthStrategyFactory

Factory for creating authentication strategy instances.

```python
from django.core.exceptions import ValidationError
from apps.automation.models import IntegrationTypeModel


class AuthStrategyFactory:
    """
    Factory for creating authentication strategy instances.
    
    Uses the integration type's auth_type field to determine
    which strategy class to instantiate.
    
    Requirements: 7.1-7.7
    """
    
    _strategy_registry = {
        'oauth': OAuthStrategy,
        'meta': MetaStrategy,
        'api_key': APIKeyStrategy,
    }
    
    @classmethod
    def create_strategy(cls, integration_type: IntegrationTypeModel) -> AuthStrategy:
        """
        Create appropriate authentication strategy for integration type.
        
        Args:
            integration_type: IntegrationTypeModel instance
            
        Returns:
            Concrete AuthStrategy instance
            
        Raises:
            ValidationError: If auth_type is unrecognized
        """
        auth_type = integration_type.auth_type
        
        strategy_class = cls._strategy_registry.get(auth_type)
        if not strategy_class:
            raise ValidationError(
                f"Unrecognized auth_type: {auth_type}. "
                f"Supported types: {', '.join(cls._strategy_registry.keys())}"
            )
        
        return strategy_class(integration_type)
    
    @classmethod
    def register_strategy(cls, auth_type: str, strategy_class: type):
        """
        Register a new authentication strategy.
        
        Enables extensibility for future auth types.
        
        Args:
            auth_type: Authentication type identifier
            strategy_class: Strategy class to register
        """
        cls._strategy_registry[auth_type] = strategy_class
```


#### 6. InstallationService

Manages the installation process for all authentication types.

```python
import uuid
from typing import Dict, Any, Optional
from django.utils import timezone
from apps.automation.models import (
    IntegrationTypeModel,
    Integration,
    InstallationSession,
    InstallationStatus
)


class InstallationService:
    """
    Service for managing integration installation across all auth types.
    
    Handles the installation flow from initiation through completion,
    supporting OAuth, Meta, and API key authentication.
    
    Requirements: 8.1-8.8
    """
    
    @staticmethod
    def start_installation(
        user,
        integration_type_id: str
    ) -> Dict[str, Any]:
        """
        Start Phase 1 of installation: Create session and get auth URL.
        
        Args:
            user: User instance
            integration_type_id: UUID of integration type
            
        Returns:
            Dictionary with session_id, authorization_url (if needed),
            requires_redirect, requires_api_key
        """
        integration_type = IntegrationTypeModel.objects.get(
            id=integration_type_id,
            is_active=True
        )
        
        # Check if already installed
        if Integration.objects.filter(
            user=user,
            integration_type=integration_type
        ).exists():
            raise ValidationError("Integration already installed")
        
        # Create installation session
        oauth_state = str(uuid.uuid4())
        session = InstallationSession.objects.create(
            user=user,
            integration_type=integration_type,
            oauth_state=oauth_state,
            status=InstallationStatus.DOWNLOADING,
            progress=0
        )
        
        # Create strategy
        strategy = AuthStrategyFactory.create_strategy(integration_type)
        
        # Get authorization URL (None for API key)
        authorization_url = strategy.get_authorization_url(
            state=oauth_state,
            redirect_uri=InstallationService._get_callback_url(integration_type)
        )
        
        # Update session status
        if authorization_url:
            session.status = InstallationStatus.OAUTH_SETUP
            session.progress = 50
        else:
            # API key flow - no redirect needed
            session.progress = 30
        session.save()
        
        return {
            'session_id': str(session.id),
            'authorization_url': authorization_url,
            'requires_redirect': authorization_url is not None,
            'requires_api_key': authorization_url is None,
            'auth_type': integration_type.auth_type
        }
    
    @staticmethod
    async def complete_authentication_flow(
        session_id: str,
        authorization_code: str,
        state: str,
        **kwargs
    ) -> Integration:
        """
        Complete Phase 2: Exchange code for tokens and create Integration.
        
        Args:
            session_id: Installation session UUID
            authorization_code: Auth code from provider
            state: CSRF state parameter
            **kwargs: Additional auth-type-specific parameters
            
        Returns:
            Created Integration instance
        """
        session = InstallationSession.objects.get(id=session_id)
        
        # Validate state
        if session.oauth_state != state:
            session.status = InstallationStatus.FAILED
            session.error_message = "Invalid state parameter (CSRF check failed)"
            session.save()
            raise ValidationError("Invalid state parameter")
        
        # Check expiration
        if session.is_expired:
            session.status = InstallationStatus.FAILED
            session.error_message = "Installation session expired"
            session.save()
            raise ValidationError("Installation session expired")
        
        try:
            # Create strategy
            strategy = AuthStrategyFactory.create_strategy(session.integration_type)
            
            # Complete authentication
            auth_data = await strategy.complete_authentication(
                authorization_code=authorization_code,
                state=state,
                redirect_uri=InstallationService._get_callback_url(session.integration_type),
                **kwargs
            )
            
            # Create Integration record
            integration = Integration.objects.create(
                user=session.user,
                integration_type=session.integration_type,
                oauth_token_encrypted=auth_data['access_token_encrypted'],
                refresh_token_encrypted=auth_data.get('refresh_token_encrypted'),
                token_expires_at=auth_data.get('expires_at'),
                scopes=auth_data.get('scopes', []),
                is_active=True
            )
            
            # Store auth-type-specific data
            if session.integration_type.auth_type == 'meta':
                integration.meta_business_id = auth_data.get('meta_business_id')
                integration.meta_waba_id = auth_data.get('meta_waba_id')
                integration.meta_phone_number_id = auth_data.get('meta_phone_number_id')
                integration.meta_config = auth_data.get('meta_config', {})
                integration.save()
            
            # Update session
            session.status = InstallationStatus.COMPLETED
            session.progress = 100
            session.completed_at = timezone.now()
            session.save()
            
            logger.info(
                f"Integration installed: user={session.user.id}, "
                f"type={session.integration_type.type}, "
                f"auth_type={session.integration_type.auth_type}"
            )
            
            return integration
            
        except Exception as e:
            session.status = InstallationStatus.FAILED
            session.error_message = str(e)
            session.completed_at = timezone.now()
            session.save()
            
            logger.error(
                f"Installation failed: session={session_id}, error={e}"
            )
            raise
    
    @staticmethod
    async def uninstall_integration(
        user,
        integration_id: str
    ) -> Dict[str, Any]:
        """
        Uninstall integration and revoke credentials.
        
        Requirements: 8.8
        
        Args:
            user: User instance
            integration_id: Integration UUID
            
        Returns:
            Dictionary with success status and disabled workflow count
        """
        integration = Integration.objects.get(
            id=integration_id,
            user=user
        )
        
        # Create strategy
        strategy = AuthStrategyFactory.create_strategy(integration.integration_type)
        
        # Revoke credentials with provider
        try:
            await strategy.revoke_credentials(integration)
        except Exception as e:
            logger.warning(f"Failed to revoke credentials: {e}")
        
        # Disable dependent workflows
        from apps.automation.services.workflow import WorkflowService
        disabled_count = WorkflowService.disable_workflows_for_integration(
            user=user,
            integration_type_id=integration.integration_type.id
        )
        
        # Delete integration
        integration.delete()
        
        logger.info(
            f"Integration uninstalled: user={user.id}, "
            f"type={integration.integration_type.type}, "
            f"disabled_workflows={disabled_count}"
        )
        
        return {
            'success': True,
            'disabled_workflows': disabled_count
        }
    
    @staticmethod
    def _get_callback_url(integration_type: IntegrationTypeModel) -> str:
        """Get callback URL for integration type."""
        from django.conf import settings
        
        if integration_type.auth_type == 'meta':
            return f"{settings.BASE_URL}/api/v1/integrations/meta/callback/"
        else:
            return f"{settings.BASE_URL}/api/v1/integrations/oauth/callback/"
```



#### 7. AuthClient

Generalized HTTP client for all authentication operations.

```python
import httpx
import asyncio
from typing import Dict, Any, Optional
from django.conf import settings
import logging

logger = logging.getLogger(__name__)


class AuthClient:
    """
    Generalized authentication HTTP client.
    
    Handles HTTP operations for OAuth, Meta, and API key authentication
    with retry logic and proper error handling.
    
    Requirements: 11.1-11.8
    """
    
    MAX_RETRIES = 3
    RETRY_DELAY = 1.0  # seconds
    TIMEOUT = 30.0  # seconds
    
    @classmethod
    async def exchange_oauth_code(
        cls,
        token_url: str,
        client_id: str,
        client_secret: str,
        code: str,
        redirect_uri: str
    ) -> Dict[str, Any]:
        """
        Exchange OAuth authorization code for access token.
        
        Requirements: 11.2
        """
        cls._validate_https_url(token_url)
        
        data = {
            'grant_type': 'authorization_code',
            'code': code,
            'redirect_uri': redirect_uri,
            'client_id': client_id,
            'client_secret': client_secret
        }
        
        response = await cls._post_with_retry(token_url, data=data)
        
        cls._log_auth_request('oauth_token_exchange', token_url, success=True)
        
        return response
    
    @classmethod
    async def refresh_oauth_token(
        cls,
        token_url: str,
        client_id: str,
        client_secret: str,
        refresh_token: str
    ) -> Dict[str, Any]:
        """
        Refresh OAuth access token.
        
        Requirements: 11.2
        """
        cls._validate_https_url(token_url)
        
        data = {
            'grant_type': 'refresh_token',
            'refresh_token': refresh_token,
            'client_id': client_id,
            'client_secret': client_secret
        }
        
        response = await cls._post_with_retry(token_url, data=data)
        
        cls._log_auth_request('oauth_token_refresh', token_url, success=True)
        
        return response
    
    @classmethod
    async def revoke_oauth_token(
        cls,
        revoke_url: str,
        token: str
    ) -> bool:
        """
        Revoke OAuth token.
        
        Requirements: 11.2
        """
        cls._validate_https_url(revoke_url)
        
        data = {'token': token}
        
        try:
            await cls._post_with_retry(revoke_url, data=data)
            cls._log_auth_request('oauth_token_revoke', revoke_url, success=True)
            return True
        except Exception as e:
            cls._log_auth_request('oauth_token_revoke', revoke_url, success=False)
            logger.error(f"Failed to revoke OAuth token: {e}")
            return False
    
    @classmethod
    async def exchange_meta_code(
        cls,
        app_id: str,
        app_secret: str,
        code: str,
        redirect_uri: str
    ) -> Dict[str, Any]:
        """
        Exchange Meta authorization code for short-lived token.
        
        Requirements: 11.3
        """
        url = f"https://graph.facebook.com/v18.0/oauth/access_token"
        
        params = {
            'client_id': app_id,
            'client_secret': app_secret,
            'code': code,
            'redirect_uri': redirect_uri
        }
        
        response = await cls._get_with_retry(url, params=params)
        
        cls._log_auth_request('meta_code_exchange', url, success=True)
        
        return response
    
    @classmethod
    async def exchange_meta_long_lived_token(
        cls,
        app_id: str,
        app_secret: str,
        short_lived_token: str
    ) -> Dict[str, Any]:
        """
        Exchange Meta short-lived token for long-lived token (60 days).
        
        Requirements: 11.3
        """
        url = f"https://graph.facebook.com/v18.0/oauth/access_token"
        
        params = {
            'grant_type': 'fb_exchange_token',
            'client_id': app_id,
            'client_secret': app_secret,
            'fb_exchange_token': short_lived_token
        }
        
        response = await cls._get_with_retry(url, params=params)
        
        cls._log_auth_request('meta_long_lived_exchange', url, success=True)
        
        return response
    
    @classmethod
    async def get_meta_business_details(
        cls,
        access_token: str
    ) -> Dict[str, Any]:
        """
        Retrieve Meta business account details.
        
        Requirements: 11.3
        """
        url = f"https://graph.facebook.com/v18.0/me"
        
        params = {
            'access_token': access_token,
            'fields': 'id,name,businesses{id,name,whatsapp_business_accounts{id,phone_numbers}}'
        }
        
        response = await cls._get_with_retry(url, params=params)
        
        # Extract business details
        businesses = response.get('businesses', {}).get('data', [])
        if not businesses:
            raise ValidationError("No Meta business account found")
        
        business = businesses[0]
        waba_list = business.get('whatsapp_business_accounts', {}).get('data', [])
        
        result = {
            'business_id': business['id'],
            'business_name': business['name']
        }
        
        if waba_list:
            waba = waba_list[0]
            result['waba_id'] = waba['id']
            
            phone_numbers = waba.get('phone_numbers', {}).get('data', [])
            if phone_numbers:
                result['phone_number_id'] = phone_numbers[0]['id']
        
        cls._log_auth_request('meta_business_details', url, success=True)
        
        return result
    
    @classmethod
    async def revoke_meta_token(
        cls,
        access_token: str
    ) -> bool:
        """
        Revoke Meta access token.
        
        Requirements: 11.3
        """
        url = f"https://graph.facebook.com/v18.0/me/permissions"
        
        params = {'access_token': access_token}
        
        try:
            async with httpx.AsyncClient(timeout=cls.TIMEOUT) as client:
                response = await client.delete(url, params=params)
                response.raise_for_status()
            
            cls._log_auth_request('meta_token_revoke', url, success=True)
            return True
        except Exception as e:
            cls._log_auth_request('meta_token_revoke', url, success=False)
            logger.error(f"Failed to revoke Meta token: {e}")
            return False
    
    @classmethod
    async def validate_api_key(
        cls,
        api_endpoint: str,
        api_key: str,
        header_name: str
    ) -> bool:
        """
        Validate API key by making test request.
        
        Requirements: 11.4
        """
        try:
            headers = {header_name: api_key}
            
            async with httpx.AsyncClient(timeout=cls.TIMEOUT) as client:
                response = await client.get(api_endpoint, headers=headers)
                response.raise_for_status()
            
            cls._log_auth_request('api_key_validation', api_endpoint, success=True)
            return True
        except Exception as e:
            cls._log_auth_request('api_key_validation', api_endpoint, success=False)
            logger.error(f"API key validation failed: {e}")
            return False
    
    @classmethod
    async def _post_with_retry(
        cls,
        url: str,
        data: Dict[str, Any],
        headers: Optional[Dict[str, str]] = None
    ) -> Dict[str, Any]:
        """
        POST request with exponential backoff retry.
        
        Requirements: 11.6
        """
        for attempt in range(cls.MAX_RETRIES):
            try:
                async with httpx.AsyncClient(timeout=cls.TIMEOUT) as client:
                    response = await client.post(url, data=data, headers=headers)
                    response.raise_for_status()
                    return response.json()
            except httpx.HTTPError as e:
                if attempt == cls.MAX_RETRIES - 1:
                    raise
                
                delay = cls.RETRY_DELAY * (2 ** attempt)
                logger.warning(
                    f"Request failed (attempt {attempt + 1}/{cls.MAX_RETRIES}), "
                    f"retrying in {delay}s: {e}"
                )
                await asyncio.sleep(delay)
    
    @classmethod
    async def _get_with_retry(
        cls,
        url: str,
        params: Optional[Dict[str, Any]] = None,
        headers: Optional[Dict[str, str]] = None
    ) -> Dict[str, Any]:
        """
        GET request with exponential backoff retry.
        
        Requirements: 11.6
        """
        for attempt in range(cls.MAX_RETRIES):
            try:
                async with httpx.AsyncClient(timeout=cls.TIMEOUT) as client:
                    response = await client.get(url, params=params, headers=headers)
                    response.raise_for_status()
                    return response.json()
            except httpx.HTTPError as e:
                if attempt == cls.MAX_RETRIES - 1:
                    raise
                
                delay = cls.RETRY_DELAY * (2 ** attempt)
                logger.warning(
                    f"Request failed (attempt {attempt + 1}/{cls.MAX_RETRIES}), "
                    f"retrying in {delay}s: {e}"
                )
                await asyncio.sleep(delay)
    
    @classmethod
    def _validate_https_url(cls, url: str) -> None:
        """
        Validate that URL uses HTTPS.
        
        Requirements: 11.7
        """
        if not url.startswith('https://'):
            raise ValidationError(f"URL must use HTTPS: {url}")
    
    @classmethod
    def _log_auth_request(
        cls,
        request_type: str,
        url: str,
        success: bool
    ) -> None:
        """
        Log authentication request with sanitized parameters.
        
        Requirements: 11.8
        """
        # Sanitize URL (remove query params that might contain secrets)
        sanitized_url = url.split('?')[0]
        
        logger.info(
            f"Auth request: type={request_type}, "
            f"url={sanitized_url}, "
            f"success={success}"
        )
```



#### 8. AuthConfigParser and Serializer

Type-safe parsing and serialization of authentication configurations.

```python
from dataclasses import dataclass
from typing import Dict, Any, List, Optional
import json
from django.core.exceptions import ValidationError


@dataclass
class OAuthConfig:
    """OAuth 2.0 configuration."""
    client_id: str
    client_secret_encrypted: str
    authorization_url: str
    token_url: str
    scopes: List[str]
    revoke_url: Optional[str] = None


@dataclass
class MetaConfig:
    """Meta Business configuration."""
    app_id: str
    app_secret_encrypted: str
    config_id: str
    business_verification_url: str


@dataclass
class APIKeyConfig:
    """API Key configuration."""
    api_endpoint: str
    authentication_header_name: str
    api_key_format_hint: Optional[str] = None


class AuthConfigParser:
    """
    Parser for authentication configuration JSON.
    
    Validates and parses auth_config JSON into typed objects.
    
    Requirements: 21.1-21.8
    """
    
    @staticmethod
    def parse_oauth_config(config: Dict[str, Any]) -> OAuthConfig:
        """
        Parse OAuth configuration.
        
        Requirements: 21.2
        """
        required_fields = [
            'client_id',
            'client_secret_encrypted',
            'authorization_url',
            'token_url',
            'scopes'
        ]
        
        missing = [f for f in required_fields if f not in config]
        if missing:
            raise ValidationError(
                f"Missing required OAuth fields: {', '.join(missing)}"
            )
        
        # Validate URLs
        AuthConfigParser._validate_url(config['authorization_url'], 'authorization_url')
        AuthConfigParser._validate_url(config['token_url'], 'token_url')
        
        if 'revoke_url' in config:
            AuthConfigParser._validate_url(config['revoke_url'], 'revoke_url')
        
        # Parse scopes
        scopes = config['scopes']
        if isinstance(scopes, str):
            scopes = [s.strip() for s in scopes.split(',')]
        
        return OAuthConfig(
            client_id=config['client_id'],
            client_secret_encrypted=config['client_secret_encrypted'],
            authorization_url=config['authorization_url'],
            token_url=config['token_url'],
            scopes=scopes,
            revoke_url=config.get('revoke_url')
        )
    
    @staticmethod
    def parse_meta_config(config: Dict[str, Any]) -> MetaConfig:
        """
        Parse Meta configuration.
        
        Requirements: 21.3
        """
        required_fields = [
            'app_id',
            'app_secret_encrypted',
            'config_id',
            'business_verification_url'
        ]
        
        missing = [f for f in required_fields if f not in config]
        if missing:
            raise ValidationError(
                f"Missing required Meta fields: {', '.join(missing)}"
            )
        
        # Validate URL
        AuthConfigParser._validate_url(
            config['business_verification_url'],
            'business_verification_url'
        )
        
        return MetaConfig(
            app_id=config['app_id'],
            app_secret_encrypted=config['app_secret_encrypted'],
            config_id=config['config_id'],
            business_verification_url=config['business_verification_url']
        )
    
    @staticmethod
    def parse_api_key_config(config: Dict[str, Any]) -> APIKeyConfig:
        """
        Parse API Key configuration.
        
        Requirements: 21.4
        """
        required_fields = [
            'api_endpoint',
            'authentication_header_name'
        ]
        
        missing = [f for f in required_fields if f not in config]
        if missing:
            raise ValidationError(
                f"Missing required API Key fields: {', '.join(missing)}"
            )
        
        # Validate URL
        AuthConfigParser._validate_url(config['api_endpoint'], 'api_endpoint')
        
        return APIKeyConfig(
            api_endpoint=config['api_endpoint'],
            authentication_header_name=config['authentication_header_name'],
            api_key_format_hint=config.get('api_key_format_hint')
        )
    
    @staticmethod
    def _validate_url(url: str, field_name: str) -> None:
        """
        Validate URL format.
        
        Requirements: 21.5
        """
        if not url:
            raise ValidationError(f"{field_name} cannot be empty")
        
        if not url.startswith(('http://', 'https://')):
            raise ValidationError(
                f"{field_name} must be a valid HTTP(S) URL: {url}"
            )


class AuthConfigSerializer:
    """
    Serializer for authentication configuration objects.
    
    Converts typed config objects back to JSON dictionaries.
    
    Requirements: 21.6, 21.7
    """
    
    @staticmethod
    def serialize_oauth_config(config: OAuthConfig) -> Dict[str, Any]:
        """Serialize OAuth configuration to dictionary."""
        result = {
            'client_id': config.client_id,
            'client_secret_encrypted': config.client_secret_encrypted,
            'authorization_url': config.authorization_url,
            'token_url': config.token_url,
            'scopes': config.scopes
        }
        
        if config.revoke_url:
            result['revoke_url'] = config.revoke_url
        
        return result
    
    @staticmethod
    def serialize_meta_config(config: MetaConfig) -> Dict[str, Any]:
        """Serialize Meta configuration to dictionary."""
        return {
            'app_id': config.app_id,
            'app_secret_encrypted': config.app_secret_encrypted,
            'config_id': config.config_id,
            'business_verification_url': config.business_verification_url
        }
    
    @staticmethod
    def serialize_api_key_config(config: APIKeyConfig) -> Dict[str, Any]:
        """Serialize API Key configuration to dictionary."""
        result = {
            'api_endpoint': config.api_endpoint,
            'authentication_header_name': config.authentication_header_name
        }
        
        if config.api_key_format_hint:
            result['api_key_format_hint'] = config.api_key_format_hint
        
        return result
```

## Data Models

### 1. IntegrationTypeModel (Modified)

Extended to support multiple authentication types.

```python
class AuthType(models.TextChoices):
    """Authentication type choices."""
    OAUTH = 'oauth', 'OAuth 2.0'
    META = 'meta', 'Meta Business'
    API_KEY = 'api_key', 'API Key'


class IntegrationTypeModel(models.Model):
    """
    Dynamic integration type model with multi-auth support.
    
    Requirements: 1.1-1.5, 2.1-2.7
    """
    
    id = models.UUIDField(
        primary_key=True,
        default=uuid.uuid4,
        editable=False
    )
    
    # Type identifier (kebab-case, unique)
    type = models.CharField(
        max_length=100,
        unique=True,
        db_index=True,
        help_text='Unique identifier in kebab-case (e.g., "gmail", "whatsapp")'
    )
    
    # Display information
    name = models.CharField(
        max_length=255,
        help_text='Human-readable name (e.g., "Gmail", "WhatsApp")'
    )
    icon = models.FileField(
        upload_to='integration_icons/',
        help_text='SVG or PNG icon (max 500KB)',
        blank=True,
        null=True
    )
    description = models.TextField(
        help_text='Full description of the integration'
    )
    brief_description = models.CharField(
        max_length=200,
        help_text='Short description for card display'
    )
    
    # Categorization
    category = models.CharField(
        max_length=50,
        choices=IntegrationCategory.choices,
        default=IntegrationCategory.OTHER,
        db_index=True,
        help_text='Category for filtering and organization'
    )
    
    # Authentication type (NEW)
    auth_type = models.CharField(
        max_length=20,
        choices=AuthType.choices,
        default=AuthType.OAUTH,
        db_index=True,
        help_text='Authentication method for this integration'
    )
    
    # Authentication configuration (RENAMED from oauth_config)
    auth_config = models.JSONField(
        default=dict,
        help_text='Authentication configuration (structure depends on auth_type)'
    )
    
    # Default permissions
    default_permissions = models.JSONField(
        default=dict,
        help_text='Default permission settings for new installations'
    )
    
    # Status
    is_active = models.BooleanField(
        default=True,
        db_index=True,
        help_text='Whether this integration type is visible in marketplace'
    )
    
    # Metadata
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    created_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='created_integration_types'
    )
    
    class Meta:
        db_table = 'integration_types'
        verbose_name = 'integration type'
        verbose_name_plural = 'integration types'
        ordering = ['name']
        indexes = [
            models.Index(fields=['is_active', 'category']),
            models.Index(fields=['is_active', 'auth_type']),
            models.Index(fields=['auth_type']),
        ]
    
    def __str__(self) -> str:
        return f"{self.name} ({self.type})"
    
    def clean(self):
        """Validate type identifier and auth_config."""
        # Validate kebab-case format
        if not re.match(r'^[a-z0-9]+(-[a-z0-9]+)*$', self.type):
            raise ValidationError(
                'Type must be in kebab-case format (lowercase, hyphens only)'
            )
        
        # Validate auth_config based on auth_type
        if self.auth_type == AuthType.OAUTH:
            AuthConfigParser.parse_oauth_config(self.auth_config)
        elif self.auth_type == AuthType.META:
            AuthConfigParser.parse_meta_config(self.auth_config)
        elif self.auth_type == AuthType.API_KEY:
            AuthConfigParser.parse_api_key_config(self.auth_config)
    
    def get_required_auth_fields(self) -> List[str]:
        """Get required auth_config fields for this auth_type."""
        if self.auth_type == AuthType.OAUTH:
            return ['client_id', 'client_secret_encrypted', 'authorization_url', 'token_url', 'scopes']
        elif self.auth_type == AuthType.META:
            return ['app_id', 'app_secret_encrypted', 'config_id', 'business_verification_url']
        elif self.auth_type == AuthType.API_KEY:
            return ['api_endpoint', 'authentication_header_name']
        return []
```



### 2. Integration Model (Modified)

Extended to support Meta-specific fields.

```python
class Integration(models.Model):
    """
    Integration model for connected applications.
    
    Extended to support Meta-specific fields and multiple auth types.
    
    Requirements: 5.1-5.7, 10.1-10.7
    """
    
    id = models.UUIDField(
        primary_key=True,
        default=uuid.uuid4,
        editable=False
    )
    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name='integrations'
    )
    
    integration_type = models.ForeignKey(
        IntegrationTypeModel,
        on_delete=models.PROTECT,
        related_name='installations',
        db_index=True,
        help_text='The type of integration'
    )
    
    # Encrypted OAuth/API tokens
    oauth_token_encrypted = models.BinaryField(
        null=True,
        blank=True,
        help_text='Encrypted access token (OAuth/Meta) or API key'
    )
    refresh_token_encrypted = models.BinaryField(
        null=True,
        blank=True,
        help_text='Encrypted OAuth refresh token (not used for Meta/API key)'
    )
    
    # OAuth configuration
    scopes = models.JSONField(
        default=list,
        help_text='OAuth scopes granted for this integration'
    )
    
    # Token expiration
    token_expires_at = models.DateTimeField(
        null=True,
        blank=True,
        db_index=True,
        help_text='When the token expires (null for API keys)'
    )
    
    # Meta-specific fields (NEW)
    meta_business_id = models.CharField(
        max_length=255,
        null=True,
        blank=True,
        db_index=True,
        help_text='Meta Business Account ID'
    )
    meta_waba_id = models.CharField(
        max_length=255,
        null=True,
        blank=True,
        db_index=True,
        help_text='WhatsApp Business Account ID'
    )
    meta_phone_number_id = models.CharField(
        max_length=255,
        null=True,
        blank=True,
        help_text='WhatsApp Business Phone Number ID'
    )
    meta_config = models.JSONField(
        default=dict,
        help_text='Additional Meta configuration and metadata'
    )
    
    # Integration configuration
    steering_rules = models.JSONField(
        default=dict,
        help_text='Rules defining allowed actions for this integration'
    )
    permissions = models.JSONField(
        default=dict,
        help_text='Permission settings for this integration'
    )
    
    # Status
    is_active = models.BooleanField(
        default=True,
        help_text='Whether this integration is active'
    )
    
    # Timestamps
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        db_table = 'integrations'
        verbose_name = 'integration'
        verbose_name_plural = 'integrations'
        unique_together = [['user', 'integration_type']]
        indexes = [
            models.Index(fields=['user', 'integration_type']),
            models.Index(fields=['user', 'is_active']),
            models.Index(fields=['integration_type', 'is_active']),
            models.Index(fields=['token_expires_at']),
            models.Index(fields=['meta_business_id']),
            models.Index(fields=['meta_waba_id']),
        ]
    
    def __str__(self) -> str:
        status = 'active' if self.is_active else 'inactive'
        return f"{self.user.email}: {self.integration_type.name} ({status})"
    
    def clean(self):
        """Validate Meta fields for Meta integrations."""
        if self.integration_type.auth_type == 'meta':
            if not self.meta_business_id:
                raise ValidationError(
                    "meta_business_id is required for Meta integrations"
                )
    
    @property
    def oauth_token(self) -> str:
        """Get decrypted access token."""
        if self.oauth_token_encrypted:
            return TokenEncryption.decrypt(bytes(self.oauth_token_encrypted))
        return ''
    
    @oauth_token.setter
    def oauth_token(self, value: str):
        """Set and encrypt access token."""
        if value:
            self.oauth_token_encrypted = TokenEncryption.encrypt(value)
        else:
            self.oauth_token_encrypted = None
    
    @property
    def refresh_token(self) -> str:
        """Get decrypted refresh token."""
        if self.refresh_token_encrypted:
            return TokenEncryption.decrypt(bytes(self.refresh_token_encrypted))
        return ''
    
    @refresh_token.setter
    def refresh_token(self, value: str):
        """Set and encrypt refresh token."""
        if value:
            self.refresh_token_encrypted = TokenEncryption.encrypt(value)
        else:
            self.refresh_token_encrypted = None
    
    def get_meta_phone_numbers(self) -> List[Dict[str, str]]:
        """
        Get list of Meta phone numbers from meta_config.
        
        Requirements: 10.7
        """
        if not self.meta_config:
            return []
        
        return self.meta_config.get('phone_numbers', [])

### 3. InstallationSession Model (Modified)

Extended to track auth_type for proper progress display.

```python
class InstallationSession(models.Model):
    """
    Installation session for tracking progress.
    
    Extended to track auth_type for proper UI display.
    
    Requirements: 4.1-4.11, 11.1-11.7, 12.8
    """
    
    id = models.UUIDField(
        primary_key=True,
        default=uuid.uuid4,
        editable=False
    )
    
    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name='installation_sessions'
    )
    integration_type = models.ForeignKey(
        IntegrationTypeModel,
        on_delete=models.CASCADE,
        related_name='installation_sessions'
    )
    
    # Status tracking
    status = models.CharField(
        max_length=50,
        choices=InstallationStatus.choices,
        default=InstallationStatus.DOWNLOADING,
        db_index=True,
        help_text='Current installation phase'
    )
    progress = models.IntegerField(
        default=0,
        help_text='Progress percentage (0-100)'
    )
    
    # OAuth state for CSRF protection
    oauth_state = models.CharField(
        max_length=255,
        unique=True,
        db_index=True,
        help_text='OAuth state parameter for validation'
    )
    
    # Auth type tracking (NEW)
    auth_type = models.CharField(
        max_length=20,
        default='oauth',
        help_text='Authentication type for this session'
    )
    
    # Error tracking
    error_message = models.TextField(
        blank=True,
        default='',
        help_text='Error message if installation failed'
    )
    retry_count = models.IntegerField(
        default=0,
        help_text='Number of retry attempts'
    )
    
    # Timestamps
    created_at = models.DateTimeField(auto_now_add=True, db_index=True)
    updated_at = models.DateTimeField(auto_now=True)
    completed_at = models.DateTimeField(
        null=True,
        blank=True,
        help_text='When installation completed or failed'
    )
    
    class Meta:
        db_table = 'installation_sessions'
        verbose_name = 'installation session'
        verbose_name_plural = 'installation sessions'
        ordering = ['-created_at']
        indexes = [
            models.Index(fields=['user', 'status']),
            models.Index(fields=['auth_type', 'status']),
            models.Index(fields=['created_at']),
        ]
    
    def save(self, *args, **kwargs):
        """Auto-populate auth_type from integration_type."""
        if not self.auth_type and self.integration_type:
            self.auth_type = self.integration_type.auth_type
        super().save(*args, **kwargs)

## API Endpoints

### Installation Endpoints

```python
# POST /api/v1/integrations/install/
# Start installation for any auth type
{
    "integration_type_id": "uuid"
}

# Response for OAuth/Meta (requires redirect):
{
    "session_id": "uuid",
    "authorization_url": "https://...",
    "requires_redirect": true,
    "requires_api_key": false,
    "auth_type": "oauth"
}

# Response for API Key (no redirect):
{
    "session_id": "uuid",
    "authorization_url": null,
    "requires_redirect": false,
    "requires_api_key": true,
    "auth_type": "api_key"
}
```

```python
# GET /api/v1/integrations/oauth/callback/
# OAuth callback endpoint (existing, works for standard OAuth)
# Query params: code, state, session_id
# Redirects to: /dashboard/apps?status=success or error
```

```python
# GET /api/v1/integrations/meta/callback/
# Meta callback endpoint (NEW)
# Query params: code, state, session_id
# Redirects to: /dashboard/apps?status=success or error
```

```python
# POST /api/v1/integrations/api-key/complete/
# Complete API key installation (NEW)
{
    "session_id": "uuid",
    "api_key": "sk_..."
}

# Response:
{
    "success": true,
    "integration_id": "uuid"
}
```

```python
# GET /api/v1/integrations/install/{session_id}/progress/
# Get installation progress (existing, works for all auth types)
# Response:
{
    "phase": "oauth_setup",
    "progress": 50,
    "message": "Waiting for authorization...",
    "error_message": null,
    "auth_type": "oauth"
}
```

```python
# DELETE /api/v1/integrations/{id}/uninstall/
# Uninstall integration (existing, enhanced to revoke credentials)
# Response:
{
    "success": true,
    "disabled_workflows": 3
}
```

### Webhook Endpoints

```python
# POST /api/v1/webhooks/meta/
# Meta webhook receiver (NEW)
# Verifies signature and routes events
# Headers: X-Hub-Signature-256
# Body: Meta webhook event payload

# Response:
{
    "success": true
}
```

```python
# GET /api/v1/webhooks/meta/
# Meta webhook verification (NEW)
# Query params: hub.mode, hub.verify_token, hub.challenge
# Response: hub.challenge value
```

### Integration Type Endpoints

```python
# GET /api/v1/integrations/types/{id}/
# Get integration type details (enhanced with auth_type)
# Response:
{
    "id": "uuid",
    "type": "whatsapp",
    "name": "WhatsApp",
    "description": "...",
    "category": "communication",
    "auth_type": "meta",
    "required_fields": ["app_id", "app_secret_encrypted", "config_id"],
    "is_installed": false
}
```



## Sequence Diagrams

### OAuth Installation Flow

```
User          Frontend        API              InstallationService    AuthStrategyFactory    OAuthStrategy    Provider
 │                │            │                        │                      │                   │              │
 │  Click Install │            │                        │                      │                   │              │
 │───────────────>│            │                        │                      │                   │              │
 │                │ POST /install                       │                      │                   │              │
 │                │───────────>│                        │                      │                   │              │
 │                │            │ start_installation()   │                      │                   │              │
 │                │            │───────────────────────>│                      │                   │              │
 │                │            │                        │ create_strategy()    │                   │              │
 │                │            │                        │─────────────────────>│                   │              │
 │                │            │                        │                      │ new OAuthStrategy()              │
 │                │            │                        │                      │──────────────────>│              │
 │                │            │                        │ get_authorization_url()                  │              │
 │                │            │                        │─────────────────────────────────────────>│              │
 │                │            │ {session_id, auth_url} │                      │                   │              │
 │                │            │<───────────────────────│                      │                   │              │
 │                │ {session_id, auth_url}              │                      │                   │              │
 │                │<───────────│                        │                      │                   │              │
 │                │            │                        │                      │                   │              │
 │                │ Redirect to auth_url                │                      │                   │              │
 │                │────────────────────────────────────────────────────────────────────────────────────────────>│
 │                │            │                        │                      │                   │              │
 │                │            │                        │                      │                   │  User authorizes
 │                │            │                        │                      │                   │              │
 │                │            │                        │                      │                   │  Callback    │
 │                │<────────────────────────────────────────────────────────────────────────────────────────────│
 │                │            │                        │                      │                   │              │
 │                │ GET /oauth/callback?code=...&state=...                     │                   │              │
 │                │───────────>│                        │                      │                   │              │
 │                │            │ complete_authentication_flow()                │                   │              │
 │                │            │───────────────────────>│                      │                   │              │
 │                │            │                        │ create_strategy()    │                   │              │
 │                │            │                        │─────────────────────>│                   │              │
 │                │            │                        │                      │ new OAuthStrategy()              │
 │                │            │                        │                      │──────────────────>│              │
 │                │            │                        │ complete_authentication()                │              │
 │                │            │                        │─────────────────────────────────────────>│              │
 │                │            │                        │                      │                   │ Token exchange
 │                │            │                        │                      │                   │─────────────>│
 │                │            │                        │                      │                   │ {tokens}     │
 │                │            │                        │                      │                   │<─────────────│
 │                │            │                        │ {encrypted_tokens}   │                   │              │
 │                │            │                        │<─────────────────────────────────────────│              │
 │                │            │                        │ Create Integration   │                   │              │
 │                │            │                        │ record               │                   │              │
 │                │            │ Redirect to dashboard  │                      │                   │              │
 │                │<───────────│                        │                      │                   │              │
 │  Success!      │            │                        │                      │                   │              │
 │<───────────────│            │                        │                      │                   │              │
```

### Meta Installation Flow

```
User          Frontend        API              InstallationService    AuthStrategyFactory    MetaStrategy     Meta API
 │                │            │                        │                      │                   │              │
 │  Click Install │            │                        │                      │                   │              │
 │───────────────>│            │                        │                      │                   │              │
 │                │ POST /install                       │                      │                   │              │
 │                │───────────>│                        │                      │                   │              │
 │                │            │ start_installation()   │                      │                   │              │
 │                │            │───────────────────────>│                      │                   │              │
 │                │            │                        │ create_strategy()    │                   │              │
 │                │            │                        │─────────────────────>│                   │              │
 │                │            │                        │                      │ new MetaStrategy()               │
 │                │            │                        │                      │──────────────────>│              │
 │                │            │                        │ get_authorization_url()                  │              │
 │                │            │                        │─────────────────────────────────────────>│              │
 │                │            │ {session_id, auth_url} │                      │                   │              │
 │                │            │<───────────────────────│                      │                   │              │
 │                │ {session_id, auth_url}              │                      │                   │              │
 │                │<───────────│                        │                      │                   │              │
 │                │            │                        │                      │                   │              │
 │                │ Redirect to Meta Business           │                      │                   │              │
 │                │────────────────────────────────────────────────────────────────────────────────────────────>│
 │                │            │                        │                      │                   │              │
 │                │            │                        │                      │                   │  User verifies
 │                │            │                        │                      │                   │  business    │
 │                │            │                        │                      │                   │              │
 │                │            │                        │                      │                   │  Callback    │
 │                │<────────────────────────────────────────────────────────────────────────────────────────────│
 │                │            │                        │                      │                   │              │
 │                │ GET /meta/callback?code=...&state=...                      │                   │              │
 │                │───────────>│                        │                      │                   │              │
 │                │            │ complete_authentication_flow()                │                   │              │
 │                │            │───────────────────────>│                      │                   │              │
 │                │            │                        │ create_strategy()    │                   │              │
 │                │            │                        │─────────────────────>│                   │              │
 │                │            │                        │                      │ new MetaStrategy()               │
 │                │            │                        │                      │──────────────────>│              │
 │                │            │                        │ complete_authentication()                │              │
 │                │            │                        │─────────────────────────────────────────>│              │
 │                │            │                        │                      │                   │ Exchange code│
 │                │            │                        │                      │                   │─────────────>│
 │                │            │                        │                      │                   │ Short token  │
 │                │            │                        │                      │                   │<─────────────│
 │                │            │                        │                      │                   │ Exchange for │
 │                │            │                        │                      │                   │ long-lived   │
 │                │            │                        │                      │                   │─────────────>│
 │                │            │                        │                      │                   │ Long token   │
 │                │            │                        │                      │                   │<─────────────│
 │                │            │                        │                      │                   │ Get business │
 │                │            │                        │                      │                   │ details      │
 │                │            │                        │                      │                   │─────────────>│
 │                │            │                        │                      │                   │ {business_id,│
 │                │            │                        │                      │                   │  waba_id}    │
 │                │            │                        │                      │                   │<─────────────│
 │                │            │                        │ {encrypted_tokens,   │                   │              │
 │                │            │                        │  meta_business_id}   │                   │              │
 │                │            │                        │<─────────────────────────────────────────│              │
 │                │            │                        │ Create Integration   │                   │              │
 │                │            │                        │ with Meta fields     │                   │              │
 │                │            │ Redirect to dashboard  │                      │                   │              │
 │                │<───────────│                        │                      │                   │              │
 │  Success!      │            │                        │                      │                   │              │
 │<───────────────│            │                        │                      │                   │              │
```

### API Key Installation Flow

```
User          Frontend        API              InstallationService    AuthStrategyFactory    APIKeyStrategy   External API
 │                │            │                        │                      │                   │              │
 │  Click Install │            │                        │                      │                   │              │
 │───────────────>│            │                        │                      │                   │              │
 │                │ POST /install                       │                      │                   │              │
 │                │───────────>│                        │                      │                   │              │
 │                │            │ start_installation()   │                      │                   │              │
 │                │            │───────────────────────>│                      │                   │              │
 │                │            │                        │ create_strategy()    │                   │              │
 │                │            │                        │─────────────────────>│                   │              │
 │                │            │                        │                      │ new APIKeyStrategy()             │
 │                │            │                        │                      │──────────────────>│              │
 │                │            │                        │ get_authorization_url()                  │              │
 │                │            │                        │─────────────────────────────────────────>│              │
 │                │            │                        │ None (no redirect)   │                   │              │
 │                │            │                        │<─────────────────────────────────────────│              │
 │                │            │ {session_id,           │                      │                   │              │
 │                │            │  requires_api_key:true}│                      │                   │              │
 │                │            │<───────────────────────│                      │                   │              │
 │                │ {session_id, requires_api_key}      │                      │                   │              │
 │                │<───────────│                        │                      │                   │              │
 │                │            │                        │                      │                   │              │
 │                │ Show API key input form             │                      │                   │              │
 │                │            │                        │                      │                   │              │
 │  Enter API key │            │                        │                      │                   │              │
 │───────────────>│            │                        │                      │                   │              │
 │                │ POST /api-key/complete              │                      │                   │              │
 │                │───────────>│                        │                      │                   │              │
 │                │            │ complete_authentication_flow()                │                   │              │
 │                │            │───────────────────────>│                      │                   │              │
 │                │            │                        │ create_strategy()    │                   │              │
 │                │            │                        │─────────────────────>│                   │              │
 │                │            │                        │                      │ new APIKeyStrategy()             │
 │                │            │                        │                      │──────────────────>│              │
 │                │            │                        │ complete_authentication(api_key=...)     │              │
 │                │            │                        │─────────────────────────────────────────>│              │
 │                │            │                        │                      │                   │ Validate key │
 │                │            │                        │                      │                   │─────────────>│
 │                │            │                        │                      │                   │ Valid        │
 │                │            │                        │                      │                   │<─────────────│
 │                │            │                        │ {encrypted_api_key}  │                   │              │
 │                │            │                        │<─────────────────────────────────────────│              │
 │                │            │                        │ Create Integration   │                   │              │
 │                │            │ {success: true}        │                      │                   │              │
 │                │<───────────│                        │                      │                   │              │
 │  Success!      │            │                        │                      │                   │              │
 │<───────────────│            │                        │                      │                   │              │
```

## Security Architecture

### Credential Encryption

All sensitive credentials are encrypted using Fernet symmetric encryption before storage:

```python
from cryptography.fernet import Fernet
import base64
import os


class TokenEncryption:
    """
    Token encryption utility using Fernet.
    
    Requirements: 2.7, 16.1-16.3
    """
    
    # Different keys for different credential types
    _OAUTH_KEY = os.getenv('OAUTH_ENCRYPTION_KEY')
    _META_KEY = os.getenv('META_ENCRYPTION_KEY')
    _API_KEY = os.getenv('API_KEY_ENCRYPTION_KEY')
    
    @classmethod
    def encrypt(cls, plaintext: str, credential_type: str = 'oauth') -> bytes:
        """Encrypt plaintext credential."""
        key = cls._get_key(credential_type)
        f = Fernet(key)
        return f.encrypt(plaintext.encode())
    
    @classmethod
    def decrypt(cls, ciphertext: bytes, credential_type: str = 'oauth') -> str:
        """Decrypt encrypted credential."""
        key = cls._get_key(credential_type)
        f = Fernet(key)
        return f.decrypt(ciphertext).decode()
    
    @classmethod
    def _get_key(cls, credential_type: str) -> bytes:
        """Get encryption key for credential type."""
        if credential_type == 'meta':
            return cls._META_KEY.encode()
        elif credential_type == 'api_key':
            return cls._API_KEY.encode()
        else:
            return cls._OAUTH_KEY.encode()
```

### Rate Limiting

Authentication endpoints are rate-limited to prevent abuse:

```python
from django.core.cache import cache
from django.http import HttpResponse


class AuthRateLimitMiddleware:
    """
    Rate limiting for authentication endpoints.
    
    Requirements: 16.5
    """
    
    RATE_LIMIT = 10  # attempts per hour
    WINDOW = 3600  # 1 hour in seconds
    
    def __init__(self, get_response):
        self.get_response = get_response
    
    def __call__(self, request):
        if self._is_auth_endpoint(request.path):
            if not self._check_rate_limit(request.user):
                return HttpResponse(
                    "Rate limit exceeded. Try again later.",
                    status=429
                )
        
        return self.get_response(request)
    
    def _is_auth_endpoint(self, path: str) -> bool:
        """Check if path is an authentication endpoint."""
        auth_paths = [
            '/api/v1/integrations/install/',
            '/api/v1/integrations/oauth/callback/',
            '/api/v1/integrations/meta/callback/',
            '/api/v1/integrations/api-key/complete/'
        ]
        return any(path.startswith(p) for p in auth_paths)
    
    def _check_rate_limit(self, user) -> bool:
        """Check if user is within rate limit."""
        key = f"auth_rate_limit:{user.id}"
        count = cache.get(key, 0)
        
        if count >= self.RATE_LIMIT:
            return False
        
        cache.set(key, count + 1, self.WINDOW)
        return True
```

### Webhook Signature Verification

Meta webhooks are verified using HMAC-SHA256 signatures:

```python
import hmac
import hashlib


class MetaWebhookVerifier:
    """
    Meta webhook signature verification.
    
    Requirements: 14.2, 16.8
    """
    
    @staticmethod
    def verify_signature(
        payload: bytes,
        signature_header: str,
        app_secret: str
    ) -> bool:
        """
        Verify Meta webhook signature.
        
        Args:
            payload: Raw request body
            signature_header: X-Hub-Signature-256 header value
            app_secret: Meta app secret
            
        Returns:
            True if signature is valid
        """
        if not signature_header.startswith('sha256='):
            return False
        
        expected_signature = signature_header[7:]  # Remove 'sha256=' prefix
        
        # Compute HMAC-SHA256
        computed_signature = hmac.new(
            app_secret.encode(),
            payload,
            hashlib.sha256
        ).hexdigest()
        
        # Constant-time comparison
        return hmac.compare_digest(computed_signature, expected_signature)
```



## Database Migration Strategy

### Migration Plan

The migration from `oauth_config` to `auth_config` must be backward compatible:

```python
# Migration: 0001_add_auth_type_and_rename_oauth_config.py

from django.db import migrations, models


class Migration(migrations.Migration):
    
    dependencies = [
        ('automation', '0042_previous_migration'),
    ]
    
    operations = [
        # Step 1: Add auth_type field with default 'oauth'
        migrations.AddField(
            model_name='integrationtypemodel',
            name='auth_type',
            field=models.CharField(
                max_length=20,
                choices=[
                    ('oauth', 'OAuth 2.0'),
                    ('meta', 'Meta Business'),
                    ('api_key', 'API Key'),
                ],
                default='oauth',
                db_index=True,
                help_text='Authentication method for this integration'
            ),
        ),
        
        # Step 2: Rename oauth_config to auth_config
        migrations.RenameField(
            model_name='integrationtypemodel',
            old_name='oauth_config',
            new_name='auth_config',
        ),
        
        # Step 3: Add Meta fields to Integration model
        migrations.AddField(
            model_name='integration',
            name='meta_business_id',
            field=models.CharField(
                max_length=255,
                null=True,
                blank=True,
                db_index=True,
                help_text='Meta Business Account ID'
            ),
        ),
        migrations.AddField(
            model_name='integration',
            name='meta_waba_id',
            field=models.CharField(
                max_length=255,
                null=True,
                blank=True,
                db_index=True,
                help_text='WhatsApp Business Account ID'
            ),
        ),
        migrations.AddField(
            model_name='integration',
            name='meta_phone_number_id',
            field=models.CharField(
                max_length=255,
                null=True,
                blank=True,
                help_text='WhatsApp Business Phone Number ID'
            ),
        ),
        migrations.AddField(
            model_name='integration',
            name='meta_config',
            field=models.JSONField(
                default=dict,
                help_text='Additional Meta configuration and metadata'
            ),
        ),
        
        # Step 4: Add auth_type to InstallationSession
        migrations.AddField(
            model_name='installationsession',
            name='auth_type',
            field=models.CharField(
                max_length=20,
                default='oauth',
                help_text='Authentication type for this session'
            ),
        ),
        
        # Step 5: Add indexes
        migrations.AddIndex(
            model_name='integrationtypemodel',
            index=models.Index(fields=['auth_type'], name='idx_auth_type'),
        ),
        migrations.AddIndex(
            model_name='integrationtypemodel',
            index=models.Index(
                fields=['is_active', 'auth_type'],
                name='idx_active_auth_type'
            ),
        ),
        migrations.AddIndex(
            model_name='integration',
            index=models.Index(
                fields=['meta_business_id'],
                name='idx_meta_business_id'
            ),
        ),
        migrations.AddIndex(
            model_name='integration',
            index=models.Index(
                fields=['meta_waba_id'],
                name='idx_meta_waba_id'
            ),
        ),
        migrations.AddIndex(
            model_name='installationsession',
            index=models.Index(
                fields=['auth_type', 'status'],
                name='idx_auth_type_status'
            ),
        ),
    ]
```

### Backward Compatibility

To maintain backward compatibility during transition, add a property accessor:

```python
class IntegrationTypeModel(models.Model):
    # ... existing fields ...
    
    @property
    def oauth_config(self):
        """Backward compatibility property for oauth_config."""
        return self.auth_config
    
    @oauth_config.setter
    def oauth_config(self, value):
        """Backward compatibility setter for oauth_config."""
        self.auth_config = value
```

## Error Handling

### Error Types and Recovery

```python
class AuthenticationError(Exception):
    """Base exception for authentication errors."""
    pass


class OAuthError(AuthenticationError):
    """OAuth-specific errors."""
    
    def __init__(self, error_code: str, error_description: str):
        self.error_code = error_code
        self.error_description = error_description
        super().__init__(f"{error_code}: {error_description}")


class MetaError(AuthenticationError):
    """Meta-specific errors."""
    
    def __init__(self, error_code: int, error_message: str):
        self.error_code = error_code
        self.error_message = error_message
        super().__init__(f"Meta Error {error_code}: {error_message}")


class APIKeyError(AuthenticationError):
    """API key validation errors."""
    pass


class AuthErrorHandler:
    """
    Centralized error handling for authentication flows.
    
    Requirements: 17.1-17.7
    """
    
    @staticmethod
    def handle_oauth_error(error: OAuthError, session: InstallationSession) -> Dict[str, Any]:
        """Handle OAuth errors with user-friendly messages."""
        error_messages = {
            'access_denied': 'You denied access to the application. Please try again and grant the required permissions.',
            'invalid_grant': 'The authorization code is invalid or expired. Please try again.',
            'invalid_client': 'Invalid client credentials. Please contact support.',
            'unauthorized_client': 'This application is not authorized. Please contact support.',
        }
        
        user_message = error_messages.get(
            error.error_code,
            f'Authentication failed: {error.error_description}'
        )
        
        session.status = InstallationStatus.FAILED
        session.error_message = user_message
        session.save()
        
        return {
            'error': error.error_code,
            'message': user_message,
            'can_retry': error.error_code in ['access_denied', 'invalid_grant'],
            'session_id': str(session.id)
        }
    
    @staticmethod
    def handle_meta_error(error: MetaError, session: InstallationSession) -> Dict[str, Any]:
        """Handle Meta errors with troubleshooting steps."""
        error_messages = {
            190: 'Access token is invalid or expired. Please try again.',
            200: 'Permission denied. Please ensure you have admin access to the Meta Business account.',
            368: 'The user is temporarily blocked. Please try again later.',
        }
        
        user_message = error_messages.get(
            error.error_code,
            f'Meta authentication failed: {error.error_message}'
        )
        
        troubleshooting = {
            190: 'Try logging out of Facebook and logging back in.',
            200: 'Verify you are an admin of the Meta Business account.',
            368: 'Wait a few minutes and try again.',
        }
        
        session.status = InstallationStatus.FAILED
        session.error_message = user_message
        session.save()
        
        return {
            'error': f'meta_{error.error_code}',
            'message': user_message,
            'troubleshooting': troubleshooting.get(error.error_code, 'Contact support if the issue persists.'),
            'can_retry': True,
            'session_id': str(session.id)
        }
    
    @staticmethod
    def handle_api_key_error(error: APIKeyError, session: InstallationSession) -> Dict[str, Any]:
        """Handle API key validation errors."""
        user_message = 'Invalid API key. Please verify the key and try again.'
        
        session.status = InstallationStatus.FAILED
        session.error_message = user_message
        session.save()
        
        return {
            'error': 'invalid_api_key',
            'message': user_message,
            'instructions': 'Double-check that you copied the entire API key correctly.',
            'can_retry': True,
            'session_id': str(session.id)
        }
```

## Monitoring and Logging

### Authentication Audit Log

```python
class AuthenticationAuditLog(models.Model):
    """
    Audit log for all authentication attempts.
    
    Requirements: 16.6, 23.1-23.7
    """
    
    id = models.UUIDField(
        primary_key=True,
        default=uuid.uuid4,
        editable=False
    )
    
    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name='auth_audit_logs'
    )
    integration_type = models.ForeignKey(
        IntegrationTypeModel,
        on_delete=models.CASCADE,
        related_name='auth_audit_logs'
    )
    
    # Authentication details
    auth_type = models.CharField(
        max_length=20,
        help_text='Authentication type used'
    )
    action = models.CharField(
        max_length=50,
        choices=[
            ('install_start', 'Installation Started'),
            ('install_complete', 'Installation Completed'),
            ('install_failed', 'Installation Failed'),
            ('token_refresh', 'Token Refreshed'),
            ('token_revoke', 'Token Revoked'),
            ('uninstall', 'Uninstalled'),
        ],
        help_text='Authentication action performed'
    )
    
    # Result
    success = models.BooleanField(
        help_text='Whether the action succeeded'
    )
    error_code = models.CharField(
        max_length=100,
        blank=True,
        default='',
        help_text='Error code if failed'
    )
    error_message = models.TextField(
        blank=True,
        default='',
        help_text='Error message if failed'
    )
    
    # Performance
    duration_ms = models.IntegerField(
        null=True,
        blank=True,
        help_text='Duration in milliseconds'
    )
    
    # Context
    ip_address = models.GenericIPAddressField(
        null=True,
        blank=True,
        help_text='User IP address'
    )
    user_agent = models.TextField(
        blank=True,
        default='',
        help_text='User agent string'
    )
    
    # Timestamp
    created_at = models.DateTimeField(auto_now_add=True, db_index=True)
    
    class Meta:
        db_table = 'authentication_audit_logs'
        verbose_name = 'authentication audit log'
        verbose_name_plural = 'authentication audit logs'
        ordering = ['-created_at']
        indexes = [
            models.Index(fields=['user', 'created_at']),
            models.Index(fields=['auth_type', 'action', 'success']),
            models.Index(fields=['created_at']),
        ]


class AuthenticationMetrics:
    """
    Service for tracking authentication metrics.
    
    Requirements: 23.2-23.6
    """
    
    @staticmethod
    def log_authentication_attempt(
        user,
        integration_type: IntegrationTypeModel,
        action: str,
        success: bool,
        duration_ms: Optional[int] = None,
        error_code: str = '',
        error_message: str = '',
        request=None
    ):
        """Log authentication attempt to audit log."""
        ip_address = None
        user_agent = ''
        
        if request:
            ip_address = request.META.get('REMOTE_ADDR')
            user_agent = request.META.get('HTTP_USER_AGENT', '')
        
        AuthenticationAuditLog.objects.create(
            user=user,
            integration_type=integration_type,
            auth_type=integration_type.auth_type,
            action=action,
            success=success,
            error_code=error_code,
            error_message=error_message,
            duration_ms=duration_ms,
            ip_address=ip_address,
            user_agent=user_agent
        )
        
        logger.info(
            f"Auth attempt: user={user.id}, "
            f"type={integration_type.type}, "
            f"auth_type={integration_type.auth_type}, "
            f"action={action}, "
            f"success={success}, "
            f"duration={duration_ms}ms"
        )
    
    @staticmethod
    def get_success_rate_by_auth_type() -> Dict[str, float]:
        """Calculate authentication success rate by auth type."""
        from django.db.models import Count, Q
        
        results = AuthenticationAuditLog.objects.values('auth_type').annotate(
            total=Count('id'),
            successful=Count('id', filter=Q(success=True))
        )
        
        return {
            r['auth_type']: (r['successful'] / r['total'] * 100) if r['total'] > 0 else 0
            for r in results
        }
    
    @staticmethod
    def get_average_duration_by_auth_type() -> Dict[str, float]:
        """Calculate average authentication duration by auth type."""
        from django.db.models import Avg
        
        results = AuthenticationAuditLog.objects.filter(
            success=True,
            duration_ms__isnull=False
        ).values('auth_type').annotate(
            avg_duration=Avg('duration_ms')
        )
        
        return {
            r['auth_type']: r['avg_duration']
            for r in results
        }
    
    @staticmethod
    def check_failure_rate_alert() -> Optional[str]:
        """Check if failure rate exceeds threshold."""
        from datetime import timedelta
        from django.utils import timezone
        
        # Check last hour
        since = timezone.now() - timedelta(hours=1)
        
        for auth_type in ['oauth', 'meta', 'api_key']:
            logs = AuthenticationAuditLog.objects.filter(
                auth_type=auth_type,
                created_at__gte=since
            )
            
            total = logs.count()
            if total < 10:  # Need minimum sample size
                continue
            
            failed = logs.filter(success=False).count()
            failure_rate = (failed / total) * 100
            
            if failure_rate > 10:  # Alert threshold
                return (
                    f"ALERT: {auth_type} authentication failure rate is {failure_rate:.1f}% "
                    f"({failed}/{total} attempts failed in last hour)"
                )
        
        return None
```



## Testing Strategy

### Dual Testing Approach

The testing strategy combines unit tests for specific scenarios with property-based tests for comprehensive coverage:

**Unit Tests**: Focus on specific examples, edge cases, and integration points
- OAuth callback with specific error codes
- Meta webhook signature verification with known payloads
- API key validation with mock endpoints
- Database constraint violations
- Edge cases like expired sessions, missing fields

**Property-Based Tests**: Verify universal properties across all inputs
- Use Hypothesis library for Python property-based testing
- Minimum 100 iterations per property test
- Generate random configurations, tokens, and payloads
- Each property test references its design document property

### Property-Based Testing Configuration

```python
# tests/test_auth_strategies_properties.py

from hypothesis import given, strategies as st, settings
import pytest


# Property 1: Invalid auth_type rejection
@given(auth_type=st.text().filter(lambda x: x not in ['oauth', 'meta', 'api_key']))
@settings(max_examples=100)
def test_invalid_auth_type_rejected(auth_type):
    """
    Feature: multi-auth-integration-system, Property 1:
    For any auth_type not in allowed values, validation should reject it.
    """
    integration_type = IntegrationTypeModel(
        type='test-integration',
        name='Test',
        auth_type=auth_type,
        auth_config={}
    )
    
    with pytest.raises(ValidationError):
        integration_type.full_clean()


# Property 5: Credential encryption
@given(plaintext=st.text(min_size=1, max_size=1000))
@settings(max_examples=100)
def test_credential_encryption_round_trip(plaintext):
    """
    Feature: multi-auth-integration-system, Property 5:
    For any credential, encryption then decryption should return original.
    """
    encrypted = TokenEncryption.encrypt(plaintext)
    
    # Encrypted should differ from plaintext
    assert encrypted != plaintext.encode()
    
    # Decryption should return original
    decrypted = TokenEncryption.decrypt(encrypted)
    assert decrypted == plaintext


# Property 32: Configuration serialization round-trip
@given(
    client_id=st.text(min_size=1),
    scopes=st.lists(st.text(min_size=1), min_size=1)
)
@settings(max_examples=100)
def test_oauth_config_round_trip(client_id, scopes):
    """
    Feature: multi-auth-integration-system, Property 32:
    For any valid config, parse -> serialize -> parse should be equivalent.
    """
    config_dict = {
        'client_id': client_id,
        'client_secret_encrypted': 'encrypted_secret',
        'authorization_url': 'https://example.com/auth',
        'token_url': 'https://example.com/token',
        'scopes': scopes
    }
    
    # Parse
    config_obj = AuthConfigParser.parse_oauth_config(config_dict)
    
    # Serialize
    serialized = AuthConfigSerializer.serialize_oauth_config(config_obj)
    
    # Parse again
    config_obj2 = AuthConfigParser.parse_oauth_config(serialized)
    
    # Should be equivalent
    assert config_obj == config_obj2
```

### Test Coverage Requirements

- Minimum 90% code coverage for authentication-related code
- All 33 correctness properties must have property-based tests
- Integration tests for complete flows (OAuth, Meta, API key)
- Mock external API calls (OAuth providers, Meta API)
- Test backward compatibility with existing OAuth integrations

### Testing Tools

- **pytest**: Test framework
- **Hypothesis**: Property-based testing library
- **pytest-django**: Django integration for pytest
- **pytest-asyncio**: Async test support
- **responses**: HTTP request mocking
- **factory_boy**: Test data generation

## Performance Optimizations

### Caching Strategy

```python
from django.core.cache import cache
from django.conf import settings


class AuthConfigCache:
    """
    Cache for integration type auth configurations.
    
    Requirements: 22.5
    """
    
    CACHE_TTL = 300  # 5 minutes
    
    @classmethod
    def get_auth_config(cls, integration_type_id: str) -> Optional[Dict[str, Any]]:
        """Get cached auth_config for integration type."""
        cache_key = f"auth_config:{integration_type_id}"
        return cache.get(cache_key)
    
    @classmethod
    def set_auth_config(cls, integration_type_id: str, auth_config: Dict[str, Any]):
        """Cache auth_config for integration type."""
        cache_key = f"auth_config:{integration_type_id}"
        cache.set(cache_key, auth_config, cls.CACHE_TTL)
    
    @classmethod
    def invalidate(cls, integration_type_id: str):
        """Invalidate cached auth_config."""
        cache_key = f"auth_config:{integration_type_id}"
        cache.delete(cache_key)
```

### Database Query Optimization

- Use `select_related('integration_type')` when querying Integration model
- Index on `auth_type` field for filtering by authentication method
- Composite index on `(is_active, auth_type)` for marketplace queries
- Index on `meta_business_id` and `meta_waba_id` for Meta lookups

### Async Operations

All external API calls are async to avoid blocking:

```python
# All AuthClient methods are async
await AuthClient.exchange_oauth_code(...)
await AuthClient.exchange_meta_code(...)
await AuthClient.validate_api_key(...)

# InstallationService methods are async
await InstallationService.complete_authentication_flow(...)
await InstallationService.uninstall_integration(...)
```

## Frontend Integration

### Installation Flow UI

The frontend must handle three different installation flows:

**OAuth/Meta Flow (Redirect Required)**:
1. User clicks "Install" button
2. POST to `/api/v1/integrations/install/`
3. Receive `{authorization_url, session_id, requires_redirect: true}`
4. Redirect user to `authorization_url`
5. User authorizes on provider site
6. Provider redirects to callback URL
7. Backend completes installation
8. User redirected to dashboard with success message

**API Key Flow (No Redirect)**:
1. User clicks "Install" button
2. POST to `/api/v1/integrations/install/`
3. Receive `{session_id, requires_redirect: false, requires_api_key: true}`
4. Show API key input form
5. User enters API key
6. POST to `/api/v1/integrations/api-key/complete/` with `{session_id, api_key}`
7. Show success message

### UI Components

```typescript
// Frontend component structure

interface InstallationFlowProps {
  integrationType: IntegrationType;
  onComplete: () => void;
}

function InstallationFlow({ integrationType, onComplete }: InstallationFlowProps) {
  const [session, setSession] = useState<InstallationSession | null>(null);
  
  const startInstallation = async () => {
    const response = await api.post('/integrations/install/', {
      integration_type_id: integrationType.id
    });
    
    setSession(response.data);
    
    if (response.data.requires_redirect) {
      // OAuth/Meta flow - redirect to authorization URL
      window.location.href = response.data.authorization_url;
    } else if (response.data.requires_api_key) {
      // API key flow - show input form
      // (handled by component state)
    }
  };
  
  const completeApiKeyInstallation = async (apiKey: string) => {
    await api.post('/integrations/api-key/complete/', {
      session_id: session.session_id,
      api_key: apiKey
    });
    
    onComplete();
  };
  
  // Render appropriate UI based on auth_type
  if (!session) {
    return <button onClick={startInstallation}>Install</button>;
  }
  
  if (session.requires_api_key) {
    return <ApiKeyInput onSubmit={completeApiKeyInstallation} />;
  }
  
  return <LoadingSpinner message="Redirecting to authorization..." />;
}
```

## Extensibility for Future Auth Types

The system is designed to support future authentication methods with minimal changes:

### Adding a New Auth Type

1. **Define auth type constant**:
```python
class AuthType(models.TextChoices):
    OAUTH = 'oauth', 'OAuth 2.0'
    META = 'meta', 'Meta Business'
    API_KEY = 'api_key', 'API Key'
    SAML = 'saml', 'SAML 2.0'  # NEW
```

2. **Create strategy class**:
```python
class SAMLStrategy(AuthStrategy):
    def get_required_fields(self) -> List[str]:
        return ['entity_id', 'sso_url', 'certificate']
    
    def get_authorization_url(self, state: str, redirect_uri: str) -> Optional[str]:
        # Build SAML request
        pass
    
    async def complete_authentication(self, **kwargs) -> Dict[str, Any]:
        # Validate SAML response
        pass
    
    # ... implement other methods
```

3. **Register strategy**:
```python
AuthStrategyFactory.register_strategy('saml', SAMLStrategy)
```

4. **Add admin configuration fields**:
```python
# In admin.py
if obj.auth_type == 'saml':
    return ['entity_id', 'sso_url', 'certificate']
```

5. **Update parser** (if needed):
```python
@dataclass
class SAMLConfig:
    entity_id: str
    sso_url: str
    certificate: str

class AuthConfigParser:
    @staticmethod
    def parse_saml_config(config: Dict[str, Any]) -> SAMLConfig:
        # Validation logic
        pass
```

No changes needed to:
- InstallationService (uses factory pattern)
- API endpoints (generic for all auth types)
- Database schema (JSON auth_config is flexible)
- Frontend (handles requires_redirect flag)

## Summary

This design refactors the NeuroTwin integration authentication system to support multiple authentication strategies through a flexible, extensible architecture. Key achievements:

1. **Strategy Pattern**: Clean separation of authentication methods with pluggable strategies
2. **Backward Compatibility**: Seamless migration from oauth_config to auth_config
3. **Type Safety**: Strongly-typed configuration parsing and validation
4. **Security**: Encryption for all credentials, rate limiting, audit logging
5. **Extensibility**: Easy addition of future authentication methods
6. **Comprehensive Testing**: Property-based tests ensure correctness across all inputs

The system supports OAuth 2.0, Meta Business, and API key authentication today, with a clear path to add SAML, JWT, custom auth, and other methods in the future without refactoring core components.
