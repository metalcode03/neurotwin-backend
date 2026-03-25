# OAuth Flow End-to-End Testing Guide

This guide provides instructions for testing the complete OAuth installation flow with real OAuth providers.

**Task 19 Checkpoint: Ensure OAuth flow works end-to-end**

## Prerequisites

1. Backend server running locally or on staging
2. Frontend application running and accessible
3. Test OAuth applications configured with providers
4. Environment variables properly set

## Test Providers

### Gmail (Google OAuth)

#### Setup
1. Go to [Google Cloud Console](https://console.cloud.google.com/)
2. Create a new project or select existing
3. Enable Gmail API
4. Go to "Credentials" → "Create Credentials" → "OAuth 2.0 Client ID"
5. Configure OAuth consent screen
6. Add authorized redirect URI: `http://localhost:8000/api/v1/integrations/oauth/callback/`
7. Note the Client ID and Client Secret

#### Configuration
Add to Django admin or database:
```python
IntegrationType.objects.create(
    type='gmail',
    name='Gmail',
    description='Connect your Gmail account',
    brief_description='Email integration',
    category='communication',
    oauth_config={
        'client_id': 'YOUR_GOOGLE_CLIENT_ID',
        'client_secret_encrypted': '<encrypted_secret>',
        'authorization_url': 'https://accounts.google.com/o/oauth2/v2/auth',
        'token_url': 'https://oauth2.googleapis.com/token',
        'scopes': [
            'https://www.googleapis.com/auth/gmail.readonly',
            'https://www.googleapis.com/auth/gmail.send'
        ]
    },
    is_active=True
)
```

### Slack

#### Setup
1. Go to [Slack API](https://api.slack.com/apps)
2. Click "Create New App" → "From scratch"
3. Name your app and select workspace
4. Go to "OAuth & Permissions"
5. Add redirect URL: `http://localhost:8000/api/v1/integrations/oauth/callback/`
6. Add OAuth scopes (e.g., `chat:write`, `channels:read`)
7. Note the Client ID and Client Secret

#### Configuration
```python
IntegrationType.objects.create(
    type='slack',
    name='Slack',
    description='Connect your Slack workspace',
    brief_description='Team communication',
    category='communication',
    oauth_config={
        'client_id': 'YOUR_SLACK_CLIENT_ID',
        'client_secret_encrypted': '<encrypted_secret>',
        'authorization_url': 'https://slack.com/oauth/v2/authorize',
        'token_url': 'https://slack.com/api/oauth.v2.access',
        'scopes': ['chat:write', 'channels:read']
    },
    is_active=True
)
```

## Test Scenarios

### Scenario 1: Successful Installation Flow

**Objective**: Verify complete installation works end-to-end

**Steps**:
1. Log in to NeuroTwin frontend
2. Navigate to `/dashboard/apps` (App Marketplace)
3. Find Gmail or Slack integration card
4. Click "Install" button
5. Observe Phase 1 progress bar (Downloading)
6. Observe automatic transition to Phase 2 (Setting Up)
7. Browser redirects to OAuth provider (Google/Slack)
8. Log in to provider if needed
9. Review and approve permissions
10. Browser redirects back to NeuroTwin
11. Observe Phase 2 completion
12. Verify success message displayed

**Expected Results**:
- ✅ Installation session created in database
- ✅ OAuth state parameter generated (64 chars)
- ✅ Redirect to provider with correct parameters
- ✅ Callback received with authorization code
- ✅ Tokens exchanged successfully
- ✅ Tokens encrypted and stored in database
- ✅ Integration record created
- ✅ Automation templates instantiated
- ✅ Integration shows as "Installed" in marketplace

**Verification Queries**:
```python
# Check installation session
session = InstallationSession.objects.filter(
    user=user,
    integration_type__type='gmail'
).latest('created_at')
print(f"Status: {session.status}")
print(f"Progress: {session.progress}%")

# Check integration created
integration = Integration.objects.get(
    user=user,
    integration_type__type='gmail'
)
print(f"Active: {integration.is_active}")
print(f"Has tokens: {bool(integration.oauth_token_encrypted)}")

# Verify token encryption
decrypted = TokenEncryption.decrypt(integration.oauth_token_encrypted)
print(f"Token decrypts successfully: {len(decrypted) > 0}")
```

### Scenario 2: OAuth State Validation (CSRF Protection)

**Objective**: Verify OAuth state parameter prevents CSRF attacks

**Steps**:
1. Start installation flow
2. Note the OAuth state parameter in the URL
3. Manually modify the state parameter in callback URL
4. Attempt to complete the flow

**Expected Results**:
- ✅ Installation fails with "Invalid OAuth state" error
- ✅ Session marked as FAILED
- ✅ Error message stored in session
- ✅ No Integration record created
- ✅ No tokens stored

**Manual Test**:
```bash
# Start installation and capture state
# Then manually call callback with wrong state:
curl "http://localhost:8000/api/v1/integrations/oauth/callback/?code=test_code&state=wrong_state&session_id=<session_id>"
```

### Scenario 3: User Cancels OAuth Authorization

**Objective**: Verify graceful handling when user denies permission

**Steps**:
1. Start installation flow
2. Redirect to OAuth provider
3. Click "Cancel" or "Deny" on permission screen
4. Observe error handling

**Expected Results**:
- ✅ Callback receives error parameter
- ✅ Installation session marked as FAILED
- ✅ User-friendly error message displayed
- ✅ "Retry Installation" button available
- ✅ No Integration record created

### Scenario 4: Token Exchange Failure

**Objective**: Verify error handling when token exchange fails

**Steps**:
1. Use expired or invalid authorization code
2. Attempt to complete OAuth flow

**Expected Results**:
- ✅ Token exchange returns 400/401 error
- ✅ Error logged with details
- ✅ Session marked as FAILED
- ✅ Error message stored
- ✅ Retry option available

### Scenario 5: Installation Retry Logic

**Objective**: Verify retry mechanism works correctly

**Steps**:
1. Cause installation to fail (cancel OAuth)
2. Click "Retry Installation" button
3. Complete OAuth flow successfully

**Expected Results**:
- ✅ New installation session created
- ✅ New OAuth state generated
- ✅ Retry count tracked
- ✅ Second attempt succeeds
- ✅ Integration created successfully

### Scenario 6: Rate Limiting

**Objective**: Verify rate limiting prevents abuse

**Steps**:
1. Attempt to install same integration 11 times within 1 hour
2. Observe rate limit enforcement

**Expected Results**:
- ✅ First 10 installations succeed
- ✅ 11th installation returns 429 Too Many Requests
- ✅ Retry-After header included
- ✅ User-friendly error message
- ✅ Rate limit resets after 1 hour

**Test Script**:
```python
from django.test import Client
from django.contrib.auth import get_user_model

client = Client()
user = get_user_model().objects.get(email='test@example.com')
client.force_login(user)

# Attempt 11 installations
for i in range(11):
    response = client.post('/api/v1/integrations/install/', {
        'integration_type_id': integration_type.id
    })
    print(f"Attempt {i+1}: {response.status_code}")
```

### Scenario 7: Token Encryption Verification

**Objective**: Verify tokens are encrypted at rest

**Steps**:
1. Complete successful installation
2. Query database directly
3. Inspect token fields

**Expected Results**:
- ✅ `oauth_token_encrypted` is binary data
- ✅ Token is NOT plaintext in database
- ✅ Decryption produces original token
- ✅ Different encryptions of same token produce different ciphertext

**Verification**:
```python
integration = Integration.objects.get(user=user, integration_type__type='gmail')

# Check encrypted field
print(f"Encrypted token (first 50 bytes): {integration.oauth_token_encrypted[:50]}")
print(f"Is binary: {isinstance(integration.oauth_token_encrypted, bytes)}")

# Verify decryption
decrypted = TokenEncryption.decrypt(integration.oauth_token_encrypted)
print(f"Decrypted successfully: {len(decrypted) > 0}")
print(f"Token is NOT plaintext: {'test' not in str(integration.oauth_token_encrypted)}")
```

### Scenario 8: Multiple Users Installing Same Integration

**Objective**: Verify user isolation and independent installations

**Steps**:
1. User A installs Gmail
2. User B installs Gmail
3. Verify both have independent Integration records
4. Verify tokens are different

**Expected Results**:
- ✅ Two separate Integration records created
- ✅ Each has different encrypted tokens
- ✅ Each user sees only their own installation
- ✅ Uninstalling one doesn't affect the other

### Scenario 9: Installation Progress Polling

**Objective**: Verify real-time progress updates work

**Steps**:
1. Start installation
2. Poll progress endpoint every 500ms
3. Observe status transitions

**Expected Results**:
- ✅ Initial status: DOWNLOADING
- ✅ Progress increases from 0 to 100
- ✅ Status changes to OAUTH_SETUP
- ✅ After OAuth: status changes to COMPLETED
- ✅ Progress reaches 100%

**Test Script**:
```javascript
// Frontend polling simulation
async function pollProgress(sessionId) {
  const maxAttempts = 20;
  for (let i = 0; i < maxAttempts; i++) {
    const response = await fetch(
      `/api/v1/integrations/install/${sessionId}/progress/`
    );
    const data = await response.json();
    
    console.log(`Status: ${data.status}, Progress: ${data.progress}%`);
    
    if (data.status === 'completed' || data.status === 'failed') {
      break;
    }
    
    await new Promise(resolve => setTimeout(resolve, 500));
  }
}
```

### Scenario 10: Uninstallation

**Objective**: Verify integration can be uninstalled cleanly

**Steps**:
1. Install integration successfully
2. Navigate to installed integrations
3. Click "Uninstall" button
4. Confirm uninstallation

**Expected Results**:
- ✅ Integration record deleted
- ✅ Encrypted tokens removed
- ✅ Dependent workflows disabled
- ✅ Uninstallation logged in audit log
- ✅ Integration no longer shows as installed

## Automated Test Execution

Run the automated test suite:

```bash
# Run all OAuth flow tests
uv run python manage.py test apps.automation.tests.test_oauth_flow_e2e

# Run with verbose output
uv run python manage.py test apps.automation.tests.test_oauth_flow_e2e --verbosity=2

# Run specific test
uv run python manage.py test apps.automation.tests.test_oauth_flow_e2e.OAuthFlowEndToEndTest.test_complete_installation_flow_success
```

## Checklist

Use this checklist to verify all aspects of the OAuth flow:

### Installation Flow
- [ ] Installation session created with DOWNLOADING status
- [ ] OAuth state generated (64 character hex string)
- [ ] OAuth URL built correctly with all parameters
- [ ] Session status transitions to OAUTH_SETUP
- [ ] Redirect to OAuth provider works
- [ ] OAuth provider displays correct app name and permissions
- [ ] User can approve permissions
- [ ] Callback URL receives authorization code
- [ ] OAuth state validated correctly
- [ ] Token exchange succeeds
- [ ] Tokens encrypted before storage
- [ ] Integration record created
- [ ] Session status transitions to COMPLETED
- [ ] Progress reaches 100%
- [ ] Success message displayed to user

### Token Security
- [ ] Tokens encrypted using Fernet
- [ ] Tokens stored as binary data
- [ ] Tokens NOT visible in plaintext in database
- [ ] Decryption produces original token
- [ ] Encryption key loaded from environment variable
- [ ] Different encryptions produce different ciphertext

### Error Handling
- [ ] Invalid OAuth state rejected (CSRF protection)
- [ ] User cancellation handled gracefully
- [ ] Token exchange errors caught and logged
- [ ] Network errors handled with retry option
- [ ] Error messages user-friendly
- [ ] Failed sessions marked as FAILED
- [ ] Error details stored in session

### Rate Limiting
- [ ] Rate limit enforced (10 installations/hour)
- [ ] 429 status code returned when limit exceeded
- [ ] Retry-After header included
- [ ] Rate limit resets after time period
- [ ] Rate limit per user (not global)

### Multi-User Isolation
- [ ] Multiple users can install same integration
- [ ] Each user has independent Integration record
- [ ] Tokens isolated per user
- [ ] Users see only their own installations
- [ ] Uninstalling doesn't affect other users

### Uninstallation
- [ ] Integration record deleted
- [ ] Encrypted tokens removed
- [ ] Dependent workflows disabled
- [ ] Uninstallation logged
- [ ] Confirmation required if workflows depend on integration

## Troubleshooting

### Issue: OAuth redirect fails
**Solution**: Verify redirect URI matches exactly in OAuth app configuration

### Issue: Token exchange returns 400
**Solution**: Check authorization code hasn't expired (usually 10 minutes)

### Issue: Encryption key error
**Solution**: Ensure `TOKEN_ENCRYPTION_KEY` environment variable is set

### Issue: Rate limit not working
**Solution**: Check Redis connection and cache configuration

### Issue: State validation fails
**Solution**: Verify session hasn't expired (10 minute timeout)

## Success Criteria

The OAuth flow is considered working end-to-end when:

1. ✅ All automated tests pass
2. ✅ Manual testing with Gmail succeeds
3. ✅ Manual testing with Slack succeeds
4. ✅ Token encryption verified
5. ✅ Error handling tested and working
6. ✅ Rate limiting enforced
7. ✅ CSRF protection validated
8. ✅ Multi-user isolation confirmed
9. ✅ No security vulnerabilities found
10. ✅ Performance acceptable (< 2 seconds total)

## Next Steps

After completing this checkpoint:
1. Document any issues found
2. Fix critical bugs before proceeding
3. Update error messages if needed
4. Proceed to Phase 4: Frontend implementation
