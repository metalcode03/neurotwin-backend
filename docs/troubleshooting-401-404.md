# Troubleshooting 401 & 404 Errors

## Quick Diagnosis

### Check if Backend is Running
```bash
# Test if backend is accessible
curl http://localhost:8000/api/v1/

# Expected: Should return API response or redirect
# If connection refused: Backend is not running
```

### Check if User is Authenticated
```javascript
// In browser console (F12)
console.log(localStorage.getItem('auth_token'));

// If null: User is not logged in
// If exists: Token might be expired
```

### Check CORS in Browser Console
Look for errors like:
- `Access to fetch at 'http://localhost:8000' from origin 'http://localhost:3000' has been blocked by CORS policy`
- `No 'Access-Control-Allow-Origin' header is present`

## Common Issues & Solutions

### Issue 1: 401 Unauthorized - Not Logged In

**Symptoms:**
- All API calls return 401
- `localStorage.getItem('auth_token')` returns `null`

**Solution:**
1. Navigate to login page
2. Enter credentials
3. Verify token is stored after login

**Test:**
```javascript
// After login, check token
console.log(localStorage.getItem('auth_token'));
// Should show JWT token string
```

### Issue 2: 401 Unauthorized - Expired Token

**Symptoms:**
- Was working, now returns 401
- Token exists in localStorage
- Backend logs show "Token is invalid or expired"

**Solution:**
1. Clear expired token: `localStorage.removeItem('auth_token')`
2. Log in again
3. Or implement token refresh logic

**Token Refresh (if implemented):**
```javascript
// Call refresh endpoint
const refreshToken = localStorage.getItem('refresh_token');
const response = await fetch('http://localhost:8000/api/v1/auth/refresh', {
  method: 'POST',
  headers: { 'Content-Type': 'application/json' },
  body: JSON.stringify({ refresh: refreshToken })
});
const { access } = await response.json();
localStorage.setItem('auth_token', access);
```

### Issue 3: 404 Not Found - Wrong URL Path

**Symptoms:**
- Specific endpoints return 404
- Other endpoints work fine
- Backend logs show "Not Found: /api/v1/wrong-path"

**Solution:**
Check the endpoint mapping in `docs/api-endpoint-mapping.md`

**Common mistakes:**
- Missing trailing slash: `/twin` → `/twin/`
- Wrong path: `/memory` → `/csm/profile`
- Wrong method: GET instead of POST

### Issue 4: CORS Errors

**Symptoms:**
- Browser console shows CORS error
- Network tab shows request was blocked
- Preflight OPTIONS request fails

**Solution:**

1. **Verify backend CORS settings** (`neurotwin/settings.py`):
```python
CORS_ALLOWED_ORIGINS = [
    'http://localhost:3000',
    'http://127.0.0.1:3000',
]
CORS_ALLOW_CREDENTIALS = True
```

2. **Verify frontend is running on allowed origin:**
```bash
# Check frontend URL
echo $NEXT_PUBLIC_API_URL
# Should be http://localhost:8000/api/v1
```

3. **Restart backend after CORS changes:**
```bash
# Stop backend (Ctrl+C)
# Start again
uv run python manage.py runserver
```

### Issue 5: Backend Not Running

**Symptoms:**
- All requests fail with network error
- `curl http://localhost:8000` fails
- "Failed to fetch" or "Network request failed"

**Solution:**
```bash
# Start Django backend
cd /path/to/neurotwin
uv run python manage.py runserver

# Or if using main.py
uv run python main.py

# Verify it's running
curl http://localhost:8000/admin/
# Should return HTML or redirect
```

### Issue 6: Wrong Port

**Symptoms:**
- Frontend connects to wrong backend port
- Mixed localhost:8000 and localhost:3000 errors

**Solution:**

1. **Check frontend environment variables:**
```bash
# In neuro-frontend/.env.local
NEXT_PUBLIC_API_URL=http://localhost:8000/api/v1
```

2. **Verify backend port:**
```bash
# Default Django port is 8000
uv run python manage.py runserver
# Or specify port
uv run python manage.py runserver 8000
```

3. **Check frontend API client:**
```typescript
// In neuro-frontend/src/lib/api.ts
const API_BASE = process.env.NEXT_PUBLIC_API_URL || 'http://localhost:8000/api/v1';
```

## Testing Checklist

### 1. Backend Health Check
```bash
# Test backend is running
curl http://localhost:8000/api/v1/

# Test authentication endpoint
curl http://localhost:8000/api/v1/auth/login \
  -X POST \
  -H "Content-Type: application/json" \
  -d '{"email":"test@example.com","password":"testpass"}'
```

### 2. Frontend Environment
```bash
# Check environment variables
cat neuro-frontend/.env.local

# Should contain:
# NEXT_PUBLIC_API_URL=http://localhost:8000/api/v1
```

### 3. Browser Console Tests
```javascript
// Test 1: Check token
console.log('Token:', localStorage.getItem('auth_token'));

// Test 2: Test API call
fetch('http://localhost:8000/api/v1/twin/', {
  headers: {
    'Authorization': `Bearer ${localStorage.getItem('auth_token')}`,
    'Content-Type': 'application/json'
  }
})
.then(r => r.json())
.then(data => console.log('Success:', data))
.catch(err => console.error('Error:', err));

// Test 3: Check CORS
fetch('http://localhost:8000/api/v1/twin/', {
  method: 'OPTIONS',
  headers: {
    'Origin': 'http://localhost:3000',
    'Access-Control-Request-Method': 'GET',
    'Access-Control-Request-Headers': 'authorization,content-type'
  }
})
.then(r => console.log('CORS OK:', r.headers.get('Access-Control-Allow-Origin')))
.catch(err => console.error('CORS Error:', err));
```

### 4. Network Tab Analysis

Open browser DevTools (F12) → Network tab:

**For 401 errors, check:**
- Request Headers: Is `Authorization: Bearer ...` present?
- Response: What does the error message say?
- Status: 401 Unauthorized

**For 404 errors, check:**
- Request URL: Is the path correct?
- Method: GET, POST, PATCH, DELETE?
- Response: "Not Found" or "Method Not Allowed"?

**For CORS errors, check:**
- Preflight OPTIONS request: Did it succeed?
- Response Headers: `Access-Control-Allow-Origin` present?
- Request Headers: `Origin` matches allowed origins?

## Step-by-Step Debugging

### Step 1: Verify Backend is Running
```bash
curl http://localhost:8000/admin/
# Should return HTML or redirect, not "Connection refused"
```

### Step 2: Test Authentication
```bash
# Login and get token
curl -X POST http://localhost:8000/api/v1/auth/login \
  -H "Content-Type: application/json" \
  -d '{"email":"your@email.com","password":"yourpassword"}' \
  -v

# Look for:
# < HTTP/1.1 200 OK
# {"access_token":"...","refresh_token":"..."}
```

### Step 3: Test Authenticated Endpoint
```bash
# Use token from step 2
TOKEN="your_access_token_here"

curl http://localhost:8000/api/v1/twin/ \
  -H "Authorization: Bearer $TOKEN" \
  -v

# Look for:
# < HTTP/1.1 200 OK
# < Access-Control-Allow-Origin: http://localhost:3000
```

### Step 4: Check Frontend Connection
```javascript
// In browser console on http://localhost:3000
const token = localStorage.getItem('auth_token');
console.log('Token exists:', !!token);

if (token) {
  fetch('http://localhost:8000/api/v1/twin/', {
    headers: {
      'Authorization': `Bearer ${token}`,
      'Content-Type': 'application/json'
    }
  })
  .then(r => {
    console.log('Status:', r.status);
    return r.json();
  })
  .then(data => console.log('Data:', data))
  .catch(err => console.error('Error:', err));
}
```

## Quick Fixes

### Reset Everything
```bash
# 1. Stop both servers (Ctrl+C)

# 2. Clear browser data
# - Open DevTools (F12)
# - Application tab → Storage → Clear site data

# 3. Restart backend
cd neurotwin
uv run python manage.py runserver

# 4. Restart frontend
cd neuro-frontend
npm run dev

# 5. Navigate to http://localhost:3000
# 6. Login again
```

### Force Token Refresh
```javascript
// In browser console
localStorage.removeItem('auth_token');
localStorage.removeItem('refresh_token');
// Then login again
```

### Check Django Logs
```bash
# Backend terminal should show:
# [23/Jan/2026 10:30:45] "GET /api/v1/twin/ HTTP/1.1" 200 1234
# [23/Jan/2026 10:30:46] "GET /api/v1/wrong/ HTTP/1.1" 404 567

# Look for:
# - 401: Authentication issue
# - 404: Wrong URL path
# - 500: Server error (check traceback)
```

## Still Having Issues?

1. Check `docs/api-endpoint-mapping.md` for correct endpoint paths
2. Verify CORS settings in `neurotwin/settings.py`
3. Check browser console for detailed error messages
4. Check Django terminal for backend errors
5. Test with curl to isolate frontend vs backend issues
