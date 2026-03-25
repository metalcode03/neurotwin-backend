# OAuth Quick Reference Card

Quick reference for OAuth setup and testing with Gmail and Slack.

## 🚀 Quick Start

### 1. Verify Environment Setup
```bash
python scripts/test_oauth_setup.py
```

### 2. Create OAuth Apps

**Gmail**: [Google Cloud Console](https://console.cloud.google.com/)  
**Slack**: [Slack API](https://api.slack.com/apps)

### 3. Configure in Django Admin
```
http://localhost:8000/admin/automation/integrationtypemodel/
```

---

## 📋 Gmail Configuration

### OAuth URLs
```
Authorization: https://accounts.google.com/o/oauth2/v2/auth
Token:         https://oauth2.googleapis.com/token
Revoke:        https://oauth2.googleapis.com/revoke
```

### Scopes (comma-separated)
```
https://www.googleapis.com/auth/gmail.readonly,https://www.googleapis.com/auth/gmail.send,https://www.googleapis.com/auth/gmail.modify,https://www.googleapis.com/auth/userinfo.email
```

### Redirect URI
```
Development: http://localhost:8000/api/v1/integrations/oauth/callback
Production:  https://yourdomain.com/api/v1/integrations/oauth/callback
```

---

## 📋 Slack Configuration

### OAuth URLs
```
Authorization: https://slack.com/oauth/v2/authorize
Token:         https://slack.com/api/oauth.v2.access
Revoke:        https://slack.com/api/auth.revoke
```

### Scopes (comma-separated)
```
channels:read,channels:history,chat:write,users:read,users:read.email,im:read,im:write,im:history
```

### Redirect URI
```
Development: http://localhost:8000/api/v1/integrations/oauth/callback
Production:  https://yourdomain.com/api/v1/integrations/oauth/callback
```

---

## 🧪 Testing Commands

### Start Installation
```bash
curl -X POST http://localhost:8000/api/v1/integrations/install/ \
  -H "Authorization: Bearer YOUR_JWT_TOKEN" \
  -H "Content-Type: application/json" \
  -d '{"integration_type_id": "INTEGRATION_TYPE_UUID"}'
```

### Check Progress
```bash
curl http://localhost:8000/api/v1/integrations/install/SESSION_ID/progress/ \
  -H "Authorization: Bearer YOUR_JWT_TOKEN"
```

### List Installed Integrations
```bash
curl http://localhost:8000/api/v1/integrations/installed/ \
  -H "Authorization: Bearer YOUR_JWT_TOKEN"
```

### Uninstall Integration
```bash
curl -X DELETE http://localhost:8000/api/v1/integrations/INTEGRATION_ID/uninstall/ \
  -H "Authorization: Bearer YOUR_JWT_TOKEN"
```

---

## 🔍 Verification Queries

### Check Integration Types
```sql
SELECT id, type, name, is_active, category 
FROM integration_types 
WHERE type IN ('gmail', 'slack');
```

### Check Integrations
```sql
SELECT i.id, u.email, it.name, i.is_active, i.created_at
FROM integrations i
JOIN auth_user u ON i.user_id = u.id
JOIN integration_types it ON i.integration_type_id = it.id
ORDER BY i.created_at DESC;
```

### Check Installation Sessions
```sql
SELECT id, status, progress, error_message, created_at
FROM installation_sessions
ORDER BY created_at DESC
LIMIT 10;
```

---

## 🐛 Common Issues

### Issue: `redirect_uri_mismatch`
**Fix**: Verify redirect URI in provider console matches exactly (including protocol and trailing slash)

### Issue: `invalid_client`
**Fix**: Check client_id and client_secret are correct, no extra spaces

### Issue: `Token exchange failed`
**Fix**: Check token_url is correct, verify network connectivity

### Issue: `Encryption failed`
**Fix**: Verify TOKEN_ENCRYPTION_KEY is set in .env (32 bytes, base64)

### Issue: `Rate limit exceeded`
**Fix**: Wait 1 hour or clear cache: `python manage.py shell` → `from django.core.cache import cache; cache.clear()`

---

## 📚 Documentation

- **Full Setup Guide**: `docs/oauth-setup-guide.md`
- **Test Results Template**: `docs/oauth-test-results.md`
- **Requirements**: `.kiro/specs/dynamic-app-marketplace/requirements.md`
- **Design**: `.kiro/specs/dynamic-app-marketplace/design.md`

---

## 🔐 Security Checklist

- [ ] TOKEN_ENCRYPTION_KEY is set and secure (32 bytes)
- [ ] Client secrets are never logged
- [ ] Redirect URIs use HTTPS (production)
- [ ] OAuth state validation is working (CSRF protection)
- [ ] Rate limiting is enabled
- [ ] Tokens are encrypted in database
- [ ] Audit logging is enabled

---

## 📞 Support

**Issues**: Check Django logs at `logs/django.log`  
**Provider Docs**:
- [Google OAuth 2.0](https://developers.google.com/identity/protocols/oauth2)
- [Slack OAuth](https://api.slack.com/authentication/oauth-v2)

**Code References**:
- Installation Service: `apps/automation/services/installation.py`
- OAuth Client: `apps/automation/utils/oauth_client.py`
- Models: `apps/automation/models.py`
