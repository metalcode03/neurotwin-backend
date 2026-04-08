# Multi-Auth Integration System - API Endpoints

This document describes the API endpoints implemented for the multi-auth integration system.

## Overview

The multi-auth integration system supports three authentication types:
- **OAuth 2.0**: Standard OAuth authorization code flow
- **Meta Business**: Meta's embedded signup flow for WhatsApp/Instagram
- **API Key**: Simple API key authentication

## Endpoints

### 1. Start Installation

**Endpoint**: `POST /api/v1/integrations/install/`

**Description**: Initiates the installation process for an integration type.

**Request Body**:
```json
{
  "integration_type_id": "uuid"
}
```

**Response (OAuth/Meta)**:
```json
{
  "session_id": "uuid",
  "authorization_url": "https://...",
  "requires_redirect": true,
  "requires_api_key": false,
  "auth_type": "oauth",
  "status": "oauth_setup",
  "message": "Installation started. Please complete authorization."
}
```

**Response (API Key)**:
```json
{
  "session_id": "uuid",
  "authorization_url": null,
  "requires_redirect": false,
  "requires_api_key": true,
  "auth_type": "api_key",
  "status": "downloading",
  "message": "Installation started. Please provide your API key."
}
```

**Requirements**: 12.1, 12.2, 12.3

---

### 2. Meta Callback

**Endpoint**: `GET /api/v1/integrations/meta/callback/`

**Description**: Handles Meta Business OAuth callback and completes Meta authentication.

**Query Parameters**:
- `code`: Meta authorization code
- `state`: OAuth state for CSRF protection
- `session_id`: Installation session ID

**Response**: Redirects to dashboard with success/error message

**API Version**: `GET /api/v1/integrations/meta/callback/api/`

Returns JSON response instead of redirect:
```json
{
  "success": true,
  "message": "Successfully connected to WhatsApp",
  "integration": {
    "id": "uuid",
    "type": "whatsapp",
    "name": "WhatsApp",
    "meta_business_id": "123456",
    "meta_waba_id": "789012",
    "meta_phone_number_id": "345678"
  }
}
```

**Requirements**: 9.1-9.8

---

### 3. API Key Completion

**Endpoint**: `POST /api/v1/integrations/api-key/complete/`

**Description**: Validates API key and completes API key authentication.

**Request Body**:
```json
{
  "session_id": "uuid",
  "api_key": "secret_key_here"
}
```

**Response**:
```json
{
  "success": true,
  "message": "Successfully connected to Custom API",
  "integration": {
    "id": "uuid",
    "integration_type": {...},
    "is_active": true,
    ...
  },
  "integration_id": "uuid"
}
```

**Error Response**:
```json
{
  "success": false,
  "error": "Invalid API key",
  "error_code": "API_KEY_INVALID",
  "detail": "API key validation failed",
  "retry": true
}
```

**Requirements**: 12.4-12.6

---

### 4. Get Integration Type Details

**Endpoint**: `GET /api/v1/integrations/types/{id}/`

**Description**: Retrieves detailed information about an integration type, including auth_type and required fields.

**Response**:
```json
{
  "id": "uuid",
  "type": "gmail",
  "name": "Gmail",
  "icon": "https://...",
  "description": "Connect your Gmail account...",
  "brief_description": "Email integration",
  "category": "communication",
  "auth_type": "oauth",
  "auth_config": {
    "client_id": "...",
    "authorization_url": "https://...",
    "token_url": "https://...",
    "scopes": ["email", "profile"]
  },
  "oauth_config": {...},  // Backward compatibility
  "default_permissions": {...},
  "is_active": true,
  "created_at": "2026-03-07T...",
  "updated_at": "2026-03-07T...",
  "automation_template_count": 3,
  "required_fields": [
    "client_id",
    "client_secret_encrypted",
    "authorization_url",
    "token_url",
    "scopes"
  ]
}
```

**Requirements**: 12.7

---

## Authentication Flow by Type

### OAuth 2.0 Flow

1. Client calls `POST /api/v1/integrations/install/`
2. Server returns `authorization_url` with `requires_redirect: true`
3. Client redirects user to `authorization_url`
4. User authorizes on provider's site
5. Provider redirects to `GET /api/v1/integrations/oauth/callback/`
6. Server exchanges code for tokens and creates Integration

### Meta Business Flow

1. Client calls `POST /api/v1/integrations/install/`
2. Server returns `authorization_url` with `requires_redirect: true`
3. Client redirects user to Meta Business verification
4. User completes Meta verification
5. Meta redirects to `GET /api/v1/integrations/meta/callback/`
6. Server exchanges code for long-lived token, retrieves business details, and creates Integration

### API Key Flow

1. Client calls `POST /api/v1/integrations/install/`
2. Server returns `requires_api_key: true` with no `authorization_url`
3. Client displays API key input form
4. User enters API key
5. Client calls `POST /api/v1/integrations/api-key/complete/`
6. Server validates API key and creates Integration

---

### 5. Data Export (GDPR)

**Endpoint**: `GET /api/v1/integrations/export/`

**Description**: Exports all user integration data as JSON for GDPR compliance (data portability).

**Authentication**: Required (user must be authenticated)

**Response**:
```json
{
  "success": true,
  "data": {
    "integrations": [
      {
        "id": "uuid",
        "integration_type": {
          "id": "uuid",
          "name": "WhatsApp",
          "key": "whatsapp",
          "auth_type": "meta",
          "category": "messaging"
        },
        "status": "active",
        "health_status": "healthy",
        "token_expires_at": "2026-05-07T12:00:00Z",
        "user_config": {},
        "waba_id": "123456",
        "phone_number_id": "789012",
        "business_id": "345678",
        "last_successful_sync_at": "2026-04-08T10:30:00Z",
        "consecutive_failures": 0,
        "created_at": "2026-03-01T08:00:00Z",
        "updated_at": "2026-04-08T10:30:00Z"
      }
    ],
    "conversations": [
      {
        "id": "uuid",
        "integration_id": "uuid",
        "external_contact_id": "+1234567890",
        "external_contact_name": "John Doe",
        "status": "active",
        "last_message_at": "2026-04-08T10:25:00Z",
        "created_at": "2026-03-15T14:20:00Z",
        "updated_at": "2026-04-08T10:25:00Z"
      }
    ],
    "messages": [
      {
        "id": "uuid",
        "conversation_id": "uuid",
        "direction": "inbound",
        "content": "Hello!",
        "status": "received",
        "external_message_id": "wamid.xxx",
        "retry_count": 0,
        "last_retry_at": null,
        "metadata": {},
        "created_at": "2026-04-08T10:25:00Z",
        "updated_at": "2026-04-08T10:25:00Z"
      }
    ],
    "webhook_events": [
      {
        "id": "uuid",
        "integration_type_id": "uuid",
        "integration_id": "uuid",
        "payload": {...},
        "signature": "sha256=...",
        "status": "processed",
        "error_message": null,
        "processed_at": "2026-04-08T10:25:05Z",
        "created_at": "2026-04-08T10:25:00Z",
        "updated_at": "2026-04-08T10:25:05Z"
      }
    ],
    "export_metadata": {
      "user_id": 123,
      "export_timestamp": "2026-04-08T12:00:00Z",
      "total_integrations": 1,
      "total_conversations": 1,
      "total_messages": 1,
      "total_webhook_events": 1
    }
  }
}
```

**Notes**:
- Encrypted credential fields are excluded for security
- All timestamps are in ISO 8601 format
- Export includes all data associated with user's integrations

**Requirements**: 33.7

---

### 6. Data Deletion (GDPR)

**Endpoint**: `DELETE /api/v1/integrations/delete-all/`

**Description**: Deletes all user integration data for GDPR compliance (right to be forgotten).

**Authentication**: Required (user must be authenticated)

**Response**:
```json
{
  "success": true,
  "data": {
    "message": "All integration data has been deleted",
    "deleted_integrations": 1,
    "deleted_conversations": 5,
    "deleted_messages": 127,
    "deleted_webhook_events": 89,
    "revocation_results": [
      {
        "integration_id": "uuid",
        "integration_type": "WhatsApp",
        "revocation_success": true
      }
    ]
  }
}
```

**Response (No Data)**:
```json
{
  "success": true,
  "data": {
    "message": "No integration data found to delete",
    "deleted_integrations": 0,
    "deleted_conversations": 0,
    "deleted_messages": 0,
    "deleted_webhook_events": 0
  }
}
```

**Behavior**:
1. Retrieves all user integrations
2. Attempts to revoke credentials with each provider
3. Deletes all integrations (cascade deletes conversations, messages, webhooks)
4. Logs deletion for audit trail
5. Continues deletion even if credential revocation fails

**Notes**:
- This operation is irreversible
- Credential revocation is attempted but deletion proceeds even if it fails
- All associated data is permanently deleted via cascade
- Deletion is logged for audit compliance

**Requirements**: 33.7

---

## Error Handling

All endpoints return consistent error responses:

```json
{
  "success": false,
  "error": "Error message",
  "error_code": "ERROR_CODE",
  "detail": "Detailed error information",
  "retry": true  // If retry is allowed
}
```

Common error codes:
- `META_CALLBACK_MISSING_CODE`: Missing authorization code
- `META_CALLBACK_INVALID_STATE`: CSRF check failed
- `API_KEY_MISSING_SESSION`: Missing session_id
- `API_KEY_INVALID`: API key validation failed
- `API_KEY_SESSION_EXPIRED`: Installation session expired

---

## Security Considerations

1. **CSRF Protection**: All OAuth/Meta flows validate state parameter
2. **Session Expiration**: Installation sessions expire after 24 hours
3. **Rate Limiting**: Installation endpoint is rate-limited
4. **Encryption**: All credentials are encrypted before storage
5. **HTTPS Only**: All OAuth/Meta URLs must use HTTPS

---

## Testing

To test the endpoints:

1. **OAuth Flow**: Use a test OAuth provider (e.g., Google)
2. **Meta Flow**: Use Meta's test environment
3. **API Key Flow**: Create a test integration type with API key auth

Example test integration type:
```json
{
  "type": "test-api",
  "name": "Test API",
  "auth_type": "api_key",
  "auth_config": {
    "api_endpoint": "https://api.example.com/validate",
    "authentication_header_name": "X-API-Key"
  }
}
```
