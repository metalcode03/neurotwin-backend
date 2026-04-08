# Authentication Strategy Layer

This package implements the authentication strategy layer for the Scalable Integration Engine, providing pluggable authentication methods for OAuth 2.0, Meta Business API, and API Key authentication.

## Architecture

The authentication strategy layer uses the Strategy Pattern to provide a consistent interface for different authentication methods:

```
BaseAuthStrategy (Abstract)
├── OAuthStrategy (OAuth 2.0 with PKCE)
├── MetaAuthStrategy (Meta Business API)
└── APIKeyStrategy (Simple API Key)

AuthStrategyFactory (Factory Pattern)
```

## Components

### BaseAuthStrategy (`base.py`)
Abstract base class defining the authentication strategy interface.

**Key Methods:**
- `get_authorization_url()` - Generate authorization URL
- `complete_authentication()` - Exchange code/key for tokens
- `refresh_credentials()` - Refresh expired credentials
- `revoke_credentials()` - Revoke credentials on uninstall
- `validate_config()` - Validate auth_config structure
- `get_required_fields()` - Get required configuration fields

**Data Classes:**
- `AuthorizationResult` - Result of authorization URL generation
- `AuthenticationResult` - Result of authentication completion

### OAuthStrategy (`oauth.py`)
OAuth 2.0 authentication with PKCE support.

**Features:**
- PKCE (Proof Key for Code Exchange) for enhanced security
- HTTPS enforcement for authorization and token URLs
- Token refresh using refresh_token
- Optional token revocation
- Encrypted client secret storage

**Required Config:**
- `client_id` - OAuth client identifier
- `client_secret_encrypted` - Encrypted client secret
- `authorization_url` - Provider authorization endpoint (HTTPS)
- `token_url` - Provider token endpoint (HTTPS)
- `scopes` - List of OAuth scopes

**Optional Config:**
- `revoke_url` - Token revocation endpoint

### MetaAuthStrategy (`meta.py`)
Meta Business API authentication for WhatsApp Business.

**Features:**
- Long-lived tokens (60-day expiry)
- Business account details fetching (WABA ID, phone number ID)
- Token refresh before expiry
- Meta Graph API integration

**Required Config:**
- `app_id` - Meta app identifier
- `app_secret_encrypted` - Encrypted app secret
- `config_id` - Meta configuration identifier
- `business_verification_url` - Meta Business verification URL

**Metadata Returned:**
- `business_id` - Meta Business account ID
- `waba_id` - WhatsApp Business Account ID
- `phone_number_id` - Phone number identifier
- `phone_numbers` - List of phone numbers

### APIKeyStrategy (`api_key.py`)
Simple API key authentication.

**Features:**
- No OAuth flow required
- API key validation via test request
- No token expiration or refresh
- Manual revocation only

**Required Config:**
- `api_endpoint` - Endpoint for API key validation
- `authentication_header_name` - Header name for API key

**Optional Config:**
- `additional_headers` - Additional headers for validation request

### AuthStrategyFactory (`factory.py`)
Factory for creating strategy instances.

**Features:**
- Registry pattern for strategy lookup
- Dynamic strategy registration
- Validation error for unknown auth types

**Usage:**
```python
from apps.automation.auth_strategies import AuthStrategyFactory

# Create strategy based on integration_type
strategy = AuthStrategyFactory.create_strategy(integration_type)

# Use strategy
auth_result = strategy.get_authorization_url(user_id, redirect_uri, state)
```

## Usage Examples

### OAuth Flow
```python
# 1. Generate authorization URL
strategy = AuthStrategyFactory.create_strategy(integration_type)
auth_result = strategy.get_authorization_url(
    user_id='user123',
    redirect_uri='https://app.com/callback',
    state='random_state_token'
)
# Redirect user to auth_result.url

# 2. Complete authentication (in callback)
auth_result = strategy.complete_authentication(
    code='auth_code_from_provider',
    state='random_state_token',
    redirect_uri='https://app.com/callback'
)
# Store auth_result.access_token and auth_result.refresh_token

# 3. Refresh credentials (when expired)
auth_result = strategy.refresh_credentials(integration)
# Update integration with new tokens
```

### Meta Flow
```python
# Similar to OAuth but with Meta-specific business details
strategy = AuthStrategyFactory.create_strategy(integration_type)
auth_result = strategy.complete_authentication(code, state, redirect_uri)

# Access Meta-specific metadata
business_id = auth_result.metadata['business_id']
waba_id = auth_result.metadata['waba_id']
phone_number_id = auth_result.metadata['phone_number_id']
```

### API Key Flow
```python
# No authorization URL needed
strategy = AuthStrategyFactory.create_strategy(integration_type)
auth_result = strategy.get_authorization_url(user_id, redirect_uri, state)
# auth_result.url is None - show API key input form

# Complete with API key
auth_result = strategy.complete_authentication(api_key='user_provided_key')
# Store auth_result.access_token (which is the API key)
```

## Requirements Mapping

- **Requirements 4.1-4.6**: BaseAuthStrategy interface
- **Requirements 5.1-5.7**: OAuthStrategy implementation
- **Requirements 6.1-6.7**: MetaAuthStrategy implementation
- **Requirements 7.1-7.7**: APIKeyStrategy implementation
- **Requirements 8.1-8.7**: AuthStrategyFactory implementation

## Security Considerations

1. **Encryption**: All secrets (client_secret, app_secret, API keys) are encrypted using Fernet symmetric encryption with separate keys per auth type
2. **HTTPS Enforcement**: OAuth URLs must use HTTPS protocol
3. **PKCE**: OAuth flow uses PKCE for enhanced security
4. **State Validation**: OAuth state parameter prevents CSRF attacks
5. **Token Storage**: All tokens are encrypted before database storage

## Testing

Property-based tests (optional tasks 4.2, 4.4, 4.8) validate:
- Strategy instantiation with invalid config
- OAuth HTTPS enforcement
- Factory error handling for unknown auth types

## Extension

To add a new authentication strategy:

1. Create a new strategy class inheriting from `BaseAuthStrategy`
2. Implement all abstract methods
3. Register with factory:
```python
AuthStrategyFactory.register_strategy('custom', CustomStrategy)
```

## Dependencies

- `httpx` - HTTP client for API requests
- `cryptography` - Fernet encryption
- `django` - Framework utilities
- `apps.automation.utils.encryption` - TokenEncryption utility
- `apps.automation.utils.oauth_state` - OAuth state caching
