# OAuth Setup Guide for NeuroTwin Integrations

This guide provides step-by-step instructions for setting up OAuth applications with real providers (Gmail and Slack) for the NeuroTwin Dynamic App Marketplace.

## Prerequisites

- Admin access to NeuroTwin Django admin panel
- Google Cloud Console account (for Gmail)
- Slack workspace with admin permissions (for Slack)
- NeuroTwin backend running locally or on a server with HTTPS

## Table of Contents

1. [Gmail OAuth Setup](#gmail-oauth-setup)
2. [Slack OAuth Setup](#slack-oauth-setup)
3. [Configuring Integration Types in Django Admin](#configuring-integration-types-in-django-admin)
4. [Testing the Installation Flow](#testing-the-installation-flow)
5. [Troubleshooting](#troubleshooting)

---

## Gmail OAuth Setup

### Step 1: Create a Google Cloud Project

1. Go to [Google Cloud Console](https://console.cloud.google.com/)
2. Click **Select a project** → **New Project**
3. Enter project name: `NeuroTwin Gmail Integration`
4. Click **Create**
5. Wait for project creation to complete

### Step 2: Enable Gmail API

1. In the Google Cloud Console, select your project
2. Navigate to **APIs & Services** → **Library**
3. Search for "Gmail API"
4. Click on **Gmail API**
5. Click **Enable**

### Step 3: Configure OAuth Consent Screen

1. Navigate to **APIs & Services** → **OAuth consent screen**
2. Select **External** user type (or Internal if using Google Workspace)
3. Click **Create**
4. Fill in the required fields:
   - **App name**: `NeuroTwin`
   - **User support email**: Your email
   - **Developer contact information**: Your email
5. Click **Save and Continue**
6. On the **Scopes** page, click **Add or Remove Scopes**
7. Add the following scopes:
   - `https://www.googleapis.com/auth/gmail.readonly` (Read emails)
   - `https://www.googleapis.com/auth/gmail.send` (Send emails)
   - `https://www.googleapis.com/auth/gmail.modify` (Modify emails)
8. Click **Update** → **Save and Continue**
9. On **Test users** page (if External), add test user emails
10. Click **Save and Continue**
11. Review and click **Back to Dashboard**

### Step 4: Create OAuth 2.0 Credentials

1. Navigate to **APIs & Services** → **Credentials**
2. Click **Create Credentials** → **OAuth client ID**
3. Select **Application type**: **Web application**
4. Enter **Name**: `NeuroTwin Gmail OAuth Client`
5. Under **Authorized redirect URIs**, click **Add URI**
6. Add your redirect URI:
   - **Development**: `http://localhost:8000/api/v1/integrations/oauth/callback`
   - **Production**: `https://yourdomain.com/api/v1/integrations/oauth/callback`
7. Click **Create**
8. **IMPORTANT**: Copy and save:
   - **Client ID** (e.g., `123456789-abc.apps.googleusercontent.com`)
   - **Client Secret** (e.g., `GOCSPX-abc123...`)

### Step 5: OAuth Configuration Details for Gmail

Use these values when configuring the IntegrationType in Django admin:

```json
{
  "client_id": "YOUR_CLIENT_ID_FROM_STEP_4",
  "client_secret_encrypted": "WILL_BE_ENCRYPTED_AUTOMATICALLY",
  "authorization_url": "https://accounts.google.com/o/oauth2/v2/auth",
  "token_url": "https://oauth2.googleapis.com/token",
  "revoke_url": "https://oauth2.googleapis.com/revoke",
  "scopes": [
    "https://www.googleapis.com/auth/gmail.readonly",
    "https://www.googleapis.com/auth/gmail.send",
    "https://www.googleapis.com/auth/gmail.modify",
    "https://www.googleapis.com/auth/userinfo.email"
  ]
}
```

---

## Slack OAuth Setup

### Step 1: Create a Slack App

1. Go to [Slack API](https://api.slack.com/apps)
2. Click **Create New App**
3. Select **From scratch**
4. Enter **App Name**: `NeuroTwin`
5. Select your **Development Slack Workspace**
6. Click **Create App**

### Step 2: Configure OAuth & Permissions

1. In your app settings, navigate to **OAuth & Permissions** (left sidebar)
2. Scroll down to **Redirect URLs**
3. Click **Add New Redirect URL**
4. Add your redirect URI:
   - **Development**: `http://localhost:8000/api/v1/integrations/oauth/callback`
   - **Production**: `https://yourdomain.com/api/v1/integrations/oauth/callback`
5. Click **Add** → **Save URLs**

### Step 3: Add OAuth Scopes

1. Still in **OAuth & Permissions**, scroll to **Scopes**
2. Under **Bot Token Scopes**, click **Add an OAuth Scope**
3. Add the following scopes:
   - `channels:read` - View basic information about public channels
   - `channels:history` - View messages in public channels
   - `chat:write` - Send messages as the app
   - `users:read` - View people in the workspace
   - `users:read.email` - View email addresses of people
   - `im:read` - View direct messages
   - `im:write` - Start direct messages
   - `im:history` - View messages in direct messages

### Step 4: Get OAuth Credentials

1. Navigate to **Basic Information** (left sidebar)
2. Scroll to **App Credentials**
3. **IMPORTANT**: Copy and save:
   - **Client ID** (e.g., `123456789.123456789`)
   - **Client Secret** (e.g., `abc123def456...`)
   - **Signing Secret** (optional, for webhook verification)

### Step 5: OAuth Configuration Details for Slack

Use these values when configuring the IntegrationType in Django admin:

```json
{
  "client_id": "YOUR_CLIENT_ID_FROM_STEP_4",
  "client_secret_encrypted": "WILL_BE_ENCRYPTED_AUTOMATICALLY",
  "authorization_url": "https://slack.com/oauth/v2/authorize",
  "token_url": "https://slack.com/api/oauth.v2.access",
  "revoke_url": "https://slack.com/api/auth.revoke",
  "scopes": [
    "channels:read",
    "channels:history",
    "chat:write",
    "users:read",
    "users:read.email",
    "im:read",
    "im:write",
    "im:history"
  ]
}
```

---

## Configuring Integration Types in Django Admin

### Step 1: Access Django Admin

1. Start your Django development server:
   ```bash
   uv run python manage.py runserver
   ```

2. Navigate to: `http://localhost:8000/admin/`

3. Log in with your superuser credentials

### Step 2: Create or Update Gmail Integration Type

1. Navigate to **Automation** → **Integration types**
2. Click **Add integration type** (or edit existing Gmail entry)
3. Fill in the fields:

   **Basic Information:**
   - **Type**: `gmail` (kebab-case, unique identifier)
   - **Name**: `Gmail`
   - **Brief description**: `Connect your Gmail account to automate email workflows`
   - **Description**: `Gmail integration allows NeuroTwin to read, send, and manage your emails. Automate email responses, organize your inbox, and create smart email workflows.`
   - **Category**: `Communication`
   - **Is active**: ✓ (checked)

   **OAuth Configuration:**
   - **Client ID**: Paste from Google Cloud Console (Step 4 of Gmail setup)
   - **Client Secret**: Paste from Google Cloud Console (will be encrypted automatically)
   - **Authorization URL**: `https://accounts.google.com/o/oauth2/v2/auth`
   - **Token URL**: `https://oauth2.googleapis.com/token`
   - **Revoke URL**: `https://oauth2.googleapis.com/revoke`
   - **Scopes**: Enter as comma-separated or JSON array:
     ```
     https://www.googleapis.com/auth/gmail.readonly,https://www.googleapis.com/auth/gmail.send,https://www.googleapis.com/auth/gmail.modify,https://www.googleapis.com/auth/userinfo.email
     ```

   **Default Permissions:**
   ```json
   {
     "read_emails": true,
     "send_emails": true,
     "modify_emails": true
   }
   ```

4. Click **Save**

### Step 3: Create or Update Slack Integration Type

1. Navigate to **Automation** → **Integration types**
2. Click **Add integration type** (or edit existing Slack entry)
3. Fill in the fields:

   **Basic Information:**
   - **Type**: `slack` (kebab-case, unique identifier)
   - **Name**: `Slack`
   - **Brief description**: `Connect your Slack workspace to automate team communications`
   - **Description**: `Slack integration enables NeuroTwin to send messages, read channels, and manage your workspace communications. Create automated workflows for team notifications and responses.`
   - **Category**: `Communication`
   - **Is active**: ✓ (checked)

   **OAuth Configuration:**
   - **Client ID**: Paste from Slack App settings
   - **Client Secret**: Paste from Slack App settings (will be encrypted automatically)
   - **Authorization URL**: `https://slack.com/oauth/v2/authorize`
   - **Token URL**: `https://slack.com/api/oauth.v2.access`
   - **Revoke URL**: `https://slack.com/api/auth.revoke`
   - **Scopes**: Enter as comma-separated or JSON array:
     ```
     channels:read,channels:history,chat:write,users:read,users:read.email,im:read,im:write,im:history
     ```

   **Default Permissions:**
   ```json
   {
     "read_channels": true,
     "send_messages": true,
     "read_dms": true
   }
   ```

4. Click **Save**

---

## Testing the Installation Flow

### Prerequisites for Testing

1. Ensure Django server is running:
   ```bash
   uv run python manage.py runserver
   ```

2. Ensure you have a test user account created

3. Verify OAuth redirect URI matches in:
   - Provider settings (Google/Slack)
   - Django settings (`OAUTH_REDIRECT_URI`)

### Test Gmail Installation

1. **Start Installation** (via API or frontend):
   ```bash
   curl -X POST http://localhost:8000/api/v1/integrations/install/ \
     -H "Authorization: Bearer YOUR_JWT_TOKEN" \
     -H "Content-Type: application/json" \
     -d '{"integration_type_id": "GMAIL_INTEGRATION_TYPE_UUID"}'
   ```

2. **Expected Response**:
   ```json
   {
     "session_id": "uuid-here",
     "oauth_url": "https://accounts.google.com/o/oauth2/v2/auth?client_id=...",
     "status": "downloading"
   }
   ```

3. **Navigate to OAuth URL**: Open the `oauth_url` in a browser

4. **Authorize**: 
   - Select your Google account
   - Review permissions
   - Click **Allow**

5. **Verify Redirect**: You should be redirected to your callback URL

6. **Check Installation Status**:
   ```bash
   curl http://localhost:8000/api/v1/integrations/install/SESSION_ID/progress/ \
     -H "Authorization: Bearer YOUR_JWT_TOKEN"
   ```

7. **Expected Final Status**:
   ```json
   {
     "phase": "completed",
     "progress": 100,
     "message": "Gmail installed successfully!"
   }
   ```

8. **Verify in Database**:
   - Check Django admin → **Integrations**
   - Should see new Integration record for Gmail
   - Tokens should be encrypted (binary data)

### Test Slack Installation

Follow the same steps as Gmail, but use Slack integration type UUID.

**Expected Slack OAuth Flow**:
1. Redirects to Slack authorization page
2. Shows workspace selection (if multiple workspaces)
3. Shows permission scopes
4. User clicks **Allow**
5. Redirects back to callback URL
6. Installation completes

### Test Error Scenarios

1. **User Cancels Authorization**:
   - Start installation
   - Click "Cancel" or "Deny" on OAuth page
   - Verify error handling:
     ```json
     {
       "phase": "failed",
       "error_message": "OAuth error: access_denied",
       "can_retry": true
     }
     ```

2. **Invalid Credentials**:
   - Temporarily change client_secret in admin to invalid value
   - Attempt installation
   - Verify error: "Token exchange failed"

3. **Rate Limiting**:
   - Attempt 11 installations within 1 hour
   - 11th attempt should return HTTP 429

### Verify Token Encryption

1. Access Django shell:
   ```bash
   uv run python manage.py shell
   ```

2. Check token encryption:
   ```python
   from apps.automation.models import Integration
   
   # Get an integration
   integration = Integration.objects.first()
   
   # Check encrypted fields (should be binary)
   print(type(integration.oauth_token_encrypted))  # <class 'memoryview'>
   
   # Check decrypted token (should be string)
   print(type(integration.oauth_token))  # <class 'str'>
   print(len(integration.oauth_token) > 0)  # True
   ```

---

## Troubleshooting

### Common Issues

#### 1. Redirect URI Mismatch

**Error**: `redirect_uri_mismatch` or `invalid_redirect_uri`

**Solution**:
- Verify redirect URI in provider settings matches exactly
- Check for trailing slashes
- Ensure protocol matches (http vs https)
- For development, use `http://localhost:8000/...`
- For production, use `https://yourdomain.com/...`

#### 2. Invalid Client Credentials

**Error**: `invalid_client` or `unauthorized_client`

**Solution**:
- Verify client_id and client_secret are correct
- Check for extra spaces or newlines
- Regenerate credentials if needed
- Ensure OAuth client is enabled in provider console

#### 3. Scope Errors

**Error**: `invalid_scope` or scope-related errors

**Solution**:
- Verify scopes are enabled in provider console
- Check scope format (space-separated for Google, comma for Slack)
- Ensure app has necessary permissions
- For Google: Check OAuth consent screen configuration

#### 4. Token Exchange Fails

**Error**: `Token exchange failed`

**Solution**:
- Check Django logs for detailed error
- Verify token_url is correct
- Ensure network connectivity to provider
- Check for firewall/proxy issues
- Verify authorization code hasn't expired (use within 10 minutes)

#### 5. CSRF/State Validation Fails

**Error**: `OAuth state validation failed`

**Solution**:
- Ensure cookies are enabled
- Check session configuration in Django
- Verify state parameter is being passed correctly
- Check for clock skew between servers

#### 6. Encryption Errors

**Error**: `Encryption failed` or `Decryption failed`

**Solution**:
- Verify `TOKEN_ENCRYPTION_KEY` is set in `.env`
- Key must be 32 bytes, base64-encoded
- Generate new key if needed:
  ```python
  from cryptography.fernet import Fernet
  print(Fernet.generate_key().decode())
  ```

### Debugging Tips

1. **Enable Debug Logging**:
   ```python
   # In settings.py
   LOGGING = {
       'version': 1,
       'handlers': {
           'console': {
               'class': 'logging.StreamHandler',
           },
       },
       'loggers': {
           'apps.automation': {
               'handlers': ['console'],
               'level': 'DEBUG',
           },
       },
   }
   ```

2. **Check Installation Session**:
   ```python
   from apps.automation.models import InstallationSession
   
   session = InstallationSession.objects.get(id='session-uuid')
   print(f"Status: {session.status}")
   print(f"Error: {session.error_message}")
   print(f"Retry count: {session.retry_count}")
   ```

3. **Test OAuth URLs Manually**:
   - Copy authorization URL from API response
   - Open in browser
   - Check for any provider-specific errors
   - Verify redirect works

4. **Verify Database State**:
   ```sql
   -- Check integration types
   SELECT id, type, name, is_active FROM integration_types;
   
   -- Check integrations
   SELECT id, user_id, integration_type_id, is_active FROM integrations;
   
   -- Check installation sessions
   SELECT id, status, error_message, retry_count FROM installation_sessions 
   ORDER BY created_at DESC LIMIT 10;
   ```

### Getting Help

If you encounter issues not covered here:

1. Check Django logs: `tail -f logs/django.log`
2. Check provider documentation:
   - [Google OAuth 2.0](https://developers.google.com/identity/protocols/oauth2)
   - [Slack OAuth](https://api.slack.com/authentication/oauth-v2)
3. Review the implementation:
   - `apps/automation/services/installation.py`
   - `apps/automation/utils/oauth_client.py`
4. Check the spec requirements:
   - `.kiro/specs/dynamic-app-marketplace/requirements.md`
   - `.kiro/specs/dynamic-app-marketplace/design.md`

---

## Security Checklist

Before deploying to production:

- [ ] All OAuth redirect URIs use HTTPS
- [ ] `TOKEN_ENCRYPTION_KEY` is set and secure (32 bytes, random)
- [ ] Client secrets are never logged or exposed in responses
- [ ] Rate limiting is enabled (10 installations/hour)
- [ ] OAuth state validation is working (CSRF protection)
- [ ] Tokens are encrypted at rest in database
- [ ] Token refresh is implemented and tested
- [ ] Token revocation works on uninstall
- [ ] Audit logging is enabled for all installations
- [ ] Error messages don't expose sensitive information

---

## Next Steps

After successful OAuth testing:

1. **Create Automation Templates**: Define pre-configured workflows for Gmail and Slack
2. **Test Template Instantiation**: Verify workflows are created on installation
3. **Test Workflow Execution**: Execute workflows using the installed integrations
4. **Frontend Integration**: Build the App Marketplace UI
5. **User Acceptance Testing**: Test with real users
6. **Production Deployment**: Deploy with production OAuth apps

---

## Appendix: Environment Variables

Add these to your `.env` file:

```bash
# OAuth Configuration
OAUTH_REDIRECT_URI=http://localhost:8000/api/v1/integrations/oauth/callback
FRONTEND_URL=http://localhost:3000

# Token Encryption (generate with: python -c "from cryptography.fernet import Fernet; print(Fernet.generate_key().decode())")
TOKEN_ENCRYPTION_KEY=your-32-byte-base64-encoded-key-here

# Rate Limiting
INSTALLATION_RATE_LIMIT=10/hour
API_RATE_LIMIT=1000/hour

# Cache TTL (seconds)
CACHE_INTEGRATION_TYPES_TTL=300
CACHE_USER_INSTALLATIONS_TTL=60
CACHE_OAUTH_CONFIG_TTL=600

# Session Cleanup
INSTALLATION_SESSION_CLEANUP_HOURS=24
```

Generate encryption key:
```bash
python -c "from cryptography.fernet import Fernet; print(Fernet.generate_key().decode())"
```
