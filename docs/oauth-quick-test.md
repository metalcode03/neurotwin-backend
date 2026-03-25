# OAuth Flow Quick Test Guide

Quick commands to test the OAuth flow implementation.

## Run Automated Tests

```bash
# Test token encryption (fastest)
uv run python manage.py test apps.automation.tests.test_oauth_flow_e2e.TokenEncryptionTest

# Test OAuth client utilities
uv run python manage.py test apps.automation.tests.test_oauth_flow_e2e.OAuthClientTest

# Test complete OAuth flow (requires mocking)
uv run python manage.py test apps.automation.tests.test_oauth_flow_e2e.OAuthFlowEndToEndTest

# Run all OAuth tests
uv run python manage.py test apps.automation.tests.test_oauth_flow_e2e
```

## Use Testing Helper Script

```bash
# Test encryption works
uv run python scripts/test_oauth_flow.py test-encryption

# Create test installation session
uv run python scripts/test_oauth_flow.py create-session --user test@example.com --type gmail

# Generate OAuth URL for session
uv run python scripts/test_oauth_flow.py generate-oauth-url --session <session-id>

# List user's installations
uv run python scripts/test_oauth_flow.py list-installations --user test@example.com

# List installation sessions
uv run python scripts/test_oauth_flow.py list-sessions --user test@example.com

# Verify token encryption in database
uv run python scripts/test_oauth_flow.py verify-encryption --user test@example.com --type gmail

# Clean up test data
uv run python scripts/test_oauth_flow.py cleanup --user test@example.com
```

## Manual Testing with Real OAuth Providers

### 1. Set up Gmail OAuth App
1. Go to [Google Cloud Console](https://console.cloud.google.com/)
2. Create OAuth 2.0 credentials
3. Add redirect URI: `http://localhost:8000/api/v1/integrations/oauth/callback/`
4. Add to Django admin or database

### 2. Test Installation Flow
1. Start Django server: `uv run python manage.py runserver`
2. Navigate to marketplace (when frontend ready)
3. Click "Install" on Gmail
4. Complete OAuth flow
5. Verify integration created

### 3. Verify Token Encryption
```python
from apps.automation.models import Integration
from apps.automation.utils.encryption import TokenEncryption

integration = Integration.objects.get(user__email='test@example.com')
print(f"Encrypted: {integration.oauth_token_encrypted[:50]}")

decrypted = TokenEncryption.decrypt(integration.oauth_token_encrypted)
print(f"Decrypts successfully: {len(decrypted) > 0}")
```

## Check Implementation Status

```bash
# Check if all services exist
ls apps/automation/services/

# Check if all utilities exist
ls apps/automation/utils/

# Check if migrations applied
uv run python manage.py showmigrations automation

# Check if models created
uv run python manage.py shell
>>> from apps.automation.models import IntegrationType, InstallationSession
>>> IntegrationType.objects.count()
>>> InstallationSession.objects.count()
```

## Quick Validation Checklist

- [ ] Token encryption tests pass
- [ ] OAuth client tests pass
- [ ] Installation service exists
- [ ] OAuth utilities exist
- [ ] Models created and migrated
- [ ] API endpoints registered
- [ ] Rate limiting configured
- [ ] Caching configured
- [ ] Error logging works

## Environment Variables Required

```bash
# .env file
ENCRYPTION_KEY=<generate-with-fernet>
OAUTH_REDIRECT_URI=http://localhost:8000/api/v1/integrations/oauth/callback/
INSTALLATION_RATE_LIMIT_COUNT=10
INSTALLATION_RATE_LIMIT_PERIOD=3600
```

Generate encryption key:
```python
from cryptography.fernet import Fernet
print(Fernet.generate_key().decode())
```

## Common Issues

### Issue: ENCRYPTION_KEY not set
**Solution**: Add to `.env` file

### Issue: Tests fail with import errors
**Solution**: Run `uv sync` to install dependencies

### Issue: OAuth redirect fails
**Solution**: Verify redirect URI matches in OAuth app config

### Issue: Rate limit not working
**Solution**: Check Redis connection and cache configuration

## Success Indicators

✅ All automated tests pass  
✅ Token encryption/decryption works  
✅ OAuth URLs generate correctly  
✅ Installation sessions created  
✅ Error handling works  
✅ Rate limiting enforced  

## Next Steps

After validation:
1. Test with real OAuth providers
2. Proceed to Phase 4: Frontend implementation
3. Create App Marketplace UI
4. Implement installation progress UI
