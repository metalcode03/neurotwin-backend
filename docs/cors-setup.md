# CORS Configuration

## Overview

Cross-Origin Resource Sharing (CORS) is configured to allow the Next.js frontend to communicate with the Django backend API.

## Configuration

### Development Environment

The following origins are allowed in development mode (DEBUG=True):

- `http://localhost:3000` - Primary Next.js dev server
- `http://localhost:5673` - Alternative frontend port
- `http://127.0.0.1:3000` - Localhost alternative
- `http://127.0.0.1:5673` - Localhost alternative

### Production Environment

When deployed (DEBUG=False), the following origin is added:

- `https://neurotwinai.com` - Production domain

## Settings

### CORS_ALLOW_CREDENTIALS
Set to `True` to allow cookies and authorization headers to be sent with requests.

### CORS_ALLOW_HEADERS
Allowed headers include:
- `authorization` - For JWT tokens
- `content-type` - For JSON payloads
- `x-csrftoken` - For CSRF protection
- Standard headers (accept, origin, user-agent, etc.)

### CORS_ALLOW_METHODS
Allowed HTTP methods:
- GET, POST, PUT, PATCH, DELETE, OPTIONS

### CORS_PREFLIGHT_MAX_AGE
Preflight requests are cached for 1 hour (3600 seconds) to reduce overhead.

## Middleware Order

The CORS middleware is placed early in the middleware stack:

```python
MIDDLEWARE = [
    'django.middleware.security.SecurityMiddleware',
    'corsheaders.middleware.CorsMiddleware',  # Must be before CommonMiddleware
    'django.contrib.sessions.middleware.SessionMiddleware',
    # ... other middleware
]
```

## Testing CORS

To verify CORS is working:

1. Start the Django backend:
   ```bash
   uv run python manage.py runserver
   ```

2. Start the Next.js frontend:
   ```bash
   cd neuro-frontend
   npm run dev
   ```

3. Open browser console and check for CORS errors when making API requests.

## Troubleshooting

### Still seeing CORS errors?

1. **Check the origin**: Ensure your frontend is running on one of the allowed origins
2. **Restart the backend**: Changes to settings.py require a server restart
3. **Check middleware order**: CORS middleware must be before CommonMiddleware
4. **Verify credentials**: If sending cookies/auth headers, ensure CORS_ALLOW_CREDENTIALS=True

### Adding new origins

To add a new development port or domain:

1. Edit `neurotwin/settings.py`
2. Add the origin to `CORS_ALLOWED_ORIGINS` list
3. Restart the Django server

## Security Notes

- In production, only add trusted domains to CORS_ALLOWED_ORIGINS
- Never use `CORS_ALLOW_ALL_ORIGINS = True` in production
- Keep CORS_ALLOW_CREDENTIALS = True only if needed for authentication
- Regularly review and update allowed origins
