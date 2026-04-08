# Integration Engine - Developer Guide

## Overview

This guide explains how to extend the Scalable Integration Engine by adding new authentication strategies, integration types, and custom functionality. The engine is designed with extensibility in mind using the Strategy Pattern and Factory Pattern.

## Table of Contents

- [Architecture Overview](#architecture-overview)
- [Adding New Authentication Strategies](#adding-new-authentication-strategies)
- [Adding New Integration Types](#adding-new-integration-types)
- [Extending the Factory Pattern](#extending-the-factory-pattern)
- [Testing Requirements](#testing-requirements)
- [Best Practices](#best-practices)

---

## Architecture Overview

The Integration Engine follows a layered architecture:

```
┌─────────────────────────────────────────┐
│         API Layer (Views)               │
│  Installation, Webhooks, Messages       │
└─────────────────────────────────────────┘
                  ↓
┌─────────────────────────────────────────┐
│      Service Layer (Business Logic)     │
│  Installation, Delivery, Health         │
└─────────────────────────────────────────┘
                  ↓
┌─────────────────────────────────────────┐
│    Authentication Strategy Layer        │
│  OAuth, Meta, API Key (Pluggable)       │
└─────────────────────────────────────────┘
                  ↓
┌─────────────────────────────────────────┐
│      Processing Layer (Celery)          │
│  Message Queue, Rate Limiting, Retry    │
└─────────────────────────────────────────┘
                  ↓
┌─────────────────────────────────────────┐
│       Storage Layer (Models)            │
│  Integration, Conversation, Message     │
└─────────────────────────────────────────┘
```

### Key Design Patterns

1. **Strategy Pattern**: Authentication strategies are pluggable and interchangeable
2. **Factory Pattern**: AuthStrategyFactory creates appropriate strategy instances
3. **Service Layer**: Business logic is isolated from views and serializers
4. **Queue-Based Processing**: All message processing is asynchronous via Celery

---

## Adding New Authentication Strategies

### Step 1: Create Strategy Class

Create a new file in `apps/automation/auth_strategies/`:

```python
# apps/automation/auth_strategies/custom.py

from typing import Dict, List, Optional
from apps.automation.auth_strategies.base import (
    BaseAuthStrategy,
    AuthorizationResult,
    AuthenticationResult
)
from apps.automation.utils.encryption import TokenEncryption
import httpx
from django.utils import timezone
from datetime import timedelta

class CustomAuthStrategy(BaseAuthStrategy):
    """
    Custom authentication strategy for XYZ platform.
    
    Requirements: [List your requirements here]
    """
    
    def get_required_fields(self) -> List[str]:
        """
        Define required fields in auth_config.
        
        Returns:
            List of required field names
        """
        return [
            'client_id',
            'client_secret_encrypted',
            'auth_endpoint',
            'token_endpoint',
            'api_base_url'
        ]
    
    def get_authorization_url(
        self,
        user_id: str,
        redirect_uri: str,
        state: str
    ) -> AuthorizationResult:
        """
        Generate authorization URL for user to grant permissions.
        
        Args:
            user_id: User identifier
            redirect_uri: Callback URL after authorization
            state: CSRF protection token
            
        Returns:
            AuthorizationResult with URL and session info
        """
        # Build authorization URL with required parameters
        params = {
            'client_id': self.auth_config['client_id'],
            'redirect_uri': redirect_uri,
            'response_type': 'code',
            'state': state,
            'scope': 'read write'
        }
        
        # Store any session data needed for callback
        from apps.automation.utils.oauth_state import cache_oauth_state
        cache_oauth_state(state, {
            'user_id': user_id,
            'integration_type_id': str(self.integration_type.id)
        })
        
        url = f"{self.auth_config['auth_endpoint']}?{urlencode(params)}"
        
        return AuthorizationResult(
            url=url,
            state=state,
            session_id=state
        )
    
    def complete_authentication(
        self,
        code: str,
        state: str,
        redirect_uri: str
    ) -> AuthenticationResult:
        """
        Exchange authorization code for access tokens.
        
        Args:
            code: Authorization code from provider
            state: CSRF protection token
            redirect_uri: Original callback URL
            
        Returns:
            AuthenticationResult with tokens and metadata
        """
        # Validate state
        from apps.automation.utils.oauth_state import get_oauth_state
        session_data = get_oauth_state(state, consume=True)
        if not session_data:
            raise ValidationError("Invalid or expired OAuth state")
        
        # Exchange code for tokens
        token_data = {
            'grant_type': 'authorization_code',
            'code': code,
            'redirect_uri': redirect_uri,
            'client_id': self.auth_config['client_id'],
            'client_secret': self._decrypt_client_secret()
        }
        
        response = httpx.post(
            self.auth_config['token_endpoint'],
            data=token_data,
            timeout=30.0
        )
        response.raise_for_status()
        
        tokens = response.json()
        
        # Fetch any additional metadata needed
        metadata = self._fetch_account_details(tokens['access_token'])
        
        return AuthenticationResult(
            access_token=tokens['access_token'],
            refresh_token=tokens.get('refresh_token'),
            expires_at=timezone.now() + timedelta(seconds=tokens.get('expires_in', 3600)),
            metadata=metadata
        )
    
    def refresh_credentials(self, integration) -> AuthenticationResult:
        """
        Refresh expired credentials.
        
        Args:
            integration: Integration with expired credentials
            
        Returns:
            AuthenticationResult with new tokens
        """
        if not integration.refresh_token:
            raise ValidationError("No refresh token available")
        
        token_data = {
            'grant_type': 'refresh_token',
            'refresh_token': integration.refresh_token,
            'client_id': self.auth_config['client_id'],
            'client_secret': self._decrypt_client_secret()
        }
        
        response = httpx.post(
            self.auth_config['token_endpoint'],
            data=token_data,
            timeout=30.0
        )
        response.raise_for_status()
        
        tokens = response.json()
        
        return AuthenticationResult(
            access_token=tokens['access_token'],
            refresh_token=tokens.get('refresh_token', integration.refresh_token),
            expires_at=timezone.now() + timedelta(seconds=tokens.get('expires_in', 3600)),
            metadata={}
        )
    
    def revoke_credentials(self, integration) -> bool:
        """
        Revoke credentials with provider.
        
        Args:
            integration: Integration to revoke
            
        Returns:
            True if revocation successful
        """
        revoke_url = self.auth_config.get('revoke_endpoint')
        if not revoke_url:
            return True  # No revocation endpoint
        
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
            return response.status_code in [200, 204]
        except Exception as e:
            logger.error(f"Failed to revoke credentials: {e}")
            return False
    
    def _decrypt_client_secret(self) -> str:
        """Decrypt client secret from auth_config"""
        encrypted = self.auth_config['client_secret_encrypted']
        return TokenEncryption.decrypt(
            base64.b64decode(encrypted),
            auth_type='custom'  # Use your auth type
        )
    
    def _fetch_account_details(self, access_token: str) -> Dict:
        """Fetch account details from provider API"""
        response = httpx.get(
            f"{self.auth_config['api_base_url']}/account",
            headers={'Authorization': f'Bearer {access_token}'},
            timeout=30.0
        )
        response.raise_for_status()
        
        data = response.json()
        return {
            'account_id': data['id'],
            'account_name': data['name'],
            # Add any other metadata needed
        }
```

### Step 2: Register Strategy with Factory

Update `apps/automation/auth_strategies/factory.py`:

```python
from apps.automation.auth_strategies.custom import CustomAuthStrategy

class AuthStrategyFactory:
    _registry: Dict[str, Type[BaseAuthStrategy]] = {
        AuthType.OAUTH: OAuthStrategy,
        AuthType.META: MetaAuthStrategy,
        AuthType.API_KEY: APIKeyStrategy,
        'custom': CustomAuthStrategy,  # Add your strategy
    }
```

Or register dynamically:

```python
from apps.automation.auth_strategies import AuthStrategyFactory
from apps.automation.auth_strategies.custom import CustomAuthStrategy

AuthStrategyFactory.register_strategy('custom', CustomAuthStrategy)
```

### Step 3: Add Auth Type to Models

Update `apps/automation/models.py`:

```python
class AuthType(models.TextChoices):
    OAUTH = 'oauth', 'OAuth 2.0'
    META = 'meta', 'Meta Business'
    API_KEY = 'api_key', 'API Key'
    CUSTOM = 'custom', 'Custom Auth'  # Add your type
```

### Step 4: Create Migration

```bash
python manage.py makemigrations
python manage.py migrate
```

### Step 5: Add Encryption Key

Add to `.env`:

```bash
CUSTOM_ENCRYPTION_KEY=<generate-with-fernet>
```

Generate key:

```python
from cryptography.fernet import Fernet
print(Fernet.generate_key().decode())
```

Update `apps/automation/utils/encryption.py`:

```python
def _get_encryption_key(self, auth_type: str) -> bytes:
    keys = {
        'oauth': settings.OAUTH_ENCRYPTION_KEY,
        'meta': settings.META_ENCRYPTION_KEY,
        'api_key': settings.API_KEY_ENCRYPTION_KEY,
        'custom': settings.CUSTOM_ENCRYPTION_KEY,  # Add your key
    }
    # ... rest of method
```

---

## Adding New Integration Types

### Step 1: Create Integration Type via Admin

1. Go to Django Admin: `/admin/automation/integrationtypemodel/`
2. Click "Add Integration Type"
3. Fill in fields:
   - **Type**: Unique identifier (e.g., `custom-platform`)
   - **Name**: Display name (e.g., `Custom Platform`)
   - **Description**: User-facing description
   - **Auth Type**: Select your auth type (e.g., `custom`)
   - **Auth Config**: JSON configuration
   - **Category**: Choose category (messaging, productivity, etc.)
   - **Icon**: Upload icon or provide URL

### Step 2: Configure Auth Config

Example for custom OAuth:

```json
{
  "client_id": "your_client_id",
  "client_secret_encrypted": "base64_encrypted_secret",
  "auth_endpoint": "https://platform.com/oauth/authorize",
  "token_endpoint": "https://platform.com/oauth/token",
  "revoke_endpoint": "https://platform.com/oauth/revoke",
  "api_base_url": "https://api.platform.com/v1"
}
```

### Step 3: Configure Rate Limits (Optional)

Add `rate_limit_config` to Integration Type:

```json
{
  "messages_per_minute": 30,
  "requests_per_minute": 120,
  "burst_limit": 10
}
```

### Step 4: Test Installation Flow

```python
# Test via API
import requests

# 1. Start installation
response = requests.post(
    'http://localhost:8000/api/v1/integrations/install/',
    headers={'Authorization': 'Bearer <token>'},
    json={'integration_type_id': '<uuid>'}
)

# 2. Follow authorization_url
# 3. Complete callback
# 4. Verify integration created
```

---

## Extending the Factory Pattern

### Dynamic Strategy Registration

Register strategies at runtime:

```python
# In your app's ready() method
from django.apps import AppConfig

class MyAppConfig(AppConfig):
    name = 'my_app'
    
    def ready(self):
        from apps.automation.auth_strategies import AuthStrategyFactory
        from my_app.strategies import MyCustomStrategy
        
        AuthStrategyFactory.register_strategy('my_custom', MyCustomStrategy)
```

### Strategy Validation

Add custom validation to your strategy:

```python
class CustomAuthStrategy(BaseAuthStrategy):
    def validate_config(self) -> Tuple[bool, List[str]]:
        """Custom validation logic"""
        is_valid, errors = super().validate_config()
        
        # Add custom validation
        if 'api_base_url' in self.auth_config:
            url = self.auth_config['api_base_url']
            if not url.startswith('https://'):
                errors.append("api_base_url must use HTTPS")
                is_valid = False
        
        return is_valid, errors
```

### Strategy Hooks

Override methods for custom behavior:

```python
class CustomAuthStrategy(BaseAuthStrategy):
    def __init__(self, integration_type):
        super().__init__(integration_type)
        # Custom initialization
        self.api_client = self._create_api_client()
    
    def _create_api_client(self):
        """Create custom API client"""
        return CustomAPIClient(
            base_url=self.auth_config['api_base_url']
        )
```

---

## Testing Requirements

### Unit Tests

Create tests in `apps/automation/tests/test_custom_strategy.py`:

```python
import pytest
from apps.automation.auth_strategies.custom import CustomAuthStrategy
from apps.automation.models import IntegrationTypeModel

@pytest.fixture
def custom_integration_type(db):
    return IntegrationTypeModel.objects.create(
        type='custom-platform',
        name='Custom Platform',
        auth_type='custom',
        auth_config={
            'client_id': 'test_client',
            'client_secret_encrypted': 'encrypted_secret',
            'auth_endpoint': 'https://platform.com/oauth/authorize',
            'token_endpoint': 'https://platform.com/oauth/token',
            'api_base_url': 'https://api.platform.com/v1'
        }
    )

def test_strategy_instantiation(custom_integration_type):
    """Test strategy can be instantiated with valid config"""
    strategy = CustomAuthStrategy(custom_integration_type)
    assert strategy.integration_type == custom_integration_type

def test_get_authorization_url(custom_integration_type):
    """Test authorization URL generation"""
    strategy = CustomAuthStrategy(custom_integration_type)
    result = strategy.get_authorization_url(
        user_id='user123',
        redirect_uri='https://app.com/callback',
        state='random_state'
    )
    
    assert result.url.startswith('https://platform.com/oauth/authorize')
    assert 'client_id=test_client' in result.url
    assert 'state=random_state' in result.url

def test_complete_authentication(custom_integration_type, mocker):
    """Test authentication completion"""
    # Mock HTTP requests
    mock_post = mocker.patch('httpx.post')
    mock_post.return_value.json.return_value = {
        'access_token': 'access_token_123',
        'refresh_token': 'refresh_token_456',
        'expires_in': 3600
    }
    
    strategy = CustomAuthStrategy(custom_integration_type)
    result = strategy.complete_authentication(
        code='auth_code',
        state='random_state',
        redirect_uri='https://app.com/callback'
    )
    
    assert result.access_token == 'access_token_123'
    assert result.refresh_token == 'refresh_token_456'

def test_invalid_config_raises_error(db):
    """Test strategy validation with invalid config"""
    integration_type = IntegrationTypeModel.objects.create(
        type='custom-platform',
        name='Custom Platform',
        auth_type='custom',
        auth_config={'client_id': 'test'}  # Missing required fields
    )
    
    with pytest.raises(ValidationError):
        CustomAuthStrategy(integration_type)
```

### Integration Tests

Test complete installation flow:

```python
@pytest.mark.django_db
def test_custom_installation_flow(client, user, custom_integration_type):
    """Test complete installation flow"""
    client.force_authenticate(user=user)
    
    # 1. Start installation
    response = client.post('/api/v1/integrations/install/', {
        'integration_type_id': str(custom_integration_type.id)
    })
    assert response.status_code == 200
    assert 'authorization_url' in response.json()
    
    session_id = response.json()['session_id']
    
    # 2. Mock callback (simulate OAuth provider redirect)
    # ... test callback handling
    
    # 3. Verify integration created
    from apps.automation.models import Integration
    integration = Integration.objects.filter(
        user=user,
        integration_type=custom_integration_type
    ).first()
    assert integration is not None
    assert integration.status == 'active'
```

### Property-Based Tests (Optional)

Use Hypothesis for property-based testing:

```python
from hypothesis import given, strategies as st

@given(
    client_id=st.text(min_size=1, max_size=100),
    state=st.text(min_size=10, max_size=50)
)
def test_authorization_url_always_valid(client_id, state, custom_integration_type):
    """Property: Authorization URL is always valid for any input"""
    custom_integration_type.auth_config['client_id'] = client_id
    custom_integration_type.save()
    
    strategy = CustomAuthStrategy(custom_integration_type)
    result = strategy.get_authorization_url(
        user_id='user123',
        redirect_uri='https://app.com/callback',
        state=state
    )
    
    # Property: URL should always be valid HTTPS
    assert result.url.startswith('https://')
    assert client_id in result.url
    assert state in result.url
```

### Test Coverage Requirements

- **Minimum 85% code coverage** for new strategies
- **All public methods** must have unit tests
- **Happy path and error cases** must be tested
- **Integration tests** for complete flows

Run tests:

```bash
# Run all tests
pytest apps/automation/tests/

# Run with coverage
pytest --cov=apps.automation.auth_strategies apps/automation/tests/

# Run specific test file
pytest apps/automation/tests/test_custom_strategy.py
```

---

## Best Practices

### Security

1. **Always encrypt secrets** before storing in auth_config
2. **Use HTTPS** for all external API calls
3. **Validate webhook signatures** before processing
4. **Use constant-time comparison** for signature verification
5. **Implement CSRF protection** with state parameter
6. **Rotate encryption keys** periodically

### Error Handling

1. **Classify errors** as transient or permanent
2. **Provide user-friendly messages** for all errors
3. **Log errors with context** (user_id, integration_id, etc.)
4. **Use circuit breaker** for external API calls
5. **Implement retry logic** for transient failures

### Performance

1. **Use async processing** for all external API calls
2. **Implement rate limiting** to prevent quota exhaustion
3. **Cache frequently accessed data** (integration types, configs)
4. **Use database indexes** for query optimization
5. **Monitor task queue length** and worker health

### Code Organization

1. **Keep strategies focused** - one responsibility per strategy
2. **Extract common logic** to base class or utilities
3. **Use type hints** for all method signatures
4. **Document all public methods** with docstrings
5. **Follow Django/DRF conventions** for consistency

### Testing

1. **Mock external API calls** in tests
2. **Test both success and failure paths**
3. **Use fixtures** for common test data
4. **Test edge cases** (expired tokens, rate limits, etc.)
5. **Run tests before committing** code

---

## Example: Complete Custom Strategy

See `apps/automation/auth_strategies/` for complete examples:

- `oauth.py` - OAuth 2.0 with PKCE
- `meta.py` - Meta Business API
- `api_key.py` - Simple API key authentication

---

## Troubleshooting

### Strategy Not Found

**Error**: `Unknown auth_type: custom`

**Solution**: Ensure strategy is registered with factory:

```python
from apps.automation.auth_strategies import AuthStrategyFactory
from my_app.strategies import CustomAuthStrategy

AuthStrategyFactory.register_strategy('custom', CustomAuthStrategy)
```

### Validation Error on Instantiation

**Error**: `Invalid auth_config: Missing required field: client_id`

**Solution**: Ensure all required fields are present in auth_config:

```python
def get_required_fields(self) -> List[str]:
    return ['client_id', 'client_secret_encrypted', ...]
```

### Token Encryption Fails

**Error**: `Encryption key not found for auth_type: custom`

**Solution**: Add encryption key to settings and `.env`:

```python
# settings.py
CUSTOM_ENCRYPTION_KEY = os.getenv('CUSTOM_ENCRYPTION_KEY')

# .env
CUSTOM_ENCRYPTION_KEY=<your-fernet-key>
```

---

## Resources

- [Authentication Strategy README](../apps/automation/auth_strategies/README.md)
- [Celery Tasks README](../apps/automation/tasks/README.md)
- [API Documentation](./integration-engine-api.md)
- [Troubleshooting Guide](./integration-engine-troubleshooting.md)

---

## Support

For development questions, contact: dev-support@neurotwin.com

For architecture discussions, see: [Design Document](../.kiro/specs/scalable-integration-engine/design.md)
