# Login Page Fixes - React setState & API URL Issues

## Issues Fixed

### Issue 1: Missing `/api/v1` in API Base URL ❌ → ✅

**Problem:**
- Frontend was calling `http://localhost:8000/twin/` instead of `http://localhost:8000/api/v1/twin/`
- All API calls (except auth) were getting 404 errors
- Environment variable was missing the `/api/v1` path

**Root Cause:**
```bash
# neuro-frontend/.env.local (WRONG)
NEXT_PUBLIC_API_URL=http://localhost:8000
```

**Fix Applied:**
```bash
# neuro-frontend/.env.local (CORRECT)
NEXT_PUBLIC_API_URL=http://localhost:8000/api/v1
```

**Why This Happened:**
The API client in `src/lib/api.ts` uses `process.env.NEXT_PUBLIC_API_URL` as the base URL and appends endpoint paths like `/twin/`, `/voice/`, etc. Without `/api/v1` in the base URL, requests were going to:
- ❌ `http://localhost:8000/twin/` (404 Not Found)
- ✅ `http://localhost:8000/api/v1/twin/` (200 OK)

### Issue 2: React setState During Render ❌ → ✅

**Problem:**
```
Cannot update a component (`Router`) while rendering a different component (`LoginPage`). 
To locate the bad setState() call inside `LoginPage`, follow the stack trace...
```

**Root Cause:**
The login page was calling `router.push()` during the render phase:

```typescript
// WRONG - setState during render
export default function LoginPage() {
  // ... component code ...
  
  if (isAuthenticated && !authLoading) {
    router.push('/dashboard/twin');  // ❌ Causes React error
    return null;
  }
  
  return <AuthCard>...</AuthCard>;
}
```

**Why This Is Wrong:**
- React's render phase should be pure (no side effects)
- `router.push()` triggers a state update in the Router component
- Calling it during render violates React's rules
- This causes the "Cannot update component while rendering" error

**Fix Applied:**
Moved the redirect logic into a `useEffect` hook:

```typescript
// CORRECT - setState in effect
export default function LoginPage() {
  // ... component code ...
  
  // Redirect authenticated users to dashboard using useEffect
  useEffect(() => {
    if (isAuthenticated && !authLoading) {
      router.push('/dashboard/twin');  // ✅ Safe in effect
    }
  }, [isAuthenticated, authLoading, router]);
  
  return <AuthCard>...</AuthCard>;
}
```

**Why This Works:**
- `useEffect` runs after render (during commit phase)
- Side effects like navigation are safe in effects
- Dependencies array ensures it only runs when auth state changes
- No more React warnings!

## Files Modified

### 1. `neuro-frontend/.env.local`
```diff
- NEXT_PUBLIC_API_URL=http://localhost:8000
+ NEXT_PUBLIC_API_URL=http://localhost:8000/api/v1
```

### 2. `neuro-frontend/src/app/auth/login/page.tsx`
```diff
- import { useState } from 'react';
+ import React, { useState, useEffect } from 'react';

- // Redirect authenticated users to dashboard
- if (isAuthenticated && !authLoading) {
-   router.push('/dashboard/twin');
-   return null;
- }
+ // Redirect authenticated users to dashboard using useEffect
+ useEffect(() => {
+   if (isAuthenticated && !authLoading) {
+     router.push('/dashboard/twin');
+   }
+ }, [isAuthenticated, authLoading, router]);
```

## Testing the Fixes

### 1. Restart Frontend Development Server

**IMPORTANT:** Next.js needs to be restarted to pick up the `.env.local` changes!

```bash
# Stop the frontend (Ctrl+C)
cd neuro-frontend

# Restart the dev server
npm run dev
```

### 2. Clear Browser Cache

```javascript
// Open browser console (F12) and run:
localStorage.clear();
sessionStorage.clear();
location.reload();
```

### 3. Test Login Flow

1. Navigate to `http://localhost:3000/auth/login`
2. Enter credentials and submit
3. Check browser console - should see no React errors
4. Check Network tab - API calls should go to `http://localhost:8000/api/v1/*`

### 4. Verify API Calls

Open Network tab (F12) and check the request URLs:

**Before Fix (404 errors):**
```
❌ GET http://localhost:8000/twin/ → 404 Not Found
❌ GET http://localhost:8000/voice/ → 404 Not Found
❌ GET http://localhost:8000/subscription/ → 404 Not Found
```

**After Fix (200 success):**
```
✅ GET http://localhost:8000/api/v1/twin/ → 200 OK
✅ GET http://localhost:8000/api/v1/voice/ → 200 OK
✅ GET http://localhost:8000/api/v1/subscription/ → 200 OK
```

## Common Issues After Fix

### Issue: Still Getting 404 Errors

**Cause:** Frontend not restarted after `.env.local` change

**Solution:**
```bash
# Stop frontend (Ctrl+C)
# Start again
npm run dev
```

### Issue: Still Seeing React Warning

**Cause:** Browser cached old JavaScript bundle

**Solution:**
```bash
# Hard refresh in browser
# Windows/Linux: Ctrl + Shift + R
# Mac: Cmd + Shift + R

# Or clear cache
localStorage.clear();
location.reload();
```

### Issue: Environment Variable Not Loading

**Cause:** `.env.local` file not in correct location

**Solution:**
```bash
# Verify file location
ls neuro-frontend/.env.local

# Should be in the root of neuro-frontend directory
# NOT in neuro-frontend/src/.env.local
```

## Understanding the Fixes

### Why `/api/v1` Must Be in Base URL

The API client constructs URLs like this:

```typescript
// In src/lib/api.ts
const API_BASE = process.env.NEXT_PUBLIC_API_URL || 'http://localhost:8000/api/v1';

async function request<T>(endpoint: string, ...) {
  const response = await fetch(`${API_BASE}${endpoint}`, ...);
  //                              ↑         ↑
  //                         Base URL   Endpoint
}

// Example calls:
api.twin.get()  // → fetch('http://localhost:8000/api/v1' + '/twin/')
api.voice.get() // → fetch('http://localhost:8000/api/v1' + '/voice/')
```

Without `/api/v1` in the base URL:
```typescript
// WRONG
API_BASE = 'http://localhost:8000'
api.twin.get() // → 'http://localhost:8000/twin/' ❌ 404
```

With `/api/v1` in the base URL:
```typescript
// CORRECT
API_BASE = 'http://localhost:8000/api/v1'
api.twin.get() // → 'http://localhost:8000/api/v1/twin/' ✅ 200
```

### Why useEffect for Navigation

React has two phases:
1. **Render Phase** (pure, no side effects)
   - Calculate what should be displayed
   - Must be pure functions
   - Can be called multiple times

2. **Commit Phase** (side effects allowed)
   - Update the DOM
   - Run effects (useEffect)
   - Safe for navigation, API calls, etc.

```typescript
// ❌ WRONG - Side effect during render
function Component() {
  if (condition) {
    router.push('/somewhere'); // Causes error!
  }
  return <div>...</div>;
}

// ✅ CORRECT - Side effect in useEffect
function Component() {
  useEffect(() => {
    if (condition) {
      router.push('/somewhere'); // Safe!
    }
  }, [condition]);
  
  return <div>...</div>;
}
```

## Verification Checklist

After applying fixes, verify:

- [ ] Frontend restarted (`npm run dev`)
- [ ] Browser cache cleared
- [ ] Can login without React errors
- [ ] Network tab shows requests to `/api/v1/*`
- [ ] All API calls return 200 (not 404)
- [ ] No console errors about setState
- [ ] Redirect to dashboard works after login

## Related Documentation

- **API Endpoint Mapping:** `docs/api-endpoint-mapping.md`
- **Troubleshooting Guide:** `docs/troubleshooting-401-404.md`
- **Quick Reference:** `docs/quick-fix-reference.md`
