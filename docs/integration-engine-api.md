# Scalable Integration Engine - API Documentation

## Overview

The Scalable Integration Engine provides a flexible, production-ready system for integrating third-party platforms with NeuroTwin. It supports multiple authentication strategies (OAuth 2.0, Meta Business API, API Key) and provides queue-based message processing with rate limiting and fault tolerance.

**Base URL**: `/api/v1/`

**Authentication**: All endpoints require JWT authentication via `Authorization: Bearer <token>` header unless otherwise specified.

## Table of Contents

- [Installation Endpoints](#installation-endpoints)
- [Webhook Endpoints](#webhook-endpoints)
- [Integration Management](#integration-management)
- [Conversation & Message Endpoints](#conversation--message-endpoints)
- [Monitoring & Health](#monitoring--health)
- [GDPR Compliance](#gdpr-compliance)
- [Error Responses](#error-responses)
- [Rate Limits](#rate-limits)

---

## Installation Endpoints

### Start Integration Installation

Initiates the installation process for an integration type.

**Endpoint**: `POST /api/v1/integrations/install/`

**Authentication**: Required

**Request Body**:
```json
{
  "integration_type_id": "uuid",
  "redirect_uri": "https://app.neurotwin.com/callback"
}
```

**Response (OAuth/Meta)**:
```json
{
  "session_id": "550e8400-e29b-41d4-a716-446655440000",
  "authorization_url": "https://accounts.google.com/o/oauth2/v2/auth?...",
  "requires_redirect": true,
  "requires_api_key": false,
  "auth_type": "oauth",
  "status": "oauth_pending",
  "message": "Installation started. Please complete authorization."
}
```

**Response (API Key)**:
```json
{
  "session_id": "550e8400-e29b-41d4-a716-446655440000",
  "authorization_url": null,
  "requires_redirect": false,
  "requires_api_key": true,
  "auth_type": "api_key",
  "status": "initiated",
  "message": "Installation started. Please provide your API key."
}
```

**Error Codes**:
- `INTEGRATION_TYPE_NOT_FOUND` (404): Integration type doesn't exist
- `RATE_LIMIT_EXCEEDED` (429): Too many installation attempts
- `VALIDATION_ERROR` (400): Invalid request data

**Rate Limit**: 10 requests per minute per user

---

### OAuth Callback

Handles OAuth 2.0 callback and completes authentication.

**Endpoint**: `GET /api/v1/integrations/oauth/callback/`

**Authentication**: Not required (uses state parameter)

**Query Parameters**:
- `code` (required): Authorization code from OAuth provider
- `state` (required): CSRF protection token
- `session_id` (optional): Installation session ID

**Response**: Redirects to dashboard with success/error message

**API Version**: `GET /api/v1/integrations/oauth/callback/api/`

Returns JSON instead of redirect:
```json
{
  "success": true,
  "message": "Successfully connected to Gmail",
  "integration": {
    "id": "uuid",
    "integration_type": {
      "id": "uuid",
      "name": "Gmail",
      "key": "gmail",
      "auth_type": "oauth"
    },
    "status": "active",
    "health_status": "healthy",
    "token_expires_at": "2026-05-08T12:00:00Z",
    "created_at": "2026-04-08T10:30:00Z"
  }
}
```

**Error Codes**:
- `OAUTH_CALLBACK_MISSING_CODE` (400): Missing authorization code
- `OAUTH_CALLBACK_INVALID_STATE` (400): Invalid or expired state
- `OAUTH_TOKEN_EXCHANGE_FAILED` (400): Failed to exchange code for tokens
- `SESSION_EXPIRED` (400): Installation session expired

---

### Meta Callback

Handles Meta Business API callback and completes authentication.

**Endpoint**: `GET /api/v1/integrations/meta/callback/`

**Authentication**: Not required (uses state parameter)

**Query Parameters**:
- `code` (required): Authorization code from Meta
- `state` (required): CSRF protection token
- `session_id` (optional): Installation session ID

**Response**: Redirects to dashboard with success/error message

**API Version**: `GET /api/v1/integrations/meta/callback/api/`

Returns JSON instead of redirect:
```json
{
  "success": true,
  "message": "Successfully connected to WhatsApp",
  "integration": {
    "id": "uuid",
    "integration_type": {
      "id": "uuid",
      "name": "WhatsApp",
      "key": "whatsapp",
      "auth_type": "meta"
    },
    "status": "active",
    "health_status": "healthy",
    "waba_id": "123456789",
    "phone_number_id": "987654321",
    "business_id": "456789123",
    "token_expires_at": "2026-06-07T10:30:00Z",
    "created_at": "2026-04-08T10:30:00Z"
  }
}
```

**Error Codes**:
- `META_CALLBACK_MISSING_CODE` (400): Missing authorization code
- `META_CALLBACK_INVALID_STATE` (400): Invalid or expired state
- `META_TOKEN_EXCHANGE_FAILED` (400): Failed to exchange code for tokens
- `META_BUSINESS_FETCH_FAILED` (400): Failed to fetch business details
- `SESSION_EXPIRED` (400): Installation session expired

---

### API Key Completion

Validates API key and completes authentication.

**Endpoint**: `POST /api/v1/integrations/api-key/complete/`

**Authentication**: Required

**Request Body**:
```json
{
  "session_id": "550e8400-e29b-41d4-a716-446655440000",
  "api_key": "sk_live_abc123xyz789"
}
```

**Response**:
```json
{
  "success": true,
  "message": "Successfully connected to Custom API",
  "integration": {
    "id": "uuid",
    "integration_type": {
      "id": "uuid",
      "name": "Custom API",
      "key": "custom-api",
      "auth_type": "api_key"
    },
    "status": "active",
    "health_status": "healthy",
    "created_at": "2026-04-08T10:30:00Z"
  },
  "integration_id": "uuid"
}
```

**Error Codes**:
- `API_KEY_MISSING_SESSION` (400): Missing session_id
- `API_KEY_INVALID` (400): API key validation failed
- `API_KEY_SESSION_EXPIRED` (400): Installation session expired
- `SESSION_NOT_FOUND` (404): Session doesn't exist

**Rate Limit**: 5 requests per minute per user

---

## Webhook Endpoints

### Meta Webhook

Receives webhook events from Meta platforms (WhatsApp, Instagram).

**Endpoint**: `POST /api/v1/webhooks/meta/`

**Authentication**: Signature verification (X-Hub-Signature-256 header)

**Headers**:
- `X-Hub-Signature-256`: HMAC SHA256 signature of payload

**Request Body** (example - incoming message):
```json
{
  "object": "whatsapp_business_account",
  "entry": [{
    "id": "WABA_ID",
    "changes": [{
      "value": {
        "messaging_product": "whatsapp",
        "metadata": {
          "display_phone_number": "+1234567890",
          "phone_number_id": "PHONE_NUMBER_ID"
        },
        "messages": [{
          "from": "+9876543210",
          "id": "wamid.xxx",
          "timestamp": "1712577000",
          "text": {
            "body": "Hello!"
          },
          "type": "text"
        }]
      },
      "field": "messages"
    }]
  }]
}
```

**Response**:
```json
{
  "status": "received"
}
```

**Status Code**: 200 (must respond within 5 seconds)

**Error Codes**:
- `WEBHOOK_SIGNATURE_INVALID` (401): Invalid signature
- `WEBHOOK_INTEGRATION_NOT_FOUND` (404): No integration found for WABA ID

**Rate Limit**: 1000 requests per minute (global)

---

### Meta Webhook Verification

Handles Meta webhook verification challenge.

**Endpoint**: `GET /api/v1/webhooks/meta/`

**Authentication**: Verify token validation

**Query Parameters**:
- `hub.mode`: Should be "subscribe"
- `hub.verify_token`: Verification token (must match META_WEBHOOK_VERIFY_TOKEN)
- `hub.challenge`: Challenge string to echo back

**Response**: Returns the challenge string

**Example**:
```
GET /api/v1/webhooks/meta/?hub.mode=subscribe&hub.verify_token=my_token&hub.challenge=1234567890
```

Response:
```
1234567890
```

**Error Codes**:
- `WEBHOOK_VERIFICATION_FAILED` (403): Invalid verify token

---

## Integration Management

### List Integrations

Retrieves all integrations for the authenticated user.

**Endpoint**: `GET /api/v1/integrations/`

**Authentication**: Required

**Query Parameters**:
- `status` (optional): Filter by status (active, disconnected, expired, revoked)
- `auth_type` (optional): Filter by auth type (oauth, meta, api_key)
- `page` (optional): Page number (default: 1)
- `page_size` (optional): Items per page (default: 20, max: 100)

**Response**:
```json
{
  "count": 5,
  "next": "https://api.neurotwin.com/api/v1/integrations/?page=2",
  "previous": null,
  "results": [
    {
      "id": "uuid",
      "integration_type": {
        "id": "uuid",
        "name": "WhatsApp",
        "key": "whatsapp",
        "icon": "https://...",
        "auth_type": "meta",
        "category": "messaging"
      },
      "status": "active",
      "health_status": "healthy",
      "token_expires_at": "2026-06-07T10:30:00Z",
      "last_successful_sync_at": "2026-04-08T09:00:00Z",
      "consecutive_failures": 0,
      "created_at": "2026-03-01T08:00:00Z",
      "updated_at": "2026-04-08T09:00:00Z"
    }
  ]
}
```

**Rate Limit**: 60 requests per minute per user

---

### Get Integration Details

Retrieves detailed information about a specific integration.

**Endpoint**: `GET /api/v1/integrations/{id}/`

**Authentication**: Required

**Response**:
```json
{
  "id": "uuid",
  "integration_type": {
    "id": "uuid",
    "name": "WhatsApp",
    "key": "whatsapp",
    "icon": "https://...",
    "description": "Connect your WhatsApp Business account",
    "auth_type": "meta",
    "category": "messaging"
  },
  "status": "active",
  "health_status": "healthy",
  "waba_id": "123456789",
  "phone_number_id": "987654321",
  "business_id": "456789123",
  "token_expires_at": "2026-06-07T10:30:00Z",
  "last_successful_sync_at": "2026-04-08T09:00:00Z",
  "consecutive_failures": 0,
  "user_config": {},
  "created_at": "2026-03-01T08:00:00Z",
  "updated_at": "2026-04-08T09:00:00Z"
}
```

**Error Codes**:
- `INTEGRATION_NOT_FOUND` (404): Integration doesn't exist
- `PERMISSION_DENIED` (403): User doesn't own this integration

**Rate Limit**: 60 requests per minute per user

---

### Delete Integration

Uninstalls an integration and revokes credentials.

**Endpoint**: `DELETE /api/v1/integrations/{id}/`

**Authentication**: Required

**Response**:
```json
{
  "success": true,
  "message": "Integration deleted successfully",
  "revocation_success": true
}
```

**Behavior**:
1. Attempts to revoke credentials with provider
2. Deletes integration (cascade deletes conversations, messages, webhooks)
3. Logs deletion for audit
4. Continues deletion even if revocation fails

**Error Codes**:
- `INTEGRATION_NOT_FOUND` (404): Integration doesn't exist
- `PERMISSION_DENIED` (403): User doesn't own this integration

**Rate Limit**: 10 requests per minute per user

---

## Conversation & Message Endpoints

### List Conversations

Retrieves conversations for a specific integration.

**Endpoint**: `GET /api/v1/integrations/{id}/conversations/`

**Authentication**: Required

**Query Parameters**:
- `status` (optional): Filter by status (active, archived)
- `page` (optional): Page number (default: 1)
- `page_size` (optional): Items per page (default: 20, max: 100)

**Response**:
```json
{
  "count": 15,
  "next": "https://api.neurotwin.com/api/v1/integrations/{id}/conversations/?page=2",
  "previous": null,
  "results": [
    {
      "id": "uuid",
      "external_contact_id": "+9876543210",
      "external_contact_name": "John Doe",
      "status": "active",
      "last_message_at": "2026-04-08T10:25:00Z",
      "unread_count": 2,
      "created_at": "2026-03-15T14:20:00Z"
    }
  ]
}
```

**Error Codes**:
- `INTEGRATION_NOT_FOUND` (404): Integration doesn't exist
- `PERMISSION_DENIED` (403): User doesn't own this integration

**Rate Limit**: 60 requests per minute per user

---

### List Messages

Retrieves messages for a specific conversation.

**Endpoint**: `GET /api/v1/conversations/{id}/messages/`

**Authentication**: Required

**Query Parameters**:
- `direction` (optional): Filter by direction (inbound, outbound)
- `status` (optional): Filter by status (pending, sent, delivered, read, failed)
- `page` (optional): Page number (default: 1)
- `page_size` (optional): Items per page (default: 50, max: 100)

**Response**:
```json
{
  "count": 127,
  "next": "https://api.neurotwin.com/api/v1/conversations/{id}/messages/?page=2",
  "previous": null,
  "results": [
    {
      "id": "uuid",
      "direction": "inbound",
      "content": "Hello! How can I help you?",
      "status": "received",
      "external_message_id": "wamid.xxx",
      "retry_count": 0,
      "metadata": {},
      "created_at": "2026-04-08T10:25:00Z"
    },
    {
      "id": "uuid",
      "direction": "outbound",
      "content": "Thanks for reaching out!",
      "status": "sent",
      "external_message_id": "wamid.yyy",
      "retry_count": 0,
      "metadata": {},
      "created_at": "2026-04-08T10:26:00Z"
    }
  ]
}
```

**Error Codes**:
- `CONVERSATION_NOT_FOUND` (404): Conversation doesn't exist
- `PERMISSION_DENIED` (403): User doesn't own this conversation

**Rate Limit**: 60 requests per minute per user

---

### Send Message

Sends a message through an integration.

**Endpoint**: `POST /api/v1/conversations/{id}/messages/`

**Authentication**: Required

**Request Body**:
```json
{
  "content": "Hello! This is a test message.",
  "metadata": {
    "priority": "high",
    "tags": ["customer-support"]
  }
}
```

**Response**:
```json
{
  "id": "uuid",
  "direction": "outbound",
  "content": "Hello! This is a test message.",
  "status": "pending",
  "external_message_id": null,
  "retry_count": 0,
  "metadata": {
    "priority": "high",
    "tags": ["customer-support"]
  },
  "created_at": "2026-04-08T10:30:00Z"
}
```

**Behavior**:
1. Validates user owns the integration
2. Checks rate limit
3. Creates message with status='pending'
4. Enqueues async task for delivery
5. Returns immediately (message sent asynchronously)

**Error Codes**:
- `CONVERSATION_NOT_FOUND` (404): Conversation doesn't exist
- `PERMISSION_DENIED` (403): User doesn't own this conversation
- `RATE_LIMIT_EXCEEDED` (429): Rate limit exceeded
- `INTEGRATION_DISCONNECTED` (400): Integration is disconnected

**Rate Limit**: 20 messages per minute per integration

---

## Monitoring & Health

### Integration Health

Retrieves health metrics for a specific integration.

**Endpoint**: `GET /api/v1/integrations/{id}/health/`

**Authentication**: Required

**Response**:
```json
{
  "integration_id": "uuid",
  "health_status": "healthy",
  "last_successful_sync_at": "2026-04-08T09:00:00Z",
  "consecutive_failures": 0,
  "recent_error_count": 0,
  "rate_limit_status": {
    "limit": 20,
    "current": 5,
    "remaining": 15,
    "reset_at": 1712577600.0
  },
  "token_expires_at": "2026-06-07T10:30:00Z",
  "token_expires_in_hours": 1416
}
```

**Health Status Values**:
- `healthy`: All operations successful
- `degraded`: 3-9 consecutive failures
- `disconnected`: 10+ consecutive failures

**Error Codes**:
- `INTEGRATION_NOT_FOUND` (404): Integration doesn't exist
- `PERMISSION_DENIED` (403): User doesn't own this integration

**Rate Limit**: 60 requests per minute per user

---

### System Health Check

Checks overall system health (database, Redis, Celery).

**Endpoint**: `GET /api/v1/health/`

**Authentication**: Not required

**Response**:
```json
{
  "status": "healthy",
  "timestamp": "2026-04-08T10:30:00Z",
  "components": {
    "database": {
      "status": "healthy",
      "response_time_ms": 5
    },
    "redis": {
      "status": "healthy",
      "response_time_ms": 2
    },
    "celery": {
      "status": "healthy",
      "active_workers": 4,
      "queued_tasks": 15
    }
  }
}
```

**Status Values**:
- `healthy`: All components operational
- `degraded`: Some components slow or partially unavailable
- `unhealthy`: Critical components unavailable

**Rate Limit**: 10 requests per minute per IP

---

### Task Monitoring (Admin)

Retrieves Celery task execution statistics.

**Endpoint**: `GET /api/v1/admin/tasks/stats/`

**Authentication**: Required (admin only)

**Query Parameters**:
- `period` (optional): Time period (hour, day, week) (default: hour)
- `task_name` (optional): Filter by task name

**Response**:
```json
{
  "period": "hour",
  "timestamp": "2026-04-08T10:30:00Z",
  "tasks": [
    {
      "task_name": "process_incoming_message",
      "total_tasks": 1250,
      "successful_tasks": 1245,
      "failed_tasks": 5,
      "average_duration_ms": 125,
      "success_rate": 99.6
    },
    {
      "task_name": "send_outgoing_message",
      "total_tasks": 980,
      "successful_tasks": 975,
      "failed_tasks": 5,
      "average_duration_ms": 450,
      "success_rate": 99.5
    }
  ]
}
```

**Error Codes**:
- `PERMISSION_DENIED` (403): User is not admin

**Rate Limit**: 30 requests per minute per user

---

## GDPR Compliance

### Export User Data

Exports all integration data for the authenticated user.

**Endpoint**: `GET /api/v1/integrations/export/`

**Authentication**: Required

**Response**:
```json
{
  "success": true,
  "data": {
    "integrations": [...],
    "conversations": [...],
    "messages": [...],
    "webhook_events": [...],
    "export_metadata": {
      "user_id": 123,
      "export_timestamp": "2026-04-08T12:00:00Z",
      "total_integrations": 3,
      "total_conversations": 15,
      "total_messages": 487,
      "total_webhook_events": 523
    }
  }
}
```

**Notes**:
- Encrypted credentials are excluded for security
- All timestamps in ISO 8601 format
- Complete data export for GDPR compliance

**Rate Limit**: 5 requests per hour per user

---

### Delete All User Data

Deletes all integration data for the authenticated user.

**Endpoint**: `DELETE /api/v1/integrations/delete-all/`

**Authentication**: Required

**Response**:
```json
{
  "success": true,
  "data": {
    "message": "All integration data has been deleted",
    "deleted_integrations": 3,
    "deleted_conversations": 15,
    "deleted_messages": 487,
    "deleted_webhook_events": 523,
    "revocation_results": [
      {
        "integration_id": "uuid",
        "integration_type": "WhatsApp",
        "revocation_success": true
      },
      {
        "integration_id": "uuid",
        "integration_type": "Gmail",
        "revocation_success": true
      }
    ]
  }
}
```

**Behavior**:
1. Retrieves all user integrations
2. Attempts to revoke credentials with each provider
3. Deletes all integrations (cascade deletes all related data)
4. Logs deletion for audit
5. Continues deletion even if revocation fails

**Warning**: This operation is irreversible

**Rate Limit**: 1 request per hour per user

---

## Error Responses

All error responses follow this format:

```json
{
  "success": false,
  "error": "Human-readable error message",
  "error_code": "ERROR_CODE",
  "detail": "Detailed error information",
  "retry": true
}
```

### Common Error Codes

| Code | HTTP Status | Description | Retry |
|------|-------------|-------------|-------|
| `VALIDATION_ERROR` | 400 | Invalid request data | No |
| `AUTHENTICATION_FAILED` | 401 | Invalid or missing authentication | No |
| `PERMISSION_DENIED` | 403 | User lacks permission | No |
| `NOT_FOUND` | 404 | Resource not found | No |
| `RATE_LIMIT_EXCEEDED` | 429 | Too many requests | Yes |
| `INTEGRATION_DISCONNECTED` | 400 | Integration is disconnected | No |
| `SESSION_EXPIRED` | 400 | Installation session expired | No |
| `WEBHOOK_SIGNATURE_INVALID` | 401 | Invalid webhook signature | No |
| `OAUTH_TOKEN_EXCHANGE_FAILED` | 400 | OAuth token exchange failed | Yes |
| `META_BUSINESS_FETCH_FAILED` | 400 | Failed to fetch Meta business details | Yes |
| `API_KEY_INVALID` | 400 | API key validation failed | No |
| `INTERNAL_SERVER_ERROR` | 500 | Server error | Yes |

---

## Rate Limits

Rate limits are enforced per user and per endpoint:

| Endpoint Category | Limit | Window |
|-------------------|-------|--------|
| Installation | 10 requests | 1 minute |
| API Key Completion | 5 requests | 1 minute |
| Integration Management | 60 requests | 1 minute |
| Conversations & Messages | 60 requests | 1 minute |
| Message Sending | 20 messages | 1 minute per integration |
| Webhooks (global) | 1000 requests | 1 minute |
| Health Check | 10 requests | 1 minute per IP |
| Data Export | 5 requests | 1 hour |
| Data Deletion | 1 request | 1 hour |

**Rate Limit Headers**:
```
X-RateLimit-Limit: 60
X-RateLimit-Remaining: 45
X-RateLimit-Reset: 1712577600
```

**Rate Limit Exceeded Response**:
```json
{
  "success": false,
  "error": "Rate limit exceeded. Please try again in 30 seconds.",
  "error_code": "RATE_LIMIT_EXCEEDED",
  "retry_after": 30
}
```

---

## OpenAPI Schema

The complete OpenAPI 3.0 schema is available at:

**Endpoint**: `GET /api/v1/schema/`

**Format**: JSON or YAML

**Interactive Documentation**: Available at `/api/v1/docs/` (Swagger UI)

---

## Changelog

### Version 1.0.0 (2026-04-08)
- Initial release
- OAuth 2.0, Meta Business API, and API Key authentication
- Message processing with rate limiting
- Webhook support for Meta platforms
- GDPR compliance endpoints
- Health monitoring and task statistics

---

## Support

For API support, contact: api-support@neurotwin.com

For webhook issues, see: [Troubleshooting Guide](./integration-engine-troubleshooting.md)
