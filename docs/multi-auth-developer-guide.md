# Multi-Auth Integration System: Developer Guide

## Overview

This guide shows you how to add new authentication types to the Multi-Auth Integration System. The system is designed for extensibility using the Strategy pattern, making it straightforward to add support for new authentication methods like SAML, JWT, custom OAuth variants, or proprietary authentication schemes.

## Architecture Overview

The Multi-Auth system uses three key patterns:

1. **Strategy Pattern**: Each authentication type is a concrete strategy implementing `AuthStrategy`
2. **Factory Pattern**: `AuthStrategyFactory` creates the appropriate strategy instance
3. **Configuration Pattern**: Flexible JSON storage for auth-type-specific configuration

```
┌─────────────────────────────────────────────────────────────┐
│                    AuthStrategyFactory                      │
│  - create_strategy(integration_type) → AuthStrategy        │
│  - register_strategy(auth_type, strategy_class)            │
└────────────────────┬────────────────────────────────────────┘
                     │
         ┌───────────┼───────────┬───────────────┐
         │           │           │               │
    ┌────▼────┐ ┌───▼────┐ ┌───▼────┐     ┌────▼────┐
    │OAuth    │ │Meta    │ │APIKey  │     │Your New │
    │Strategy │ │Strategy│ │Strategy│     │Strategy │
    └─────────┘ └────────┘ └────────┘     └─────────┘
```

## Step-by-Step Guide

### Step 1: Define Your Authentication Strategy

Create a new strategy class that extends `AuthStrategy` base class.

**File:** `apps/automation/services/auth_strategies/saml_strategy.py`

```python
from typing import Optional, Dict, Any, List
from django.core.exceptions import ValidationError
from apps.automation.services.auth_strategy import AuthStrategy
from apps.automation.models import Integration


class SAMLStrategy(AuthStrategy):
    """
    SAML 2.0 authentication strategy.
    
    Implements SAML-based single sign-on for enterprise integrations.
    """
    
    def get_required_fields(self) -> List[str]:
        """
        Define required configuration fields for SAML.
        
        Returns:
            List of required field names in auth_config
        """
        return [
            'idp_entity_id',
            'idp_sso_url',
            'idp_x509_cert',
            'sp_entity_id',
            'sp_acs_url'
        ]
    
    def validate_config(self) -> None:
        """
        Validate SAML-specific configuration.
        
        Raises:
            ValidationError: If configuration is invalid
        """
        super().validate_config()
        
        # Validate HTTPS URLs
        for url_field in ['idp_sso_url', 'sp_acs_url']:
            url = self.auth_config.get(url_field, '')
            if not url.startswith('https://'):
                raise ValidationError(
                    f"{url_field} must use HTTPS protocol"
                )
        
        # Validate certificate format
        cert = self.auth_config.get('idp_x509_cert', '')
        if not cert.startswith('-----BEGIN CERTIFICATE-----'):
            raise ValidationError(
                "idp_x509_cert must be a valid X.509 certificate"
            )
```

    def get_authorization_url(self, state: str, redirect_uri: str) -> Optional[str]:
        """
        Build SAML authentication request URL.
        
        Args:
            state: CSRF protection state parameter
            redirect_uri: Callback URL after authentication
            
        Returns:
            SAML SSO URL with encoded authentication request
        """
        from onelogin.saml2.auth import OneLogin_Saml2_Auth
        
        # Build SAML authentication request
        saml_settings = self._build_saml_settings(redirect_uri)
        auth = OneLogin_Saml2_Auth(saml_settings)
        
        # Generate SAML request and return SSO URL
        return auth.login(return_to=state)
    
    async def complete_authentication(
        self,
        authorization_code: str,
        state: str,
        redirect_uri: str,
        **kwargs
    ) -> Dict[str, Any]:
        """
        Process SAML response and extract user attributes.
        
        Args:
            authorization_code: SAML response (base64 encoded)
            state: CSRF protection state parameter
            redirect_uri: Callback URL used in authentication
            **kwargs: Additional parameters (saml_response)
            
        Returns:
            Dictionary with authentication data
        """
        from onelogin.saml2.auth import OneLogin_Saml2_Auth
        
        saml_response = kwargs.get('saml_response')
        if not saml_response:
            raise ValidationError("SAML response is required")
        
        # Process SAML response
        saml_settings = self._build_saml_settings(redirect_uri)
        auth = OneLogin_Saml2_Auth(saml_settings)
        auth.process_response()
        
        if not auth.is_authenticated():
            raise ValidationError(f"SAML authentication failed: {auth.get_errors()}")
        
        # Extract user attributes
        attributes = auth.get_attributes()
        name_id = auth.get_nameid()
        
        # Store SAML session data (encrypted)
        from apps.automation.utils.encryption import TokenEncryption
        session_data = {
            'name_id': name_id,
            'attributes': attributes,
            'session_index': auth.get_session_index()
        }
        
        session_encrypted = TokenEncryption.encrypt(str(session_data))
        
        return {
            'access_token_encrypted': session_encrypted,
            'refresh_token_encrypted': None,
            'expires_at': None,  # SAML sessions managed by IdP
            'saml_name_id': name_id,
            'saml_attributes': attributes
        }
    
    async def refresh_credentials(self, integration: Integration) -> Dict[str, Any]:
        """
        SAML sessions are managed by IdP (no-op).
        
        Args:
            integration: Integration instance
            
        Returns:
            Empty dictionary (no refresh needed)
        """
        return {}
    
    async def revoke_credentials(self, integration: Integration) -> bool:
        """
        Initiate SAML Single Logout (SLO).
        
        Args:
            integration: Integration instance to revoke
            
        Returns:
            True if logout initiated successfully
        """
        from onelogin.saml2.auth import OneLogin_Saml2_Auth
        
        try:
            saml_settings = self._build_saml_settings()
            auth = OneLogin_Saml2_Auth(saml_settings)
            
            # Initiate Single Logout
            auth.logout()
            return True
        except Exception as e:
            logger.error(f"Failed to initiate SAML logout: {e}")
            return False
    
    def _build_saml_settings(self, redirect_uri: str = None) -> Dict[str, Any]:
        """Build SAML settings from auth_config."""
        return {
            'sp': {
                'entityId': self.auth_config['sp_entity_id'],
                'assertionConsumerService': {
                    'url': redirect_uri or self.auth_config['sp_acs_url'],
                    'binding': 'urn:oasis:names:tc:SAML:2.0:bindings:HTTP-POST'
                }
            },
            'idp': {
                'entityId': self.auth_config['idp_entity_id'],
                'singleSignOnService': {
                    'url': self.auth_config['idp_sso_url'],
                    'binding': 'urn:oasis:names:tc:SAML:2.0:bindings:HTTP-Redirect'
                },
                'x509cert': self.auth_config['idp_x509_cert']
            }
        }
```

### Step 2: Register Your Strategy with the Factory

Add your strategy to the factory's registry.

**File:** `apps/automation/services/auth_strategy_factory.py`

```python
from apps.automation.services.auth_strategies.saml_strategy import SAMLStrategy

class AuthStrategyFactory:
    """Factory for creating authentication strategy instances."""
    
    _strategy_registry = {
        'oauth': OAuthStrategy,
        'meta': MetaStrategy,
        'api_key': APIKeyStrategy,
        'saml': SAMLStrategy,  # Add your new strategy
    }
    
    @classmethod
    def create_strategy(cls, integration_type: IntegrationTypeModel) -> AuthStrategy:
        """Create appropriate authentication strategy."""
        auth_type = integration_type.auth_type
        
        strategy_class = cls._strategy_registry.get(auth_type)
        if not strategy_class:
            raise ValidationError(
                f"Unrecognized auth_type: {auth_type}. "
                f"Supported types: {', '.join(cls._strategy_registry.keys())}"
            )
        
        return strategy_class(integration_type)
```

**Alternative: Dynamic Registration**

For plugins or external modules, use dynamic registration:

```python
# In your plugin initialization
from apps.automation.services.auth_strategy_factory import AuthStrategyFactory
from my_plugin.saml_strategy import SAMLStrategy

# Register your strategy
AuthStrategyFactory.register_strategy('saml', SAMLStrategy)
```

### Step 3: Update Database Schema

Add your new auth_type to the model choices.

**File:** `apps/automation/models.py`

```python
class IntegrationTypeModel(models.Model):
    """Model representing an integration type."""
    
    class AuthType(models.TextChoices):
        OAUTH = 'oauth', 'OAuth 2.0'
        META = 'meta', 'Meta Business'
        API_KEY = 'api_key', 'API Key'
        SAML = 'saml', 'SAML 2.0'  # Add your new type
    
    auth_type = models.CharField(
        max_length=20,
        choices=AuthType.choices,
        default=AuthType.OAUTH
    )
```

**Create a migration:**

```bash
uv run python manage.py makemigrations automation
uv run python manage.py migrate automation
```

### Step 4: Configure Admin Interface

Add admin configuration for your new auth type.

**File:** `apps/automation/admin.py`

```python
from django.contrib import admin
from apps.automation.models import IntegrationTypeModel

@admin.register(IntegrationTypeModel)
class IntegrationTypeAdmin(admin.ModelAdmin):
    """Admin interface for integration types."""
    
    fieldsets = [
        ('Basic Information', {
            'fields': ['name', 'description', 'icon_url', 'category', 'is_active']
        }),
        ('Authentication', {
            'fields': ['auth_type', 'auth_config']
        })
    ]
    
    def get_form(self, request, obj=None, **kwargs):
        """Customize form based on auth_type."""
        form = super().get_form(request, obj, **kwargs)
        
        # Add help text based on auth_type
        if obj and obj.auth_type == 'saml':
            form.base_fields['auth_config'].help_text = (
                'Required fields: idp_entity_id, idp_sso_url, idp_x509_cert, '
                'sp_entity_id, sp_acs_url'
            )
        
        return form
```

### Step 5: Add Callback Endpoint (if needed)

If your auth type requires a callback endpoint, add it to the API.

**File:** `apps/automation/views.py`

```python
from django.http import HttpResponse
from django.shortcuts import redirect
from rest_framework.decorators import api_view
from apps.automation.services.installation_service import InstallationService

@api_view(['POST'])
def saml_callback(request):
    """
    Handle SAML assertion consumer service (ACS) callback.
    
    POST /api/v1/integrations/saml/callback/
    """
    saml_response = request.POST.get('SAMLResponse')
    relay_state = request.POST.get('RelayState')  # Contains session_id
    
    try:
        # Extract session_id from relay_state
        session_id = relay_state
        
        # Complete authentication
        integration = await InstallationService.complete_authentication_flow(
            session_id=session_id,
            authorization_code=saml_response,
            state=relay_state,
            saml_response=saml_response
        )
        
        # Redirect to dashboard
        return redirect(
            f'/dashboard/apps?installation=success&integration_id={integration.id}'
        )
    
    except Exception as e:
        logger.error(f"SAML callback failed: {e}")
        return redirect(
            f'/dashboard/apps?installation=error&message={str(e)}'
        )
```

**Add URL route:**

**File:** `apps/automation/urls.py`

```python
from django.urls import path
from apps.automation import views

urlpatterns = [
    # Existing routes
    path('integrations/install/', views.start_installation),
    path('integrations/oauth/callback/', views.oauth_callback),
    path('integrations/meta/callback/', views.meta_callback),
    
    # Add your new callback route
    path('integrations/saml/callback/', views.saml_callback),
]
```

### Step 6: Create Configuration Parser (Optional)

For type-safe configuration handling, create a parser.

**File:** `apps/automation/services/auth_config_parser.py`

```python
from dataclasses import dataclass
from typing import Dict, Any

@dataclass
class SAMLConfig:
    """Type-safe SAML configuration."""
    idp_entity_id: str
    idp_sso_url: str
    idp_x509_cert: str
    sp_entity_id: str
    sp_acs_url: str
    
    @classmethod
    def from_dict(cls, config: Dict[str, Any]) -> 'SAMLConfig':
        """Parse SAML config from dictionary."""
        return cls(
            idp_entity_id=config['idp_entity_id'],
            idp_sso_url=config['idp_sso_url'],
            idp_x509_cert=config['idp_x509_cert'],
            sp_entity_id=config['sp_entity_id'],
            sp_acs_url=config['sp_acs_url']
        )
    
    def to_dict(self) -> Dict[str, Any]:
        """Serialize SAML config to dictionary."""
        return {
            'idp_entity_id': self.idp_entity_id,
            'idp_sso_url': self.idp_sso_url,
            'idp_x509_cert': self.idp_x509_cert,
            'sp_entity_id': self.sp_entity_id,
            'sp_acs_url': self.sp_acs_url
        }

class AuthConfigParser:
    """Parser for authentication configurations."""
    
    @staticmethod
    def parse_saml_config(config: Dict[str, Any]) -> SAMLConfig:
        """Parse and validate SAML configuration."""
        try:
            return SAMLConfig.from_dict(config)
        except KeyError as e:
            raise ValidationError(f"Missing required SAML field: {e}")
```

### Step 7: Write Tests

Create comprehensive tests for your new strategy.

**File:** `apps/automation/tests/test_saml_strategy.py`

```python
import pytest
from django.core.exceptions import ValidationError
from apps.automation.models import IntegrationTypeModel
from apps.automation.services.auth_strategies.saml_strategy import SAMLStrategy

@pytest.fixture
def saml_integration_type():
    """Create SAML integration type for testing."""
    return IntegrationTypeModel.objects.create(
        name='Enterprise SSO',
        auth_type='saml',
        auth_config={
            'idp_entity_id': 'https://idp.example.com',
            'idp_sso_url': 'https://idp.example.com/sso',
            'idp_x509_cert': '-----BEGIN CERTIFICATE-----\nMIIC...\n-----END CERTIFICATE-----',
            'sp_entity_id': 'https://neurotwin.com',
            'sp_acs_url': 'https://neurotwin.com/api/v1/integrations/saml/callback/'
        }
    )

def test_saml_strategy_initialization(saml_integration_type):
    """Test SAML strategy initializes correctly."""
    strategy = SAMLStrategy(saml_integration_type)
    assert strategy.integration_type == saml_integration_type
    assert strategy.auth_config == saml_integration_type.auth_config

def test_saml_strategy_required_fields():
    """Test SAML strategy validates required fields."""
    strategy = SAMLStrategy.__new__(SAMLStrategy)
    required = strategy.get_required_fields()
    
    assert 'idp_entity_id' in required
    assert 'idp_sso_url' in required
    assert 'idp_x509_cert' in required
    assert 'sp_entity_id' in required
    assert 'sp_acs_url' in required

def test_saml_strategy_missing_fields():
    """Test SAML strategy rejects missing fields."""
    integration_type = IntegrationTypeModel(
        name='Invalid SAML',
        auth_type='saml',
        auth_config={'idp_entity_id': 'https://idp.example.com'}
    )
    
    with pytest.raises(ValidationError) as exc:
        SAMLStrategy(integration_type)
    
    assert 'Missing required fields' in str(exc.value)

def test_saml_strategy_https_validation():
    """Test SAML strategy requires HTTPS URLs."""
    integration_type = IntegrationTypeModel(
        name='Invalid SAML',
        auth_type='saml',
        auth_config={
            'idp_entity_id': 'https://idp.example.com',
            'idp_sso_url': 'http://idp.example.com/sso',  # HTTP not allowed
            'idp_x509_cert': '-----BEGIN CERTIFICATE-----\nMIIC...\n-----END CERTIFICATE-----',
            'sp_entity_id': 'https://neurotwin.com',
            'sp_acs_url': 'https://neurotwin.com/callback/'
        }
    )
    
    with pytest.raises(ValidationError) as exc:
        SAMLStrategy(integration_type)
    
    assert 'must use HTTPS' in str(exc.value)

@pytest.mark.asyncio
async def test_saml_complete_authentication(saml_integration_type, mocker):
    """Test SAML authentication completion."""
    strategy = SAMLStrategy(saml_integration_type)
    
    # Mock SAML library
    mock_auth = mocker.patch('onelogin.saml2.auth.OneLogin_Saml2_Auth')
    mock_auth.return_value.is_authenticated.return_value = True
    mock_auth.return_value.get_nameid.return_value = 'user@example.com'
    mock_auth.return_value.get_attributes.return_value = {
        'email': ['user@example.com'],
        'name': ['Test User']
    }
    
    result = await strategy.complete_authentication(
        authorization_code='',
        state='test-state',
        redirect_uri='https://neurotwin.com/callback/',
        saml_response='base64-encoded-response'
    )
    
    assert 'access_token_encrypted' in result
    assert result['saml_name_id'] == 'user@example.com'
    assert 'email' in result['saml_attributes']
```

### Step 8: Update Frontend (if needed)

Add frontend handling for your new auth type.

**File:** `neuro-frontend/src/lib/api/marketplace.ts`

```typescript
export async function startInstallation(integrationTypeId: string) {
    const response = await fetch('/api/v1/integrations/install/', {
        method: 'POST',
        headers: {
            'Authorization': `Bearer ${getToken()}`,
            'Content-Type': 'application/json'
        },
        body: JSON.stringify({ integration_type_id: integrationTypeId })
    });
    
    const data = await response.json();
    
    // Handle different auth types
    if (data.auth_type === 'saml') {
        // SAML requires POST form submission
        submitSAMLForm(data.authorization_url, data.session_id);
    } else if (data.requires_redirect) {
        // OAuth/Meta redirect
        window.location.href = data.authorization_url;
    } else if (data.requires_api_key) {
        // API key input
        showApiKeyModal(data.session_id);
    }
}

function submitSAMLForm(ssoUrl: string, sessionId: string) {
    // Create hidden form for SAML POST
    const form = document.createElement('form');
    form.method = 'POST';
    form.action = ssoUrl;
    
    const relayState = document.createElement('input');
    relayState.type = 'hidden';
    relayState.name = 'RelayState';
    relayState.value = sessionId;
    form.appendChild(relayState);
    
    document.body.appendChild(form);
    form.submit();
}
```

## Complete Example: Adding SAML Support

Here's a complete checklist for adding SAML authentication:

### Checklist

- [ ] **Step 1**: Create `SAMLStrategy` class extending `AuthStrategy`
- [ ] **Step 2**: Implement all required methods:
  - [ ] `get_required_fields()`
  - [ ] `validate_config()`
  - [ ] `get_authorization_url()`
  - [ ] `complete_authentication()`
  - [ ] `refresh_credentials()`
  - [ ] `revoke_credentials()`
- [ ] **Step 3**: Register strategy in `AuthStrategyFactory`
- [ ] **Step 4**: Add `SAML` to `AuthType` choices in models
- [ ] **Step 5**: Create and run database migration
- [ ] **Step 6**: Update admin interface for SAML configuration
- [ ] **Step 7**: Add SAML callback endpoint and URL route
- [ ] **Step 8**: Create `SAMLConfig` dataclass for type safety
- [ ] **Step 9**: Write unit tests for strategy
- [ ] **Step 10**: Write integration tests for complete flow
- [ ] **Step 11**: Update frontend to handle SAML flow
- [ ] **Step 12**: Update API documentation
- [ ] **Step 13**: Add SAML example to admin interface

## Best Practices

### 1. Security First

```python
# Always validate HTTPS for external URLs
def validate_config(self) -> None:
    super().validate_config()
    
    for url_field in ['authorization_url', 'token_url']:
        url = self.auth_config.get(url_field, '')
        if not url.startswith('https://'):
            raise ValidationError(f"{url_field} must use HTTPS")

# Always encrypt sensitive credentials
from apps.automation.utils.encryption import TokenEncryption

credentials_encrypted = TokenEncryption.encrypt(credentials)
```

### 2. Error Handling

```python
async def complete_authentication(self, **kwargs) -> Dict[str, Any]:
    try:
        # Authentication logic
        pass
    except ExternalAPIError as e:
        logger.error(f"Authentication failed: {e}")
        raise ValidationError(
            "Authentication failed. Please try again or contact support."
        )
```

### 3. Logging and Audit

```python
from apps.automation.services.auth_metrics import AuthenticationMetrics

# Log all authentication attempts
AuthenticationMetrics.log_authentication_attempt(
    user=user,
    integration_type=integration_type,
    action='install_complete',
    success=True,
    duration_ms=duration
)
```

### 4. Type Safety

```python
from dataclasses import dataclass
from typing import Dict, Any

@dataclass
class YourAuthConfig:
    """Type-safe configuration for your auth type."""
    field1: str
    field2: str
    
    @classmethod
    def from_dict(cls, config: Dict[str, Any]) -> 'YourAuthConfig':
        return cls(
            field1=config['field1'],
            field2=config['field2']
        )
```

### 5. Testing

```python
# Test all error paths
def test_strategy_invalid_config():
    with pytest.raises(ValidationError):
        YourStrategy(invalid_integration_type)

# Test async operations
@pytest.mark.asyncio
async def test_strategy_complete_authentication():
    result = await strategy.complete_authentication(...)
    assert 'access_token_encrypted' in result
```

## Common Patterns

### Pattern 1: Token Exchange

```python
async def complete_authentication(self, **kwargs) -> Dict[str, Any]:
    # Exchange authorization code for access token
    token_data = await AuthClient.exchange_token(
        token_url=self.auth_config['token_url'],
        code=kwargs['authorization_code'],
        client_id=self.auth_config['client_id'],
        client_secret=self._get_decrypted_secret()
    )
    
    # Encrypt and return
    return {
        'access_token_encrypted': TokenEncryption.encrypt(token_data['access_token']),
        'expires_at': timezone.now() + timedelta(seconds=token_data['expires_in'])
    }
```

### Pattern 2: No Redirect Flow

```python
def get_authorization_url(self, state: str, redirect_uri: str) -> Optional[str]:
    # Return None for auth types that don't require redirect
    return None

async def complete_authentication(self, **kwargs) -> Dict[str, Any]:
    # Validate credentials directly
    credentials = kwargs.get('credentials')
    if not self._validate_credentials(credentials):
        raise ValidationError("Invalid credentials")
    
    return {
        'access_token_encrypted': TokenEncryption.encrypt(credentials),
        'expires_at': None
    }
```

### Pattern 3: Custom Callback Parameters

```python
async def complete_authentication(self, **kwargs) -> Dict[str, Any]:
    # Extract custom parameters from kwargs
    custom_param = kwargs.get('custom_param')
    if not custom_param:
        raise ValidationError("custom_param is required")
    
    # Process authentication with custom parameters
    result = await self._process_custom_auth(custom_param)
    return result
```

## Troubleshooting

### Issue: Strategy Not Found

**Error:** `ValidationError: Unrecognized auth_type: saml`

**Solution:** Ensure strategy is registered in factory:
```python
AuthStrategyFactory.register_strategy('saml', SAMLStrategy)
```

### Issue: Missing Configuration Fields

**Error:** `ValidationError: Missing required fields for SAMLStrategy`

**Solution:** Check `get_required_fields()` matches your `auth_config`:
```python
def get_required_fields(self) -> List[str]:
    return ['field1', 'field2']  # Must match auth_config keys
```

### Issue: Import Errors

**Error:** `ImportError: cannot import name 'SAMLStrategy'`

**Solution:** Check file location and imports:
```python
# Correct import path
from apps.automation.services.auth_strategies.saml_strategy import SAMLStrategy
```

## Resources

- **Base Strategy Interface**: `apps/automation/services/auth_strategy.py`
- **Factory Implementation**: `apps/automation/services/auth_strategy_factory.py`
- **Existing Strategies**: `apps/automation/services/auth_strategies/`
- **HTTP Client**: `apps/automation/services/auth_client.py`
- **Encryption Utilities**: `apps/automation/utils/encryption.py`
- **Test Examples**: `apps/automation/tests/test_*_strategy.py`

## Summary

Adding a new authentication type requires:

1. Create strategy class extending `AuthStrategy`
2. Implement all required abstract methods
3. Register strategy in factory
4. Update database schema and run migrations
5. Configure admin interface
6. Add callback endpoint (if needed)
7. Write comprehensive tests
8. Update frontend handling
9. Document the new auth type

The system is designed for extensibility - most changes are additive and don't require modifying existing code.
