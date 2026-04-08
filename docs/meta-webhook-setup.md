# Meta Webhook Setup Guide

This guide explains how to configure Meta webhooks for WhatsApp and Instagram integrations.

## Overview

Meta webhooks enable real-time event notifications from WhatsApp Business API and Instagram. The webhook infrastructure verifies signatures, processes events, and routes them to appropriate handlers.

**Requirements**: 14.1-14.8, 16.8

## Architecture

```
Meta Platform → Webhook Endpoint → Signature Verification → Event Router → Handlers
```

## Configuration

### 1. Environment Variables

Add these to your `.env` file:

```bash
# Meta App Secret (from Meta App Dashboard)
META_APP_SECRET=your_meta_app_secret_here

# Webhook Verification Token (you choose this)
META_WEBHOOK_VERIFY_TOKEN=your_secure_random_token_here

# Encryption Keys (generate using: python -c "from cryptography.fernet import Fernet; print(Fernet.generate_key().decode())")
OAUTH_ENCRYPTION_KEY=your_oauth_encryption_key_here
META_ENCRYPTION_KEY=your_meta_encryption_key_here
API_KEY_ENCRYPTION_KEY=your_api_key_encryption_key_here
```

### 2. Generate Encryption Keys

```bash
# Generate encryption keys
python -c "from cryptography.fernet import Fernet; print('OAUTH_ENCRYPTION_KEY=' + Fernet.generate_key().decode())"
python -c "from cryptography.fernet import Fernet; print('META_ENCRYPTION_KEY=' + Fernet.generate_key().decode())"
python -c "from cryptography.fernet import Fernet; print('API_KEY_ENCRYPTION_KEY=' + Fernet.generate_key().decode())"
```

### 3. Meta App Dashboard Configuration

1. Go to [Meta for Developers](https://developers.facebook.com/)
2. Select your app
3. Navigate to **Webhooks** in the left sidebar
4. Click **Add Subscription** for WhatsApp or Instagram
5. Configure webhook:
   - **Callback URL**: `https://yourdomain.com/api/v1/automation/webhooks/meta/`
   - **Verify Token**: Use the same value as `META_WEBHOOK_VERIFY_TOKEN`
6. Subscribe to events:
   - `messages` - Incoming messages
   - `message_status` - Message delivery status
   - `account_updates` - Account-level changes

## Webhook Endpoints

### GET /api/v1/automation/webhooks/meta/

**Purpose**: Webhook verification during setup

**Query Parameters**:
- `hub.mode`: Should be "subscribe"
- `hub.verify_token`: Your verification token
- `hub.challenge`: Random string from Meta

**Response**: Returns the challenge value if verification succeeds

**Example**:
```
GET /api/v1/automation/webhooks/meta/?hub.mode=subscribe&hub.verify_token=your_token&hub.challenge=1234567890
```

### POST /api/v1/automation/webhooks/meta/

**Purpose**: Receive webhook events from Meta

**Headers**:
- `X-Hub-Signature-256`: HMAC-SHA256 signature for verification

**Request Body**:
```json
{
  "object": "whatsapp_business_account",
  "entry": [
    {
      "id": "BUSINESS_ID",
      "changes": [
        {
          "field": "messages",
          "value": {
            "messaging_product": "whatsapp",
            "messages": [
              {
                "from": "1234567890",
                "id": "wamid.XXX",
                "timestamp": "1234567890",
                "type": "text",
                "text": {
                  "body": "Hello"
                }
              }
            ]
          }
        }
      ]
    }
  ]
}
```

**Response**: HTTP 200 (must respond within 20 seconds)

## Security

### Signature Verification

All webhook requests are verified using HMAC-SHA256:

1. Meta signs the payload with your app secret
2. Signature is sent in `X-Hub-Signature-256` header (format: `sha256=<signature>`)
3. Server computes expected signature and compares using constant-time comparison
4. Requests with invalid signatures are rejected with HTTP 401

**Implementation**: `apps/automation/utils/webhook_verifier.py`

### Constant-Time Comparison

Uses `hmac.compare_digest()` to prevent timing attacks when comparing signatures.

## Event Types

### Messages (`field: "messages"`)

Incoming messages from users:
- Text messages
- Media messages (images, videos, documents)
- Location messages
- Contact messages

**Handler**: `_handle_message_event()` in `apps/automation/views/webhooks.py`

### Message Status (`field: "message_status"`)

Status updates for sent messages:
- `sent` - Message sent to Meta
- `delivered` - Message delivered to user
- `read` - Message read by user
- `failed` - Message delivery failed

**Handler**: `_handle_message_status_event()`

### Account Updates (`field: "account_updates"`)

Account-level changes:
- Phone number changes
- Permission revocations
- Account status changes

**Handler**: `_handle_account_update_event()`

## Testing

### Local Testing with ngrok

1. Install ngrok: `npm install -g ngrok`
2. Start your Django server: `uv run python manage.py runserver`
3. Expose local server: `ngrok http 8000`
4. Use ngrok URL in Meta webhook configuration: `https://your-ngrok-url.ngrok.io/api/v1/automation/webhooks/meta/`

### Manual Verification Test

```bash
# Test verification endpoint
curl "http://localhost:8000/api/v1/automation/webhooks/meta/?hub.mode=subscribe&hub.verify_token=your_token&hub.challenge=test123"

# Should return: test123
```

### Signature Verification Test

```python
import hmac
import hashlib
import json

payload = json.dumps({"test": "data"})
app_secret = "your_app_secret"

signature = hmac.new(
    key=app_secret.encode('utf-8'),
    msg=payload.encode('utf-8'),
    digestmod=hashlib.sha256
).hexdigest()

print(f"X-Hub-Signature-256: sha256={signature}")
```

## Logging

All webhook events are logged with:
- Timestamp (UTC)
- Event type (`object` field)
- Business ID
- Number of entries

**Log Location**: Django logs (configured in `settings.py`)

**Example Log**:
```
INFO Meta webhook received: timestamp=2024-01-15T10:30:00Z, event_type=whatsapp_business_account, business_id=123456789, entries_count=1
```

## Troubleshooting

### Verification Fails

**Symptom**: Meta shows "Verification failed" during setup

**Solutions**:
1. Check `META_WEBHOOK_VERIFY_TOKEN` matches the token in Meta dashboard
2. Ensure webhook URL is publicly accessible (use ngrok for local testing)
3. Check Django logs for error messages

### Signature Verification Fails

**Symptom**: Webhook requests return HTTP 401

**Solutions**:
1. Verify `META_APP_SECRET` matches your Meta app secret
2. Check that request body is not modified before verification
3. Ensure `X-Hub-Signature-256` header is present

### Events Not Processing

**Symptom**: Webhook returns 200 but events aren't processed

**Solutions**:
1. Check Django logs for processing errors
2. Verify event handlers are implemented
3. Ensure database connections are working

### Timeout Issues

**Symptom**: Meta retries webhook requests

**Solutions**:
1. Ensure processing completes within 20 seconds
2. Move heavy processing to background tasks (Django-Q)
3. Return HTTP 200 immediately, process asynchronously

## Production Checklist

- [ ] `META_APP_SECRET` configured in production environment
- [ ] `META_WEBHOOK_VERIFY_TOKEN` configured and matches Meta dashboard
- [ ] Encryption keys generated and configured
- [ ] Webhook URL uses HTTPS
- [ ] Webhook subscribed to required events in Meta dashboard
- [ ] Signature verification tested
- [ ] Event handlers implemented
- [ ] Logging configured
- [ ] Error monitoring enabled
- [ ] Background task queue configured (Django-Q with Redis)

## References

- [Meta Webhooks Documentation](https://developers.facebook.com/docs/graph-api/webhooks)
- [WhatsApp Business API Webhooks](https://developers.facebook.com/docs/whatsapp/cloud-api/webhooks)
- [Instagram Webhooks](https://developers.facebook.com/docs/instagram-api/webhooks)
- Requirements: 14.1-14.8, 16.8
