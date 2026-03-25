# API Endpoint Mapping - Frontend to Backend

## Issues Found and Fixed

### 1. URL Path Mismatches (404 Errors)

#### Fixed in Frontend API Client:
- ✅ `/twin` → `/twin/` (added trailing slash)
- ✅ `/twin/model` → `/twin/` (model update uses main twin endpoint)
- ✅ `/subscription` → `/subscription/` (added trailing slash)
- ✅ `/voice` → `/voice/` (added trailing slash)
- ✅ `/voice/call/{id}` → `/voice/calls/{id}` (fixed path)
- ✅ `/memory/*` → `/csm/profile` (memory uses CSM endpoints)

#### Still Need Backend Implementation:
- ⚠️ `/actions/{id}/approve` - Backend only has `/actions/{id}/undo`
- ⚠️ `/actions/{id}/reject` - Backend only has `/actions/{id}/undo`
- ⚠️ `/csm/memories` - Memory list endpoint not implemented
- ⚠️ `/csm/memories/{id}` - Memory detail endpoint not implemented
- ⚠️ `/subscription/features/{tier}` - Tier features endpoint not implemented

### 2. CORS Configuration (401 Errors)

#### Backend CORS Settings (Already Configured):
```python
CORS_ALLOWED_ORIGINS = [
    'http://localhost:3000',      # Next.js dev server
    'http://localhost:5673',      # Alternative port
    'http://127.0.0.1:3000',
    'http://127.0.0.1:5673',
]
CORS_ALLOW_CREDENTIALS = True
```

#### JWT Authentication:
- Frontend stores token in `localStorage` as `auth_token`
- Token sent as `Authorization: Bearer {token}` header
- Backend uses `rest_framework_simplejwt.authentication.JWTAuthentication`

### 3. Complete Endpoint Mapping

| Frontend Call | Backend URL | Status |
|--------------|-------------|--------|
| `api.twin.get()` | `GET /api/v1/twin/` | ✅ Working |
| `api.twin.updateBlend()` | `PATCH /api/v1/twin/blend` | ✅ Working |
| `api.twin.updateModel()` | `PATCH /api/v1/twin/` | ✅ Working |
| `api.killSwitch.activate()` | `POST /api/v1/kill-switch/activate` | ✅ Working |
| `api.killSwitch.deactivate()` | `POST /api/v1/kill-switch/deactivate` | ✅ Working |
| `api.apps.list()` | `GET /api/v1/integrations/` | ✅ Working |
| `api.apps.install()` | `POST /api/v1/integrations/{type}/connect` | ✅ Working |
| `api.apps.configure()` | `PATCH /api/v1/integrations/{id}/permissions` | ✅ Working |
| `api.apps.disconnect()` | `DELETE /api/v1/integrations/{id}` | ✅ Working |
| `api.activity.list()` | `GET /api/v1/audit?page={n}` | ✅ Working |
| `api.activity.approve()` | `POST /api/v1/actions/{id}/approve` | ⚠️ Not Implemented |
| `api.activity.reject()` | `POST /api/v1/actions/{id}/reject` | ⚠️ Not Implemented |
| `api.memory.list()` | `GET /api/v1/csm/memories` | ⚠️ Not Implemented |
| `api.memory.get()` | `GET /api/v1/csm/memories/{id}` | ⚠️ Not Implemented |
| `api.memory.getPersonalityProfile()` | `GET /api/v1/csm/profile` | ✅ Working |
| `api.voice.getProfile()` | `GET /api/v1/voice/` | ✅ Working |
| `api.voice.getCalls()` | `GET /api/v1/voice/calls` | ✅ Working |
| `api.voice.approveSession()` | `POST /api/v1/voice/approve-session` | ✅ Working |
| `api.voice.terminateCall()` | `DELETE /api/v1/voice/calls/{id}` | ✅ Working |
| `api.security.getAuditLog()` | `GET /api/v1/audit` | ✅ Working |
| `api.security.getPermissions()` | `GET /api/v1/permissions/` | ✅ Working |
| `api.security.updatePermissions()` | `PATCH /api/v1/permissions/` | ✅ Working |
| `api.subscription.get()` | `GET /api/v1/subscription/` | ✅ Working |
| `api.subscription.upgrade()` | `POST /api/v1/subscription/upgrade` | ✅ Working |
| `api.subscription.getTierFeatures()` | `GET /api/v1/subscription/features/{tier}` | ⚠️ Not Implemented |

## Authentication Flow

### Login Process:
1. User submits credentials to `/api/v1/auth/login`
2. Backend returns `{ access_token, refresh_token }`
3. Frontend stores `access_token` in `localStorage` as `auth_token`
4. All subsequent requests include `Authorization: Bearer {access_token}` header

### Token Refresh:
1. When access token expires (401 response)
2. Frontend calls `/api/v1/auth/refresh` with refresh token
3. Backend returns new access token
4. Frontend updates stored token

### Current Issue:
If you're getting 401 errors, check:
1. Is the user logged in? Check `localStorage.getItem('auth_token')`
2. Is the token valid? Try refreshing or re-logging in
3. Is CORS configured? Check browser console for CORS errors
4. Is the backend running? Check `http://localhost:8000/api/v1/`

## Testing Endpoints

### Using curl:
```bash
# Get access token
curl -X POST http://localhost:8000/api/v1/auth/login \
  -H "Content-Type: application/json" \
  -d '{"email":"user@example.com","password":"password"}'

# Use token
curl http://localhost:8000/api/v1/twin/ \
  -H "Authorization: Bearer YOUR_ACCESS_TOKEN"
```

### Using browser console:
```javascript
// Check if token exists
console.log(localStorage.getItem('auth_token'));

// Test API call
fetch('http://localhost:8000/api/v1/twin/', {
  headers: {
    'Authorization': `Bearer ${localStorage.getItem('auth_token')}`,
    'Content-Type': 'application/json'
  }
}).then(r => r.json()).then(console.log);
```

## Next Steps

### Backend Implementation Needed:
1. Add approve/reject endpoints to `/apps/safety/urls_actions.py`
2. Add memory list/detail endpoints to CSM or create separate memory app
3. Add tier features endpoint to subscription app
4. Ensure all endpoints have trailing slashes for consistency

### Frontend Updates:
- ✅ Fixed URL paths to match backend
- ✅ Added trailing slashes where needed
- ✅ Updated memory endpoints to use CSM
- ✅ Fixed voice call endpoint paths
