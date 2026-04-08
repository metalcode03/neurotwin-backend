# User Settings API Documentation

## Overview

The User Settings API provides endpoints for managing user preferences, including Brain mode selection for AI request routing.

## Endpoints

### GET /api/v1/users/settings

Retrieve current user settings.

**Authentication**: Required (JWT)

**Response**:
```json
{
  "success": true,
  "data": {
    "brain_mode": "brain",
    "cognitive_blend": 50,
    "notification_preferences": {},
    "subscription_tier": "free"
  }
}
```

**Fields**:
- `brain_mode`: User's preferred Brain mode (brain, brain_pro, brain_gen)
- `cognitive_blend`: Cognitive blend value from Twin (0-100, read-only)
- `notification_preferences`: User notification preferences (JSON object)
- `subscription_tier`: User's subscription tier (read-only)

### PUT /api/v1/users/settings

Update user settings.

**Authentication**: Required (JWT)

**Request Body**:
```json
{
  "brain_mode": "brain_pro"
}
```

**Response (Success)**:
```json
{
  "success": true,
  "message": "Settings updated successfully",
  "data": {
    "brain_mode": "brain_pro",
    "cognitive_blend": 50,
    "notification_preferences": {},
    "subscription_tier": "pro"
  }
}
```

**Response (Error - Brain Mode Restricted)**:
```json
{
  "success": false,
  "error": {
    "code": "BRAIN_MODE_RESTRICTED",
    "message": "Brain mode Brain Pro requires PRO tier or higher. Your current tier is free."
  }
}
```

**Status Codes**:
- `200 OK`: Settings updated successfully
- `400 Bad Request`: Invalid input
- `403 Forbidden`: Brain mode not allowed for user's subscription tier

## Brain Mode Tier Requirements

| Brain Mode | Required Tier | Description |
|------------|---------------|-------------|
| brain | FREE, PRO, TWIN+, EXECUTIVE | Balanced - Fast and efficient |
| brain_pro | PRO, TWIN+, EXECUTIVE | Advanced - Higher reasoning quality |
| brain_gen | EXECUTIVE | Genius - Maximum intelligence |

## Database Schema

### UserSettings Model

```python
class UserSettings(models.Model):
    id = models.UUIDField(primary_key=True)
    user = models.OneToOneField(User, related_name='settings')
    brain_mode = models.CharField(max_length=20, default='brain')
    notification_preferences = models.JSONField(default=dict)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
```

## Implementation Details

### Files Created/Modified

1. **apps/authentication/user_settings_models.py** - UserSettings model and BrainMode enum
2. **apps/authentication/settings_service.py** - Business logic for settings management
3. **apps/authentication/serializers.py** - Added UserSettingsSerializer and UpdateUserSettingsSerializer
4. **apps/authentication/views.py** - Added UserSettingsView with GET and PUT methods
5. **apps/authentication/urls_users.py** - URL routing for user settings endpoints
6. **apps/authentication/migrations/0003_add_user_settings.py** - Database migration
7. **core/api/urls.py** - Added users/ path to v1 API patterns

### Service Layer

The `UserSettingsService` provides the following methods:

- `get_or_create_settings(user)`: Get or create user settings
- `get_settings_data(user)`: Get settings with additional context (cognitive_blend, subscription_tier)
- `update_brain_mode(user, brain_mode)`: Update brain_mode with tier validation
- `validate_brain_mode_access(user, brain_mode)`: Check if user has access to brain_mode

### Validation

Brain mode selection is validated against the user's subscription tier:
- Validation occurs in both the serializer and service layer
- Returns 403 Forbidden if user attempts to select a restricted brain mode
- Provides clear error messages indicating required tier

## Usage Examples

### Frontend Integration

```typescript
// Get user settings
const response = await fetch('/api/v1/users/settings', {
  headers: {
    'Authorization': `Bearer ${accessToken}`
  }
});
const { data } = await response.json();
console.log(data.brain_mode); // "brain"

// Update brain mode
const updateResponse = await fetch('/api/v1/users/settings', {
  method: 'PUT',
  headers: {
    'Authorization': `Bearer ${accessToken}`,
    'Content-Type': 'application/json'
  },
  body: JSON.stringify({ brain_mode: 'brain_pro' })
});

if (updateResponse.status === 403) {
  // Handle tier restriction
  const error = await updateResponse.json();
  console.error(error.error.message);
}
```

## Requirements Satisfied

- **Requirement 5.8**: Brain mode preference storage and retrieval
- **Requirement 15.7**: GET /api/v1/users/settings endpoint
- **Requirement 15.8**: PUT /api/v1/users/settings endpoint
- **Requirement 15.9**: Brain mode validation against subscription tier
- **Requirement 15.10**: Save preference and return updated settings
