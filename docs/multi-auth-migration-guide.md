# Multi-Auth Integration System: Migration Guide

## Overview

This guide helps you migrate existing OAuth integrations to the new Multi-Auth Integration System. The refactoring introduces support for multiple authentication strategies (OAuth, Meta Business, API Key) while maintaining full backward compatibility with existing OAuth integrations.

## What Changed

### Database Schema Changes

#### 1. `oauth_config` → `auth_config` Field Rename

**Before:**
```python
class IntegrationTypeModel(models.Model):
    oauth_config = models.JSONField(default=dict)
```

**After:**
```python
class IntegrationTypeModel(models.Model):
    auth_config = models.JSONField(default=dict)  # Renamed from oauth_config
    auth_type = models.CharField(
        max_length=20,
        choices=[('oauth', 'OAuth 2.0'), ('meta', 'Meta Business'), ('api_key', 'API Key')],
        default='oauth'
    )
```

#### 2. New Meta-Specific Fields in Integration Model

```python
class Integration(models.Model):
    # Existing fields remain unchanged
    oauth_token_encrypted = models.TextField()
    refresh_token_encrypted = models.TextField(null=True)
    
    # New Meta-specific fields
    meta_business_id = models.CharField(max_length=255, null=True, db_index=True)
    meta_waba_id = models.CharField(max_length=255, null=True, db_index=True)
    meta_phone_number_id = models.CharField(max_length=255, null=True)
    meta_config = models.JSONField(default=dict)
```

#### 3. New `auth_type` Field in InstallationSession Model

```python
class InstallationSession(models.Model):
    auth_type = models.CharField(max_length=20, default='oauth')
```

### Service Layer Changes

#### 1. OAuthClient → AuthClient Rename

**Before:**
```python
from apps.automation.services.oauth_client import OAuthClient

token_data = await OAuthClient.exchange_code(...)
```

**After:**
```python
from apps.automation.services.auth_client import AuthClient

token_data = await AuthClient.exchange_oauth_code(...)
```

#### 2. InstallationService Method Renames

**Before:**
```python
# Start installation
result = InstallationService.start_installation(user, integration_type_id)
auth_url = InstallationService.get_oauth_authorization_url(session_id)

# Complete installation
integration = await InstallationService.complete_oauth_flow(
    session_id, code, state
)
```

**After:**
```python
# Start installation (returns auth URL directly)
result = InstallationService.start_installation(user, integration_type_id)
# result contains: session_id, authorization_url, requires_redirect, auth_type

# Complete installation (renamed method)
integration = await InstallationService.complete_authentication_flow(
    session_id, code, state
)
```

## Migration Steps

### Step 1: Run Database Migrations

The migrations are designed to be zero-downtime and fully reversible.

```bash
# Apply migrations
uv run python manage.py migrate automation

# Verify migration success
uv run python manage.py showmigrations automation
```

**What the migrations do:**
1. Add `auth_type` field to `IntegrationTypeModel` (default: 'oauth')
2. Rename `oauth_config` to `auth_config` (data preserved)
3. Add Meta-specific fields to `Integration` model
4. Add `auth_type` field to `InstallationSession` model
5. Create database indexes for performance

### Step 2: Update Service Layer Code

#### Update Import Statements

```python
# OLD
from apps.automation.services.oauth_client import OAuthClient

# NEW
from apps.automation.services.auth_client import AuthClient
```

#### Update Method Calls

```python
# OLD: Exchange OAuth code
token_data = await OAuthClient.exchange_code(
    token_url=token_url,
    client_id=client_id,
    client_secret=client_secret,
    code=code,
    redirect_uri=redirect_uri
)

# NEW: Exchange OAuth code
token_data = await AuthClient.exchange_oauth_code(
    token_url=token_url,
    client_id=client_id,
    client_secret=client_secret,
    code=code,
    redirect_uri=redirect_uri
)
```

```python
# OLD: Refresh OAuth token
token_data = await OAuthClient.refresh_token(
    token_url=token_url,
    client_id=client_id,
    client_secret=client_secret,
    refresh_token=refresh_token
)

# NEW: Refresh OAuth token
token_data = await AuthClient.refresh_oauth_token(
    token_url=token_url,
    client_id=client_id,
    client_secret=client_secret,
    refresh_token=refresh_token
)
```

### Step 3: Update Model Access Patterns

#### Accessing auth_config

The system maintains backward compatibility through a property accessor:

```python
# Both of these work during transition period
integration_type.oauth_config  # Backward compatible property
integration_type.auth_config   # New field name (preferred)

# Update your code to use auth_config
# OLD
config = integration_type.oauth_config

# NEW
config = integration_type.auth_config
```

#### Accessing Integration Type Configuration

```python
# OLD: Direct access
client_id = integration_type.oauth_config['client_id']

# NEW: Use auth_config (same structure for OAuth)
client_id = integration_type.auth_config['client_id']
```

### Step 4: Update Admin Customizations

If you have custom admin code for `IntegrationTypeModel`:

```python
# OLD
class IntegrationTypeAdmin(admin.ModelAdmin):
    fields = ['name', 'oauth_config', 'is_active']

# NEW
class IntegrationTypeAdmin(admin.ModelAdmin):
    fields = ['name', 'auth_type', 'auth_config', 'is_active']
    
    def get_form(self, request, obj=None, **kwargs):
        # The new admin automatically shows different fields based on auth_type
        return super().get_form(request, obj, **kwargs)
```

### Step 5: Update API Clients

If you have frontend or API clients calling installation endpoints:

```python
# OLD: Start installation response
{
    "session_id": "uuid",
    "authorization_url": "https://..."
}

# NEW: Start installation response (OAuth)
{
    "session_id": "uuid",
    "authorization_url": "https://...",
    "requires_redirect": true,
    "requires_api_key": false,
    "auth_type": "oauth"
}
```

Update your frontend code to check `requires_redirect`:

```typescript
// OLD
const response = await startInstallation(integrationTypeId);
window.location.href = response.authorization_url;

// NEW
const response = await startInstallation(integrationTypeId);
if (response.requires_redirect) {
    window.location.href = response.authorization_url;
} else if (response.requires_api_key) {
    // Show API key input form
    showApiKeyModal(response.session_id);
}
```

## Backward Compatibility Features

### 1. Automatic auth_type Detection

All existing `IntegrationTypeModel` records automatically get `auth_type='oauth'` during migration. No manual updates needed.

### 2. oauth_config Property Accessor

The `IntegrationTypeModel` provides a backward-compatible property:

```python
@property
def oauth_config(self):
    """Backward compatibility accessor for auth_config."""
    return self.auth_config

@oauth_config.setter
def oauth_config(self, value):
    """Backward compatibility setter for auth_config."""
    self.auth_config = value
```

This means existing code using `oauth_config` continues to work without changes.

### 3. Unchanged OAuth Configuration Structure

The structure of OAuth configuration remains identical:

```json
{
    "client_id": "your-client-id",
    "client_secret_encrypted": "base64-encrypted-secret",
    "authorization_url": "https://provider.com/oauth/authorize",
    "token_url": "https://provider.com/oauth/token",
    "scopes": ["scope1", "scope2"]
}
```

### 4. Existing Integrations Continue Working

All existing `Integration` records continue to function without modification. The new Meta-specific fields are nullable and only used for Meta integrations.

## Rollback Procedure

If you need to rollback the migration:

```bash
# Rollback to previous migration
uv run python manage.py migrate automation <previous_migration_number>
```

The migrations are designed to be reversible:
- `auth_config` is renamed back to `oauth_config`
- `auth_type` field is removed
- Meta-specific fields are removed
- All data is preserved

## Testing Your Migration

### 1. Verify Existing OAuth Integrations

```python
# Test that existing integrations still work
from apps.automation.models import Integration, IntegrationTypeModel

# Check all OAuth integration types have correct auth_type
oauth_types = IntegrationTypeModel.objects.filter(auth_type='oauth')
print(f"Found {oauth_types.count()} OAuth integration types")

# Verify auth_config is accessible
for integration_type in oauth_types:
    assert 'client_id' in integration_type.auth_config
    assert integration_type.auth_type == 'oauth'
    print(f"✓ {integration_type.name} migrated successfully")
```

### 2. Test Installation Flow

```python
# Test OAuth installation still works
result = InstallationService.start_installation(user, oauth_integration_type_id)
assert result['auth_type'] == 'oauth'
assert result['requires_redirect'] is True
assert 'authorization_url' in result
```

### 3. Test Backward Compatibility

```python
# Test oauth_config property accessor
integration_type = IntegrationTypeModel.objects.first()
assert integration_type.oauth_config == integration_type.auth_config
print("✓ Backward compatibility property works")
```

## Common Migration Issues

### Issue 1: Import Errors

**Error:**
```
ImportError: cannot import name 'OAuthClient' from 'apps.automation.services.oauth_client'
```

**Solution:**
Update import to use `AuthClient`:
```python
from apps.automation.services.auth_client import AuthClient
```

### Issue 2: Missing auth_type Field

**Error:**
```
IntegrationTypeModel has no attribute 'auth_type'
```

**Solution:**
Run migrations:
```bash
uv run python manage.py migrate automation
```

### Issue 3: Method Not Found

**Error:**
```
AttributeError: 'InstallationService' object has no attribute 'get_oauth_authorization_url'
```

**Solution:**
The method was removed. Use `start_installation` which returns the authorization URL directly:
```python
# OLD
session = InstallationService.start_installation(user, type_id)
auth_url = InstallationService.get_oauth_authorization_url(session.id)

# NEW
result = InstallationService.start_installation(user, type_id)
auth_url = result['authorization_url']
```

## Performance Considerations

### Database Indexes

The migration adds indexes for performance:
- `auth_type` field (for filtering by authentication type)
- `meta_business_id` and `meta_waba_id` (for Meta integrations)
- Composite index on `(is_active, auth_type)`

### Caching

The new system includes auth_config caching:

```python
from apps.automation.utils.auth_config_cache import AuthConfigCache

# Cache auth_config for 5 minutes
config = AuthConfigCache.get_auth_config(integration_type_id)

# Invalidate cache when config changes
AuthConfigCache.invalidate(integration_type_id)
```

## Next Steps

After completing the migration:

1. **Update Documentation**: Update any internal documentation referencing `oauth_config`
2. **Update Tests**: Update test fixtures to use `auth_config`
3. **Monitor Logs**: Check authentication logs for any errors
4. **Performance Testing**: Verify query performance with new indexes

## Support

If you encounter issues during migration:

1. Check the migration logs: `uv run python manage.py showmigrations automation`
2. Review the authentication audit logs for errors
3. Test with a single integration type before migrating all
4. Keep the rollback procedure ready

## Summary

The migration to Multi-Auth Integration System is designed to be seamless:

✅ **Zero downtime** - Migrations run without service interruption  
✅ **Backward compatible** - Existing OAuth integrations continue working  
✅ **Reversible** - Full rollback capability if needed  
✅ **Data preserved** - No data loss during migration  
✅ **Performance optimized** - New indexes improve query speed  

Your existing OAuth integrations will continue to work exactly as before, while gaining the ability to add Meta and API Key integrations in the future.
