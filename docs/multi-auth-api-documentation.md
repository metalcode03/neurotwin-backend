# Multi-Auth Integration System: API Documentation

## Overview

This document describes the REST API endpoints for the Multi-Auth Integration System, which supports OAuth 2.0, Meta Business, and API Key authentication strategies.

## Base URL

```
https://api.neurotwin.com/api/v1
```

## Authentication

All endpoints require JWT authentication via the `Authorization` header:

```
Authorization: Bearer <jwt_token>
```

## Endpoints

### 1. Start Installation

Initiates the installation process for an integration. Returns different responses based on the authentication type.

**Endpoint:** `POST /integrations/install/`

**Request Body:**
```json
{
    "integration_type_id": "uuid-of-integration-type"
}
```

**Response (OAuth 2.0):**
```json
{
    "session_id": "550e8400-e29b-41d4-a716-446655440000",
    "authorization_url": "https://accounts.google.com/o/oauth2/v2/auth?client_id=...&redirect_uri=...&state=...",
    "requires_redirect": true,
    "requires_api_key": false,
    "auth_type": "oauth"
}
```

**Response (Meta Business):**
```json
{
    "session_id": "550e8400-e29b-41d4-a716-446655440001",
    "authorization_url": "https://www.facebook.com/v18.0/dialog/oauth?app_id=...&config_id=...&state=...",
    "requires_redirect": true,
    "requires_api_key": false,
    "auth_type": "meta"
}
```

**Response (API Key):**
```json
{
    "session_id": "550e8400-e29b-41d4-a716-446655440002",
    "authorization_url": null,
    "requires_redirect": false,
    "requires_api_key": true,
    "auth_type": "api_key",
    "api_key_format_hint": "Format: sk-xxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxx"
}
```

**Status Codes:**
- `200 OK` - Installation started successfully
- `400 Bad Request` - Invalid integration_type_id or integration already installed
- `401 Unauthorized` - Missing or invalid JWT token
- `404 Not Found` - Integration type not found or inactive

**Example Usage:**

```bash
curl -X POST https://api.neurotwin.com/api/v1/integrations/install/ \
  -H "Authorization: Bearer <jwt_token>" \
  -H "Content-Type: application/json" \
  -d '{"integration_type_id": "550e8400-e29b-41d4-a716-446655440000"}'
```

```typescript
// Frontend example
const response = await fetch('/api/v1/integrations/install/', {
    method: 'POST',
    headers: {
        'Authorization': `Bearer ${token}`,
        'Content-Type': 'application/json'
    },
    body: JSON.stringify({
        integration_type_id: integrationTypeId
    })
});

const data = await response.json();

if (data.requires_redirect) {
    // OAuth or Meta flow - redirect user
    window.location.href = data.authorization_url;
} else if (data.requires_api_key) {
    // API Key flow - show input modal
    showApiKeyModal(data.session_id, data.api_key_format_hint);
}
```

---

### 2. OAuth Callback

Handles the OAuth 2.0 callback after user authorization. This is the standard OAuth callback endpoint.

**Endpoint:** `GET /integrations/oauth/callback/`

**Query Parameters:**
- `code` (required) - Authorization code from OAuth provider
- `state` (required) - CSRF protection state parameter
- `session_id` (required) - Installation session UUID

**Response:**
Redirects to dashboard with success or error message:
- Success: `/dashboard/apps?installation=success&integration_id=<uuid>`
- Error: `/dashboard/apps?installation=error&message=<error_message>`

**Status Codes:**
- `302 Found` - Redirect to dashboard
- `400 Bad Request` - Invalid parameters or state mismatch
- `401 Unauthorized` - Session expired or invalid

**Example URL:**
```
https://api.neurotwin.com/api/v1/integrations/oauth/callback/?code=4/0AY0e-g7...&state=550e8400-e29b-41d4-a716-446655440000&session_id=550e8400-e29b-41d4-a716-446655440000
```

---

### 3. Meta Callback

Handles the Meta Business callback after user authorization. This endpoint is specific to Meta integrations (WhatsApp, Instagram).

**Endpoint:** `GET /integrations/meta/callback/`

**Query Parameters:**
- `code` (required) - Authorization code from Meta
- `state` (required) - CSRF protection state parameter
- `session_id` (required) - Installation session UUID

**Response:**
Redirects to dashboard with success or error message:
- Success: `/dashboard/apps?installation=success&integration_id=<uuid>&meta_business_id=<business_id>`
- Error: `/dashboard/apps?installation=error&message=<error_message>`

**Status Codes:**
- `302 Found` - Redirect to dashboard
- `400 Bad Request` - Invalid parameters or state mismatch
- `401 Unauthorized` - Session expired or invalid
- `403 Forbidden` - Meta business verification failed

**Example URL:**
```
https://api.neurotwin.com/api/v1/integrations/meta/callback/?code=AQD...&state=550e8400-e29b-41d4-a716-446655440001&session_id=550e8400-e29b-41d4-a716-446655440001
```

**What Happens:**
1. Exchanges Meta authorization code for short-lived token
2. Exchanges short-lived token for long-lived token (60-day expiry)
3. Retrieves Meta business account details (business_id, waba_id, phone_number_id)
4. Creates Integration record with encrypted tokens and Meta-specific fields
5. Redirects to dashboard

---

### 4. Complete API Key Installation

Completes the API key installation flow by validating and storing the API key.

**Endpoint:** `POST /integrations/api-key/complete/`

**Request Body:**
```json
{
    "session_id": "550e8400-e29b-41d4-a716-446655440002",
    "api_key": "sk-xxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxx"
}
```

**Response (Success):**
```json
{
    "success": true,
    "integration_id": "550e8400-e29b-41d4-a716-446655440003",
    "message": "API key validated and integration created successfully"
}
```

**Response (Error):**
```json
{
    "success": false,
    "error": "Invalid API key",
    "message": "The provided API key could not be validated. Please check the key and try again."
}
```

**Status Codes:**
- `200 OK` - API key validated and integration created
- `400 Bad Request` - Invalid session_id or missing api_key
- `401 Unauthorized` - Missing or invalid JWT token
- `403 Forbidden` - API key validation failed

**Example Usage:**

```bash
curl -X POST https://api.neurotwin.com/api/v1/integrations/api-key/complete/ \
  -H "Authorization: Bearer <jwt_token>" \
  -H "Content-Type: application/json" \
  -d '{
    "session_id": "550e8400-e29b-41d4-a716-446655440002",
    "api_key": "sk-xxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxx"
  }'
```

```typescript
// Frontend example
const response = await fetch('/api/v1/integrations/api-key/complete/', {
    method: 'POST',
    headers: {
        'Authorization': `Bearer ${token}`,
        'Content-Type': 'application/json'
    },
    body: JSON.stringify({
        session_id: sessionId,
        api_key: apiKey
    })
});

const data = await response.json();

if (data.success) {
    // Redirect to dashboard
    window.location.href = `/dashboard/apps?installation=success&integration_id=${data.integration_id}`;
} else {
    // Show error message
    showError(data.message);
}
```

---

### 5. Get Integration Type Details

Retrieves details about a specific integration type, including authentication requirements.

**Endpoint:** `GET /integrations/types/{id}/`

**Path Parameters:**
- `id` (required) - UUID of the integration type

**Response (OAuth):**
```json
{
    "id": "550e8400-e29b-41d4-a716-446655440000",
    "name": "Gmail",
    "description": "Connect your Gmail account to send and receive emails",
    "icon_url": "https://cdn.neurotwin.com/icons/gmail.png",
    "auth_type": "oauth",
    "required_fields": [
        "client_id",
        "client_secret_encrypted",
        "authorization_url",
        "token_url",
        "scopes"
    ],
    "scopes": [
        "https://www.googleapis.com/auth/gmail.send",
        "https://www.googleapis.com/auth/gmail.readonly"
    ],
    "is_active": true,
    "category": "email"
}
```

**Response (Meta):**
```json
{
    "id": "550e8400-e29b-41d4-a716-446655440001",
    "name": "WhatsApp Business",
    "description": "Connect your WhatsApp Business account to send and receive messages",
    "icon_url": "https://cdn.neurotwin.com/icons/whatsapp.png",
    "auth_type": "meta",
    "required_fields": [
        "app_id",
        "app_secret_encrypted",
        "config_id",
        "business_verification_url"
    ],
    "permissions": [
        "whatsapp_business_management",
        "whatsapp_business_messaging"
    ],
    "is_active": true,
    "category": "messaging"
}
```

**Response (API Key):**
```json
{
    "id": "550e8400-e29b-41d4-a716-446655440002",
    "name": "Custom API",
    "description": "Connect to a custom API using an API key",
    "icon_url": "https://cdn.neurotwin.com/icons/api.png",
    "auth_type": "api_key",
    "required_fields": [
        "api_endpoint",
        "authentication_header_name"
    ],
    "api_key_format_hint": "Format: sk-xxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxx",
    "is_active": true,
    "category": "custom"
}
```

**Status Codes:**
- `200 OK` - Integration type found
- `401 Unauthorized` - Missing or invalid JWT token
- `404 Not Found` - Integration type not found

---

### 6. List Integration Types

Retrieves a list of all available integration types, optionally filtered by authentication type.

**Endpoint:** `GET /integrations/types/`

**Query Parameters:**
- `auth_type` (optional) - Filter by authentication type: `oauth`, `meta`, `api_key`
- `category` (optional) - Filter by category: `email`, `messaging`, `calendar`, `custom`
- `is_active` (optional) - Filter by active status: `true`, `false`

**Response:**
```json
{
    "count": 15,
    "results": [
        {
            "id": "550e8400-e29b-41d4-a716-446655440000",
            "name": "Gmail",
            "description": "Connect your Gmail account",
            "icon_url": "https://cdn.neurotwin.com/icons/gmail.png",
            "auth_type": "oauth",
            "category": "email",
            "is_active": true
        },
        {
            "id": "550e8400-e29b-41d4-a716-446655440001",
            "name": "WhatsApp Business",
            "description": "Connect your WhatsApp Business account",
            "icon_url": "https://cdn.neurotwin.com/icons/whatsapp.png",
            "auth_type": "meta",
            "category": "messaging",
            "is_active": true
        }
    ]
}
```

**Example Usage:**

```bash
# Get all OAuth integrations
curl -X GET "https://api.neurotwin.com/api/v1/integrations/types/?auth_type=oauth" \
  -H "Authorization: Bearer <jwt_token>"

# Get all messaging integrations
curl -X GET "https://api.neurotwin.com/api/v1/integrations/types/?category=messaging" \
  -H "Authorization: Bearer <jwt_token>"
```

---

### 7. Meta Webhook Endpoint

Receives webhook events from Meta for WhatsApp and Instagram integrations.

**Endpoint:** `POST /webhooks/meta/`

**Headers:**
- `X-Hub-Signature-256` (required) - HMAC-SHA256 signature for verification

**Request Body (Message Event):**
```json
{
    "object": "whatsapp_business_account",
    "entry": [
        {
            "id": "WHATSAPP_BUSINESS_ACCOUNT_ID",
            "changes": [
                {
                    "value": {
                        "messaging_product": "whatsapp",
                        "metadata": {
                            "display_phone_number": "+1234567890",
                            "phone_number_id": "PHONE_NUMBER_ID"
                        },
                        "messages": [
                            {
                                "from": "+1234567890",
                                "id": "wamid.xxx",
                                "timestamp": "1234567890",
                                "text": {
                                    "body": "Hello"
                                },
                                "type": "text"
                            }
                        ]
                    },
                    "field": "messages"
                }
            ]
        }
    ]
}
```

**Response:**
```json
{
    "success": true
}
```

**Status Codes:**
- `200 OK` - Webhook processed successfully
- `400 Bad Request` - Invalid webhook payload
- `403 Forbidden` - Invalid signature

**Webhook Verification (GET):**

Meta sends a verification request when you configure the webhook URL.

**Endpoint:** `GET /webhooks/meta/`

**Query Parameters:**
- `hub.mode` - Should be "subscribe"
- `hub.verify_token` - Your verification token
- `hub.challenge` - Challenge string to return

**Response:**
Returns the `hub.challenge` value as plain text if verification succeeds.

**Example:**
```
GET /webhooks/meta/?hub.mode=subscribe&hub.verify_token=your_token&hub.challenge=1234567890
```

---

## Error Responses

All endpoints return consistent error responses:

```json
{
    "error": "error_code",
    "message": "Human-readable error message",
    "details": {
        "field": "Additional error details"
    }
}
```

### Common Error Codes

- `invalid_session` - Installation session not found or expired
- `invalid_state` - CSRF state parameter mismatch
- `invalid_code` - Authorization code invalid or expired
- `invalid_api_key` - API key validation failed
- `integration_exists` - Integration already installed for this user
- `auth_failed` - Authentication with provider failed
- `token_exchange_failed` - Failed to exchange code for token
- `rate_limit_exceeded` - Too many authentication attempts

---

## Rate Limiting

Authentication endpoints are rate-limited to prevent abuse:

- **Installation endpoints**: 10 requests per hour per user
- **Webhook endpoints**: 1000 requests per hour per integration

Rate limit headers are included in responses:

```
X-RateLimit-Limit: 10
X-RateLimit-Remaining: 7
X-RateLimit-Reset: 1234567890
```

When rate limit is exceeded, the API returns `429 Too Many Requests`:

```json
{
    "error": "rate_limit_exceeded",
    "message": "Too many authentication attempts. Please try again in 1 hour.",
    "retry_after": 3600
}
```

---

## Complete Integration Flow Examples

### OAuth 2.0 Flow (Gmail)

```typescript
// Step 1: Start installation
const startResponse = await fetch('/api/v1/integrations/install/', {
    method: 'POST',
    headers: {
        'Authorization': `Bearer ${token}`,
        'Content-Type': 'application/json'
    },
    body: JSON.stringify({
        integration_type_id: gmailIntegrationTypeId
    })
});

const { session_id, authorization_url, auth_type } = await startResponse.json();

// Step 2: Redirect to OAuth provider
window.location.href = authorization_url;

// Step 3: User authorizes and is redirected back to callback
// GET /api/v1/integrations/oauth/callback/?code=xxx&state=xxx&session_id=xxx

// Step 4: Backend completes authentication and redirects to dashboard
// User lands on: /dashboard/apps?installation=success&integration_id=xxx
```

### Meta Business Flow (WhatsApp)

```typescript
// Step 1: Start installation
const startResponse = await fetch('/api/v1/integrations/install/', {
    method: 'POST',
    headers: {
        'Authorization': `Bearer ${token}`,
        'Content-Type': 'application/json'
    },
    body: JSON.stringify({
        integration_type_id: whatsappIntegrationTypeId
    })
});

const { session_id, authorization_url, auth_type } = await startResponse.json();

// Step 2: Redirect to Meta Business verification
window.location.href = authorization_url;

// Step 3: User completes Meta Business verification
// GET /api/v1/integrations/meta/callback/?code=xxx&state=xxx&session_id=xxx

// Step 4: Backend exchanges tokens, retrieves business details, creates integration
// User lands on: /dashboard/apps?installation=success&integration_id=xxx&meta_business_id=xxx
```

### API Key Flow (Custom API)

```typescript
// Step 1: Start installation
const startResponse = await fetch('/api/v1/integrations/install/', {
    method: 'POST',
    headers: {
        'Authorization': `Bearer ${token}`,
        'Content-Type': 'application/json'
    },
    body: JSON.stringify({
        integration_type_id: customApiIntegrationTypeId
    })
});

const { session_id, requires_api_key, api_key_format_hint } = await startResponse.json();

// Step 2: Show API key input modal (no redirect)
const apiKey = await showApiKeyModal(api_key_format_hint);

// Step 3: Submit API key for validation
const completeResponse = await fetch('/api/v1/integrations/api-key/complete/', {
    method: 'POST',
    headers: {
        'Authorization': `Bearer ${token}`,
        'Content-Type': 'application/json'
    },
    body: JSON.stringify({
        session_id: session_id,
        api_key: apiKey
    })
});

const { success, integration_id } = await completeResponse.json();

// Step 4: Redirect to dashboard
if (success) {
    window.location.href = `/dashboard/apps?installation=success&integration_id=${integration_id}`;
}
```

---

## Security Considerations

### CSRF Protection

All OAuth and Meta flows use the `state` parameter for CSRF protection:
- State is generated server-side and stored in `InstallationSession`
- State is validated on callback to prevent CSRF attacks
- State mismatches result in `400 Bad Request`

### Token Encryption

All credentials are encrypted before storage:
- OAuth access tokens and refresh tokens
- Meta long-lived tokens
- API keys

Encryption uses Fernet symmetric encryption with separate keys per auth type.

### Webhook Signature Verification

Meta webhooks are verified using HMAC-SHA256:
- Signature is in `X-Hub-Signature-256` header
- Computed using app secret and request body
- Constant-time comparison prevents timing attacks

### HTTPS Required

All authentication URLs must use HTTPS:
- OAuth authorization and token URLs
- Meta business verification URLs
- API key validation endpoints

Non-HTTPS URLs are rejected with `400 Bad Request`.

---

## Changelog

### Version 2.0 (Current)
- Added support for Meta Business authentication
- Added support for API Key authentication
- Renamed `oauth_config` to `auth_config`
- Added `auth_type` field to responses
- Added Meta callback endpoint
- Added API key completion endpoint
- Added `requires_redirect` and `requires_api_key` flags

### Version 1.0 (Legacy)
- OAuth 2.0 support only
- Single callback endpoint for all integrations
