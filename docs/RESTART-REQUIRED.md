# ⚠️ RESTART REQUIRED - Environment Variable Changed

## Critical: Frontend Must Be Restarted!

The `.env.local` file was updated with the correct API base URL. Next.js only reads environment variables at startup, so you **MUST restart the development server** for changes to take effect.

## Quick Fix Steps

### 1. Stop Frontend Server
```bash
# In the terminal running the frontend, press:
Ctrl + C
```

### 2. Restart Frontend Server
```bash
cd neuro-frontend
npm run dev
```

### 3. Clear Browser Cache
```bash
# In browser console (F12), run:
localStorage.clear();
location.reload();
```

### 4. Test Login
- Go to `http://localhost:3000/auth/login`
- Login with your credentials
- Check Network tab - URLs should now include `/api/v1`

## What Changed

### Before (404 errors):
```
NEXT_PUBLIC_API_URL=http://localhost:8000
↓
API calls: http://localhost:8000/twin/ ❌ 404
```

### After (working):
```
NEXT_PUBLIC_API_URL=http://localhost:8000/api/v1
↓
API calls: http://localhost:8000/api/v1/twin/ ✅ 200
```

## Verification

After restarting, check the Network tab (F12):

✅ **Correct URLs:**
- `http://localhost:8000/api/v1/twin/`
- `http://localhost:8000/api/v1/voice/`
- `http://localhost:8000/api/v1/subscription/`

❌ **Wrong URLs (if not restarted):**
- `http://localhost:8000/twin/`
- `http://localhost:8000/voice/`
- `http://localhost:8000/subscription/`

## Still Having Issues?

If you still see 404 errors after restarting:

1. **Verify environment variable loaded:**
```javascript
// In browser console
console.log(process.env.NEXT_PUBLIC_API_URL);
// Should show: undefined (it's only available server-side during build)
```

2. **Check the actual requests in Network tab:**
- Open DevTools (F12)
- Go to Network tab
- Login and watch the requests
- URLs should include `/api/v1`

3. **Hard refresh browser:**
```
Windows/Linux: Ctrl + Shift + R
Mac: Cmd + Shift + R
```

4. **Verify .env.local location:**
```bash
# Should be here:
neuro-frontend/.env.local

# NOT here:
neuro-frontend/src/.env.local
```

## Summary

✅ Fixed: Missing `/api/v1` in API base URL
✅ Fixed: React setState during render error
⚠️ **Action Required:** Restart frontend server!
