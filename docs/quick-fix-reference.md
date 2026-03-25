# Quick Fix Reference Card

## 🚨 Getting 401 Unauthorized?

### Check 1: Are you logged in?
```javascript
// Browser console (F12)
localStorage.getItem('auth_token')
// null = not logged in → Go to /login
// string = logged in → Check next step
```

### Check 2: Is backend running?
```bash
curl http://localhost:8000/api/v1/
# Connection refused? → Start backend:
uv run python manage.py runserver
```

### Check 3: Is token expired?
```javascript
// Clear and re-login
localStorage.removeItem('auth_token');
// Then navigate to /login
```

## 🚨 Getting 404 Not Found?

### Quick Reference Table:
| ❌ Wrong | ✅ Correct |
|---------|-----------|
| `/twin` | `/twin/` |
| `/subscription` | `/subscription/` |
| `/voice` | `/voice/` |
| `/memory/list` | `/csm/profile` |
| `/voice/call/123` | `/voice/calls/123` |

### Check: Is the endpoint implemented?
See `docs/api-endpoint-mapping.md` for complete list.

## 🚨 CORS Errors?

### Check 1: Frontend URL in CORS settings?
```python
# neurotwin/settings.py
CORS_ALLOWED_ORIGINS = [
    'http://localhost:3000',  # ← Must match your frontend
]
```

### Check 2: Restart backend after CORS changes
```bash
# Ctrl+C to stop, then:
uv run python manage.py runserver
```

## 🔧 Quick Reset (Nuclear Option)

```bash
# 1. Stop everything (Ctrl+C both terminals)

# 2. Clear browser storage
# DevTools (F12) → Application → Clear site data

# 3. Restart backend
cd neurotwin
uv run python manage.py runserver

# 4. Restart frontend  
cd neuro-frontend
npm run dev

# 5. Login again at http://localhost:3000/login
```

## 📋 Startup Checklist

```bash
# Terminal 1: Backend
cd neurotwin
uv run python manage.py runserver
# Wait for: "Starting development server at http://127.0.0.1:8000/"

# Terminal 2: Frontend
cd neuro-frontend
npm run dev
# Wait for: "ready - started server on 0.0.0.0:3000"

# Browser: http://localhost:3000
# Login with your credentials
```

## 🧪 Quick Test Commands

```bash
# Test backend is alive
curl http://localhost:8000/api/v1/

# Test login
curl -X POST http://localhost:8000/api/v1/auth/login \
  -H "Content-Type: application/json" \
  -d '{"email":"test@example.com","password":"pass123"}'

# Test authenticated endpoint (replace TOKEN)
curl http://localhost:8000/api/v1/twin/ \
  -H "Authorization: Bearer YOUR_TOKEN_HERE"
```

## 📚 Full Documentation

- **Complete endpoint mapping:** `docs/api-endpoint-mapping.md`
- **Detailed troubleshooting:** `docs/troubleshooting-401-404.md`
- **Implementation summary:** `docs/api-fixes-summary.md`

## 🆘 Still Stuck?

1. Check Django terminal for error messages
2. Check browser console (F12) for error details
3. Check Network tab in DevTools for request/response
4. Verify environment variables in `.env` and `.env.local`
